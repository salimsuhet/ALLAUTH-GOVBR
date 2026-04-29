"""
allauth_govbr.govbr.views
~~~~~~~~~~~~~~~~~~~~~~~~~
Views OAuth2 para o Gov.br com PKCE manual.

PKCE (Proof Key for Code Exchange) é OBRIGATÓRIO no Gov.br e não é
suportado nativamente pelo django-allauth 0.51.x, então é implementado
aqui via sobrescrita do método login() e de um OAuth2Client customizado.

Notas de implementação:
  - Basic Auth no token endpoint: resolvido via basic_auth = True no
    adapter; o OAuth2Client 0.51.x já suporta isso nativamente com
    requests.auth.HTTPBasicAuth.
  - PKCE (code_verifier): o OAuth2Client 0.51.x não tem token_params,
    então GovBrOAuth2Client adiciona um parâmetro code_verifier próprio.
  - URLs do adapter: propriedades avaliadas em tempo de execução para
    que alterações em settings sejam refletidas sem reiniciar o processo.
"""
import base64
import hashlib
import logging
import os
from urllib.parse import parse_qsl

import requests as _requests
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.providers.oauth2.client import OAuth2Client, OAuth2Error
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)
from allauth.utils import build_absolute_uri
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse

from .provider import GovBrProvider

logger = logging.getLogger(__name__)


def _govbr_base():
    """Retorna a URL base do SSO Gov.br lida dos settings em tempo de execução."""
    return getattr(
        settings,
        "GOVBR_SSO_BASE_URL",
        "https://sso.acesso.gov.br",
        # Homologação: GOVBR_SSO_BASE_URL = "https://sso.staging.acesso.gov.br"
    )


# ---------------------------------------------------------------------------
# Cliente OAuth2 customizado — adiciona code_verifier (PKCE)
# ---------------------------------------------------------------------------

class GovBrOAuth2Client(OAuth2Client):
    """
    Estende OAuth2Client para incluir code_verifier no token endpoint.

    O OAuth2Client padrão do allauth 0.51.x não suporta PKCE (não há
    campo token_params nem code_verifier). Este cliente adiciona esse
    parâmetro ao POST de troca do código de autorização.

    Basic Auth é tratado pelo próprio OAuth2Client quando basic_auth=True
    (que é passado pelo adapter via get_client()). Não é necessário
    reimplementar essa parte.
    """

    def __init__(self, *args, code_verifier="", **kwargs):
        super().__init__(*args, **kwargs)
        self.code_verifier = code_verifier

    def get_access_token(self, code):
        data = {
            "redirect_uri": self.callback_url,
            "grant_type": "authorization_code",
            "code": code,
        }

        # Injeta code_verifier (PKCE) quando disponível
        if self.code_verifier:
            data["code_verifier"] = self.code_verifier

        # Basic Auth: usa requests.auth.HTTPBasicAuth quando basic_auth=True
        # (comportamento herdado do OAuth2Client padrão do allauth 0.51.x)
        if self.basic_auth:
            auth = _requests.auth.HTTPBasicAuth(self.consumer_key, self.consumer_secret)
        else:
            auth = None
            data.update({
                "client_id": self.consumer_key,
                "client_secret": self.consumer_secret,
            })

        self._strip_empty_keys(data)

        resp = _requests.post(
            self.access_token_url,
            data=data,
            headers=self.headers,
            auth=auth,
            timeout=10,
        )

        access_token = None
        if resp.status_code in [200, 201]:
            if (
                resp.headers["content-type"].split(";")[0] == "application/json"
                or resp.text[:2] == '{"'
            ):
                access_token = resp.json()
            else:
                access_token = dict(parse_qsl(resp.text))

        if not access_token or "access_token" not in access_token:
            raise OAuth2Error("Error retrieving access token: %s" % resp.content)

        return access_token


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class GovBrOAuth2Adapter(OAuth2Adapter):
    provider_id = GovBrProvider.id

    # O OAuth2Client 0.51.x envia Authorization: Basic quando basic_auth=True.
    # O Gov.br exige Basic Auth no token endpoint (não aceita credenciais no body).
    basic_auth = True

    # URLs como propriedades para ler settings em tempo de execução
    @property
    def access_token_url(self):
        return f"{_govbr_base()}/token"

    @property
    def authorize_url(self):
        return f"{_govbr_base()}/authorize"

    @property
    def profile_url(self):
        return f"{_govbr_base()}/userinfo"

    @property
    def jwks_url(self):
        return f"{_govbr_base()}/jwk"

    def complete_login(self, request, app, token, **kwargs):
        headers = {"Authorization": f"Bearer {token.token}"}
        resp = _requests.get(self.profile_url, headers=headers, timeout=10)
        resp.raise_for_status()
        extra_data = resp.json()
        logger.debug(
            "[GovBr] userinfo recebido: sub=%s | scopes=%s",
            extra_data.get("sub", "?"),
            extra_data.get("scope", "?"),
        )
        return self.get_provider().sociallogin_from_response(request, extra_data)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class GovBrLoginView(OAuth2LoginView):
    """
    Sobrescreve login() para injetar parâmetros PKCE na URL de autorização.

    Por que login() e não get_client()?
    No allauth 0.51.x, client.state é None quando get_client() é chamado
    (recebe o token CSRF string somente depois, em OAuth2LoginView.login()).
    Fazer client.state["chave"] = valor dentro de get_client() lança
    TypeError. A solução é sobrescrever login() e passar os parâmetros
    como extra_params para client.get_redirect_url().
    """

    def login(self, request, *args, **kwargs):
        # Gera code_verifier aleatório (43–128 chars, URL-safe base64 sem padding)
        verifier_bytes = os.urandom(40)
        code_verifier = (
            base64.urlsafe_b64encode(verifier_bytes).rstrip(b"=").decode("ascii")
        )
        request.session["govbr_pkce_verifier"] = code_verifier

        # Deriva code_challenge via S256
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = (
            base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        )

        logger.debug("[GovBr] PKCE challenge gerado para a sessão.")

        app = self.adapter.get_app(request)
        client = self.get_client(request, app)
        client.state = SocialLogin.stash_state(request)

        extra_params = {
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        return HttpResponseRedirect(
            client.get_redirect_url(self.adapter.authorize_url, extra_params)
        )

    def get_client(self, request, app):
        """Retorna GovBrOAuth2Client sem code_verifier (usado só no login)."""
        callback_url = build_absolute_uri(
            request, reverse(self.adapter.provider_id + "_callback")
        )
        provider = self.adapter.get_provider()
        scope = provider.get_scope(request)

        return GovBrOAuth2Client(
            request,
            app.client_id,
            app.secret,
            self.adapter.access_token_method,
            self.adapter.access_token_url,
            callback_url,
            scope,
            basic_auth=self.adapter.basic_auth,
        )


class GovBrCallbackView(OAuth2CallbackView):
    """
    Callback do Gov.br.

    Retorna GovBrOAuth2Client com code_verifier recuperado da sessão,
    que é enviado no corpo do POST de troca do código de autorização.
    """

    def get_client(self, request, app):
        callback_url = build_absolute_uri(
            request, reverse(self.adapter.provider_id + "_callback")
        )
        provider = self.adapter.get_provider()
        scope = provider.get_scope(request)

        verifier = request.session.get("govbr_pkce_verifier", "")
        if not verifier:
            logger.warning("[GovBr] code_verifier não encontrado na sessão!")

        return GovBrOAuth2Client(
            request,
            app.client_id,
            app.secret,
            self.adapter.access_token_method,
            self.adapter.access_token_url,
            callback_url,
            scope,
            basic_auth=self.adapter.basic_auth,
            code_verifier=verifier,
        )


oauth2_login = GovBrLoginView.adapter_view(GovBrOAuth2Adapter)
oauth2_callback = GovBrCallbackView.adapter_view(GovBrOAuth2Adapter)

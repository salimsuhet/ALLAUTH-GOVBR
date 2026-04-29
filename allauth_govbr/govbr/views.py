"""
allauth_govbr.govbr.views
~~~~~~~~~~~~~~~~~~~~~~~~~
Views OAuth2 para o Gov.br com PKCE manual.

PKCE (Proof Key for Code Exchange) é OBRIGATÓRIO no Gov.br e não é
suportado nativamente pelo django-allauth 0.51.x, então é implementado
aqui manualmente via sobrescrita do método login() e de um OAuth2Client
customizado que usa Basic Auth no token endpoint.

Correções aplicadas em relação à versão original:
  - Bug 1: client.state é uma string CSRF, não um dict — PKCE agora é
    injetado via extra_params em login() e token_params no cliente.
  - Bug 2: Gov.br exige Authorization: Basic no token endpoint;
    o allauth padrão envia credenciais no corpo do POST.
  - Bug 3: URLs do adapter eram avaliadas na importação do módulo;
    agora são propriedades avaliadas em tempo de execução.
"""
import base64
import hashlib
import logging
import os

import requests as _requests
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
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
        # Homologação: defina GOVBR_SSO_BASE_URL = "https://sso.staging.acesso.gov.br"
    )


# ---------------------------------------------------------------------------
# Cliente OAuth2 customizado — Basic Auth no token endpoint
# ---------------------------------------------------------------------------

class GovBrOAuth2Client(OAuth2Client):
    """
    Subclasse de OAuth2Client que envia as credenciais do cliente via
    Authorization: Basic no token endpoint, conforme exigido pelo Gov.br.

    O allauth padrão envia client_id/client_secret no corpo do POST
    (parâmetros de formulário), mas o Gov.br rejeita essa forma e espera
    o header HTTP Basic Auth — comportamento idêntico ao confirmado no
    plugin de referência PHP (GovBrStrategy.php, linhas 34-36).
    """

    def get_access_token(self, code):
        data = {
            "redirect_uri": self.callback_url,
            "grant_type": "authorization_code",
            "code": code,
        }
        if self.state:
            data["state"] = self.state

        # Injeta code_verifier (PKCE) se presente
        data.update(self.token_params)

        credentials = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode("ascii")
        ).decode("ascii")

        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        resp = _requests.post(
            self.access_token_url,
            data=data,
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        return self.parse_token(resp.content)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class GovBrOAuth2Adapter(OAuth2Adapter):
    provider_id = GovBrProvider.id

    # URLs como propriedades para ler settings em tempo de execução (Bug 3)
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
    No allauth 0.51.x, get_client() é chamado ANTES de client.state ser
    definido (client.state recebe o token CSRF string somente depois, em
    OAuth2LoginView.login()). Tentar fazer client.state["chave"] = valor
    dentro de get_client() resulta em TypeError porque client.state é None
    nesse momento. A solução correta é sobrescrever login() inteiro.
    """

    def login(self, request, *args, **kwargs):
        # Gera code_verifier aleatório (43-128 chars, URL-safe base64 sem padding)
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
        """Retorna GovBrOAuth2Client (Basic Auth no token endpoint)."""
        callback_url = reverse(self.adapter.provider_id + "_callback")
        callback_url = build_absolute_uri(request, callback_url)
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
        )


class GovBrCallbackView(OAuth2CallbackView):
    """
    Callback do Gov.br.

    Injeta code_verifier via token_params do cliente para que seja
    enviado no corpo do POST de troca do código de autorização.
    """

    def get_client(self, request, app):
        callback_url = reverse(self.adapter.provider_id + "_callback")
        callback_url = build_absolute_uri(request, callback_url)
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
            token_params={"code_verifier": verifier},
        )


oauth2_login = GovBrLoginView.adapter_view(GovBrOAuth2Adapter)
oauth2_callback = GovBrCallbackView.adapter_view(GovBrOAuth2Adapter)

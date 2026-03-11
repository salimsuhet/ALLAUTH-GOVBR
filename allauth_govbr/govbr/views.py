"""
allauth_govbr.govbr.views
~~~~~~~~~~~~~~~~~~~~~~~~~
Views OAuth2 para o Gov.br com PKCE manual.

PKCE (Proof Key for Code Exchange) é OBRIGATÓRIO no Gov.br e não é
suportado nativamente pelo django-allauth 0.51.x, então é implementado
aqui manualmente via sobrescrita das views de login/callback.
"""
import base64
import hashlib
import logging
import os

import requests
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)
from django.conf import settings

from .provider import GovBrProvider

logger = logging.getLogger(__name__)

# Permite sobrescrever a URL base via settings para usar staging em dev
_BASE = getattr(
    settings,
    "GOVBR_SSO_BASE_URL",
    "https://sso.acesso.gov.br",
    # Staging: "https://sso.staging.acesso.gov.br"
)


class GovBrOAuth2Adapter(OAuth2Adapter):
    provider_id = GovBrProvider.id

    access_token_url = f"{_BASE}/token"
    authorize_url = f"{_BASE}/authorize"
    profile_url = f"{_BASE}/userinfo/"
    jwks_url = f"{_BASE}/jwk"

    def complete_login(self, request, app, token, **kwargs):
        headers = {"Authorization": f"Bearer {token.token}"}
        resp = requests.get(self.profile_url, headers=headers, timeout=10)
        resp.raise_for_status()
        extra_data = resp.json()
        logger.debug(
            "[GovBr] userinfo recebido: sub=%s | scopes=%s",
            extra_data.get("sub", "?"),
            extra_data.get("scope", "?"),
        )
        return self.get_provider().sociallogin_from_response(request, extra_data)


class GovBrLoginView(OAuth2LoginView):
    """
    Injeta parâmetros PKCE (code_challenge + code_challenge_method=S256)
    na URL de autorização, conforme exigido pelo Gov.br.
    """

    def get_client(self, request, app):
        client = super().get_client(request, app)

        # Gera code_verifier aleatório (43-128 chars, URL-safe base64)
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

        client.state["code_challenge"] = code_challenge
        client.state["code_challenge_method"] = "S256"

        logger.debug("[GovBr] PKCE challenge gerado para a sessão.")
        return client


class GovBrCallbackView(OAuth2CallbackView):
    """
    Injeta o code_verifier no request de troca do código de autorização.
    """

    def get_client(self, request, app):
        client = super().get_client(request, app)
        verifier = request.session.get("govbr_pkce_verifier", "")
        if not verifier:
            logger.warning("[GovBr] code_verifier não encontrado na sessão!")
        client.state["code_verifier"] = verifier
        return client


oauth2_login = GovBrLoginView.adapter_view(GovBrOAuth2Adapter)
oauth2_callback = GovBrCallbackView.adapter_view(GovBrOAuth2Adapter)

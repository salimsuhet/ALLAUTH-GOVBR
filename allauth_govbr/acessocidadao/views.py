"""
allauth_govbr.acessocidadao.views
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Views OAuth2 para o Acesso Cidadão ES (PRODEST).

O Acesso Cidadão ES usa hybrid flow (response_type = "code id_token")
com nonce obrigatório e response_mode = "form_post".
NÃO usa PKCE.
"""
import logging
import secrets

import requests
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)
from django.conf import settings

from .provider import AcessoCidadaoProvider

logger = logging.getLogger(__name__)

# Permite sobrescrever via settings (útil para ambiente de homologação)
_BASE = getattr(
    settings,
    "ACESSOCIDADAO_ES_BASE_URL",
    "https://acessocidadao.es.gov.br/is",
)


class AcessoCidadaoAdapter(OAuth2Adapter):
    provider_id = AcessoCidadaoProvider.id

    access_token_url = f"{_BASE}/connect/token"
    authorize_url = f"{_BASE}/connect/authorize"
    profile_url = f"{_BASE}/connect/userinfo"

    def complete_login(self, request, app, token, **kwargs):
        headers = {"Authorization": f"Bearer {token.token}"}
        resp = requests.get(self.profile_url, headers=headers, timeout=10)
        resp.raise_for_status()
        extra_data = resp.json()
        logger.debug(
            "[AcessoCidadaoES] userinfo recebido: sub=%s | subNovo=%s",
            extra_data.get("sub", "?"),
            extra_data.get("subNovo", "?"),
        )
        return self.get_provider().sociallogin_from_response(request, extra_data)


class AcessoCidadaoLoginView(OAuth2LoginView):
    """
    Configura o hybrid flow do Acesso Cidadão ES:
    - response_type = "code id_token"
    - response_mode = "form_post"
    - nonce obrigatório (gerado e salvo na sessão)
    """

    def get_client(self, request, app):
        client = super().get_client(request, app)

        # Nonce obrigatório — associa a sessão ao id_token retornado
        nonce = secrets.token_urlsafe(32)
        request.session["aces_nonce"] = nonce

        client.state["nonce"] = nonce
        client.state["response_type"] = "code id_token"
        client.state["response_mode"] = "form_post"

        logger.debug("[AcessoCidadaoES] Nonce gerado para a sessão.")
        return client


class AcessoCidadaoCallbackView(OAuth2CallbackView):
    """
    Callback para o Acesso Cidadão ES.
    Não precisa de customização extra além da herança base.
    """
    pass


oauth2_login = AcessoCidadaoLoginView.adapter_view(AcessoCidadaoAdapter)
oauth2_callback = AcessoCidadaoCallbackView.adapter_view(AcessoCidadaoAdapter)

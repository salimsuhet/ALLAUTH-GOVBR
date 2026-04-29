"""
allauth_govbr.govbr.views  (GeoNode 5.x / allauth 0.63.x)
~~~~~~~~~~~~~~~~~~~~~~~~~~
Adapter OAuth2 para o Login Único Gov.br.

No allauth 0.63.x, PKCE é suportado nativamente pelo provider via
get_pkce_params(). A geração do code_verifier/challenge, o armazenamento
no state dict e a passagem para get_access_token() são todos automáticos.

Esta view só precisa:
  - Definir as URLs do SSO Gov.br (via properties para leitura lazy dos settings)
  - Declarar basic_auth = True (Gov.br exige Authorization: Basic no token endpoint)
  - Declarar pkce_enabled_default = True no provider (ver provider.py)
"""
import logging

import requests as _requests
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)
from django.conf import settings

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


class GovBrOAuth2Adapter(OAuth2Adapter):
    provider_id = GovBrProvider.id

    # Gov.br exige Basic Auth (Authorization: Basic) no token endpoint.
    # O OAuth2Client do allauth 0.63.x suporta isso nativamente via basic_auth=True.
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


# No allauth 0.63.x, OAuth2LoginView e OAuth2CallbackView já fazem tudo:
# - LoginView:    OAuth2Provider.redirect() gera PKCE, salva no state dict
# - CallbackView: lê pkce_code_verifier do state, passa para get_access_token()
oauth2_login = OAuth2LoginView.adapter_view(GovBrOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(GovBrOAuth2Adapter)

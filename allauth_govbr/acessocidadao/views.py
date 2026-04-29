"""
allauth_govbr.acessocidadao.views  (GeoNode 5.x / allauth 0.63.x)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Views OAuth2 para o Acesso Cidadão ES (PRODEST).

No allauth 0.63.x, o fluxo de login é iniciado por AcessoCidadaoProvider.redirect()
(sobrescrito em provider.py), que injeta nonce, response_type e response_mode
automaticamente. Não é necessária uma LoginView customizada.

O callback ainda precisa de tratamento especial:
  - csrf_exempt:  response_mode=form_post faz o AC-ES enviar um POST externo
    para a callback URI. O CsrfViewMiddleware bloquearia esse POST com 403.
  - POST → GET:   OAuth2CallbackView.dispatch() verifica "code" not in request.GET
    diretamente. Os parâmetros do form_post chegam em request.POST e precisam
    ser copiados para request.GET antes do super().dispatch().
    (get_request_param() já checa POST, mas a guarda inicial usa GET diretamente.)
"""
import logging

import requests as _requests
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)
from django.conf import settings
from django.utils.datastructures import QueryDict
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .provider import AcessoCidadaoProvider

logger = logging.getLogger(__name__)


def _aces_base():
    """Retorna a URL base do Acesso Cidadão ES lida dos settings em tempo de execução."""
    return getattr(
        settings,
        "ACESSOCIDADAO_ES_BASE_URL",
        "https://acessocidadao.es.gov.br/is",
    )


class AcessoCidadaoAdapter(OAuth2Adapter):
    provider_id = AcessoCidadaoProvider.id

    @property
    def access_token_url(self):
        return f"{_aces_base()}/connect/token"

    @property
    def authorize_url(self):
        return f"{_aces_base()}/connect/authorize"

    @property
    def profile_url(self):
        return f"{_aces_base()}/connect/userinfo"

    def complete_login(self, request, app, token, **kwargs):
        headers = {"Authorization": f"Bearer {token.token}"}
        resp = _requests.get(self.profile_url, headers=headers, timeout=10)
        resp.raise_for_status()
        extra_data = resp.json()
        logger.debug(
            "[AcessoCidadaoES] userinfo recebido: sub=%s | subNovo=%s",
            extra_data.get("sub", "?"),
            extra_data.get("subNovo", "?"),
        )
        return self.get_provider().sociallogin_from_response(request, extra_data)


@method_decorator(csrf_exempt, name="dispatch")
class AcessoCidadaoCallbackView(OAuth2CallbackView):
    """
    Callback para o Acesso Cidadão ES com suporte a form_post.

    @csrf_exempt: necessário porque o POST vem de um servidor externo (AC-ES)
    sem token CSRF do Django.

    dispatch(): copia request.POST para request.GET quando o método é POST,
    para que a verificação `"code" not in request.GET` do allauth passe corretamente.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            mutable = QueryDict(mutable=True)
            mutable.update(request.POST)
            request.GET = mutable
            logger.debug(
                "[AcessoCidadaoES] Callback via POST (form_post); "
                "parâmetros copiados para request.GET."
            )
        return super().dispatch(request, *args, **kwargs)


oauth2_login = OAuth2LoginView.adapter_view(AcessoCidadaoAdapter)
oauth2_callback = AcessoCidadaoCallbackView.adapter_view(AcessoCidadaoAdapter)

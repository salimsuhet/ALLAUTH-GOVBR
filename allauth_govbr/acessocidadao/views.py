"""
allauth_govbr.acessocidadao.views
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Views OAuth2 para o Acesso Cidadão ES (PRODEST).

O Acesso Cidadão ES usa hybrid flow (response_type = "code id_token")
com nonce obrigatório e response_mode = "form_post".
NÃO usa PKCE.

Notas de implementação:
  - client.state é uma string CSRF, não um dict — nonce e demais
    parâmetros do hybrid flow são injetados via extra_params em login().
  - response_mode = "form_post": o servidor de autorização faz POST de
    volta para o callback URI. O Django bloqueia POSTs externos via CSRF
    middleware, então AcessoCidadaoCallbackView é marcado como csrf_exempt.
    O dispatch() também copia request.POST para request.GET para que o
    OAuth2CallbackView do allauth encontre 'code' e 'state' onde espera.
  - URLs do adapter: propriedades avaliadas em tempo de execução.
"""
import logging
import secrets

import requests as _requests
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)
from django.conf import settings
from django.http import HttpResponseRedirect
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


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class AcessoCidadaoAdapter(OAuth2Adapter):
    provider_id = AcessoCidadaoProvider.id

    # URLs como propriedades para ler settings em tempo de execução
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


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class AcessoCidadaoLoginView(OAuth2LoginView):
    """
    Sobrescreve login() para configurar o hybrid flow do Acesso Cidadão ES:
      - response_type = "code id_token"
      - response_mode = "form_post"
      - nonce obrigatório (gerado e salvo na sessão)

    Por que login() e não get_client()?
    No allauth 0.51.x, client.state é None quando get_client() é chamado
    e só recebe o token CSRF string depois que get_client() retorna.
    Atribuir client.state["chave"] = valor lança TypeError. A solução é
    sobrescrever login() e passar os parâmetros como extra_params para
    client.get_redirect_url().
    """

    def login(self, request, *args, **kwargs):
        # Nonce obrigatório — vincula a sessão ao id_token retornado
        nonce = secrets.token_urlsafe(32)
        request.session["aces_nonce"] = nonce

        logger.debug("[AcessoCidadaoES] Nonce gerado para a sessão.")

        app = self.adapter.get_app(request)
        client = self.get_client(request, app)
        client.state = SocialLogin.stash_state(request)

        extra_params = {
            "nonce": nonce,
            "response_type": "code id_token",
            "response_mode": "form_post",
        }

        return HttpResponseRedirect(
            client.get_redirect_url(self.adapter.authorize_url, extra_params)
        )


@method_decorator(csrf_exempt, name="dispatch")
class AcessoCidadaoCallbackView(OAuth2CallbackView):
    """
    Callback para o Acesso Cidadão ES com suporte a form_post.

    Por que csrf_exempt?
    Quando response_mode = "form_post", o servidor de autorização do
    Acesso Cidadão ES faz um POST externo de volta para esta URL. Esse
    POST não carrega o token CSRF do Django, então o CsrfViewMiddleware
    retornaria 403 Forbidden sem essa isenção.

    Por que copiar POST para GET?
    OAuth2CallbackView.dispatch() do allauth 0.51.x verifica
    `if "code" not in request.GET`, então os parâmetros precisam estar
    em request.GET. O allauth usa get_request_param(), que já verifica
    request.POST primeiro — mas a guarda inicial usa request.GET
    diretamente. Copiar garante que ambas as verificações passem.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            # form_post: parâmetros chegam no corpo; copia para GET para
            # que o OAuth2CallbackView os encontre onde espera.
            mutable = QueryDict(mutable=True)
            mutable.update(request.POST)
            request.GET = mutable
            logger.debug(
                "[AcessoCidadaoES] Callback via POST (form_post); "
                "parâmetros copiados para request.GET."
            )
        return super().dispatch(request, *args, **kwargs)


oauth2_login = AcessoCidadaoLoginView.adapter_view(AcessoCidadaoAdapter)
oauth2_callback = AcessoCidadaoCallbackView.adapter_view(AcessoCidadaoAdapter)

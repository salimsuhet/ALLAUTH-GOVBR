"""
allauth_govbr.acessocidadao.provider  (GeoNode 5.x / allauth 0.63.x)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provider OAuth2/OIDC para o Acesso Cidadão ES (PRODEST).

Mudanças em relação ao branch main (allauth 0.51.x):
  - oauth2_adapter_class = AcessoCidadaoAdapter: padrão do allauth 0.63.x.
  - redirect() sobrescrito para injetar nonce, response_type e response_mode
    sem precisar de LoginView customizada. O nonce é passado via **kwargs para
    stash_redirect_state(), ficando disponível no state dict do callback como
    state["nonce"].
  - providers.registry.register() mantido.
"""
import secrets

from allauth.socialaccount import providers

from allauth_govbr.base import GovIdentityAccount, GovIdentityProvider


class AcessoCidadaoAccount(GovIdentityAccount):
    def to_str(self):
        data = self.account.extra_data
        return (
            data.get("nomeSocial")
            or data.get("nome")
            or data.get("apelido")
            or super().to_str()
        )


class AcessoCidadaoProvider(GovIdentityProvider):
    id = "acessocidadaoes"
    name = "Acesso Cidadão ES"
    account_class = AcessoCidadaoAccount

    def get_default_scope(self):
        return ["openid", "profile", "email"]

    def redirect(self, request, process, next_url=None, data=None, **kwargs):
        """
        Sobrescreve redirect() para injetar os parâmetros do hybrid flow:
          - nonce:          obrigatório pelo AC-ES
          - response_type:  "code id_token" (hybrid flow)
          - response_mode:  "form_post" (callback via POST)

        O nonce é armazenado no state dict via **kwargs para stash_redirect_state,
        permitindo validação futura: state["nonce"] == nonce do id_token retornado.
        """
        nonce = secrets.token_urlsafe(32)

        # Injeta parâmetros do hybrid flow na URL de autorização
        auth_params = dict(self.get_auth_params())
        auth_params.update({
            "nonce": nonce,
            "response_type": "code id_token",
            "response_mode": "form_post",
        })
        kwargs["auth_params"] = auth_params

        # Armazena nonce no state dict (via **kwargs → stash_redirect_state)
        return super().redirect(
            request, process, next_url=next_url, data=data, nonce=nonce, **kwargs
        )

    def extract_uid(self, data):
        # subNovo é o identificador atual; sub está deprecado
        return str(data.get("subNovo") or data["sub"])

    def extract_common_fields(self, data):
        nome = data.get("nomeSocial") or data.get("nome") or ""
        parts = nome.split(" ")
        return dict(
            username=str(data.get("subNovo") or data.get("sub", "")),
            email=data.get("email", ""),
            first_name=parts[0] if parts else "",
            last_name=" ".join(parts[1:]) if len(parts) > 1 else "",
        )

    def extract_extra_data(self, data):
        return {
            "sub_novo": data.get("subNovo"),
            "sub_legado": data.get("sub"),
            "nome": data.get("nome"),
            "nome_civil": data.get("nomeCivil"),
            "nome_social": data.get("nomeSocial"),
            "nome_validado": data.get("nomeValidado"),
            "apelido": data.get("apelido"),
            "cpf": data.get("cpf"),
            "data_nascimento": data.get("dataNascimento"),
            "avatar_url": data.get("avatarUrl"),
            "agente_publico": data.get("agentePublico"),
            "provider_source": "acessocidadaoes",
        }


providers.registry.register(AcessoCidadaoProvider)

"""
allauth_govbr.govbr.provider  (GeoNode 5.x / allauth 0.63.x)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provider OAuth2/OIDC para o Login Único Gov.br (federal).

Mudanças em relação ao branch main (allauth 0.51.x):
  - pkce_enabled_default = True: ativa PKCE nativo do allauth 0.63.x.
    O Gov.br exige S256, que é o único método suportado por generate_code_challenge().
    Ao ativar pkce_enabled_default, o provider.redirect() chama get_pkce_params()
    automaticamente, armazena code_verifier no state dict e passa para
    get_access_token() no callback — sem código manual.
  - oauth2_adapter_class = GovBrOAuth2Adapter: padrão do allauth 0.63.x para
    conectar provider ao adapter sem precisar de views customizadas.
  - providers.registry.register() ainda funciona via importação automática do
    módulo pelo ProviderRegistry.load() — mantido para compatibilidade.
"""
from allauth.socialaccount import providers
from allauth.socialaccount.providers.oauth2.utils import generate_code_challenge

from allauth_govbr.base import GovIdentityAccount, GovIdentityProvider


class GovBrAccount(GovIdentityAccount):
    def to_str(self):
        return self.account.extra_data.get("name", super().to_str())


class GovBrProvider(GovIdentityProvider):
    id = "govbr"
    name = "Gov.br"
    account_class = GovBrAccount

    # PKCE é obrigatório no Gov.br. pkce_enabled_default = True garante que
    # get_pkce_params() sempre retorna o challenge, independente de OAUTH_PKCE_ENABLED.
    pkce_enabled_default = True

    def get_pkce_params(self):
        """
        Sobrescreve para sempre gerar PKCE (não condicional ao setting).
        Gov.br exige PKCE em todos os fluxos — não é opcional.
        generate_code_challenge() do allauth já retorna S256.
        """
        return generate_code_challenge()

    def get_default_scope(self):
        return ["openid", "email", "profile"]

    def extract_uid(self, data):
        # O sub no Gov.br é o CPF do cidadão
        return str(data["sub"])

    def extract_common_fields(self, data):
        name = data.get("name") or ""
        parts = name.split(" ")
        return dict(
            username=data.get("preferred_username", data["sub"]),
            email=data.get("email", ""),
            first_name=parts[0] if parts else "",
            last_name=" ".join(parts[1:]) if len(parts) > 1 else "",
        )

    def extract_extra_data(self, data):
        return {
            "cpf": data.get("sub"),
            "name": data.get("name"),
            "picture": data.get("picture"),
            "social_name": data.get("social_name"),
            "preferred_username": data.get("preferred_username"),
            "reliability": data.get("reliability_info", {}),
            "amr": data.get("amr", []),
            "phone_number": data.get("phone_number"),
            "provider_source": "govbr",
        }


# Registro via importação automática pelo ProviderRegistry.load()
providers.registry.register(GovBrProvider)

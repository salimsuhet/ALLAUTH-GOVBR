"""
allauth_govbr.govbr.provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provider OAuth2/OIDC para o Login Único Gov.br (federal).

Características:
- PKCE obrigatório (S256)
- Sub pairwise (o sub é o CPF do cidadão)
- Scopes: openid, email, profile, govbr_confiabilidades
"""
from allauth.socialaccount import providers

from allauth_govbr.base import GovIdentityAccount, GovIdentityProvider


class GovBrAccount(GovIdentityAccount):
    def to_str(self):
        return self.account.extra_data.get("name", super().to_str())


class GovBrProvider(GovIdentityProvider):
    id = "govbr"
    name = "Gov.br"
    account_class = GovBrAccount

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
            # CPF — no Gov.br, o sub é o CPF
            "cpf": data.get("sub"),
            # Identificação
            "name": data.get("name"),
            "picture": data.get("picture"),
            "social_name": data.get("social_name"),
            "preferred_username": data.get("preferred_username"),
            # Confiabilidade (escopo govbr_confiabilidades)
            "reliability": data.get("reliability_info", {}),
            # Métodos de autenticação usados (ex: ["passwd", "x509"])
            "amr": data.get("amr", []),
            # Contato
            "phone_number": data.get("phone_number"),
            # Metadado interno
            "provider_source": "govbr",
        }


# Registro obrigatório para allauth 0.51.x (compatível com GeoNode 4.x)
providers.registry.register(GovBrProvider)

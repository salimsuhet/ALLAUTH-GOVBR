"""
allauth_govbr.acessocidadao.provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provider OAuth2/OIDC para o Acesso Cidadão ES (PRODEST).

Documentação oficial:
  https://docs.developer.acessocidadao.es.gov.br/

Características:
- Hybrid flow: response_type = "code id_token"
- Nonce obrigatório
- SEM PKCE
- UID: campo "subNovo" (substitui "sub" deprecado)
- Scopes públicos: openid, profile, email, agentepublico
- Scopes que precisam de aprovação: nome, cpf, dataNascimento, etc.
"""
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
        # Scopes públicos (não precisam de aprovação do PRODEST)
        return ["openid", "profile", "email"]

    def extract_uid(self, data):
        # subNovo é o identificador atual; sub está deprecado
        return str(data.get("subNovo") or data["sub"])

    def extract_common_fields(self, data):
        # Prioriza nome social se disponível
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
            # Identificadores
            "sub_novo": data.get("subNovo"),
            "sub_legado": data.get("sub"),
            # Nome
            "nome": data.get("nome"),
            "nome_civil": data.get("nomeCivil"),
            "nome_social": data.get("nomeSocial"),
            "nome_validado": data.get("nomeValidado"),
            "apelido": data.get("apelido"),
            # CPF (requer scope aprovado pelo PRODEST)
            "cpf": data.get("cpf"),
            # Outros dados pessoais (requerem scopes aprovados)
            "data_nascimento": data.get("dataNascimento"),
            "avatar_url": data.get("avatarUrl"),
            # Papel institucional (scope: agentepublico)
            "agente_publico": data.get("agentePublico"),
            # Metadado interno
            "provider_source": "acessocidadaoes",
        }


# Registro obrigatório para allauth 0.51.x (compatível com GeoNode 4.x)
providers.registry.register(AcessoCidadaoProvider)

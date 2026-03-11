"""
local_settings.py — exemplo de configuração para GeoNode 4.x
=============================================================

Inclua este conteúdo no seu local_settings.py (ou equivalente) do GeoNode
para ativar os provedores Gov.br e Acesso Cidadão ES.

Documentação dos provedores:
  Gov.br:            https://manual-roteiro-integracao-login-unico.servicos.gov.br/
  Acesso Cidadão ES: https://docs.developer.acessocidadao.es.gov.br/
"""

# ---------------------------------------------------------------------------
# 1. Registra o app do plugin
# ---------------------------------------------------------------------------
INSTALLED_APPS += ["allauth_govbr"]  # noqa: F821

# ---------------------------------------------------------------------------
# 2. URLs dos servidores SSO
#    Troque pelas URLs de produção quando for fazer o go-live.
# ---------------------------------------------------------------------------

# Gov.br
# Produção:    https://sso.acesso.gov.br
# Homologação: https://sso.staging.acesso.gov.br
GOVBR_SSO_BASE_URL = "https://sso.staging.acesso.gov.br"

# Acesso Cidadão ES (PRODEST)
# Produção:    https://acessocidadao.es.gov.br/is
# (não há ambiente de staging público documentado)
ACESSOCIDADAO_ES_BASE_URL = "https://acessocidadao.es.gov.br/is"

# ---------------------------------------------------------------------------
# 3. Configuração dos providers (allauth 0.51.x — GeoNode 4.x)
# ---------------------------------------------------------------------------
SOCIALACCOUNT_PROVIDERS = {
    "govbr": {
        # Scopes base — sempre disponíveis
        "SCOPE": ["openid", "email", "profile"],
        # Adicione "govbr_confiabilidades" para receber selos de confiança
        # "SCOPE": ["openid", "email", "profile", "govbr_confiabilidades"],
    },
    "acessocidadaoes": {
        # Scopes públicos (não precisam de aprovação do PRODEST)
        "SCOPE": ["openid", "profile", "email", "agentepublico"],
        # Scopes que requerem solicitação formal ao PRODEST:
        # "SCOPE": ["openid", "profile", "email", "nome", "cpf", "dataNascimento"],
    },
}

# ---------------------------------------------------------------------------
# 4. Adapter com vinculação por CPF
# ---------------------------------------------------------------------------
SOCIALACCOUNT_ADAPTER = "allauth_govbr.adapter.GovIdentityAccountAdapter"

# Mantém o adapter de conta local padrão do GeoNode
ACCOUNT_ADAPTER = "geonode.people.adapters.LocalAccountAdapter"

# ---------------------------------------------------------------------------
# 5. Extractors de perfil para o GeoNode
# ---------------------------------------------------------------------------
SOCIALACCOUNT_PROFILE_EXTRACTORS = {
    "govbr": "allauth_govbr.extractors.GovBrExtractor",
    "acessocidadaoes": "allauth_govbr.extractors.AcessoCidadaoExtractor",
    # Mantenha os extractors existentes do GeoNode se necessário:
    # "facebook": "geonode.people.profileextractors.FacebookExtractor",
    # "linkedin_oauth2": "geonode.people.profileextractors.LinkedInExtractor",
}

# ---------------------------------------------------------------------------
# 6. Comportamento de cadastro e aprovação
# ---------------------------------------------------------------------------
SOCIALACCOUNT_AUTO_SIGNUP = False   # exige preenchimento de cadastro
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_APPROVAL_REQUIRED = True    # recomendado para implantações governamentais
ACCOUNT_EMAIL_VERIFICATION = "optional"

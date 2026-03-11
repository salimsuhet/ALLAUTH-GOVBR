"""
allauth_govbr.extractors
~~~~~~~~~~~~~~~~~~~~~~~~
ProfileExtractors para o GeoNode 4.x.

Configuração em local_settings.py:
    SOCIALACCOUNT_PROFILE_EXTRACTORS = {
        "govbr": "allauth_govbr.extractors.GovBrExtractor",
        "acessocidadaoes": "allauth_govbr.extractors.AcessoCidadaoExtractor",
    }
"""


class GovBrExtractor:
    """
    Extrai campos do perfil recebido do endpoint /userinfo do Gov.br federal.

    Campos disponíveis (dependem dos scopes solicitados):
        sub, name, email, preferred_username, picture,
        social_name, reliability_info, amr, phone_number
    """

    def extract_area(self, data):
        return None

    def extract_city(self, data):
        return None

    def extract_country(self, data):
        return "BR"

    def extract_delivery(self, data):
        return None

    def extract_email_address(self, data):
        return data.get("email", "")

    def extract_fax(self, data):
        return None

    def extract_first_name(self, data):
        parts = (data.get("name") or "").split(" ")
        return parts[0] if parts else ""

    def extract_last_name(self, data):
        parts = (data.get("name") or "").split(" ")
        return " ".join(parts[1:]) if len(parts) > 1 else ""

    def extract_organization(self, data):
        return None

    def extract_phone(self, data):
        return data.get("phone_number", "")

    def extract_profile(self, data):
        return data.get("profile", "")

    def extract_position(self, data):
        return None

    def extract_zip_code(self, data):
        return None


class AcessoCidadaoExtractor:
    """
    Extrai campos do perfil recebido do endpoint /connect/userinfo
    do Acesso Cidadão ES (PRODEST).

    Campos disponíveis (dependem dos scopes aprovados):
        sub, subNovo, nome, nomeSocial, nomeCivil, apelido,
        email, cpf, dataNascimento, agentePublico, avatarUrl
    """

    def extract_area(self, data):
        return None

    def extract_city(self, data):
        return None

    def extract_country(self, data):
        return "BR"

    def extract_delivery(self, data):
        return None

    def extract_email_address(self, data):
        return data.get("email", "")

    def extract_fax(self, data):
        return None

    def extract_first_name(self, data):
        # Prioriza nome social se disponível
        nome = data.get("nomeSocial") or data.get("nome") or ""
        parts = nome.split(" ")
        return parts[0] if parts else ""

    def extract_last_name(self, data):
        nome = data.get("nomeSocial") or data.get("nome") or ""
        parts = nome.split(" ")
        return " ".join(parts[1:]) if len(parts) > 1 else ""

    def extract_organization(self, data):
        return None

    def extract_phone(self, data):
        return None

    def extract_profile(self, data):
        return data.get("avatarUrl", "")

    def extract_position(self, data):
        return None

    def extract_zip_code(self, data):
        return None

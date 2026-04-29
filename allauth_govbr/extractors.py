"""
allauth_govbr.extractors  (GeoNode 5.x / allauth 0.63.x)
~~~~~~~~~~~~~~~~~~~~~~~~~
ProfileExtractors para o GeoNode 5.x.

Mudanças em relação ao branch main (allauth 0.51.x / GeoNode 4.x):
  - extract_email_address → extract_email  (renomeado no GeoNode 5.x BaseExtractor)
  - extract_phone         → extract_voice  (renomeado no GeoNode 5.x BaseExtractor)
  - extract_zip_code      → extract_zipcode (renomeado no GeoNode 5.x BaseExtractor)

Configuração em local_settings.py:
    SOCIALACCOUNT_PROFILE_EXTRACTORS = {
        "govbr": "allauth_govbr.extractors.GovBrExtractor",
        "acessocidadaoes": "allauth_govbr.extractors.AcessoCidadaoExtractor",
    }
"""


class GovBrExtractor:
    """
    Extrai campos do /userinfo do Gov.br federal.
    Implementa a interface BaseExtractor do GeoNode 5.x.
    """

    def extract_area(self, data):
        return None

    def extract_city(self, data):
        return None

    def extract_country(self, data):
        return "BR"

    def extract_delivery(self, data):
        return None

    def extract_email(self, data):
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

    def extract_voice(self, data):
        return data.get("phone_number", "")

    def extract_profile(self, data):
        return data.get("profile", "")

    def extract_position(self, data):
        return None

    def extract_zipcode(self, data):
        return None


class AcessoCidadaoExtractor:
    """
    Extrai campos do /connect/userinfo do Acesso Cidadão ES (PRODEST).
    Implementa a interface BaseExtractor do GeoNode 5.x.
    """

    def extract_area(self, data):
        return None

    def extract_city(self, data):
        return None

    def extract_country(self, data):
        return "BR"

    def extract_delivery(self, data):
        return None

    def extract_email(self, data):
        return data.get("email", "")

    def extract_fax(self, data):
        return None

    def extract_first_name(self, data):
        nome = data.get("nomeSocial") or data.get("nome") or ""
        parts = nome.split(" ")
        return parts[0] if parts else ""

    def extract_last_name(self, data):
        nome = data.get("nomeSocial") or data.get("nome") or ""
        parts = nome.split(" ")
        return " ".join(parts[1:]) if len(parts) > 1 else ""

    def extract_organization(self, data):
        return None

    def extract_voice(self, data):
        return None

    def extract_profile(self, data):
        return data.get("avatarUrl", "")

    def extract_position(self, data):
        return None

    def extract_zipcode(self, data):
        return None

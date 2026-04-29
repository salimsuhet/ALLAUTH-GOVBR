"""
allauth_govbr.base  (GeoNode 5.x / allauth 0.63.x)
~~~~~~~~~~~~~~~~~~
Classes base compartilhadas entre os providers Gov.br e Acesso Cidadão ES.

Mudanças em relação ao branch main (allauth 0.51.x):
  - get_scope(): no allauth 0.63.x, a assinatura é get_scope() sem request.
    No 0.51.x era get_scope(request). A base GovIdentityProvider não
    sobrescreve get_scope() — herda a implementação padrão do OAuth2Provider,
    que lê SCOPE dos settings e chama get_default_scope() como fallback.
"""
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider


class GovIdentityAccount(ProviderAccount):
    """Conta base para provedores de identidade gov."""

    def get_avatar_url(self):
        return self.account.extra_data.get("picture", "")

    def to_str(self):
        dflt = super().to_str()
        return self.account.extra_data.get("name", dflt)


class GovIdentityProvider(OAuth2Provider):
    """
    Provider base com lógica comum de extração de campos.
    Subclasses devem implementar extract_uid, extract_common_fields e
    extract_extra_data.

    Nota sobre get_scope():
    No allauth 0.63.x, OAuth2Provider.get_scope() não recebe request:
        def get_scope(self):
            settings = self.get_settings()
            return list(settings.get("SCOPE", self.get_default_scope()))
    Subclasses devem sobrescrever get_default_scope() para definir o scope
    padrão quando SCOPE não está nos SOCIALACCOUNT_PROVIDERS settings.
    """

    account_class = GovIdentityAccount

    def get_default_scope(self):
        return ["openid", "email", "profile"]

    def extract_uid(self, data):
        raise NotImplementedError("Subclasses devem implementar extract_uid()")

    def extract_common_fields(self, data):
        raise NotImplementedError("Subclasses devem implementar extract_common_fields()")

    def extract_extra_data(self, data):
        return data

"""
allauth_govbr.base
~~~~~~~~~~~~~~~~~~
Classes base compartilhadas entre os providers Gov.br (federal)
e Acesso Cidadão ES (PRODEST).
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
    Subclasses devem implementar extract_uid e extract_common_fields.
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

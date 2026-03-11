from django.apps import AppConfig


class GovBrConfig(AppConfig):
    name = "allauth_govbr"
    verbose_name = "Login Gov.br / Acesso Cidadão ES"
    # O registro dos providers é feito em cada provider.py
    # via providers.registry.register() para compatibilidade com allauth 0.51.x

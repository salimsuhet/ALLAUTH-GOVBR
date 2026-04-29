"""
allauth_govbr.apps  (GeoNode 5.x / allauth 0.63.x)
~~~~~~~~~~~~~~~~~~
AppConfig do plugin. Constrói GovIdentityAccountAdapter após o setup
completo do Django para evitar importações circulares.
"""
import sys

from django.apps import AppConfig


class GovBrConfig(AppConfig):
    name = "allauth_govbr"
    verbose_name = "Login Gov.br / Acesso Cidadão ES"

    def ready(self):
        """
        Finaliza a construção de GovIdentityAccountAdapter injetando
        geonode.people.adapters.SocialAccountAdapter como base.
        Feito aqui (post-setup) para evitar ImportError circular.
        """
        from allauth_govbr import adapter as adapter_module

        cls = adapter_module._build_adapter_class()

        # Substitui o placeholder None pelo adapter real no módulo
        adapter_module.GovIdentityAccountAdapter = cls

        # Também injeta no sys.modules para que a string de settings
        # "allauth_govbr.adapter.GovIdentityAccountAdapter" resolva corretamente
        sys.modules[__name__]  # noop — garante que o módulo está carregado

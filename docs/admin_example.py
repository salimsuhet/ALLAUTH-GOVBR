"""
admin.py — registro opcional para expor o CPF no Django Admin do GeoNode
=========================================================================

Copie o conteúdo abaixo para o admin.py do seu projeto ou app customizado.
Não sobrescreva diretamente o admin do GeoNode em produção — use o padrão
unregister/re-register.
"""
from django.contrib import admin
from geonode.people.admin import ProfileAdmin
from geonode.people.models import Profile


admin.site.unregister(Profile)


@admin.register(Profile)
class CustomProfileAdmin(ProfileAdmin):
    list_display = ProfileAdmin.list_display + ("cpf",)
    search_fields = list(ProfileAdmin.search_fields) + ["cpf"]
    readonly_fields = list(getattr(ProfileAdmin, "readonly_fields", [])) + ["cpf"]

    fieldsets = ProfileAdmin.fieldsets + (
        (
            "Identificação Gov",
            {
                "fields": ("cpf",),
                "description": (
                    "CPF preenchido automaticamente via Login Gov.br "
                    "ou Acesso Cidadão ES. Não edite manualmente."
                ),
            },
        ),
    )

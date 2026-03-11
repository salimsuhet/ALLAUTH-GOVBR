"""
urls.py — trecho para incluir no urls.py do projeto GeoNode
===========================================================

Adicione o include abaixo no seu urls.py principal.
"""
from django.urls import include, path

# Adicione esta linha à sua lista urlpatterns existente:
urlpatterns_extra = [
    path("accounts/", include("allauth_govbr.urls")),
]

# Isso gera as rotas:
#   /accounts/govbr/login/
#   /accounts/govbr/login/callback/
#   /accounts/acessocidadaoes/login/
#   /accounts/acessocidadaoes/login/callback/
#
# Cadastre exatamente estas URLs como Redirect URIs nos respectivos portais:
#
#   Gov.br:
#     https://SEU_DOMINIO/accounts/govbr/login/callback/
#
#   Acesso Cidadão ES:
#     https://SEU_DOMINIO/accounts/acessocidadaoes/login/callback/

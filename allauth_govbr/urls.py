"""
allauth_govbr.urls
~~~~~~~~~~~~~~~~~~
Rotas para os dois providers.

Inclua em urls.py do projeto GeoNode:

    from django.urls import path, include

    urlpatterns += [
        path("accounts/", include("allauth_govbr.urls")),
    ]

Callbacks resultantes:
    /accounts/govbr/login/           → inicia fluxo Gov.br (com PKCE)
    /accounts/govbr/login/callback/  → callback Gov.br
    /accounts/acessocidadaoes/login/           → inicia fluxo AC-ES
    /accounts/acessocidadaoes/login/callback/  → callback AC-ES
"""
from django.urls import include, path

from allauth_govbr.govbr import views as govbr_views
from allauth_govbr.acessocidadao import views as aces_views

govbr_patterns = [
    path("login/", govbr_views.oauth2_login, name="govbr_login"),
    path("login/callback/", govbr_views.oauth2_callback, name="govbr_callback"),
]

aces_patterns = [
    path("login/", aces_views.oauth2_login, name="acessocidadaoes_login"),
    path("login/callback/", aces_views.oauth2_callback, name="acessocidadaoes_callback"),
]

urlpatterns = [
    path("govbr/", include(govbr_patterns)),
    path("acessocidadaoes/", include(aces_patterns)),
]

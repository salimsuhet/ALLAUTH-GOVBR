"""
Configurações mínimas do Django para rodar os testes unitários
sem depender de uma instalação completa do GeoNode.
"""
SECRET_KEY = "test-secret-key-apenas-para-testes"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth_govbr",
    "allauth_govbr.govbr",
    "allauth_govbr.acessocidadao",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

SITE_ID = 1

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# allauth-govbr — branch `geonode-5.0.x`

Plugin [django-allauth](https://django-allauth.readthedocs.io/) para autenticação com:

- 🇧🇷 **Login Único Gov.br** (federal) — `sso.acesso.gov.br`
- 🟢 **Acesso Cidadão ES** (PRODEST) — `acessocidadao.es.gov.br`

**Este branch é compatível com GeoNode 5.0.x (django-allauth 0.63.x, Django 5.2).**
Para GeoNode 4.4.x (allauth 0.51.x), use o branch `main`.

---

## Índice

1. [Requisitos](#1-requisitos)
2. [Instalação do pacote](#2-instalação-do-pacote)
3. [Registrar o app no Django](#3-registrar-o-app-no-django)
4. [Configurar as URLs](#4-configurar-as-urls)
5. [Configurar os providers](#5-configurar-os-providers)
6. [Aplicar a migration do CPF](#6-aplicar-a-migration-do-cpf)
7. [Cadastrar os sistemas nos portais](#7-cadastrar-os-sistemas-nos-portais)
8. [Variáveis de ambiente por ambiente](#8-variáveis-de-ambiente-por-ambiente)
9. [Scopes disponíveis](#9-scopes-disponíveis)
10. [Vinculação de contas por CPF](#10-vinculação-de-contas-por-cpf)
11. [Testes](#11-testes)
12. [Diferenças técnicas entre os providers](#12-diferenças-técnicas-entre-os-providers)
13. [Diferenças em relação ao branch main (GeoNode 4.x)](#13-diferenças-em-relação-ao-branch-main-geonode-4x)
14. [Solução de problemas](#14-solução-de-problemas)

---

## 1. Requisitos

| Dependência    | Versão          | Observação                         |
|----------------|-----------------|------------------------------------|
| Python         | 3.10+           |                                    |
| Django         | 4.2 ou 5.2      | GeoNode 5.0.2 usa Django 5.2.12    |
| django-allauth | 0.63.x          | Versão usada pelo GeoNode 5.0.2    |
| GeoNode        | 5.0.x           | Testado no 5.0.2                   |
| requests       | 2.28+           | Para chamadas ao endpoint /userinfo|

> ⚠️ **Atenção:** Este branch **não é compatível** com allauth 0.51.x (GeoNode 4.x).
> A API de providers e views mudou completamente entre 0.51.x e 0.63.x.

---

## 2. Instalação do pacote

### Via pip a partir do repositório (branch específico)

```bash
pip install git+https://github.com/salimsuhet/ALLAUTH-GOVBR.git@geonode-5.0.x#egg=allauth-govbr
```

### Em `requirements.txt` do geonode-project ou geonode-cluster

```txt
git+https://github.com/salimsuhet/ALLAUTH-GOVBR.git@geonode-5.0.x#egg=allauth-govbr
```

### Verificar a instalação

```bash
python -c "import allauth_govbr; print('OK')"
```

---

## 3. Registrar o app no Django

Abra o `local_settings.py` e adicione:

```python
INSTALLED_APPS += ["allauth_govbr"]
```

O plugin registra os dois providers automaticamente quando o módulo é importado
pelo `ProviderRegistry` do allauth 0.63.x.

---

## 4. Configurar as URLs

```python
# urls.py
from django.urls import path, include

urlpatterns += [
    path("accounts/", include("allauth_govbr.urls")),
]
```

| Provider          | Iniciar login                       | Callback (Redirect URI)                     |
|-------------------|-------------------------------------|---------------------------------------------|
| Gov.br            | `/accounts/govbr/login/`           | `/accounts/govbr/login/callback/`           |
| Acesso Cidadão ES | `/accounts/acessocidadaoes/login/` | `/accounts/acessocidadaoes/login/callback/` |

---

## 5. Configurar os providers

```python
# ---------------------------------------------------------------
# URLs dos servidores SSO
# ---------------------------------------------------------------
GOVBR_SSO_BASE_URL = "https://sso.acesso.gov.br"
# Homologação: GOVBR_SSO_BASE_URL = "https://sso.staging.acesso.gov.br"

ACESSOCIDADAO_ES_BASE_URL = "https://acessocidadao.es.gov.br/is"

# ---------------------------------------------------------------
# Configuração dos providers
# ---------------------------------------------------------------
SOCIALACCOUNT_PROVIDERS = {
    "govbr": {
        "SCOPE": ["openid", "email", "profile"],
        # PKCE é habilitado automaticamente pelo plugin (pkce_enabled_default=True)
        # Não é necessário OAUTH_PKCE_ENABLED neste bloco.
    },
    "acessocidadaoes": {
        "SCOPE": ["openid", "profile", "email", "agentepublico"],
    },
}

# ---------------------------------------------------------------
# Adapter com vinculação por CPF
# ---------------------------------------------------------------
SOCIALACCOUNT_ADAPTER = "allauth_govbr.adapter.GovIdentityAccountAdapter"

# Mantém o adapter de conta local do GeoNode
ACCOUNT_ADAPTER = "geonode.people.adapters.LocalAccountAdapter"

# ---------------------------------------------------------------
# Extractors de perfil para o GeoNode 5.x
# ---------------------------------------------------------------
SOCIALACCOUNT_PROFILE_EXTRACTORS = {
    "govbr": "allauth_govbr.extractors.GovBrExtractor",
    "acessocidadaoes": "allauth_govbr.extractors.AcessoCidadaoExtractor",
}

# ---------------------------------------------------------------
# Comportamento de registro e aprovação
# ---------------------------------------------------------------
SOCIALACCOUNT_AUTO_SIGNUP = False
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_APPROVAL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "optional"
```

---

## 6. Aplicar a migration do CPF

O plugin precisa adicionar o campo `cpf` ao model `Profile` do GeoNode.

```bash
# 1. Descubra a última migration do app 'people'
python manage.py showmigrations people

# 2. Copie e renomeie para o número seguinte (ex: 0039)
cp allauth_govbr/migrations/0001_add_cpf_to_profile.py \
   /caminho/geonode/people/migrations/0039_add_cpf_to_profile.py

# 3. Ajuste a dependência no arquivo copiado
#    dependencies = [("people", "0038_...")]  ← última migration real

# 4. Execute
python manage.py migrate people
```

---

## 7. Cadastrar os sistemas nos portais

### Gov.br

Cadastre a aplicação no portal do Login Único Gov.br com Redirect URI:
```
https://SEU_DOMINIO/accounts/govbr/login/callback/
```

```python
import os
SOCIALACCOUNT_PROVIDERS["govbr"]["APP"] = {
    "client_id": os.environ.get("GOVBR_CLIENT_ID"),
    "secret":    os.environ.get("GOVBR_CLIENT_SECRET"),
    "key":       "",
}
```

### Acesso Cidadão ES (PRODEST)

Entre em contato com `atendimento@prodest.es.gov.br` com Redirect URI:
```
https://SEU_DOMINIO/accounts/acessocidadaoes/login/callback/
```

```python
import os
SOCIALACCOUNT_PROVIDERS["acessocidadaoes"]["APP"] = {
    "client_id": os.environ.get("ACES_CLIENT_ID"),
    "secret":    os.environ.get("ACES_CLIENT_SECRET"),
    "key":       "",
}
```

---

## 8. Variáveis de ambiente por ambiente

```dotenv
# Gov.br
GOVBR_CLIENT_ID=seu-client-id-govbr
GOVBR_CLIENT_SECRET=seu-client-secret-govbr
GOVBR_SSO_BASE_URL=https://sso.acesso.gov.br

# Acesso Cidadão ES
ACES_CLIENT_ID=seu-client-id-acessocidadao
ACES_CLIENT_SECRET=seu-client-secret-acessocidadao
ACESSOCIDADAO_ES_BASE_URL=https://acessocidadao.es.gov.br/is
```

---

## 9. Scopes disponíveis

### Gov.br

| Scope | Campos retornados | Aprovação |
|-------|-------------------|-----------|
| `openid` | `sub` (= CPF), `iss`, `iat`, `exp` | Não |
| `email` | `email`, `email_verified` | Não |
| `profile` | `name`, `picture`, `preferred_username` | Não |
| `phone` | `phone_number`, `phone_number_verified` | Não |
| `govbr_confiabilidades` | `reliability_info` (bronze/prata/ouro) | Não |

### Acesso Cidadão ES

| Scope | Campos retornados | Aprovação |
|-------|-------------------|-----------|
| `openid` | `sub` (deprecado), `subNovo`, `apelido`, `avatarUrl` | Não |
| `profile` | `subNovo`, `apelido`, `avatarUrl` | Não |
| `email` | `email` | Não |
| `agentepublico` | `agentePublico` (true/false) | Não |
| `nome` | `nome`, `nomeValidado`, `nomeCivil`, `nomeSocial` | ⚠️ PRODEST |
| `cpf` | `cpf` | ⚠️ PRODEST |
| `dataNascimento` | `dataNascimento`, `dataNascimentoValidada` | ⚠️ PRODEST |

---

## 10. Vinculação de contas por CPF

Funciona da mesma forma que no branch main. O `GovIdentityAccountAdapter`
herda de `geonode.people.adapters.SocialAccountAdapter` neste branch para
compatibilidade total com o GeoNode 5.x.

```
Cidadão faz login via Gov.br (1ª vez)
  → CPF = sub do userinfo
  → Profile sem CPF → criado, CPF salvo

Mesmo cidadão via Acesso Cidadão ES depois
  → CPF do scope 'cpf' (PRODEST)
  → Profile com esse CPF encontrado
  → SocialAccount AC-ES conectado ao usuário existente ✓
```

**Pré-requisito para AC-ES:** scope `cpf` aprovado pelo PRODEST.

---

## 11. Testes

```bash
pip install -e ".[dev]"
pytest tests/
```

---

## 12. Diferenças técnicas entre os providers

| Característica | Gov.br | Acesso Cidadão ES |
|---|---|---|
| PKCE | **Obrigatório S256** (automático via `pkce_enabled_default=True`) | Não usa |
| `response_type` | `code` | `code id_token` |
| `response_mode` | — | `form_post` (POST externo — requer `csrf_exempt` no callback) |
| `nonce` | Opcional | **Obrigatório** (injetado em `AcessoCidadaoProvider.redirect()`) |
| Identificador único | `sub` = CPF | `subNovo` |
| Autenticação no token endpoint | `Authorization: Basic` (obrigatório) | POST body (padrão OAuth2) |
| CPF no token | `sub` (sempre disponível) | scope `cpf` (aprovação PRODEST) |
| Nível de conta | `reliability_info.level` | `agentePublico` |

---

## 13. Diferenças em relação ao branch main (GeoNode 4.x)

| Aspecto | branch `main` (GeoNode 4.x) | branch `geonode-5.0.x` (GeoNode 5.x) |
|---|---|---|
| allauth | 0.51.x | 0.63.x |
| Django | 3.2 | 5.2 |
| PKCE Gov.br | Manual (`GovBrLoginView`, `GovBrCallbackView`, `GovBrOAuth2Client`) | Automático (`pkce_enabled_default = True`) |
| Nonce AC-ES | `AcessoCidadaoLoginView.login()` | `AcessoCidadaoProvider.redirect()` |
| Basic Auth Gov.br | `GovBrOAuth2Client.get_access_token()` reimplementado | `basic_auth = True` no adapter (suporte nativo) |
| Adapter base | `DefaultSocialAccountAdapter` | `geonode.people.adapters.SocialAccountAdapter` |
| `Profile.user` | Código incorreto (`perfil.user`) | Corrigido: `usuario = perfil` (Profile IS o usuário) |
| Extractors | `extract_email_address`, `extract_phone`, `extract_zip_code` | `extract_email`, `extract_voice`, `extract_zipcode` |
| State | String CSRF (`SocialLogin.stash_state`) | Dict com PKCE/nonce (`statekit.stash_state`) |

---

## 14. Solução de problemas

### `403 Forbidden` no callback do Acesso Cidadão ES

O POST externo do form_post é bloqueado sem `@csrf_exempt`. Confirme que está
no branch `geonode-5.0.x` e que a view `AcessoCidadaoCallbackView` está ativa.

### `invalid_client` ao fazer login com Gov.br

Gov.br exige `Authorization: Basic` no token endpoint. O `GovBrOAuth2Adapter`
define `basic_auth = True`. Se o erro persistir, confirme que está no branch correto.

### `AttributeError: 'Profile' has no attribute 'user'`

Erro do branch `main` (GeoNode 4.x) onde `perfil.user` foi usado incorretamente.
No branch `geonode-5.0.x` isso está corrigido: `Profile` IS o usuário (extends AbstractUser).

### `GovIdentityAccountAdapter is None`

O `apps.py` do plugin não foi executado. Confirme que `allauth_govbr` está em
`INSTALLED_APPS` e que o Django terminou o setup antes de tentar usar o adapter.

### PKCE: `code_challenge` não está na URL de autorização

Confirme que `"govbr"` está em `SOCIALACCOUNT_PROVIDERS` no `local_settings.py`.
Se o bloco `govbr` não existir, o provider não encontra `get_settings()` e
`pkce_enabled_default` pode ser ignorado pelo fallback.

### Ativar logs de debug

```python
# local_settings.py
LOGGING["loggers"]["allauth_govbr"] = {
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
}
```

---

## Licença

MIT

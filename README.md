# allauth-govbr

Plugin [django-allauth](https://django-allauth.readthedocs.io/) para autenticação com:

- 🇧🇷 **Login Único Gov.br** (federal) — `sso.acesso.gov.br`
- 🟢 **Acesso Cidadão ES** (PRODEST) — `acessocidadao.es.gov.br`

Compatível com **GeoNode 4.x** (django-allauth 0.51.x).

Inclui **vinculação automática de contas por CPF**: um cidadão que já se autenticou via Gov.br será reconhecido automaticamente ao entrar pelo Acesso Cidadão ES, e vice-versa — sem criar contas duplicadas.

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
11. [Painel administrativo](#11-painel-administrativo)
12. [Testes](#12-testes)
13. [Diferenças técnicas entre os providers](#13-diferenças-técnicas-entre-os-providers)
14. [Solução de problemas](#14-solução-de-problemas)

---

## 1. Requisitos

| Dependência    | Versão mínima | Observação                          |
|----------------|---------------|-------------------------------------|
| Python         | 3.8           |                                     |
| Django         | 3.2           |                                     |
| django-allauth | 0.51.0        | Versão usada pelo GeoNode 4.x       |
| GeoNode        | 4.0           | Testado até 4.2                     |
| requests       | 2.28          | Para chamadas ao endpoint /userinfo |

> ⚠️ **Atenção:** O GeoNode 4.x fixa o django-allauth em `0.51.0`. Este plugin
> foi desenvolvido especificamente para essa versão. **Não use** com allauth 65.x+,
> pois a API de providers mudou completamente.

---

## 2. Instalação do pacote

### Opção A — A partir do repositório (recomendado durante desenvolvimento)

```bash
# Clone ou baixe e descompacte o repositório
git clone https://github.com/seu-org/allauth-govbr.git
cd allauth-govbr

# Instale em modo editável dentro do virtualenv do GeoNode
pip install -e .
```

### Opção B — Diretamente no ambiente do GeoNode via pip

```bash
# Dentro do virtualenv do GeoNode (normalmente em /opt/geonode/venv ou similar)
source /opt/geonode/venv/bin/activate

pip install /caminho/para/allauth-govbr
```

### Verificar a instalação

```bash
python -c "import allauth_govbr; print('OK')"
```

---

## 3. Registrar o app no Django

Abra o arquivo `local_settings.py` do GeoNode (geralmente em
`/opt/geonode/geonode/local_settings.py` ou no diretório do projeto) e adicione:

```python
INSTALLED_APPS += ["allauth_govbr"]
```

> O plugin registra os dois providers automaticamente ao ser carregado.
> Não é necessário adicionar `allauth_govbr.govbr` ou
> `allauth_govbr.acessocidadao` separadamente.

---

## 4. Configurar as URLs

Abra o `urls.py` principal do projeto GeoNode e inclua as rotas do plugin:

```python
# urls.py
from django.urls import path, include

urlpatterns += [
    path("accounts/", include("allauth_govbr.urls")),
]
```

Isso registra as seguintes rotas automaticamente:

| Provider          | Iniciar login                       | Callback (Redirect URI)                     |
|-------------------|-------------------------------------|---------------------------------------------|
| Gov.br            | `/accounts/govbr/login/`           | `/accounts/govbr/login/callback/`           |
| Acesso Cidadão ES | `/accounts/acessocidadaoes/login/` | `/accounts/acessocidadaoes/login/callback/` |

> As URLs de **Callback** são as que você deve cadastrar nos portais de integração
> de cada provider (veja a [seção 7](#7-cadastrar-os-sistemas-nos-portais)).

---

## 5. Configurar os providers

Adicione o bloco abaixo no `local_settings.py`:

```python
# ---------------------------------------------------------------
# URLs dos servidores SSO
# ---------------------------------------------------------------

# Gov.br — use a URL de staging em homologação
GOVBR_SSO_BASE_URL = "https://sso.acesso.gov.br"
# Homologação: GOVBR_SSO_BASE_URL = "https://sso.staging.acesso.gov.br"

# Acesso Cidadão ES
ACESSOCIDADAO_ES_BASE_URL = "https://acessocidadao.es.gov.br/is"

# ---------------------------------------------------------------
# Configuração dos providers
# ---------------------------------------------------------------
SOCIALACCOUNT_PROVIDERS = {
    "govbr": {
        "SCOPE": ["openid", "email", "profile"],
        # Para incluir selos de confiabilidade (bronze/prata/ouro):
        # "SCOPE": ["openid", "email", "profile", "govbr_confiabilidades"],
    },
    "acessocidadaoes": {
        # Scopes públicos — não precisam de aprovação do PRODEST
        "SCOPE": ["openid", "profile", "email", "agentepublico"],
        # Scopes que exigem aprovação formal do PRODEST (LGPD):
        # "SCOPE": ["openid", "profile", "email", "nome", "cpf", "dataNascimento"],
    },
}

# ---------------------------------------------------------------
# Adapter com vinculação por CPF
# ---------------------------------------------------------------
SOCIALACCOUNT_ADAPTER = "allauth_govbr.adapter.GovIdentityAccountAdapter"

# Mantém o adapter de conta local padrão do GeoNode
ACCOUNT_ADAPTER = "geonode.people.adapters.LocalAccountAdapter"

# ---------------------------------------------------------------
# Extractors de perfil (mapeiam os campos do provider para o GeoNode)
# ---------------------------------------------------------------
SOCIALACCOUNT_PROFILE_EXTRACTORS = {
    "govbr": "allauth_govbr.extractors.GovBrExtractor",
    "acessocidadaoes": "allauth_govbr.extractors.AcessoCidadaoExtractor",
    # Se já houver outros extractors no seu projeto, mantenha-os:
    # "facebook": "geonode.people.profileextractors.FacebookExtractor",
}

# ---------------------------------------------------------------
# Comportamento de registro e aprovação
# ---------------------------------------------------------------
SOCIALACCOUNT_AUTO_SIGNUP = False    # exige que o usuário preencha o cadastro
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_APPROVAL_REQUIRED = True     # recomendado para implantações governamentais
ACCOUNT_EMAIL_VERIFICATION = "optional"
```

---

## 6. Aplicar a migration do CPF

O plugin precisa de um campo `cpf` no model `Profile` do GeoNode para armazenar
e cruzar os CPFs entre providers.

### Passo a passo

**1. Descubra a última migration do app `people` do GeoNode:**

```bash
python manage.py showmigrations people
```

A saída será algo como:

```
people
 [X] 0001_initial
 [X] 0002_profile_extra_fields
 [X] 0030_alter_profile_something   ← esta é a última
```

**2. Copie o arquivo de migration e renomeie com o número seguinte:**

```bash
# Exemplo: se a última for 0030, renomeie para 0031
cp allauth_govbr/migrations/0001_add_cpf_to_profile.py \
   /caminho/para/geonode/people/migrations/0031_add_cpf_to_profile.py
```

**3. Ajuste a dependência dentro do arquivo copiado:**

```python
# Abra o arquivo e altere:
dependencies = [
    ("people", "0030_alter_profile_something"),  # ← coloque a última migration real
]
```

**4. Execute a migration:**

```bash
python manage.py migrate people
```

**5. Confirme que o campo foi criado:**

```bash
python manage.py shell -c "
from geonode.people.models import Profile
print(Profile._meta.get_field('cpf'))
"
# Deve imprimir: <django.db.models.fields.CharField: cpf>
```

---

## 7. Cadastrar os sistemas nos portais

### Gov.br

1. Acesse o portal de integração do Login Único Gov.br e cadastre sua aplicação.
2. Informe como **Redirect URI**:
   ```
   https://SEU_DOMINIO/accounts/govbr/login/callback/
   ```
3. Anote o **Client ID** e o **Client Secret** gerados.
4. Adicione as credenciais ao `local_settings.py`:

```python
import os

SOCIALACCOUNT_PROVIDERS["govbr"]["APP"] = {
    "client_id": os.environ.get("GOVBR_CLIENT_ID"),
    "secret":    os.environ.get("GOVBR_CLIENT_SECRET"),
    "key":       "",
}
```

Ou via Django Admin em `/admin/socialaccount/socialapp/`:
- Provider: `govbr`
- Name: `Gov.br`
- Client ID e Secret conforme cadastro
- Sites: adicione o site atual

---

### Acesso Cidadão ES (PRODEST)

1. Entre em contato com o PRODEST pelo e-mail `atendimento@prodest.es.gov.br`
   para cadastrar sua aplicação no **AC Admin**.
2. Informe como **Redirect URI**:
   ```
   https://SEU_DOMINIO/accounts/acessocidadaoes/login/callback/
   ```
3. Informe os scopes necessários (scopes não públicos exigem justificativa LGPD).
4. Adicione as credenciais ao `local_settings.py`:

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

Crie um arquivo `.env` na raiz do projeto (nunca commite este arquivo):

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

| Variável                    | Padrão                                 | Descrição                                      |
|-----------------------------|----------------------------------------|------------------------------------------------|
| `GOVBR_SSO_BASE_URL`        | `https://sso.acesso.gov.br`            | Use `https://sso.staging.acesso.gov.br` para homologação |
| `GOVBR_CLIENT_ID`           | —                                      | Client ID do Gov.br                            |
| `GOVBR_CLIENT_SECRET`       | —                                      | Client Secret do Gov.br                        |
| `ACESSOCIDADAO_ES_BASE_URL` | `https://acessocidadao.es.gov.br/is`  | URL base do AC-ES                              |
| `ACES_CLIENT_ID`            | —                                      | Client ID do AC-ES                             |
| `ACES_CLIENT_SECRET`        | —                                      | Client Secret do AC-ES                         |

---

## 9. Scopes disponíveis

### Gov.br

| Scope                           | Campos retornados                             | Aprovação |
|---------------------------------|-----------------------------------------------|-----------|
| `openid`                        | `sub` (= CPF), `iss`, `iat`, `exp`            | Não       |
| `email`                         | `email`, `email_verified`                     | Não       |
| `profile`                       | `name`, `picture`, `preferred_username`       | Não       |
| `phone`                         | `phone_number`, `phone_number_verified`       | Não       |
| `govbr_confiabilidades`         | `reliability_info` (nível: bronze/prata/ouro) | Não       |
| `govbr_confiabilidades_idtoken` | Selos incluídos no próprio `id_token`         | Não       |

### Acesso Cidadão ES

| Scope            | Campos retornados                                  | Aprovação              |
|------------------|----------------------------------------------------|------------------------|
| `openid`         | `sub` (deprecado), `subNovo`, `apelido`, `avatarUrl` | Não                  |
| `profile`        | `subNovo`, `apelido`, `avatarUrl`                  | Não                    |
| `email`          | `email`                                            | Não                    |
| `agentepublico`  | `agentePublico` (true/false)                       | Não                    |
| `nome`           | `nome`, `nomeValidado`, `nomeCivil`, `nomeSocial`  | ⚠️ Solicitar ao PRODEST |
| `cpf`            | `cpf`                                              | ⚠️ Solicitar ao PRODEST |
| `dataNascimento` | `dataNascimento`, `dataNascimentoValidada`          | ⚠️ Solicitar ao PRODEST |
| `filiacao`       | `nomePai`, `nomeMae` (e flags de validação)        | ⚠️ Solicitar ao PRODEST |

> Para solicitar scopes não públicos do AC-ES, envie e-mail para
> `atendimento@prodest.es.gov.br` com justificativa conforme a LGPD.
> Detalhes em: https://docs.developer.acessocidadao.es.gov.br/AutenticacaoUsuarios/Scopes

---

## 10. Vinculação de contas por CPF

O `GovIdentityAccountAdapter` realiza a vinculação automática:

```
Cidadão faz login via Gov.br pela 1ª vez
  → CPF extraído do campo "sub"
  → Nenhum Profile com esse CPF no banco
  → Novo usuário criado, CPF salvo no Profile

Mesmo cidadão faz login via Acesso Cidadão ES depois
  → CPF extraído do campo "cpf" (scope aprovado pelo PRODEST)
  → Profile com esse CPF encontrado
  → SocialAccount do AC-ES conectado ao mesmo usuário existente ✓
  → Sem conta duplicada
```

### Pré-requisitos para a vinculação funcionar

- **Gov.br**: sempre disponível — o `sub` no userinfo é o CPF do cidadão.
- **Acesso Cidadão ES**: requer o **scope `cpf`** aprovado pelo PRODEST.
  Sem esse scope, o AC-ES não retorna o CPF e a vinculação não ocorre
  (o sistema cria uma conta nova normalmente, sem erros).

---

## 11. Painel administrativo

Para visualizar e buscar usuários por CPF no Django Admin, copie o conteúdo
de `docs/admin_example.py` para o `admin.py` do seu projeto:

```bash
cat docs/admin_example.py >> /caminho/para/seu_app/admin.py
```

Isso adiciona o campo CPF à listagem, busca e formulário de detalhes do
model `Profile` no Admin (`/admin/people/profile/`).

---

## 12. Testes

### Instalar dependências de desenvolvimento

```bash
pip install -e ".[dev]"
```

### Rodar os testes

```bash
pytest tests/
```

### Com cobertura

```bash
pip install pytest-cov
pytest tests/ --cov=allauth_govbr --cov-report=term-missing
```

### O que é testado

- `tests/test_cpf.py`: validação de CPF, formatação, mascaramento para logs
  e extração do CPF do `extra_data` por provider.

---

## 13. Diferenças técnicas entre os providers

| Característica      | Gov.br                        | Acesso Cidadão ES                       |
|---------------------|-------------------------------|-----------------------------------------|
| PKCE                | **Obrigatório** (S256)        | Não usa                                 |
| `response_type`     | `code`                        | `code id_token`                         |
| `response_mode`     | —                             | `form_post`                             |
| `nonce`             | Opcional                      | **Obrigatório**                         |
| Identificador único | `sub` = CPF                   | `subNovo` (substitui `sub` deprecado)   |
| Campo nome          | `name`                        | `nome`, `nomeSocial`, `apelido`         |
| CPF no token        | `sub` (sempre disponível)     | scope `cpf` (aprovação pelo PRODEST)    |
| Nível de conta      | `reliability_info.level`      | `agentePublico`                         |

---

## 14. Solução de problemas

### `error: unauthorized_client` no callback

O `redirect_uri` usado não está cadastrado no portal. Verifique se a URL é
**idêntica** (incluindo barra final e capitalização) à cadastrada.

### `KeyError: 'sub'` no login

O endpoint `/userinfo` não retornou o campo `sub`. Verifique se o scope
`openid` está na lista e se o token está sendo enviado no header
`Authorization: Bearer <token>`.

### Conta duplicada criada mesmo com CPF

Verifique:
1. A migration foi aplicada: `python manage.py showmigrations people`
2. O scope `cpf` está aprovado no AC-ES
3. `SOCIALACCOUNT_ADAPTER` aponta para `allauth_govbr.adapter.GovIdentityAccountAdapter`

### Usuário redirecionado para login sem mensagem de erro

O usuário tem `is_active = False`. Ative pelo Admin ou via shell:

```bash
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.get(username='cpf_do_usuario')
u.is_active = True
u.save()
"
```

### Ativar logs de debug do plugin

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

# Instalação do allauth-govbr no GeoNode 4 via Docker

Este guia descreve como instalar o plugin
[allauth-govbr](https://github.com/salimsuhet/ALLAUTH-GOVBR) em uma instalação
do GeoNode 4 baseada em Docker, usando a estrutura do
[geonode-project](https://github.com/GeoNode/geonode-project).

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Estrutura esperada do projeto](#2-estrutura-esperada-do-projeto)
3. [Passo 1 — Adicionar o plugin ao requirements.txt](#3-passo-1--adicionar-o-plugin-ao-requirementstxt)
4. [Passo 2 — Configurar o local_settings.py](#4-passo-2--configurar-o-local_settingspy)
5. [Passo 3 — Registrar as URLs](#5-passo-3--registrar-as-urls)
6. [Passo 4 — Configurar as variáveis de ambiente (.env)](#6-passo-4--configurar-as-variáveis-de-ambiente-env)
7. [Passo 5 — Copiar a migration do CPF](#7-passo-5--copiar-a-migration-do-cpf)
8. [Passo 6 — Reconstruir a imagem Docker](#8-passo-6--reconstruir-a-imagem-docker)
9. [Passo 7 — Executar as migrations](#9-passo-7--executar-as-migrations)
10. [Passo 8 — Registrar credenciais dos providers](#10-passo-8--registrar-credenciais-dos-providers)
11. [Verificar a instalação](#11-verificar-a-instalação)
12. [Atualizar o plugin](#12-atualizar-o-plugin)
13. [Solução de problemas Docker](#13-solução-de-problemas-docker)

---

## 1. Pré-requisitos

- Docker >= 20.10 e docker-compose >= 1.29 instalados no servidor
- GeoNode 4.x rodando via **geonode-project** (não a imagem vanilla)
- Acesso ao terminal do servidor com permissões de execução do Docker
- Credenciais de acesso registradas nos portais Gov.br e/ou Acesso Cidadão ES

> ⚠️ **Por que geonode-project?**
> A instalação via imagem vanilla (`geonode/geonode:4.x`) não permite
> customizações persistentes sem rebuild. O geonode-project fornece um
> `Dockerfile` próprio onde você instala dependências adicionais —
> é o método oficial recomendado pela equipe do GeoNode.
>
> Se ainda não usa o geonode-project, consulte:
> https://github.com/GeoNode/geonode-project

---

## 2. Estrutura esperada do projeto

Após clonar o geonode-project, a estrutura é semelhante a:

```
/opt/geonode_custom/meu_geonode/
├── Dockerfile                  ← imagem customizada do Django
├── docker-compose.yml
├── .env                        ← variáveis de ambiente
├── src/
│   ├── requirements.txt        ← dependências Python adicionais
│   ├── meu_geonode/
│   │   ├── settings.py
│   │   ├── local_settings.py   ← customizações locais
│   │   └── urls.py             ← rotas do projeto
│   └── manage.py
└── ...
```

Nos comandos a seguir, substitua `meu_geonode` pelo nome real do seu projeto.

---

## 3. Passo 1 — Adicionar o plugin ao requirements.txt

Abra o arquivo `src/requirements.txt` e adicione a linha do plugin:

```txt
# allauth-govbr — Login Gov.br e Acesso Cidadão ES
git+https://github.com/salimsuhet/ALLAUTH-GOVBR.git#egg=allauth-govbr
```

> Isso instrui o pip a instalar o pacote diretamente do repositório GitHub
> a cada `docker-compose build`. Para fixar uma versão específica (recomendado
> em produção), use uma tag ou commit:
>
> ```txt
> git+https://github.com/salimsuhet/ALLAUTH-GOVBR.git@v1.0.0#egg=allauth-govbr
> ```

---

## 4. Passo 2 — Configurar o local_settings.py

Edite `src/meu_geonode/local_settings.py` e adicione o bloco abaixo.
Se o arquivo não existir, crie-o — ele é importado automaticamente pelo
`settings.py` do geonode-project.

```python
import os

# -------------------------------------------------------------------
# 1. Registra o app do plugin
# -------------------------------------------------------------------
INSTALLED_APPS += ["allauth_govbr"]

# -------------------------------------------------------------------
# 2. URLs dos servidores SSO (lidas do .env)
# -------------------------------------------------------------------
GOVBR_SSO_BASE_URL = os.environ.get(
    "GOVBR_SSO_BASE_URL",
    "https://sso.acesso.gov.br",
)
ACESSOCIDADAO_ES_BASE_URL = os.environ.get(
    "ACESSOCIDADAO_ES_BASE_URL",
    "https://acessocidadao.es.gov.br/is",
)

# -------------------------------------------------------------------
# 3. Configuração dos providers
# -------------------------------------------------------------------
SOCIALACCOUNT_PROVIDERS = {
    "govbr": {
        "SCOPE": ["openid", "email", "profile"],
        "APP": {
            "client_id": os.environ.get("GOVBR_CLIENT_ID", ""),
            "secret":    os.environ.get("GOVBR_CLIENT_SECRET", ""),
            "key":       "",
        },
    },
    "acessocidadaoes": {
        # Scopes públicos; adicione "nome", "cpf" etc. após aprovação do PRODEST
        "SCOPE": ["openid", "profile", "email", "agentepublico"],
        "APP": {
            "client_id": os.environ.get("ACES_CLIENT_ID", ""),
            "secret":    os.environ.get("ACES_CLIENT_SECRET", ""),
            "key":       "",
        },
    },
}

# -------------------------------------------------------------------
# 4. Adapter com vinculação de contas por CPF
# -------------------------------------------------------------------
SOCIALACCOUNT_ADAPTER = "allauth_govbr.adapter.GovIdentityAccountAdapter"
ACCOUNT_ADAPTER     = "geonode.people.adapters.LocalAccountAdapter"

# -------------------------------------------------------------------
# 5. Extractors de perfil para o GeoNode
# -------------------------------------------------------------------
SOCIALACCOUNT_PROFILE_EXTRACTORS = {
    "govbr":           "allauth_govbr.extractors.GovBrExtractor",
    "acessocidadaoes": "allauth_govbr.extractors.AcessoCidadaoExtractor",
}

# -------------------------------------------------------------------
# 6. Comportamento de registro
# -------------------------------------------------------------------
SOCIALACCOUNT_AUTO_SIGNUP    = False
ACCOUNT_EMAIL_REQUIRED       = True
ACCOUNT_APPROVAL_REQUIRED    = True   # recomendado para implantações gov
ACCOUNT_EMAIL_VERIFICATION   = "optional"
```

---

## 5. Passo 3 — Registrar as URLs

Edite `src/meu_geonode/urls.py` e inclua as rotas do plugin.
Procure a linha que contém `urlpatterns` e adicione o `include`:

```python
from django.urls import path, include

# Adicione ANTES do padrão de catch-all do GeoNode (se existir):
urlpatterns += [
    path("accounts/", include("allauth_govbr.urls")),
]
```

Isso registra:

| Provider          | Login                               | Callback                                    |
|-------------------|-------------------------------------|---------------------------------------------|
| Gov.br            | `/accounts/govbr/login/`           | `/accounts/govbr/login/callback/`           |
| Acesso Cidadão ES | `/accounts/acessocidadaoes/login/` | `/accounts/acessocidadaoes/login/callback/` |

> Cadastre exatamente as URLs de **Callback** nos portais Gov.br e AC-ES,
> substituindo `SEU_DOMINIO` pelo hostname real do GeoNode.

---

## 6. Passo 4 — Configurar as variáveis de ambiente (.env)

Abra o arquivo `.env` na raiz do projeto e adicione as variáveis abaixo.
Este arquivo **nunca deve ser versionado** no Git (certifique-se de que
`.env` está no `.gitignore`).

```dotenv
# -----------------------------------------------
# Gov.br — Login Único Federal
# -----------------------------------------------
GOVBR_CLIENT_ID=cole-aqui-o-client-id-govbr
GOVBR_CLIENT_SECRET=cole-aqui-o-client-secret-govbr

# Produção:    https://sso.acesso.gov.br
# Homologação: https://sso.staging.acesso.gov.br
GOVBR_SSO_BASE_URL=https://sso.staging.acesso.gov.br

# -----------------------------------------------
# Acesso Cidadão ES — PRODEST
# -----------------------------------------------
ACES_CLIENT_ID=cole-aqui-o-client-id-acessocidadao
ACES_CLIENT_SECRET=cole-aqui-o-client-secret-acessocidadao
ACESSOCIDADAO_ES_BASE_URL=https://acessocidadao.es.gov.br/is
```

> **Dica de segurança:** Em servidores de produção, considere usar
> Docker Secrets ou um cofre de credenciais (Vault, AWS Secrets Manager)
> em vez de variáveis no `.env`.

---

## 7. Passo 5 — Copiar a migration do CPF

O plugin precisa adicionar o campo `cpf` ao model `Profile` do GeoNode.
Como as migrations do GeoNode ficam dentro da imagem base, precisamos
copiá-las para o projeto antes do build.

### 7a. Descubra a última migration do app `people`

Execute temporariamente no container existente (antes do rebuild):

```bash
docker-compose exec django python manage.py showmigrations people
```

Exemplo de saída:

```
people
 [X] 0001_initial
 [X] 0002_profile_extra
 [X] 0025_alter_profile_avatar   ← esta é a última
```

### 7b. Crie a pasta de migrations no projeto e copie o arquivo

```bash
# Cria a pasta dentro do src do projeto
mkdir -p src/meu_geonode/people_migrations/

# Copia o arquivo de migration do plugin para a pasta do projeto
# (ajuste o caminho se o plugin estiver instalado em outro local)
cp /caminho/para/allauth-govbr/allauth_govbr/migrations/0001_add_cpf_to_profile.py \
   src/meu_geonode/people_migrations/0026_add_cpf_to_profile.py
```

### 7c. Edite a dependência no arquivo copiado

Abra `src/meu_geonode/people_migrations/0026_add_cpf_to_profile.py` e
ajuste a dependência para refletir a última migration real:

```python
dependencies = [
    ("people", "0025_alter_profile_avatar"),   # ← última migration existente
]
```

### 7d. Instrua o Django a usar esta pasta de migrations

Adicione ao `local_settings.py`:

```python
MIGRATION_MODULES = {
    "people": "meu_geonode.people_migrations",
}
```

> Isso diz ao Django para procurar as migrations do app `people` na pasta
> do projeto, em vez da pasta padrão dentro do pacote geonode.

---

## 8. Passo 6 — Reconstruir a imagem Docker

Com todas as alterações salvas, reconstrua a imagem:

```bash
cd /opt/geonode_custom/meu_geonode

# Força o rebuild completo (baixa o plugin do GitHub e instala)
docker-compose build --no-cache django

# Se também usar Celery (tarefas assíncronas):
docker-compose build --no-cache celery
```

> O build pode demorar alguns minutos na primeira vez.
> Acompanhe o progresso — verifique se a linha
> `Successfully installed allauth-govbr` aparece no log.

Após o build, reinicie os containers:

```bash
docker-compose up -d
```

---

## 9. Passo 7 — Executar as migrations

Com os containers rodando, aplique a migration do CPF:

```bash
docker-compose exec django python manage.py migrate people
```

Saída esperada:

```
Operations to perform:
  Apply all migrations: people
Running migrations:
  Applying people.0026_add_cpf_to_profile... OK
```

Em seguida, colete os arquivos estáticos (boa prática após qualquer build):

```bash
docker-compose exec django python manage.py collectstatic --noinput
```

---

## 10. Passo 8 — Registrar credenciais dos providers

As credenciais podem ser configuradas de duas formas:

### Via variáveis de ambiente (já feito no Passo 4)

Se você preencheu `GOVBR_CLIENT_ID`, `GOVBR_CLIENT_SECRET`, `ACES_CLIENT_ID`
e `ACES_CLIENT_SECRET` no `.env`, as credenciais já estão ativas.

### Via Django Admin (alternativa)

1. Acesse `https://SEU_DOMINIO/admin/socialaccount/socialapp/`
2. Clique em **Add Social Application**
3. Preencha:

| Campo     | Gov.br               | Acesso Cidadão ES   |
|-----------|----------------------|---------------------|
| Provider  | `govbr`              | `acessocidadaoes`   |
| Name      | Gov.br               | Acesso Cidadão ES   |
| Client ID | (do portal Gov.br)   | (do AC Admin)       |
| Secret    | (do portal Gov.br)   | (do AC Admin)       |
| Sites     | adicione o site atual | adicione o site atual |

---

## 11. Verificar a instalação

### Verificar se o provider foi registrado

```bash
docker-compose exec django python manage.py shell -c "
from allauth.socialaccount import providers
for p in providers.registry.get_list():
    print(p.id, '-', p.name)
"
```

Deve listar `govbr - Gov.br` e `acessocidadaoes - Acesso Cidadão ES`
entre os providers.

### Verificar se o campo CPF existe no Profile

```bash
docker-compose exec django python manage.py shell -c "
from geonode.people.models import Profile
f = Profile._meta.get_field('cpf')
print('Campo CPF:', f)
print('Unique:', f.unique)
"
```

### Testar as URLs

Acesse no navegador:

```
https://SEU_DOMINIO/accounts/govbr/login/
https://SEU_DOMINIO/accounts/acessocidadaoes/login/
```

Ambas devem redirecionar para os respectivos portais de login.

### Verificar os logs em tempo real

```bash
# Logs do container Django
docker-compose logs -f django

# Filtrar apenas logs do plugin
docker-compose logs -f django | grep -i "GovAdapter\|GovBr\|AcessoCidadao"
```

---

## 12. Atualizar o plugin

Quando uma nova versão do plugin for publicada:

```bash
# Rebuild da imagem (o pip vai buscar a versão mais recente do GitHub)
docker-compose build --no-cache django celery

# Reinicia os containers
docker-compose up -d

# Aplica eventuais novas migrations
docker-compose exec django python manage.py migrate
```

Se o plugin estiver fixado em uma tag (`@v1.0.0`), atualize a tag no
`requirements.txt` antes de reconstruir.

---

## 13. Solução de problemas Docker

### O provider não aparece na tela de login do GeoNode

Verifique se `allauth_govbr` está em `INSTALLED_APPS`:

```bash
docker-compose exec django python manage.py shell -c "
from django.conf import settings
print('allauth_govbr' in settings.INSTALLED_APPS)
"
```

Se retornar `False`, confira se `local_settings.py` está sendo carregado.
O geonode-project importa o local_settings automaticamente, mas verifique
se o arquivo está no caminho correto.

### Erro `ModuleNotFoundError: No module named 'allauth_govbr'`

O pacote não foi instalado no build. Verifique:

```bash
# Confirma se está na imagem
docker-compose exec django pip show allauth-govbr
```

Se não estiver, verifique se a linha foi adicionada corretamente ao
`requirements.txt` e refaça o build com `--no-cache`.

### Erro `django.db.utils.ProgrammingError: column people_profile.cpf does not exist`

A migration não foi aplicada. Execute:

```bash
docker-compose exec django python manage.py migrate people
```

Se o erro persistir, verifique se `MIGRATION_MODULES` está configurado no
`local_settings.py` e se o arquivo de migration está na pasta correta.

### Callback retorna `error: redirect_uri_mismatch`

A URL de callback cadastrada no portal não confere com a usada pelo plugin.
Confirme que a URL cadastrada é **exatamente**:

```
https://SEU_DOMINIO/accounts/govbr/login/callback/
https://SEU_DOMINIO/accounts/acessocidadaoes/login/callback/
```

Sem barra, com barra, com ou sem `www` — precisa ser idêntica ao que está
no portal de cada provider.

### Ativar logs detalhados temporariamente

```python
# local_settings.py — adicione para debug, remova em produção
LOGGING["loggers"]["allauth_govbr"] = {
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
}
LOGGING["loggers"]["allauth"] = {
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
}
```

Depois de adicionar, reinicie o container:

```bash
docker-compose restart django
docker-compose logs -f django
```

### `403 Forbidden` no callback do Acesso Cidadão ES

O `response_mode = form_post` faz o AC-ES enviar um **POST externo** para o callback.
O Django bloqueia esse POST com 403 via CSRF middleware se a view não estiver isenta.
A `AcessoCidadaoCallbackView` já aplica `@csrf_exempt` internamente — confirme que
está usando a versão corrigida do plugin (`git+https://github.com/salimsuhet/ALLAUTH-GOVBR.git`).

Se o problema persistir com a versão correta, verifique se há um proxy reverso (nginx)
que está bloqueando o POST antes de ele chegar ao Django.

### `invalid_client` ao fazer login com Gov.br

O Gov.br rejeita credenciais no corpo do POST e exige `Authorization: Basic` no token
endpoint. O `GovBrOAuth2Adapter` já configura `basic_auth = True` automaticamente.
Se ocorrer esse erro, confirme que o plugin está atualizado:

```bash
docker-compose exec django pip show allauth-govbr
# Verifique a data do commit no campo Location ou atualize com:
docker-compose build --no-cache django
```


### Verificar variáveis de ambiente dentro do container

```bash
docker-compose exec django env | grep -E "GOVBR|ACES"
```

Se as variáveis estiverem vazias, verifique se o `.env` está na raiz do
projeto e se o `docker-compose.yml` tem `env_file: .env` configurado
(o geonode-project já inclui isso por padrão).

---

## Referências

- Repositório do plugin: https://github.com/salimsuhet/ALLAUTH-GOVBR
- GeoNode Project (template Docker): https://github.com/GeoNode/geonode-project
- Documentação GeoNode Docker: https://docs.geonode.org/en/master/install/basic/index.html
- Documentação Acesso Cidadão ES: https://docs.developer.acessocidadao.es.gov.br/
- Portal Login Único Gov.br: https://www.gov.br/governodigital/pt-br/estrategias-e-governanca-digital/transformacao-digital/ferramentas/login-unico

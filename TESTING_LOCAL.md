# Guia de testes locais — SSH reverse tunnel

Este guia descreve como testar o fluxo OAuth2 completo do Gov.br e do Acesso
Cidadão ES com o GeoNode rodando na sua workstation local, usando um servidor
de datacenter como ponto de entrada público para os callbacks OAuth2.

**Domínio de homologação:** `https://geonode-dev.geobases.es.gov.br`

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Como funciona o túnel](#2-como-funciona-o-túnel)
3. [Configurar nginx no datacenter](#3-configurar-nginx-no-datacenter)
4. [Abrir o túnel SSH da workstation](#4-abrir-o-túnel-ssh-da-workstation)
5. [Configurar o GeoNode local](#5-configurar-o-geonode-local)
6. [Registrar as redirect URIs nos portais](#6-registrar-as-redirect-uris-nos-portais)
7. [Verificar se está tudo funcionando](#7-verificar-se-está-tudo-funcionando)
8. [Testes unitários sem OAuth](#8-testes-unitários-sem-oauth)
9. [Solução de problemas](#9-solução-de-problemas)

---

## 1. Pré-requisitos

| O quê | Onde | Observação |
|---|---|---|
| Servidor no datacenter | Acessível via SSH | Ubuntu 22.04+ recomendado |
| Domínio DNS | `geonode-dev.geobases.es.gov.br` | Apontando para o IP do servidor |
| Certificado TLS | No servidor | Obtido com `certbot` (Let's Encrypt) |
| GeoNode local | Workstation ou VM Vagrant | Porta `8000` exposta |
| Credenciais de homologação | Portal Gov.br e/ou AC-ES | Conta de desenvolvedor necessária |

---

## 2. Como funciona o túnel

```
Navegador / Gov.br
    │
    │  1. Usuário clica "Entrar com Gov.br"
    │     → GeoNode monta URL de autorização e redireciona
    │
    ▼
Gov.br (sso.staging.acesso.gov.br)
    │
    │  2. Usuário autentica e Gov.br envia o callback para:
    │     https://geonode-dev.geobases.es.gov.br/accounts/govbr/login/callback/
    │
    ▼
nginx no datacenter (porta 443)
    │
    │  3. nginx repassa para localhost:9000
    │
    ▼
sshd no datacenter (localhost:9000)
    │
    │  4. SSH reverse tunnel entrega na workstation local (localhost:8000)
    │
    ▼
GeoNode (workstation local, porta 8000)
    │
    │  5. GeoNode troca o código pelo token diretamente com o Gov.br
    │     (saída de rede direta da workstation — sem passar pelo datacenter)
    │
    ▼
Fluxo concluído — usuário logado
```

---

## 3. Configurar nginx no datacenter

### 3.1 Instalar nginx e certbot

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 3.2 Criar o arquivo de configuração

```bash
sudo tee /etc/nginx/sites-available/geonode-dev.conf << 'EOF'
server {
    listen 80;
    server_name geonode-dev.geobases.es.gov.br;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name geonode-dev.geobases.es.gov.br;

    ssl_certificate     /etc/letsencrypt/live/geonode-dev.geobases.es.gov.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/geonode-dev.geobases.es.gov.br/privkey.pem;

    ssl_protocols      TLSv1.2 TLSv1.3;
    ssl_ciphers        HIGH:!aNULL:!MD5;
    ssl_session_cache  shared:SSL:10m;

    # Timeout generoso para o fluxo OAuth (o GeoNode local pode demorar)
    proxy_connect_timeout 30s;
    proxy_read_timeout    60s;

    location / {
        proxy_pass         http://127.0.0.1:9000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;

        # WebSocket (hot-reload do Django)
        proxy_http_version 1.1;
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection "upgrade";
    }
}
EOF
```

### 3.3 Habilitar o site e obter o certificado

```bash
sudo ln -s /etc/nginx/sites-available/geonode-dev.conf \
           /etc/nginx/sites-enabled/geonode-dev.conf

sudo nginx -t
sudo systemctl reload nginx

# Obtém certificado Let's Encrypt (porta 80 precisa estar aberta no firewall)
sudo certbot --nginx -d geonode-dev.geobases.es.gov.br

sudo systemctl reload nginx
```

### 3.4 Ajustar sshd_config para aceitar o túnel reverso

```bash
sudo tee -a /etc/ssh/sshd_config << 'EOF'

# Permite SSH reverse tunnels (bind em localhost apenas)
AllowTcpForwarding yes
GatewayPorts      no
EOF

sudo systemctl reload sshd
```

> **Nota:** `GatewayPorts no` garante que a porta `9000` do túnel só escuta em
> `localhost` no datacenter — não fica exposta para o mundo.

---

## 4. Abrir o túnel SSH da workstation

### 4.1 Comando simples (para um teste rápido)

```bash
ssh -N \
    -R 9000:localhost:8000 \
    -o ServerAliveInterval=30 \
    -o ExitOnForwardFailure=yes \
    usuario@geonode-dev.geobases.es.gov.br
```

Mantendo o terminal aberto, qualquer requisição que chegar na porta `9000` do
datacenter será entregue na porta `8000` da sua workstation.

### 4.2 Entrada no `~/.ssh/config` (mais conveniente)

```ssh-config
Host geonode-tunnel
    HostName        geonode-dev.geobases.es.gov.br
    User            usuario
    RemoteForward   9000 localhost:8000
    ServerAliveInterval 30
    ServerAliveCountMax  3
    ExitOnForwardFailure yes
```

Depois basta rodar:

```bash
ssh -N geonode-tunnel
```

### 4.3 Manter o túnel sempre ativo com `autossh`

```bash
# Instala autossh (Ubuntu/Debian)
sudo apt install autossh

# Inicia e deixa rodando em background
autossh -M 0 -f -N geonode-tunnel

# Para parar
pkill autossh
```

Para iniciar automaticamente com o sistema, crie um serviço systemd do usuário:

```bash
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/geonode-tunnel.service << 'EOF'
[Unit]
Description=SSH reverse tunnel GeoNode dev
After=network-online.target

[Service]
ExecStart=/usr/bin/autossh -M 0 -N geonode-tunnel
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF

systemctl --user enable --now geonode-tunnel
systemctl --user status geonode-tunnel
```

---

## 5. Configurar o GeoNode local

### 5.1 Expor a VM Vagrant na porta 8000 da workstation

Se você usa o Vagrant do `geonode-cluster`, adicione o `forwarded_port`
no `Vagrantfile` ou em `envs/.env`:

```dotenv
# envs/.env (geonode-cluster)

# GeoNode VM já escuta em 192.168.56.20 — forward para a workstation
# Adicione ao Vagrantfile manualmente ou use o IP direto no SSH

GEONODE_PORT=8000
```

Ou simplesmente use o IP da VM Vagrant diretamente no túnel:

```bash
# Em vez de localhost:8000, aponta para a VM Vagrant
ssh -N -R 9000:192.168.56.20:80 usuario@geonode-dev.geobases.es.gov.br
```

### 5.2 `local_settings.py` do GeoNode

```python
# SITEURL precisa ser o domínio público — o Gov.br usa isso para montar
# a redirect_uri e para CSRF validation via ALLOWED_HOSTS
SITEURL = "https://geonode-dev.geobases.es.gov.br/"

ALLOWED_HOSTS = [
    "geonode-dev.geobases.es.gov.br",
    "localhost",
    "127.0.0.1",
    "192.168.56.20",    # IP da VM Vagrant
]

# Confia no header X-Forwarded-Proto enviado pelo nginx
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST    = True

# ── Gov.br — homologação ───────────────────────────────────────
import os

GOVBR_SSO_BASE_URL = "https://sso.staging.acesso.gov.br"

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
        "SCOPE": ["openid", "profile", "email"],
        "APP": {
            "client_id": os.environ.get("ACES_CLIENT_ID", ""),
            "secret":    os.environ.get("ACES_CLIENT_SECRET", ""),
            "key":       "",
        },
    },
}

SOCIALACCOUNT_ADAPTER = "allauth_govbr.adapter.GovIdentityAccountAdapter"
ACCOUNT_ADAPTER      = "geonode.people.adapters.LocalAccountAdapter"

SOCIALACCOUNT_PROFILE_EXTRACTORS = {
    "govbr":           "allauth_govbr.extractors.GovBrExtractor",
    "acessocidadaoes": "allauth_govbr.extractors.AcessoCidadaoExtractor",
}
```

### 5.3 Variáveis de ambiente (`.env` ou exportadas no shell)

```dotenv
GOVBR_CLIENT_ID=<client_id_homologacao>
GOVBR_CLIENT_SECRET=<client_secret_homologacao>

ACES_CLIENT_ID=<client_id_hml_acessocidadao>
ACES_CLIENT_SECRET=<client_secret_hml_acessocidadao>
```

---

## 6. Registrar as redirect URIs nos portais

### Gov.br — Portal do desenvolvedor

Acesse o portal de integração do Login Único Gov.br e cadastre:

| Campo | Valor |
|---|---|
| Nome do sistema | GeoNode DEV |
| Ambiente | Homologação |
| Redirect URI | `https://geonode-dev.geobases.es.gov.br/accounts/govbr/login/callback/` |
| Tipo de grant | Authorization Code |

> O Gov.br de homologação aceita `https` para a redirect URI. HTTP não é aceito
> mesmo em homologação.

### Acesso Cidadão ES — PRODEST

Entre em contato com `atendimento@prodest.es.gov.br` informando:

| Campo | Valor |
|---|---|
| Sistema | GeoNode DEV — SECTI-ES |
| Ambiente | Homologação |
| Redirect URI | `https://geonode-dev.geobases.es.gov.br/accounts/acessocidadaoes/login/callback/` |
| Scopes necessários | `openid profile email agentepublico` |
| response\_mode | `form_post` |

---

## 7. Verificar se está tudo funcionando

### 7.1 Checklist antes de testar

```bash
# 1. Túnel está ativo?
ssh -O check geonode-tunnel 2>&1 || echo "Túnel não encontrado"

# 2. nginx no datacenter está respondendo?
curl -I https://geonode-dev.geobases.es.gov.br

# 3. GeoNode está escutando na porta local?
curl -I http://localhost:8000 || curl -I http://192.168.56.20:80

# 4. O datacenter consegue alcançar localhost:9000?
ssh usuario@geonode-dev.geobases.es.gov.br \
    "curl -I http://localhost:9000" 2>&1
```

### 7.2 Verificar o PKCE na URL de autorização

Acesse no navegador:

```
https://geonode-dev.geobases.es.gov.br/accounts/govbr/login/
```

A URL de redirecionamento gerada deve conter os parâmetros PKCE:

```
https://sso.staging.acesso.gov.br/authorize
  ?client_id=SEU_CLIENT_ID
  &redirect_uri=https%3A%2F%2Fgeonode-dev.geobases.es.gov.br%2Faccounts%2Fgovbr%2Flogin%2Fcallback%2F
  &response_type=code
  &scope=openid+email+profile
  &code_challenge=<base64url-string>         ← deve estar presente
  &code_challenge_method=S256                ← deve ser S256
  &state=<csrf-token>
```

Se `code_challenge` estiver ausente, verifique:
- `allauth_govbr` está em `INSTALLED_APPS`
- O provider `govbr` está em `SOCIALACCOUNT_PROVIDERS`
- O GeoNode está usando o branch correto do plugin

### 7.3 Verificar logs em tempo real

```bash
# Django dev server (GeoNode local)
python manage.py runserver 0.0.0.0:8000 2>&1 | grep -E "govbr|aces|allauth|ERROR"

# Ativar logs DEBUG do plugin no local_settings.py:
LOGGING["loggers"]["allauth_govbr"] = {
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
}
```

---

## 8. Testes unitários sem OAuth

Para validar CPF, PKCE e lógica do adapter sem depender de servidores externos:

```bash
# Instalar dependências de dev
pip install -e ".[dev]"

# Rodar todos os testes
pytest tests/ -v

# Testar apenas a validação de CPF
pytest tests/test_cpf.py -v

# Verificar geração de PKCE do allauth 0.63.x (branch geonode-5.0.x)
python -c "
from allauth.socialaccount.providers.oauth2.utils import generate_code_challenge
p = generate_code_challenge()
print('verifier  :', p['code_verifier'][:30], '...')
print('challenge :', p['code_challenge'][:30], '...')
print('method    :', p['code_challenge_method'])
"

# Verificar geração manual de PKCE (branch main / GeoNode 4.x)
python -c "
import base64, hashlib, os
verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b'=').decode()
challenge = base64.urlsafe_b64encode(
    hashlib.sha256(verifier.encode()).digest()
).rstrip(b'=').decode()
print('verifier  :', verifier[:30], '...')
print('challenge :', challenge[:30], '...')
print('method    : S256')
"
```

---

## 9. Solução de problemas

### `Connection refused` ao abrir o túnel

O sshd do datacenter não tem `AllowTcpForwarding yes`. Verifique e recarregue:

```bash
sudo grep -n "AllowTcpForwarding\|GatewayPorts" /etc/ssh/sshd_config
sudo systemctl reload sshd
```

### `502 Bad Gateway` no nginx

O GeoNode local não está escutando ou o túnel caiu. Verifique:

```bash
# No datacenter — a porta 9000 está ouvindo?
ss -tlnp | grep 9000

# Se não estiver: reabrir o túnel da workstation
ssh -N geonode-tunnel
```

### `redirect_uri_mismatch` no Gov.br

A `redirect_uri` enviada pelo GeoNode não bate com o que está cadastrado no
portal do Gov.br. Verifique:

- `SITEURL` no `local_settings.py` termina com `/` e usa `https`
- A URI cadastrada no portal é exatamente:
  `https://geonode-dev.geobases.es.gov.br/accounts/govbr/login/callback/`

### `CSRF verification failed` no callback

O `SITEURL` ou o `ALLOWED_HOSTS` não inclui o domínio público. Verifique
também se `USE_X_FORWARDED_HOST = True` e
`SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` estão no
`local_settings.py`.

### `invalid_client` na troca do token (Gov.br)

O Gov.br exige `Authorization: Basic` no token endpoint. O `GovBrOAuth2Adapter`
já define `basic_auth = True`. Se o erro persistir, confirme que o plugin
instalado corresponde ao branch correto e que o `client_id`/`client_secret`
no `.env` estão corretos.

### `403 Forbidden` no callback do Acesso Cidadão ES

O `response_mode = form_post` gera um POST externo sem token CSRF. A
`AcessoCidadaoCallbackView` já aplica `@csrf_exempt`. Se ainda ocorrer 403,
verifique se há um `CSRFMiddleware` adicional ou firewall de aplicação (WAF)
bloqueando POSTs externos no nginx.

### Sessão expirada — `code_verifier não encontrado`

O `code_verifier` do PKCE é guardado na sessão Django entre o clique em
"Entrar com Gov.br" e o retorno do callback. Verifique:

- `SESSION_ENGINE` não é `django.contrib.sessions.backends.cache` sem backend
  persistente
- O `SESSION_COOKIE_AGE` é maior que o tempo máximo do fluxo OAuth (padrão
  Django: 1209600 segundos / 2 semanas — suficiente)
- Em múltiplos workers, o backend de sessão é compartilhado (Redis ou banco)

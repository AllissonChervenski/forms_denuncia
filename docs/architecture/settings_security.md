# Configurações de Segurança (forms_denuncia/settings.py)

## 📍 Arquivo: `forms_denuncia/settings.py`

## 🎯 O que é
Configurações que **endurecem** a aplicação Django para produção. Separadas em bloco `if not DEBUG:` para ativar automaticamente quando `DEBUG=False`.

---

## 💻 Código Completo

```python
# ========================================== #
# SECURITY SETTINGS (Produção)
# ========================================== #

if not DEBUG:
    # HTTPS Obrigatório
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Headers de Proteção do Navegador
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # HSTS (Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Clickjacking Protection
    X_FRAME_OPTIONS = 'DENY'

    # Referrer Policy
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
```

---

## 🔍 Linha por Linha

### Variáveis Base (Fora do if)

```python
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')]
```

| Variável | Fonte | Perigo se Errado |
|----------|-------|------------------|
| `SECRET_KEY` | `.env` | **Chave mestra** - assina cookies, tokens CSRF, password reset. Se vazada → sessões falsificadas, CSRF bypass, reset de senha. |
| `DEBUG` | `.env` | `True` em produção expõe stack traces, variáveis, SQL queries. |
| `ALLOWED_HOSTS` | `.env` | `['*']` permite **Host Header Injection** (cache poisoning, password reset poisoning). |

---

### Bloco `if not DEBUG:` - Ativação Automática

```python
if not DEBUG:
    # ... configs de produção
```

**Como funciona:**
- Desenvolvimento: `DEBUG=True` (padrão) → bloco **ignorado**.
- Produção: `.env` tem `DEBUG=False` → bloco **ativado automaticamente**.
- **Zero config manual** no deploy.

---

### HTTPS Obrigatório

```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

| Setting | O que faz | Ataca |
|---------|-----------|-------|
| `SECURE_SSL_REDIRECT` | Redirect **todo HTTP → HTTPS** (301) | SSL Stripping, sniffing |
| `SESSION_COOKIE_SECURE` | Cookie `sessionid` só via HTTPS | Session hijacking em WiFi aberto |
| `CSRF_COOKIE_SECURE` | Cookie `csrftoken` só via HTTPS | CSRF token theft |

**Requisito:** Nginx/Load Balancer deve terminar TLS e passar `X-Forwarded-Proto: https`.

---

### Headers de Proteção do Navegador

```python
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
```

| Header HTTP | Valor | Protege Contra |
|-------------|-------|----------------|
| `X-XSS-Protection` | `1; mode=block` | Reflected XSS (IE/Edge legacy, alguns ainda usam) |
| `X-Content-Type-Options` | `nosniff` | MIME sniffing (executa `.jpg` como script) |

---

### HSTS (HTTP Strict Transport Security)

```python
SECURE_HSTS_SECONDS = 31536000      # 1 ano em segundos
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

**O que é HSTS?**
Diz ao navegador: **"Só fale HTTPS com este domínio por 1 ano"**.

**Fluxo:**
1. Usuário acessa `https://exemplo.com` pela primeira vez.
2. Servidor responde com header: `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
3. Navegador **guarda** essa regra.
4. Próximas vezes: **Navegador converte HTTP → HTTPS internamente** (sem request ao servidor).
5. Mesmo se usuário digitar `http://`, vai para `https://`.

**Parâmetros:**
| Parâmetro | Valor | Significado |
|-----------|-------|-------------|
| `max-age` | 31536000 | 1 ano (365 dias × 24h × 60m × 60s) |
| `includeSubDomains` | True | Aplica a `api.exemplo.com`, `admin.exemplo.com`, etc. |
| `preload` | True | Permite submeter ao **HSTS Preload List** (Chrome/Firefox/Safari/Edge hardcoded) |

**⚠️ Cuidado:** Uma vez no Preload List, **não tem volta fácil**. Só submeta se **certeza** de HTTPS permanente.

---

### Clickjacking Protection

```python
X_FRAME_OPTIONS = 'DENY'
```

**O que faz:** Header `X-Frame-Options: DENY`.

**Clickjacking:** Atacante põe seu site em `<iframe>` invisível sobre botões maliciosos.

| Valor | Comportamento |
|-------|---------------|
| `DENY` | **Nunca** permite iframe (mais seguro) |
| `SAMEORIGIN` | Permite iframe só do mesmo domínio |
| `ALLOW-FROM uri` | Deprecado |

**Quando NÃO usar `DENY`:** Se sua app **precisa** ser embedada (ex: widget, dashboard externo).

---

### Referrer Policy

```python
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
```

**Header:** `Referrer-Policy: strict-origin-when-cross-origin`

| Cenário | Referrer Enviado |
|---------|------------------|
| Mesmo origem (HTTPS → HTTPS) | URL completa |
| Cross-origin HTTPS → HTTPS | Apenas origem (`https://exemplo.com`) |
| HTTPS → HTTP | **Nenhum** (não vaza URL segura para inseguro) |

**Por que não `no-referrer`?** Quebraria analytics legítimos. Este é equilíbrio.

---

## 🔗 Integração com Nginx (Obrigatório)

```
┌─────────────┐     HTTPS      ┌─────────────┐     HTTP      ┌─────────────┐
│   Cliente   │ ─────────────▶ │    Nginx    │ ───────────▶  │   Django    │
│  (Browser)  │ ◀───────────── │  (TLS Term) │ ◀──────────── │  (Gunicorn) │
└─────────────┘                └─────────────┘               └─────────────┘
                                      │
                                      │ Headers que Nginx DEVE passar:
                                      │ - X-Forwarded-Proto: https
                                      │ - X-Forwarded-For: <client_ip>
                                      │ - Host: <original_host>
```

**Config Nginx mínima:**
```nginx
server {
    listen 443 ssl http2;
    server_name exemplo.com;

    ssl_certificate /etc/letsencrypt/live/exemplo.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/exemplo.com/privkey.pem;

    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;  # CRÍTICO
    }
}

server {
    listen 80;
    server_name exemplo.com;
    return 301 https://$host$request_uri;  # Redirect HTTP→HTTPS
}
```

**Django precisa do `X-Forwarded-Proto`** para `SECURE_SSL_REDIRECT` não loop infinito.

---

## 🔧 Config Django para Proxy

Adicione em `settings.py` **antes** do bloco `if not DEBUG:`:

```python
# Confia no header do proxy reverso (Nginx)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Se usa X-Forwarded-For para IP real
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
```

---

## ✅ Checklist Produção

| Item | Comando/Verificação |
|------|---------------------|
| `DEBUG=False` | `.env` tem `DEBUG=False` |
| `SECRET_KEY` forte | `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `ALLOWED_HOSTS` | `.env` tem `ALLOWED_HOSTS=exemplo.com,www.exemplo.com` |
| HTTPS no Nginx | Certbot/Let's Encrypt configurado |
| `SECURE_PROXY_SSL_HEADER` | Adicionado no `settings.py` |
| HSTS Preload | Testado em https://hstspreload.org/ |
| CSP (Content Security Policy) | **Próximo passo** - `django-csp` |

---

## 📚 Referências
- [Django Security Checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [OWASP Secure Headers](https://owasp.org/www-project-secure-headers/)
- [HSTS Preload](https://hstspreload.org/)
- [Mozilla Observatory](https://observatory.mozilla.org/) - Teste seus headers
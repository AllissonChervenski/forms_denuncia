# Configuração de Rate Limiting (django-ratelimit)

## 📍 Arquivo: `forms_denuncia/settings.py`

## 🎯 O que é
Protege endpoints públicos contra **abuso, spam, bots, força bruta** limitando requisições por IP/janela de tempo.

---

## 💻 Código Completo

```python
# ========================================== #
# RATE LIMITING (django-ratelimit)
# ========================================== #

RATELIMIT_ENABLE = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() in ('true', '1', 'yes')
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_KEY_PREFIX = 'rl'

# View customizada para quando excede limite
RATELIMIT_VIEW = 'core.views.ratelimited_error'
```

---

## 🔍 Linha por Linha

### `RATELIMIT_ENABLE = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() in ('true', '1', 'yes')`

**O que faz:** Liga/desliga rate limiting via variável de ambiente.

**Decomposição:**
```python
# 1. Lê variável (padrão 'True')
valor = os.getenv('RATE_LIMIT_ENABLED', 'True')  # ex: 'True', 'false', '1', '0'

# 2. Normaliza para minúsculo
valor_lower = valor.lower()  # 'true', 'false', '1', '0'

# 3. Verifica se está na lista de "verdadeiros"
RATELIMIT_ENABLE = valor_lower in ('true', '1', 'yes')
# Resultado: True ou False (boolean Python)
```

**Por que essa complexidade?**
- `os.getenv` retorna **string** `'True'` ou `'False'`.
- Python: `bool('False') == True` (string não-vazia é truthy!).
- Precisa comparar **conteúdo**, não truthiness.

**Valores aceitos como "ligado":** `'true'`, `'1'`, `'yes'` (case-insensitive).
**Valores "desligado":** `'false'`, `'0'`, `'no'`, `''`, qualquer outro.

---

### `RATELIMIT_USE_CACHE = 'default'`

**O que faz:** Diz ao `django-ratelimit` **onde guardar os contadores**.

**Valor `'default'`** = usa `CACHES['default']` configurado acima (Redis DB 1).

**Fluxo:**
```
Request chega → django-ratelimit
    │
    ├─ Gera chave: "rl:ip:192.168.1.1:/denunciar/"
    │
    ├─ Redis GET chave → contador atual
    │
    ├─ Se contador < limite: INCR + TTL → permite
    │
    └─ Se contador >= limite: bloqueia (429)
```

**Por que Redis?**
- **Atômico:** `INCR` é atômico no Redis (race condition free).
- **TTL automático:** Expira janela (ex: 1 minuto) → limpa sozinho.
- **Compartilhado:** Múltiplos workers Gunicorn veem mesmo contador.

---

### `RATELIMIT_KEY_PREFIX = 'rl'`

**O que faz:** Prefixo nas chaves Redis: `rl:ip:1.2.3.4:/path/`.

**Por que?**
- **Namespacing:** Evita colisão com outras chaves do cache (`forms_denuncia:cache_key`).
- **Debug:** `redis-cli KEYS "rl:*"` lista só rate limits.
- **Limpeza:** `FLUSHDB` não necessário; `SCAN "rl:*"` permite deletar seletivo.

---

### `RATELIMIT_VIEW = 'core.views.ratelimited_error'`

**O que faz:** View customizada quando **limite excedido** (HTTP 429).

**Sem isso:** Retorna `HttpResponse` genérico "Too Many Requests" (sem template, sem contexto).

**View implementada em `core/views.py`:**
```python
@require_http_methods(["GET", "POST"])
def ratelimited_error(request, exception=None):
    return HttpResponse(
        'Muitas requisições. Por favor, aguarde um momento e tente novamente.',
        status=429,
        content_type='text/plain; charset=utf-8'
    )
```

**Por que customizada?**
- Mensagem em português.
- Status 429 correto (RFC 6585).
- Content-Type explícito (evita sniffing).
- Loga `exception` se quiser monitorar.

---

## 🔗 Uso nas Views (`core/views.py`)

```python
from django_ratelimit.decorators import ratelimit

# GET: 30 req/min por IP
@ratelimit(key='ip', rate='30/m', method='GET', block=True)
def index(request):
    ...

# POST: 10 req/min por IP (protege envio de formulário)
@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def index(request):
    ...

# Protocol: GET 60/m, POST 20/m
@ratelimit(key='ip', rate='60/m', method='GET', block=True)
@ratelimit(key='ip', rate='20/m', method='POST', block=True)
def protocol(request, protocolo):
    ...
```

**Parâmetros do `@ratelimit`:**
| Parâmetro | Valor | Significado |
|-----------|-------|-------------|
| `key='ip'` | `'ip'` | Identifica por IP do cliente (`request.META['REMOTE_ADDR']`) |
| `rate='30/m'` | `'30/m'` | 30 requisições por **minuto** (`s`=seg, `h`=hora, `d`=dia) |
| `method='GET'` | `'GET'`/`'POST'` | Aplica só a esse método HTTP |
| `block=True` | `True` | **Bloqueia** (retorna 429) vs só marca `request.limited=True` |

---

## 🔗 Integração com Arquitetura

```
┌─────────────┐     Rate Limit Check      ┌─────────────┐
│   Cliente   │ ────────────────────────▶ │   Django    │
│  (Browser)  │                            │   (View)    │
└─────────────┘                            └──────┬──────┘
                                                   │
                              RATELIMIT_USE_CACHE='default'
                                                   │
                                                   ▼
                                            ┌─────────────┐
                                            │    Redis    │
                                            │   (DB 1)    │
                                            │  INCR + TTL │
                                            └─────────────┘
```

- **Redis** faz o trabalho pesado (contador atômico + expiração).
- **django-ratelimit** é middleware leve que sabe falar com Redis via `django-redis`.
- **Nenhuma query no PostgreSQL** para rate limit (performance).

---

## ⚙️ Ajustes por Ambiente

| Ambiente | `RATE_LIMIT_ENABLED` | `rate` sugerido |
|----------|---------------------|-----------------|
| Desenvolvimento | `False` | - (desligado para testes) |
| Staging | `True` | `100/m` (mais permissivo) |
| Produção | `True` | `30/m` GET, `10/m` POST |

---

## 📚 Referências
- [django-ratelimit docs](https://django-ratelimit.readthedocs.io/)
- [Rate Limiting Strategies](https://docs.djangoproject.com/en/5.2/topics/cache/#rate-limiting)
- [RFC 6585 - HTTP 429](https://tools.ietf.org/html/rfc6585)
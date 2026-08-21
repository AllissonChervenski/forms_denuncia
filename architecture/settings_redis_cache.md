# Configuração Redis: Cache, Sessions e Celery

## 📍 Arquivo: `forms_denuncia/settings.py`

## 🎯 O que é
Configura o **Redis** para três papéis simultâneos:
1. **Cache Framework** - `CACHES['default']` (views, queries, rate limit)
2. **Session Engine** - `SESSION_ENGINE` (login do admin/dashboard)
3. **Celery Broker/Backend** - `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` (filas de tasks)

---

## 💻 Código Completo

```python
# ========================================== #
# REDIS CACHE (Django Cache Framework)
# ========================================== #

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://redis:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
        },
        'KEY_PREFIX': 'forms_denuncia',
        'TIMEOUT': 300,  # 5 minutos default
    }
}

# Session backend (usa o mesmo Redis acima)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# ========================================== #
# CELERY E REDIS (Mensageria)
# ========================================== #

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Sao_Paulo'

CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos
```

---

## 🔍 Linha por Linha - Cache Framework

### `'BACKEND': 'django_redis.cache.RedisCache'`
**O que faz:** Usa a biblioteca `django-redis` (wrapper robusto sobre `redis-py`).
- Suporta **connection pooling**, **pipeline**, **scan** (não `keys *`).
- Melhor que o backend nativo `django.core.cache.backends.redis.RedisCache` (Django 4+).

### `'LOCATION': os.getenv('REDIS_URL', 'redis://redis:6379/1')`
**O que faz:** String de conexão Redis.
- **`redis://`** - Protocolo.
- **`redis`** - Host = nome do serviço Docker Compose (DNS interno).
- **`6379`** - Porta padrão.
- **`/1`** - **Database número 1** (separado do Celery que usa `/0`).
- **Por que DB separado?** Isolamento: `FLUSHDB` no cache não apaga filas Celery.

### `'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'}`
**O que faz:** Cliente padrão com suporte a:
- **Pipeline** (batch de comandos)
- **Scan iterator** (não bloqueia Redis)
- **Compressão** opcional
- **Serialização** inteligente

### `'CONNECTION_POOL_KWARGS': {'max_connections': 50, 'retry_on_timeout': True}`
| Parâmetro | Valor | Por que |
|-----------|-------|---------|
| `max_connections` | 50 | Pool compartilhado entre workers Gunicorn + Celery. 50 evita "connection pool exhausted". |
| `retry_on_timeout` | True | Resiliência: rede instável não derruba request. |

### `'KEY_PREFIX': 'forms_denuncia'`
**O que faz:** Prefixa **todas** as chaves: `forms_denuncia:cache_key`.
- **Por que?** Multi-tenancy futuro ou múltiplos apps no mesmo Redis.
- Evita colisão de chaves (`cache_key` vs `outro_app:cache_key`).

### `'TIMEOUT': 300` (5 minutos)
**O que faz:** TTL padrão se view não especificar.
- `cache.set(key, value)` → expira em 300s.
- `cache.set(key, value, timeout=60)` → sobrescreve.

---

## 🔍 Linha por Linha - Sessions

### `SESSION_ENGINE = 'django.contrib.sessions.backends.cache'`
**O que faz:** Armazena sessão **no Redis** (não no banco, não em cookie).
- **Vantagem:** Login instantâneo, escalável, não enche tabela `django_session`.
- **Requer:** `SESSION_CACHE_ALIAS = 'default'` (usa o `CACHES['default']` acima).

### `SESSION_CACHE_ALIAS = 'default'`
Aponta para o cache configurado acima (Redis DB 1).

---

## 🔍 Linha por Linha - Celery

### `CELERY_BROKER_URL = 'redis://redis:6379/0'`
**O que faz:** **Message Broker** - onde o Django "joga" as tasks.
- **DB 0** dedicado ao Celery (separado do Cache DB 1).
- Producer (Django) faz `LPUSH` na lista; Consumer (Worker) faz `BRPOP`.

### `CELERY_RESULT_BACKEND = 'redis://redis:6379/0'`
**O que faz:** Onde o Worker guarda o **resultado** da task.
- Mesmo Redis/DB do broker (simples, performático).
- Permite `AsyncResult.ready()`, `.get()`, `.status`.

### Serialização JSON
```python
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
```
**Por que JSON?**
- Seguro (não executa código como `pickle`).
- Interoperável (outros languages poderiam ler).
- Leve, legível, padrão web.

### `CELERY_TIMEZONE = 'America/Sao_Paulo'`
**O que faz:** Timezone **do Celery** (agendamento, logs, timestamps).
- **Diferente de `TIME_ZONE` do Django?** Sim, Celery roda processo separado.
- Beat usa isso para `crontab(hour=9)` = 9h BRT.

### `CELERY_TASK_TRACK_STARTED = True`
**O que faz:** Atualiza status para `STARTED` quando worker **inicia** execução.
- Permite Flower mostrar "em andamento" (não só PENDING/SUCCESS).

### `CELERY_TASK_TIME_LIMIT = 30 * 60` (30 min)
**O que faz:** **Hard limit** - Worker é **matado (SIGKILL)** se task passar disso.
- Protege contra tasks travadas (loop infinito, deadlock, I/O eterno).
- `CELERY_TASK_SOFT_TIME_LIMIT` (padrão) lança `SoftTimeLimitError` (catchable).

---

## 🔗 Diagrama de Integração

```
┌─────────────────────────────────────────────────────────────┐
                        REDIS (Container)                      
│  DB 0 (Celery)          │  DB 1 (Cache/Sessions)            │
├─────────────────────────┼───────────────────────────────────┤
│  Broker (Filas)         │  Cache Framework                  │
│  Result Backend         │  - View caching                   │
│                         │  - Rate limit counters            │
│  - celery               │  - Session storage                │
│  - celeryev (events)    │  KEY_PREFIX: forms_denuncia       │
└─────────────────────────┴───────────────────────────────────┘
           ▲                           ▲
           │ CELERY_BROKER_URL         │ CACHES['default'].LOCATION
           │ CELERY_RESULT_BACKEND     │ SESSION_ENGINE
┌──────────┴──────────┐       ┌────────┴────────┐
│   Django App        │       │  Celery Worker  │
│   (Web + Workers)   │       │  (Consumidor)   │
└─────────────────────┘       └─────────────────┘
```

---

## ⚙️ Decisões de Design

| Decisão | Justificativa |
|---------|---------------|
| Redis único, DBs separados | Operação simples (1 container), isolamento lógico |
| `django-redis` vs nativo | Pooling, scan, pipeline, compressão prontos |
| Cache = Sessions | Simplicidade: 1 config, 1 pool, escala igual |
| JSON serialization | Segurança + debugabilidade |
| TIME_LIMIT 30min | Tasks de imagem (EXIF) são rápidas; 30min = safety net |

---

## 📚 Referências
- [django-redis docs](https://django-redis.readthedocs.io/)
- [Django Cache Framework](https://docs.djangoproject.com/en/5.2/topics/cache/)
- [Celery Configuration](https://docs.celeryq.dev/en/stable/userguide/configuration.html)
- [Redis DBs vs Multiple Instances](https://redis.io/docs/latest/operate/oss_and_stack/management/database/)
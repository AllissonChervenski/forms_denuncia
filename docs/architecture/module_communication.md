# Como os Módulos se Comunicam

## 🎯 Visão Geral

O sistema segue arquitetura **desacoplada** onde módulos se comunicam via:
1. **Django ORM** (PostgreSQL) - Dados persistentes
2. **Redis** - Cache, Sessions, Rate Limit, Celery Broker
3. **Python Imports** - Código síncrono (Views → Models → Tasks)
4. **Celery Protocol** - Tasks assíncronas (Producer → Broker → Consumer)

---

## 🔗 Mapa de Comunicação

```
┌─────────────┐     ORM/DB      ┌─────────────┐
│   Models    │ ◀─────────────▶ │ PostgreSQL  │
│ (core, dash)│   Persistência  │  (Dados)    │
└──────┬──────┘                 └─────────────┘
       │
       │ Python Import
       ▼
┌─────────────┐     Redis        ┌─────────────┐
│   Views     │ ◀──────────────▶ │    Redis    │
│ (core/views)│  Cache/Rate/Broker│  (Memória)  │
└──────┬──────┘                 └──────┬──────┘
       │                               │
       │ .delay()                      │ BRPOP/LPUSH
       ▼                               ▼
┌─────────────────────────────────────────────────┐
│              CELERY WORKER                      │
│  - Importa tasks                                │
│  - Executa limpar_exif_imagem                   │
│  - Acessa Models (ORM) → PostgreSQL             │
│  - Lê/Escreve Media Volume                      │
└─────────────────────────────────────────────────┘
```

---

## 1. Views ↔ Models (Síncrono, ORM)

```python
# core/views.py
from .models import Denuncia, Cidades, Evidencia

def index(request):
    # READ
    denuncia = Denuncia.objects.filter(protocolo=protocolo).first()
    
    # WRITE
    denuncia = form.save()  # INSERT
    evidencia = Evidencia(denuncia=denuncia, imagem=f)
    evidencia.save()  # INSERT + file save
```

**Fluxo:**
```
View → Model Manager → QuerySet → SQL → PostgreSQL
                        ▲
                        │
                 Retorna Model Instance
```

---

## 2. Views ↔ Redis (Cache, Rate Limit, Sessions)

### Cache Framework
```python
# settings.py
CACHES = {'default': {'BACKEND': 'django_redis.cache.RedisCache', ...}}

# View
from django.core.cache import cache
cache.set('key', 'value', 300)  # SETEX key 300 value
cache.get('key')  # GET key
```

### Rate Limit (django-ratelimit)
```python
# Decorator usa internamente:
# redis.incr('rl:ip:1.2.3.4:/path/') + expire(60)
@ratelimit(key='ip', rate='30/m', method='GET', block=True)
```

### Sessions
```python
# settings.py
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
# request.session['user_id'] = 123 → Redis SETEX session_key 1209600 data
```

---

## 3. Views → Celery (Producer → Broker)

```python
# core/views.py
from .tasks import limpar_exif_imagem

def index(request):
    evidencia.save()
    limpar_exif_imagem.delay(evidencia.id)  # ASYNC
```

**O que acontece internamente:**
```python
# limpar_exif_imagem.delay(42)
# 1. Serializa: {"args": [42], "kwargs": {}}
# 2. Celery cria mensagem:
{
    "body": "eyJhcmdzIjogWzQyXSwgImthcmdzIjoge319",  # base64 JSON
    "headers": {"task": "core.tasks.limpar_exif_imagem", "id": "uuid", ...},
    "properties": {"delivery_mode": 2, "priority": 0}
}
# 3. Redis: LPUSH celery <mensagem>
```

---

## 4. Celery Worker → Tudo (Consumer)

```python
# core/tasks.py
@shared_task
def limpar_exif_imagem(evidencia_id):
    # 1. ORM → PostgreSQL
    evidencia = Evidencia.objects.get(id=evidencia_id)
    
    # 2. File System → Media Volume
    img = Image.open(evidencia.imagem.path)
    ...
    imagem_limpa.save(evidencia.imagem.path)
    
    # 3. Return → Redis Result Backend
    return "SUCESSO: EXIF limpo..."
```

**Arquitetura Worker:**
```
Redis BRPOP → Deserializa → Executa Task
                    │
                    ├─ ORM (SELECT/UPDATE) → PostgreSQL
                    ├─ Pillow (read/write) → Media Volume
                    └─ Return → Redis SETEX celery-task-meta-{id}
```

---

## 5. Celery Beat → Redis (Scheduler)

```python
# celery-beat container
# A cada 30s:
# 1. SELECT * FROM celery_beat_periodictask WHERE enabled=1
# 2. Para cada due: LPUSH celery {task_message}
# 3. UPDATE last_run_at
```

---

## 6. Flower → Redis (Monitoramento)

```python
# Flower conecta no Redis e:
# - INFO keyspace (memória, keys)
# - LRANGE celery (filas)
# - GET celery-task-meta-* (resultados)
# - PUBSUB celeryev.* (eventos tempo real)
```

---

## 7. Nginx (Futuro) → Web

```
Client → Nginx:443 (TLS)
    │
    ├─ /static/ → serve arquivo (volume static_volume)
    ├─ /media/  → serve arquivo (volume media_volume)
    └─ /        → proxy_pass http://web:8000
                    │
                    ├─ X-Forwarded-Proto: https
                    ├─ X-Forwarded-For: <ip>
                    └─ Host: <host>
```

---

## 📋 Resumo de Protocolos

| Comunicação | Protocolo | Porta | Dados |
|-------------|-----------|-------|-------|
| Django ↔ PostgreSQL | PostgreSQL Wire | 5432 | SQL/Resultsets |
| Django ↔ Redis | RESP (Redis) | 6379 | Commands/Responses |
| Celery ↔ Redis | RESP + Celery Protocol | 6379 | Serialized Messages |
| Flower ↔ Redis | RESP | 6379 | Commands/Events |
| Nginx ↔ Gunicorn | HTTP/1.1 | 8000 | HTTP Requests |
| Client ↔ Nginx | HTTPS/HTTP2 | 443/80 | HTTP Requests |

---

## 🔐 Isolamento e Segurança

| Limite | Como |
|--------|------|
| **Network** | Docker network `forms_denuncia_network` - só containers internos |
| **Secrets** | `.env` → `environment:` no compose (não no código) |
| **User** | Containers rodam como `appuser` (UID 999) |
| **Volumes** | `media_volume` compartilhado apenas `web` + `celery` |
| **Rate Limit** | Redis atômico - não burla com múltiplos workers |

---

## 📚 Referências
- [Django Database API](https://docs.djangoproject.com/en/5.2/topics/db/queries/)
- [Celery Protocol](https://docs.celeryq.dev/en/stable/internals/protocol.html)
- [Redis Protocol](https://redis.io/docs/latest/develop/reference/protocol-spec/)
- [Django Cache Framework](https://docs.djangoproject.com/en/5.2/topics/cache/)
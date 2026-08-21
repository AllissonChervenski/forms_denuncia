# Docker Compose - Celery Worker

## 📍 Arquivo: `docker-compose.yml` (serviço `celery`)

## 🎯 O que é
Container que executa **tasks assíncronas** (background jobs). Consome filas do Redis, executa código Python, acessa PostgreSQL e volumes de mídia.

---

## 💻 Código Completo

```yaml
# 4. Celery Worker
celery:
  build: .
  command: celery -A forms_denuncia worker -l INFO --concurrency=4 --max-tasks-per-child=1000
  volumes:
    - .:/app
    - media_volume:/app/media
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
    web:
      condition: service_started
  environment:
    - DEBUG=${DEBUG:-True}
    - SECRET_KEY=${SECRET_KEY}
    - POSTGRES_DB=${POSTGRES_DB}
    - POSTGRES_USER=${POSTGRES_USER}
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    - POSTGRES_HOST=db
    - POSTGRES_PORT=5432
    - REDIS_URL=redis://redis:6379/1
    - CELERY_BROKER_URL=redis://redis:6379/0
    - CELERY_RESULT_BACKEND=redis://redis:6379/0
  restart: always
```

---

## 🔍 Linha por Linha

### `build: .`
Usa **mesmo Dockerfile** do `web` - mesmo ambiente, dependências, usuário non-root.

### `command: celery -A forms_denuncia worker -l INFO --concurrency=4 --max-tasks-per-child=1000`

| Flag | Valor | Função |
|------|-------|--------|
| `-A forms_denuncia` | App | Importa `forms_denuncia.celery.app` |
| `worker` | Modo | Consumidor (não beat, não flower) |
| `-l INFO` | Log | Nível INFO (tasks started/succeeded) |
| `--concurrency=4` | Processos | **4 processos fork** (pool prefork) |
| `--max-tasks-per-child=1000` | Reciclagem | Reinicia processo a cada 1000 tasks |

#### `--concurrency=4` - Pool Prefork
```
Master (PID 1)
    │
    ├─ Worker 1 (PID 101) ── Task → Task → Task
    ├─ Worker 2 (PID 102) ── Task → Task → Task
    ├─ Worker 3 (PID 103) ── Task → Task → Task
    └─ Worker 4 (PID 104) ── Task → Task → Task
```
- Cada worker = **1 task por vez** (sequencial dentro do processo).
- 4 workers = **4 tasks simultâneas**.
- Processos isolados: crash de um não afeta outros.

#### `--max-tasks-per-child=1000` - Reciclagem
```
Worker executa 1000 tasks → Exit(0) → Master forka novo worker limpo
```
**Por que?** Python não devolve memória ao OS (fragmentação). Tasks de imagem (Pillow) alocam muita memória temporária.

### `volumes:`
```yaml
- .:/app              # Código (hot reload dev)
- media_volume:/app/media  # Imagens originais + processadas
```
- `media_volume` **compartilhado com `web`** - worker lê/escreve mesmas imagens.

### `depends_on:` com Healthchecks
```yaml
depends_on:
  db:
    condition: service_healthy
  redis:
    condition: service_healthy
  web:
    condition: service_started
```
Ordem: DB → Redis → Web → Celery.

### `environment:` - Variáveis Críticas
| Variável | Valor | Uso no Worker |
|----------|-------|---------------|
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Onde buscar tasks (`BRPOP`) |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` | Onde salvar resultado (`SET`) |
| `POSTGRES_HOST=db` | DNS Docker | Django ORM conecta no Postgres |
| `REDIS_URL=redis://redis:6379/1` | DB 1 | Cache/Sessions (se worker usa) |

### `restart: always`
Worker crítico - sempre reinicia.

---

## 🔗 Arquitetura Worker

```
┌─────────────────────────────────────────────────────────────────┐
│                      CELERY WORKER CONTAINER                    │
│  celery -A forms_denuncia worker --concurrency=4               │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Process 1  │  │  Process 2  │  │  Process 3  │  ...        │
│  │  (PID 101)  │  │  (PID 102)  │  │  (PID 103)  │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          ▼                                       │
│                 ┌─────────────────┐                              │
│                 │  Redis Broker   │                              │
│                 │  (DB 0)         │                              │
│                 │  BRPOP 'celery' │                              │
│                 └─────────────────┘                              │
│                          │                                       │
│                          ▼                                       │
│                 ┌─────────────────┐                              │
│                 │  PostgreSQL     │                              │
│                 │  (ORM queries)  │                              │
│                 └─────────────────┘                              │
│                          │                                       │
│                          ▼                                       │
│                 ┌─────────────────┐                              │
│                 │  Media Volume   │                              │
│                 │  (Imagens)      │                              │
│                 └─────────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Monitoramento

```bash
# Stats workers
docker compose exec celery celery -A forms_denuncia inspect stats

# Tasks registradas
docker compose exec celery celery -A forms_denuncia inspect registered

# Filas ativas
docker compose exec celery celery -A forms_denuncia inspect active_queues

# Logs tempo real
docker compose logs -f celery
```

**Output `inspect stats`:**
```json
{
  "celery@worker1": {
    "broker": { "connected": true, ... },
    "prefetch_count": 4,
    "total": {
      "core.tasks.limpar_exif_imagem": 142
    },
    "rusage": { "utime": 1234, "stime": 567, "maxrss": 89012 }
  }
}
```

---

## ⚙️ Ajustes Produção

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 1G
    reservations:
      cpus: '1'
      memory: 512M

logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## 📚 Referências
- [Celery Worker Guide](https://docs.celeryq.dev/en/stable/userguide/workers.html)
- [Prefork Pool](https://docs.celeryq.dev/en/stable/userguide/concurrency.html#prefork-pool)
- [Worker Optimization](https://docs.celeryq.dev/en/stable/userguide/optimizing.html)
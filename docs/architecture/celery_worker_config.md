# Celery Worker Configuration (docker-compose.yml)

## 📍 Arquivo: `docker-compose.yml` (serviço `celery`)

## 🎯 O que é
Container que roda o **consumidor de tarefas** Celery. Executa tasks assíncronas em background (fora do request/response HTTP).

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
**O que faz:** Usa o **mesmo Dockerfile** do serviço `web`.
- Garante: mesmas dependências, mesmo código, mesma versão Python.
- Imagem construida uma vez, reutilizada.

### `command: celery -A forms_denuncia worker -l INFO --concurrency=4 --max-tasks-per-child=1000`

| Flag | Valor | Significado |
|------|-------|-------------|
| `-A forms_denuncia` | App | Importa `forms_denuncia.celery.app` |
| `worker` | Modo | Inicia consumidor (não beat, não flower) |
| `-l INFO` | Log level | Mostra INFO+ (tasks iniciadas, finalizadas) |
| `--concurrency=4` | Processos | **4 processos fork** (pool prefork) |
| `--max-tasks-per-child=1000` | Reciclagem | Reinicia processo a cada 1000 tasks |

#### `--concurrency=4` - Pool Prefork
```
Master Process (celery)
    │
    ├─ Worker Process 1 (pid 101)
    ├─ Worker Process 2 (pid 102)
    ├─ Worker Process 3 (pid 103)
    └─ Worker Process 4 (pid 104)
```
- Cada processo = **1 task por vez** (sequencial dentro do processo).
- 4 processos = **4 tasks simultâneas**.
- **Por que 4?** CPU cores do container (ajustar conforme `deploy.resources.limits.cpus`).

#### `--max-tasks-per-child=1000` - Reciclagem de Memória
**Problema:** Python não libera memória para OS facilmente (fragmentação).
```
Processo executa 1000 tasks → Memória cresce → Reinicia limpo → Memória volta ao baseline
```
- Evita **Memory Leak** em tasks que alocam muita memória (imagens, PDFs).
- 1000 = equilibra overhead de fork vs controle de memória.

### `volumes:`
```yaml
- .:/app              # Código fonte (hot reload dev)
- media_volume:/app/media  # Arquivos de mídia (imagens processadas)
```
- `media_volume` **compartilhado** com `web` - worker lê/escreve mesmos arquivos.

### `depends_on:` com Healthchecks
```yaml
depends_on:
  db:
    condition: service_healthy      # Espera pg_isready
  redis:
    condition: service_healthy      # Espera redis-cli ping
  web:
    condition: service_started      # Só espera container subir
```
**Ordem de inicialização garantida:**
1. DB (Postgres) → Healthy
2. Redis → Healthy
3. Web → Started
4. Celery → Inicia

### `environment:` - Variáveis Críticas
| Variável | Valor | Por que |
|----------|-------|---------|
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Onde buscar tasks |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` | Onde guardar resultados |
| `POSTGRES_HOST=db` | DNS Docker | Conecta no Postgres |
| `REDIS_URL=redis://redis:6379/1` | DB 1 | Cache/Sessions (não usado pelo worker diretamente, mas Django ORM usa) |

### `restart: always`
**Política de reinício:**
| Política | Comportamento |
|----------|---------------|
| `no` | Nunca reinicia (padrão) |
| `on-failure` | Reinicia se exit code ≠ 0 |
| `always` | **Sempre reinicia** (crash, OOM, kill, host reboot) |
| `unless-stopped` | Sempre exceto `docker compose stop` |

**Por que `always`?** Worker é crítico - se morrer, tasks param de ser processadas.

---

## 🔗 Arquitetura do Worker

```
┌─────────────────────────────────────────────────────────────────┐
│                     CELERY WORKER CONTAINER                     │
│  celery -A forms_denuncia worker -l INFO --concurrency=4       │
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

## ⚙️ Ajustes para Produção

```yaml
deploy:
  resources:
    limits:
      cpus: '2'           # Limita CPU (evita roubar do host)
      memory: 1G          # Limita RAM (OOM kill controlado)
    reservations:
      cpus: '1'
      memory: 512M

# Logging estruturado
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## 📊 Monitoramento

```bash
# Ver tasks processadas
docker compose exec celery celery -A forms_denuncia inspect stats

# Ver filas ativas
docker compose exec celery celery -A forms_denuncia inspect active_queues

# Ver workers registrados
docker compose exec celery celery -A forms_denuncia inspect registered

# Logs em tempo real
docker compose logs -f celery
```

**Output típico `inspect stats`:**
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

## 📚 Referências
- [Celery Worker Guide](https://docs.celeryq.dev/en/stable/userguide/workers.html)
- [Prefork Pool](https://docs.celeryq.dev/en/stable/userguide/concurrency.html#prefork-pool)
- [Docker Compose Deploy](https://docs.docker.com/compose/compose-file/deploy/)
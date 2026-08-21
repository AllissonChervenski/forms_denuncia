# Configurações Celery (forms_denuncia/settings.py)

## 📍 Arquivo: `forms_denuncia/settings.py` (seção Celery)

## 🎯 O que é
Configurações que o **Celery** lê ao iniciar (via `app.config_from_object('django.conf:settings', namespace='CELERY')`). Todas começam com `CELERY_`.

---

## 💻 Código Completo

```python
# ========================================== #
# CELERY E REDIS (Mensageria)
# ========================================== #

# Onde o Django vai pendurar as tarefas (Message Broker)
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')

# Onde o celery guarda o resultado final da tarefa
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

# Formato de envio dos dados para a fila
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Sao_Paulo'

# Task settings
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos
```

---

## 🔍 Linha por Linha

### `CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')`

**Conceito:** **Message Broker** = "Correio" onde o Django deixa as tarefas.

```
Django (Producer)          Redis Broker           Celery Worker (Consumer)
     │                         │                         │
     │  task.delay(args)       │                         │
     ├────────────────────────▶│                         │
     │                         │   LPUSH 'celery'        │
     │                         │   {task_id, args, ...}  │
     │                         │◀────────────────────────┤  BRPOP (bloqueia)
     │                         │                         │
     │                         │   Executa task          │
     │                         │                         │
     │                         │   SET result_key        │
     │                         │   {status, result}      │
     │                         │────────────────────────▶│
```

**Parâmetros da URL:**
| Parte | Valor | Significado |
|-------|-------|-------------|
| `redis://` | Protocolo | Redis padrão (não TLS) |
| `redis` | Host | Serviço Docker Compose |
| `6379` | Porta | Padrão Redis |
| `/0` | Database | **DB 0** = dedicado ao Celery |

**Por que variável de ambiente?**
- Produção pode usar Redis gerenciado (AWS ElastiCache, Azure Redis) com URL diferente.
- Permite `redis://:senha@host:6379/0` se tiver auth.

---

### `CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')`

**Conceito:** Onde o **resultado** da task é guardado após execução.

**Fluxo:**
1. Worker termina task
2. Serializa resultado (JSON)
3. `SET celery-task-meta-{task_id} {resultado} EX 86400` (TTL 24h default)
4. Django pode consultar: `AsyncResult(task_id).get()`

**Mesmo Redis do Broker?** Sim, simples e performático. Em alta escala, separa-se.

---

### Serialização JSON

```python
CELERY_ACCEPT_CONTENT = ['json']      # Só aceita JSON (segurança)
CELERY_TASK_SERIALIZER = 'json'       # Como serializa args ao enviar
CELERY_RESULT_SERIALIZER = 'json'     # Como serializa retorno
```

**Por que JSON e não pickle?**
| Aspecto | JSON | Pickle |
|---------|------|--------|
| Segurança | ✅ Seguro (dados apenas) | ❌ Executa código arbitrário |
| Interoperabilidade | ✅ Qualquer linguagem | ❌ Só Python |
| Debug | ✅ Legível no Redis CLI | ❌ Binário |
| Performance | Bom | Ligeiramente melhor |

**`ACCEPT_CONTENT = ['json']`** = **Recusa** tasks serializadas de outra forma (proteção contra ataque).

---

### `CELERY_TIMEZONE = 'America/Sao_Paulo'`

**Timezone do Celery** (separado do Django `TIME_ZONE`).

**Por que separado?**
- Celery roda em **processo próprio** (worker/beat).
- Beat usa para `crontab(hour=9)` = 9h **nesse timezone**.
- Logs do worker mostram horário local.

---

### `CELERY_TASK_TRACK_STARTED = True`

**Estados de uma Task:**
```
PENDING → STARTED → SUCCESS/FAILURE
         ↑
    Track_STARTED=True
```

**Sem isso:** Pula de `PENDING` direto para `SUCCESS/FAILURE`.
**Com isso:** Flower/Django Admin mostram **"Em andamento"** em tempo real.

---

### `CELERY_TASK_TIME_LIMIT = 30 * 60` (30 minutos)

**Hard Time Limit** - Worker é **matado (SIGKILL)** se passar.

```
Soft Limit (configurável)     Hard Limit (TIME_LIMIT)
      │                            │
      ▼                            ▼
┌─────────┐                  ┌─────────┐
│ Levanta  │                  │ SIGKILL │
│ SoftTime │                  │ Processo│
│ LimitErr │                  │ morre   │
│ (catch)  │                  │ (uncatch)│
└─────────┘                  └─────────┘
```

**Por que 30 min?**
- Task atual: `limpar_exif_imagem` = milissegundos.
- Futuro: geração de PDFs, relatórios, envio em massa de e-mails.
- 30 min = safety net para tasks travadas (deadlock, I/O eterno, loop infinito).

---

## 🔗 Integração com Arquitetura

```
settings.py (CELERY_*)          celery.py (app.config_from_object)
       │                                    │
       │  namespace='CELERY'                │
       └──────────────────▶                 │
                                            ▼
      ┌─────────────────────────────────────────────┐
      │          Celery App (forms_denuncia)        │
      │  - broker_url = CELERY_BROKER_URL           │
      │  - result_backend = CELERY_RESULT_BACKEND   │
      │  - task_serializer = CELERY_TASK_SERIALIZER │
      │  - timezone = CELERY_TIMEZONE               │
      │  - task_track_started = CELERY_TASK_TRACK...│
      │  - task_time_limit = CELERY_TASK_TIME_LIMIT │
      └─────────────────────────────────────────────┘
```

---

## ⚙️ Configurações Avançadas (Não Usadas Ainda)

```python
# Para produção com alta carga:
CELERY_WORKER_PREFETCH_MULTIPLIER = 1    # 1 task por worker por vez (justo)
CELERY_TASK_ACKS_LATE = True             # ACK depois de executar (não perder se worker morre)
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000 # Recicla processo a cada 1000 tasks (memory leak)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True  # Resiliente a Redis subindo depois
```

---

## 📚 Referências
- [Celery Settings Reference](https://docs.celeryq.dev/en/stable/userguide/configuration.html)
- [Celery Serialization](https://docs.celeryq.dev/en/stable/userguide/configuration.html#serialization)
- [Time Limits](https://docs.celeryq.dev/en/stable/userguide/tasks.html#time-limits)
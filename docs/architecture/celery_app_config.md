# Celery App Configuration (forms_denuncia/celery.py)

## 📍 Arquivo: `forms_denuncia/celery.py`

## 🎯 O que é
Ponto de entrada do Celery. Cria a **instância `app`** que workers, beat e Flower importam. Configura descoberta automática de tasks e comportamentos de confiabilidade.

---

## 💻 Código Completo

```python
import os
from celery import Celery

# 1. Define settings module ANTES de importar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forms_denuncia.settings')

# 2. Cria instância Celery
app = Celery('forms_denuncia')

# 3. Carrega configurações do Django settings (namespace='CELERY')
app.config_from_object('django.conf:settings', namespace='CELERY')

# 4. Auto-descoberta de tasks.py nos apps instalados
app.autodiscover_tasks()

# 5. Configurações de confiabilidade (produção)
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
app.conf.worker_prefetch_multiplier = 1
```

---

## 🔍 Linha por Linha

### `os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forms_denuncia.settings')`

**O que faz:** Garante que `DJANGO_SETTINGS_MODULE` existe **antes** de qualquer import Django.

**Por que `setdefault` e não `=`?**
- Não sobrescreve se já definido (ex: `manage.py` já seta).
- Permite override via `DJANGO_SETTINGS_MODULE=outro.settings celery -A ...`.

**Quando roda:**
- Worker: `celery -A forms_denuncia worker`
- Beat: `celery -A forms_denuncia beat`
- Flower: `celery -A forms_denuncia flower`
- Django shell: `from forms_denuncia.celery import app`

---

### `app = Celery('forms_denuncia')`

**O que faz:** Cria instância **nomeada** `'forms_denuncia'`.

**Nome importa?**
- Usado em logs: `celery@worker1.forms_denuncia`
- Identifica app em Flower/monitoramento.
- **Deve ser único** se rodar múltiplos projetos no mesmo Redis.

---

### `app.config_from_object('django.conf:settings', namespace='CELERY')`

**O que faz:** Carrega **todas** configurações `CELERY_*` do `settings.py`.

**Mapeamento automático:**
| settings.py | Celery App |
|-------------|------------|
| `CELERY_BROKER_URL` | `app.conf.broker_url` |
| `CELERY_RESULT_BACKEND` | `app.conf.result_backend` |
| `CELERY_TASK_SERIALIZER` | `app.conf.task_serializer` |
| `CELERY_TIMEZONE` | `app.conf.timezone` |
| `CELERY_TASK_TRACK_STARTED` | `app.conf.task_track_started` |
| `CELERY_TASK_TIME_LIMIT` | `app.conf.task_time_limit` |

**Por que `namespace='CELERY'`?**
- Evita conflito com settings Django (`DEBUG`, `SECRET_KEY`, etc.).
- Padrão Celery 4+.

---

### `app.autodiscover_tasks()`

**O que faz:** Varre `INSTALLED_APPS` procurando `tasks.py` e **registra** tasks automaticamente.

**Como funciona:**
```python
# Para cada app em INSTALLED_APPS:
#   try: import app.tasks
#   except: pass

# Resultado: tasks ficam disponíveis como:
# 'core.tasks.limpar_exif_imagem'
```

**Sem isso:** Precisaria importar manualmente:
```python
# celery.py
from core.tasks import limpar_exif_imagem
app.register_task(limpar_exif_imagem)
```

---

### Configurações de Confiabilidade (Produção)

```python
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
app.conf.worker_prefetch_multiplier = 1
```

#### `task_acks_late = True`

**Padrão:** `False` (ACK **antes** de executar).

**Problema do padrão:**
```
Worker pega task → ACK imediato → Worker crash → Task PERDIDA (já ACKed)
```

**Com `True` (ACK late):**
```
Worker pega task → EXECUTA → Sucesso → ACK → Remove da fila
                    │
                    └─ Se crash ANTES do ACK → Task volta para fila (requeue)
```

**Garante:** **At-least-once delivery** (pelo menos uma vez).

---

#### `task_reject_on_worker_lost = True`

**Complemento do `acks_late`:**
- Worker morre **durante** execução (SIGKILL, OOM, power loss).
- Task estava "em andamento" (não ACKed ainda).
- `True` = **Rejeita** task → Volta para fila → Outro worker pega.
- `False` (padrão) = Task fica em limbo (pode executar 2x se worker revive).

**Juntos formam:** "Não perca tasks, execute pelo menos uma vez".

---

#### `worker_prefetch_multiplier = 1`

**O que é:** Quantas tasks worker **busca de uma vez** do Redis.

**Padrão:** `4` (prefetch 4 tasks por worker process).

**Problema do padrão (prefetch > 1):**
```
Worker 1: Pega 4 tasks (T1,T2,T3,T4) → Fila vazia
Worker 2: Chega, fila vazia → idle

T1 demora 10min (imagem grande)
T2,T3,T4 rápidas (1s)

Resultado: Worker 2 parado, Worker 1 sobrecarregado
```

**Com `1`:**
```
Worker pega 1 task → Executa → Volta na fila pega próxima
→ Distribuição justa (round-robin natural)
```

**Trade-off:** +1 round-trip Redis por task (latência ~1ms). **Irrelevante** para tasks > 100ms.

---

## 🔗 Integração com Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    FORMS_DENUNCIA (Celery App)              │
│  forms_denuncia/celery.py                                   │
│       │                                                     │
│       ├─ config_from_object(settings, namespace='CELERY')  │
│       │       │                                             │
│       │       ▼                                             │
│       │  ┌─────────────────────────────────────┐            │
│       │  │ settings.py                         │            │
│       │  │ CELERY_BROKER_URL = redis://...     │            │
│       │  │ CELERY_RESULT_BACKEND = redis://... │            │
│       │  │ CELERY_TASK_SERIALIZER = 'json'     │            │
│       │  │ CELERY_TIMEZONE = 'America/Sao_Paulo'│           │
│       │  │ CELERY_TASK_ACKS_LATE = True        │            │
│       │  └─────────────────────────────────────┘            │
│       │                                                     │
│       ├─ autodiscover_tasks()                               │
│       │       │                                             │
│       │       ▼                                             │
│       │  ┌─────────────────────────────────────┐            │
│       │  │ INSTALLED_APPS                      │            │
│       │  │   'core'  ──▶ core/tasks.py  ✓      │            │
│       │  │   'dashboard'  (sem tasks.py)       │            │
│       │  └─────────────────────────────────────┘            │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              REGISTRY DE TASKS                        │   │
│  │  'core.tasks.limpar_exif_imagem' → Function          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  WORKER (celery -A forms_denuncia worker)                  │
│  - Importa app de forms_denuncia.celery                    │
│  - Conecta no Redis (broker_url)                           │
│  - Consome fila 'celery'                                   │
│  - Executa tasks com acks_late, prefetch=1                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Como o Django Encontra o App (`forms_denuncia/__init__.py`)

```python
# forms_denuncia/__init__.py
from .celery import app as celery_app

__all__ = ('celery_app',)
```

**Por que?**
- `manage.py` faz `from forms_denuncia import celery_app` ao iniciar.
- Garante que Celery **carregue config** mesmo sem worker rodando.
- Permite `celery_app.send_task('core.tasks.limpar_exif_imagem', args=[id])` em views.

---

## ⚙️ Configurações Avançadas (Não Usadas Ainda)

```python
# Roteamento de filas (ex: tasks pesadas em worker dedicado)
app.conf.task_routes = {
    'core.tasks.relatorio_mensal': {'queue': 'reports'},
    'core.tasks.limpar_exif_imagem': {'queue': 'images'},
}

# Prioridade de tasks (0-9, 9=alta)
app.conf.task_default_priority = 5

# Compressão de mensagens grandes
app.conf.task_compression = 'gzip'

# Serialização de datetime
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
```

---

## 📚 Referências
- [Celery Configuration](https://docs.celeryq.dev/en/stable/userguide/configuration.html)
- [acks_late](https://docs.celeryq.dev/en/stable/userguide/tasks.html#acknowledging-tasks)
- [Prefetch](https://docs.celeryq.dev/en/stable/userguide/optimizing.html#prefetch-limits)
- [Task Rejection](https://docs.celeryq.dev/en/stable/userguide/tasks.html#task-reject-on-worker-lost)
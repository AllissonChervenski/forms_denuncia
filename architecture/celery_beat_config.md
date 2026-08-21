# Celery Beat Scheduler Configuration (docker-compose.yml)

## 📍 Arquivo: `docker-compose.yml` (serviço `celery-beat`)

## 🎯 O que é
Container que roda o **agendador de tarefas periódicas** (cron do Celery). Decide **quando** executar tasks, não executa elas (isso é o Worker).

---

## 💻 Código Completo

```yaml
# 5. Celery Beat (Periodic Tasks)
celery-beat:
  build: .
  command: celery -A forms_denuncia beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
  volumes:
    - .:/app
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

### `command: celery -A forms_denuncia beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler`

| Parte | Função |
|-------|--------|
| `beat` | Modo agendador (não worker) |
| `-l INFO` | Log level |
| `--scheduler django_celery_beat.schedulers:DatabaseScheduler` | **Guarda agendamento no PostgreSQL** |

---

## 🗄️ DatabaseScheduler vs Arquivo

### DatabaseScheduler (Usado)
```python
# Tabelas criadas por django_celery_beat:
# - celery_beat_periodictask      (tarefas agendadas)
# - celery_beat_crontabschedule   (cron: minuto, hora, dia...)
# - celery_beat_intervalschedule  (intervalo: a cada X segundos)
# - celery_beat_solarschedule     (nascer/por do sol)
# - celery_beat_clockedschedule   (timestamp único)
# - celery_beat_periodictasks     (controle de versão - 1 linha)
```

**Vantagens:**
- **Persistente:** Reinicia container → agendamentos voltam.
- **Admin Django:** Gerencia via `/admin/django_celery_beat/periodictask/`.
- **Multi-worker:** Apenas 1 beat roda (evita execução duplicada).
- **Dinâmico:** Adiciona/remove tasks sem reiniciar.

### Arquivo (Padrão Antigo)
```bash
celery -A proj beat --schedule=/app/celerybeat-schedule
```
**Problemas:** Arquivo corrompe, não funciona em múltiplos containers, sem UI.

---

## 🔗 Como Adicionar Tarefas Periódicas

### Via Django Admin (Recomendado)
```
1. Acesse /admin/django_celery_beat/periodictask/
2. "Add Periodic Task"
3. Preencha:
   - Name: "Limpeza de evidências órfãs"
   - Task: "core.tasks.limpar_evidencias_orfas"
   - Schedule: Crontab (todo dia 3h) ou Interval (a cada 1h)
   - Args: [] / Kwargs: {}
   - Enabled: ✓
```

### Via Código (Migration/Management Command)
```python
# core/management/commands/setup_periodic_tasks.py
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json

def setup():
    schedule, _ = CrontabSchedule.objects.get_or_create(
        hour=3, minute=0,  # 3:00 AM
    )
    PeriodicTask.objects.get_or_create(
        name='Limpeza diária de evidências órfãs',
        task='core.tasks.limpar_evidencias_orfas',
        crontab=schedule,
        defaults={'args': json.dumps([]), 'kwargs': json.dumps({})}
    )
```

---

## ⚙️ Configurações Avançadas (settings.py)

```python
# settings.py
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Timezone do Beat (já definido em CELERY_TIMEZONE)
CELERY_TIMEZONE = 'America/Sao_Paulo'

# Sincronização de timezone
CELERY_BEAT_SYNC_EVERY = 1000  # Re-sync DB a cada 1000 tasks
```

---

## 🔗 Integração com Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
                    CELERY BEAT CONTAINER                      
│  celery -A forms_denuncia beat --scheduler DatabaseScheduler │
│                                                              │
│  A cada 30 segundos (padrão):                               │
│  1. SELECT * FROM celery_beat_periodictask                  │
│     WHERE enabled=True AND last_run_at < now()              │
│  2. Para cada task devido:                                  │
│     LPUSH 'celery' {task_id, name, args, kwargs, ...}       │
│  3. UPDATE last_run_at = now()                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ (Redis Broker)
┌─────────────────────────────────────────────────────────────┐
                    CELERY WORKER CONTAINER                     
│  4 workers BRPOP 'celery'                                    
│  Executa tasks enfileiradas pelo Beat                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
                    POSTGRESQL                                  
│  - Tabelas django_celery_beat (agendamento)                 │
│  - Tabelas app (Denuncia, Evidencia, etc)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Exemplo de Tasks Periódicas Futuras

| Task | Schedule | Descrição |
|------|----------|-----------|
| `limpar_evidencias_orfas` | Diário 3:00 | Remove `Evidencia` sem `Denuncia` pai > 7 dias |
| `enviar_relatorio_semanal` | Segunda 8:00 | Email para admins com stats da semana |
| `limpar_sessoes_expiradas` | Hora em hora | `Session.objects.filter(expire_date__lt=now()).delete()` |
| `backup_media_metadata` | Diário 4:00 | Exporta metadados de uploads para S3/Backup |

---

## 📊 Monitoramento no Flower

```
Beat: celery@beat
├─ Scheduler: django_celery_beat.schedulers.DatabaseScheduler
├─ Schedule: 4 periodic tasks
│   ├─ limpar_evidencias_orfas (crontab: 0 3 * * *) - Next: 2026-07-29 03:00
│   ├─ enviar_relatorio_semanal (crontab: 0 8 * * 1) - Next: 2026-08-03 08:00
│   └─ ...
└─ Last sync: 2026-07-28 10:30:15
```

---

## 📚 Referências
- [Celery Beat](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html)
- [django-celery-beat](https://github.com/celery/django-celery-beat)
- [DatabaseScheduler](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html#database-scheduler)
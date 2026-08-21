import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forms_denuncia.settings.local')

app = Celery('forms_denuncia')

# Lê as configurações do Celery diretamente do ficheiro settings.py do Django
# O namespace='CELERY' significa que todas as variáveis do Celery no settings
# devem começar com 'CELERY_' (ex: CELERY_BROKER_URL)
app.config_from_object('django.conf:settings', namespace='CELERY')

# procura automaticamente por arquivos tasks.py
app.autodiscover_tasks()

# Configuração de retry para tarefas
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
app.conf.worker_prefetch_multiplier = 1
# Documentação Técnica Detalhada - Forms Denúncia
## Índice de Arquivos de Documentação

### 📁 Configurações Core (Django Settings)
- [settings_database.md](settings_database.md) - Configuração PostgreSQL
- [settings_redis_cache.md](settings_redis_cache.md) - Redis Cache & Sessions
- [settings_celery.md](settings_celery.md) - Configurações Celery
- [settings_ratelimit.md](settings_ratelimit.md) - Rate Limiting
- [settings_security.md](settings_security.md) - Hardening de Segurança
- [settings_internationalization.md](settings_internationalization.md) - i18n/L10n

### 📁 Celery & Tasks Assíncronas
- [celery_app_config.md](celery_app_config.md) - Celery App (forms_denuncia/celery.py)
- [celery_task_exif.md](celery_task_exif.md) - Task limpar_exif_imagem
- [celery_worker_config.md](celery_worker_config.md) - Worker Docker Compose
- [celery_beat_config.md](celery_beat_config.md) - Beat Scheduler

### 📁 Django Views & Forms
- [views_index_ratelimit.md](views_index_ratelimit.md) - View index com rate limiting
- [views_protocol_ratelimit.md](views_protocol_ratelimit.md) - View protocol com rate limiting
- [views_search_ratelimit.md](views_search_ratelimit.md) - View search com rate limiting
- [forms_denuncia_form.md](forms_denuncia_form.md) - Formulário de denúncia

### 📁 Infraestrutura Docker
- [docker_compose_db.md](docker_compose_db.md) - Serviço PostgreSQL
- [docker_compose_redis.md](docker_compose_redis.md) - Serviço Redis
- [docker_compose_web.md](docker_compose_web.md) - Serviço Web (Gunicorn)
- [docker_compose_celery.md](docker_compose_celery.md) - Serviço Celery Worker
- [docker_compose_beat.md](docker_compose_beat.md) - Serviço Celery Beat
- [docker_compose_flower.md](docker_compose_flower.md) - Serviço Flower
- [dockerfile_config.md](dockerfile_config.md) - Dockerfile Multi-stage

### 📁 Models & Database
- [models_denuncia.md](models_denuncia.md) - Model Denuncia
- [models_evidencia.md](models_evidencia.md) - Model Evidencia
- [models_cidade_estado.md](models_cidade_estado.md) - Models Cidade/Estado

### 📁 Arquitetura & Decisões
- [architecture_overview.md](architecture_overview.md) - Visão Geral da Arquitetura
- [tech_stack_justification.md](tech_stack_justification.md) - Justificativa da Stack
- [module_communication.md](module_communication.md) - Como Módulos se Comunicam
- [data_flow.md](data_flow.md) - Fluxo de Dados Completo

---

## Como Ler Esta Documentação

Cada arquivo `.md` segue o padrão:
1. **O que é** - Explicação simples do conceito
2. **Código** - O trecho exato
3. **Linha por Linha** - Explicação detalhada
4. **Por que assim?** - Justificativa técnica
5. **Como se conecta** - Integração com o resto
6. **Parâmetros** - Detalhamento de cada valor
7. **Alternativas** - Outras opções consideradas

**Público-alvo:** Desenvolvedor júnior aprendendo Django, Celery, Redis, PostgreSQL, Docker.
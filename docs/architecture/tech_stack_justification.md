# Justificativa da Stack Tecnológica

## 🎯 Por Que Estas Tecnologias?

---

## 🐘 PostgreSQL 16 (Banco Principal)

### ✅ Escolhido Porque:
| Requisito | PostgreSQL Atende? | Como |
|-----------|-------------------|------|
| **ACID Completo** | ✅ | Transações, WAL, MVCC |
| **UUID Nativo** | ✅ | `uuid-ossp` extension, PK `protocolo` |
| **Busca Textual** | ✅ | `pg_trgm` para similaridade futura |
| **JSONB** | ✅ | Metadados flexíveis (futuro) |
| **Concorrência** | ✅ | MVCC - leitores não bloqueiam escritores |
| **Extensões** | ✅ | `uuid-ossp`, `pg_trgm`, `postgis` (futuro geo) |
| **Maduro/Estável** | ✅ | 30+ anos, usado por Instagram, Uber, etc. |

### ❌ Alternativas Rejeitadas:
| DB | Motivo |
|----|--------|
| **SQLite** | Não suporta concorrência real (1 writer). Celery + Gunicorn = múltiplos writers. |
| **MySQL** | UUID performance pior, JSON menos robusto, MVCC limitado (InnoDB gap locks). |
| **MongoDB** | Sem ACID transacional multi-doc, overkill para dados relacionais estruturados. |

---

## 🔴 Redis 7 (Broker + Cache + Sessions + Rate Limit)

### ✅ Escolhido Porque:
| Papel | Por que Redis |
|-------|---------------|
| **Celery Broker** | Listas atômicas (LPUSH/BRPOP), pub/sub, prioridade |
| **Result Backend** | Strings TTL automático, rápido |
| **Django Cache** | `django-redis` pooling, pipeline, scan (não `keys *`) |
| **Sessions** | TTL nativo, compartilhado entre workers |
| **Rate Limit** | `INCR` atômico + `EXPIRE` = contador janela deslizante perfeito |
| **Performance** | In-memory, sub-ms latency, single-threaded (sem locks) |

### Configurações Críticas:
```bash
--appendonly yes           # AOF = zero data loss (Celery broker)
--maxmemory 256mb          # Limite controlado
--maxmemory-policy allkeys-lru  # Evicção inteligente
```

### ❌ Alternativas:
| Tech | Problema |
|------|----------|
| **RabbitMQ** | Mais complexo, mais recursos, overkill para filas simples |
| **Database (Celery SQL)** | Latência alta, polling, não escala |
| **Memcached** | Sem persistência, sem estruturas (listas, pub/sub), sem TTL automático por key |

---

## ⚙️ Celery 5.6 (Processamento Assíncrono)

### ✅ Escolhido Porque:
| Feature | Uso no Projeto |
|---------|----------------|
| **Task Queue** | `limpar_exif_imagem.delay()` - não bloqueia upload |
| **Retry/ACKs** | `acks_late`, `reject_on_worker_lost` - não perde tasks |
| **Beat Scheduler** | `django-celery-beat` - agendamento persistido no Postgres |
| **Monitoring** | Flower integração nativa |
| **Scaling** | Mais workers = mais throughput linear |
| **Mature** | 15+ anos, Django integration nativa |

### Configurações de Confiabilidade:
```python
task_acks_late = True           # ACK após execução (não perde se worker morre)
task_reject_on_worker_lost = True  # Requeue se worker morre no meio
worker_prefetch_multiplier = 1  # Fair distribution (1 task por worker por vez)
```

---

## 🌸 Flower 2.0 (Monitoramento)

### ✅ Escolhido Porque:
- **Zero config** - aponta pro broker, funciona
- **Web UI** - tasks, workers, queues, gráficos tempo real
- **API REST** - integração Prometheus/Grafana futura
- **Leve** - roda no mesmo container stack

---

## 🐍 Django 5.2 (Framework Web)

### ✅ Escolhido Porque:
| Feature | Uso |
|---------|-----|
| **ORM** | Models complexos (FK, UUID, Choices), migrations |
| **Forms** | Validação server-side, CSRF, widgets customizados |
| **Admin** | Dashboard staff**Auth**| Login staff, permissões, `LoginRequiredMixin` |
|**Security**| CSRF, XSS, Clickjacking, HSTS, Referrer Policy built-in |
|**i18n**| `pt-BR`, timezone `America/Sao_Paulo` |
|**Ecosystem**| `django-redis`, `django-ratelimit`, `django-celery-beat`, `dal` |

### LTS: Django 5.2 = Long Term Support (até abril 2026)

---

## 🦄 Gunicorn (WSGI Server)

### ✅ Escolhido Porque:
| Aspecto | Gunicorn |
|---------|----------|
| **Modelo** | Prefork (master + workers) - simples, robusto |
| **Performance** | 4 workers = 4 requests simultâneos |
| **Graceful Reload** | `SIGHUP` = zero downtime deploy |
| **Config** | `--max-requests 1000` = memory leak protection |
| **Standard** | Padrão Django produção (Heroku, Railway, Fly.io) |

### ❌ Não uWSGI:
- Config mais complexa, mais recursos, marginal gain.

---

## 🐳 Docker + Docker Compose

### ✅ Escolhido Porque:
| Benefício | Como |
|-----------|------|
| **Reprodutibilidade** | Mesmo imagem dev/staging/prod |
| **Isolamento** | Cada serviço em container próprio |
| **Orquestração** | `depends_on`, `healthcheck`, `restart` |
| **Volumes** | Persistência Postgres, Redis, Media, Static |
| **Redes** | DNS interno (`db`, `redis`, `web`) |
| **Portabilidade** | Roda em qualquer Linux/Cloud |

---

## 📦 pyproject.toml + pip (Gerenciamento Dependências)

### ✅ Moderno:
- **PEP 621** - Metadados padronizados
- **Build backend** - `setuptools` padrão
- **Editable install** - `pip install -e .` (dev)
- **Lock file** - `requirements.txt` gerado para Docker

---

## 📊 Resumo da Stack

| Camada | Tecnologia | Versão | Justificativa Principal |
|--------|------------|--------|------------------------|
| **Web Framework** | Django | 5.2 LTS | ORM, Admin, Security, Forms |
| **WSGI Server** | Gunicorn | 22 | Prefork, production-ready |
| **Async Queue** | Celery | 5.6 | Tasks confiáveis, retry, beat |
| **Broker/Cache** | Redis | 7 | Speed, atomic ops, persistence |
| **Database** | PostgreSQL | 16 | ACID, UUID, JSONB, Extensions |
| **Monitoring** | Flower | 2.0 | Celery visibility |
| **Container** | Docker | 24 | Reproducible, isolated |
| **Orchestration** | Compose | 2.26 | Multi-container, healthchecks |
| **Language** | Python | 3.11 | Performance, typing, ecosystem |

---

## 📚 Referências
- [Choose PostgreSQL](https://www.postgresql.org/about/)
- [Redis Use Cases](https://redis.io/docs/latest/develop/use-cases/)
- [Celery Architecture](https://docs.celeryq.dev/en/stable/userguide/architecture.html)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
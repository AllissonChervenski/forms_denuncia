# Visão Geral da Arquitetura - Forms Denúncia

## 🎯 Objetivo do Sistema
Plataforma web para **denúncias de negligência à saúde do trabalhador** com:
- Formulário público anônimo/identificado
- Upload de evidências (imagens) com **limpeza automática de EXIF/GPS**
- Acompanhamento via protocolo UUID
- Painel administrativo para equipe de segurança
- Processamento assíncrono para não bloquear usuário

---

## 🏗️ Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNO                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                       │
│  │   Usuário    │    │  Admin/Seg.  │    │  Monitor     │                       │
│  │  (Browser)   │    │  (Dashboard) │    │  (Flower)    │                       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                       │
└─────────│───────────────────│────────────────────│───────────────────────────────┘
          │                   │                    │
          ▼                   ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           NGINX (Futuro - TLS Termination)                      │
│                    Static Files / Media / Rate Limit / Proxy                    │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│      WEB (x4)       │    │   CELERY WORKER     │    │   CELERY BEAT       │
│  Gunicorn + Django  │    │  (x4 processes)     │    │  (Scheduler)        │
│                     │    │                     │    │                     │
│ - Views (Sync)      │    │ - limpar_exif_imagem│    │ - Periodic Tasks    │
│ - Forms/Validation  │    │ - Future: emails    │    │ - DB Scheduler      │
│ - Auth/Admin        │    │ - Future: reports   │    │                     │
│ - Rate Limit        │    │                     │    │                     │
└──────────┬──────────┘    └──────────┬──────────┘    └──────────┬──────────┘
           │                          │                          │
           └──────────────────────────┼──────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              REDIS (DB 0 | DB 1)                                │
│  ┌──────────────────────────────┐  ┌────────────────────────────────────────┐  │
│  │         DB 0: Celery         │  │         DB 1: Django Cache             │  │
│  │  - Broker (Filas)            │  │  - View Cache                          │  │
│  │  - Result Backend            │  │  - Sessions                            │  │
│  │  - Events (Flower)           │  │  - Rate Limit Counters                 │  │
│  └──────────────────────────────┘  └────────────────────────────────────────┘  │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   POSTGRESQL 16     │    │    MEDIA VOLUME     │    │   STATIC VOLUME     │
│                     │    │                     │    │                     │
│ - core_denuncia     │    │ /denuncia_images/   │    │ collectstatic/      │
│ - core_evidencia    │    │ (original + limpo)  │    │ (CSS, JS, Admin)    │
│ - core_cidade/estado│    │                     │    │                     │
│ - django_celery_beat│    │                     │    │                     │
│ - auth_user         │    │                     │    │                     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

---

## 🧩 Componentes Principais

| Componente | Tecnologia | Replicas | Função |
|------------|------------|----------|--------|
| **Web** | Django 5.2 + Gunicorn | 4 workers | HTTP Sync, Forms, Admin, Auth |
| **Celery Worker** | Celery 5.6 | 4 processes | Tasks assíncronas (EXIF, emails) |
| **Celery Beat** | Celery Beat | 1 | Agendador (DB Scheduler) |
| **Flower** | Flower 2.0 | 1 | Monitoramento Celery |
| **Redis** | Redis 7 | 1 | Broker, Cache, Sessions, Rate Limit |
| **PostgreSQL** | Postgres 16 | 1 | Dados persistentes, Agendamentos |
| **Nginx** | (Futuro) | 1 | TLS, Static, Proxy, Rate Limit |

---

## 🔄 Fluxos Principais

### 1. Envio de Denúncia (Público)
```
User → GET / → Form → POST / → Valida → Save Denuncia + Evidencias
                                              │
                                              ▼
                                    Redis Broker (LPUSH)
                                              │
                                    Celery Worker (BRPOP)
                                              │
                                    Pillow: Recria imagem sem EXIF
                                              │
                                    Sobrescreve arquivo em /media
```

### 2. Acompanhamento (Público)
```
User → GET /pesquisar/?query=uuid → 302 → GET /protocolo/<uuid>/
                                                    │
                                    Rate Limit (60/min)
                                                    │
                                    Render protocolo.html
```

### 3. Gestão (Admin/Staff)
```
Staff → Login → Dashboard → GET /protocolo/<uuid>/
                              │
                              POST /protocolo/<uuid>/ (resposta)
                              │
                              Toggle situacao + Save resposta
```

### 4. Tasks Periódicas (Futuro)
```
Celery Beat (30s) → SELECT periodic_tasks → LPUSH Redis
                                      │
                              Celery Worker executa
```

---

## 🛡️ Segurança em Camadas

| Camada | Implementação |
|--------|---------------|
| **Rede** | Nginx (futuro): TLS 1.3, Rate Limit, WAF básico |
| **Aplicação** | Django: CSRF, XSS, Clickjacking, HSTS, Referrer Policy |
| **Rate Limit** | Redis + django-ratelimit (IP-based, por endpoint) |
| **Upload** | Pillow validação + **EXIF Strip** assíncrono |
| **Dados** | PostgreSQL: UUID PK, FK constraints, NOT NULL |
| **Sessões** | Redis (não DB) - escalável, TTL automático |
| **Secrets** | `.env` + Docker secrets (não no código) |
| **Container** | Non-root user, read-only fs onde possível |

---

## 📈 Escalabilidade

| Componente | Como Escala |
|------------|-------------|
| **Web** | Mais replicas Gunicorn (stateless) |
| **Worker** | Mais `--concurrency` ou mais containers |
| **Beat** | Apenas 1 (DB Scheduler garante 1 execução) |
| **Redis** | Cluster mode / Sentinel (futuro) |
| **PostgreSQL** | Read replicas, connection pooling (PgBouncer) |
| **Media** | S3/MinIO + CloudFront (futuro) |

---

## 📋 Princípios de Design

1. **Stateless Web** - Qualquer worker atende qualquer request
2. **Async First** - Operações pesadas (I/O, CPU) fora do request
3. **Privacy by Design** - EXIF strip automático, anonimato default
4. **Observability** - Flower + Logs estruturados + Healthchecks
5. **12-Factor App** - Config no env, logs stdout, admin processes
6. **Defense in Depth** - Rate limit em múltiplas camadas

---

## 🔮 Roadmap Técnico

| Prioridade | Item |
|------------|------|
| **Alta** | Nginx + TLS (Let's Encrypt) |
| **Alta** | Backup automatizado Postgres + Media |
| **Média** | S3/MinIO para media (desacoplar volume) |
| **Média** | PgBouncer (connection pooling) |
| **Média** | Testes automatizados (pytest + GitHub Actions) |
| **Baixa** | Kubernetes (se escala > 10 containers) |
| **Baixa** | APM (Sentry, Datadog, Elastic APM) |
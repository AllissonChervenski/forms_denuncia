# Docker Compose - Serviço Web (Gunicorn + Django)

## 📍 Arquivo: `docker-compose.yml` (serviço `web`)

## 🎯 O que é
Container que roda a **aplicação Django** via **Gunicorn** (WSGI server de produção). Substitui `runserver` (desenvolvimento) por servidor robusto, multi-processo.

---

## 💻 Código Completo

```yaml
# 3. Django Web Application
web:
  build: .
  command: >
    sh -c "python manage.py migrate --noinput &&
           python manage.py collectstatic --noinput &&
           gunicorn forms_denuncia.wsgi:application --bind 0.0.0.0:8000 --workers 4 --max-requests 1000 --timeout 30 --access-logfile - --error-logfile -"
  volumes:
    - .:/app
    - static_volume:/app/static
    - media_volume:/app/media
  ports:
    - "8000:8000"
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
  environment:
    - DEBUG=${DEBUG:-True}
    - SECRET_KEY=${SECRET_KEY}
    - ALLOWED_HOSTS=${ALLOWED_HOSTS:-localhost,127.0.0.1,0.0.0.0}
    - POSTGRES_DB=${POSTGRES_DB}
    - POSTGRES_USER=${POSTGRES_USER}
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    - POSTGRES_HOST=db
    - POSTGRES_PORT=5432
    - REDIS_URL=redis://redis:6379/1
    - CELERY_BROKER_URL=redis://redis:6379/0
    - CELERY_RESULT_BACKEND=redis://redis:6379/0
    - RATE_LIMIT_ENABLED=${RATE_LIMIT_ENABLED}
  restart: always
```

---

## 🔍 Linha por Linha

### `build: .`
Usa **Dockerfile do projeto** (multi-stage, non-root user, healthcheck).

### `command: > ...` (Multi-line com fold `>`)
O `>` do YAML transforma linhas em **uma única linha** (espaços preservados).
Equivale a:
```bash
sh -c "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn forms_denuncia.wsgi:application --bind 0.0.0.0:8000 --workers 4 --max-requests 1000 --timeout 30 --access-logfile - --error-logfile -"
```

#### Passo 1: `python manage.py migrate --noinput`
- **Roda migrações** automaticamente ao subir container.
- `--noinput` = não pergunta "Tem certeza?" (automatizado).
- Garante schema atualizado antes de Gunicorn iniciar.

#### Passo 2: `python manage.py collectstatic --noinput`
- **Coleta arquivos estáticos** (CSS, JS, admin) em `STATIC_ROOT` (`/app/static`).
- `--noinput` = sobrescreve sem confirmar.
- Nginx servirá de `/app/static` (volume `static_volume`).

#### Passo 3: `gunicorn forms_denuncia.wsgi:application ...`

| Flag | Valor | Significado |
|------|-------|-------------|
| `forms_denuncia.wsgi:application` | WSGI app | Entry point Django (`wsgi.py` expõe `application`) |
| `--bind 0.0.0.0:8000` | Bind | Escuta **todas interfaces** (não só localhost) |
| `--workers 4` | Workers | **4 processos worker** (prefork) |
| `--max-requests 1000` | Reciclagem | Reinicia worker a cada 1000 requests |
| `--timeout 30` | Timeout | Mata request se > 30s (evita travamento) |
| `--access-logfile -` | Access log | Log de acesso para **stdout** (Docker logs) |
| `--error-logfile -` | Error log | Log de erro para **stderr** |

#### `--workers 4` - Quantos Workers?
**Regra geral:** `(2 × CPU cores) + 1`
- Container com 2 CPUs → 5 workers.
- Aqui 4 = conservador, deixa CPU para Celery/Redis.
- Cada worker = processo isolado, própria memória, próprio pool DB.

#### `--max-requests 1000` - Reciclagem
```
Worker processa 1000 requests → Reinicia (fork novo) → Memória limpa
```
- Evita memory leak de bibliotecas C, cache interno Django.
- Graceful: termina request atual antes de morrer.

#### `--timeout 30` - Timeout de Request
```
Request demora > 30s → Worker mata (SIGKILL) → Retorna 502/504 via Nginx
```
- Protege contra: queries lentas, loops infinitos, I/O travado.
- Nginx `proxy_read_timeout` deve ser **maior** (ex: 60s).

---

### `volumes:`
```yaml
- .:/app              # Código (hot reload dev)
- static_volume:/app/static   # collectstatic output
- media_volume:/app/media     # Uploads usuários
```
- `static_volume` e `media_volume` **persistentes** (não perdem no rebuild).
- Nginx monta mesmos volumes para servir arquivos.

### `ports: - "8000:8000"`
Expõe porta 8000 no host. **Em produção, Nginx expõe 80/443 e faz proxy para web:8000 interno.**

### `depends_on:` com Healthchecks
```yaml
depends_on:
  db:
    condition: service_healthy      # pg_isready OK
  redis:
    condition: service_healthy      # redis-cli ping OK
```
- **Não inicia Gunicorn** até DB e Redis prontos.
- Evita erro "connection refused" nos primeiros segundos.

### `environment:` - Variáveis Críticas
| Variável | Uso |
|----------|-----|
| `DEBUG` | Controla `SECURE_*`, stack traces |
| `SECRET_KEY` | Assinatura cookies, CSRF, tokens |
| `ALLOWED_HOSTS` | Host header validation |
| `POSTGRES_*` | Conexão DB (Django ORM) |
| `REDIS_URL` | Cache, Sessions, Rate Limit |
| `CELERY_BROKER_URL` | Enfileirar tasks (`.delay()`) |
| `RATE_LIMIT_ENABLED` | Liga/desliga rate limit |

### `restart: always`
Sempre reinicia (crash, deploy, host reboot).

---

## 🔗 Arquitetura Web + Gunicorn

```
┌─────────────────────────────────────────────────────────────────┐
│                        WEB CONTAINER                            │
│  Gunicorn Master (PID 1)                                        │
│       │                                                         │
│       ├─ Worker 1 (PID 101) ──▶ Django App ──▶ PostgreSQL      │
│       ├─ Worker 2 (PID 102) ──▶ Django App ──▶ PostgreSQL      │
│       ├─ Worker 3 (PID 103) ──▶ Django App ──▶ PostgreSQL      │
│       └─ Worker 4 (PID 104) ──▶ Django App ──▶ PostgreSQL      │
│       │                                                         │
│       ├─ Redis (Cache, Sessions, Rate Limit, Broker)           │
│       └─ Media Volume (Uploads)                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼ HTTP :8000
┌─────────────────────────────────────────────────────────────────┐
│                        NGINX (Futuro)                           │
│  - TLS Termination                                              │
│  - Static Files (/static/, /media/)                            │
│  - Rate Limiting (extra camada)                                │
│  - Proxy Pass → web:8000                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Gunicorn vs runserver

| Aspecto | `runserver` | `Gunicorn` |
|---------|-------------|------------|
| Processos | 1 (single-thread) | Múltiplos (prefork) |
| Produção | ❌ Não | ✅ Sim |
| Static files | Serve (lento) | Não serve (Nginx faz) |
| Hot reload | ✅ | ❌ (use `--reload` só dev) |
| Timeout | Não tem | Configurável |
| Logging | Console | Estruturado (stdout/stderr) |
| Segurança | Debug exposto | Produção-ready |

---

## 📊 Monitoramento

```bash
# Logs em tempo real
docker compose logs -f web

# Status workers
docker compose exec web ps aux | grep gunicorn

# Testar endpoint
curl -I http://localhost:8000/

# Healthcheck (Docker)
docker compose ps web
```

---

## 📚 Referências
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Gunicorn Settings](https://docs.gunicorn.org/en/stable/settings.html)
- [Django Deployment](https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/gunicorn/)
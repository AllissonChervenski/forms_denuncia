# Docker Compose - PostgreSQL Database

## 📍 Arquivo: `docker-compose.yml` (serviço `db`)

## 🎯 O que é
Container do **PostgreSQL 16** - banco de dados relacional principal. Armazena denúncias, usuários, cidades, agendamentos Celery Beat, sessões (se não usar Redis), etc.

---

## 💻 Código Completo

```yaml
# 1. PostgreSQL Database
db:
  image: postgres:16-alpine
  environment:
    - POSTGRES_DB=${POSTGRES_DB:-forms_denuncia}
    - POSTGRES_USER=${POSTGRES_USER:-forms_denuncia}
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-change-me}
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
  ports:
    - "5432:5432"
  restart: always
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-forms_denuncia} -d ${POSTGRES_DB:-forms_denuncia}"]
    interval: 10s
    timeout: 5s
    retries: 5
```

---

## 🔍 Linha por Linha

### `image: postgres:16-alpine`
- **PostgreSQL 16** (versão estável atual).
- **Alpine Linux** = imagem pequena (~150MB vs 400MB Debian).
- Segurança: menos pacotes, menor superfície de ataque.

### `environment:` - Variáveis de Inicialização
```yaml
- POSTGRES_DB=${POSTGRES_DB:-forms_denuncia}
- POSTGRES_USER=${POSTGRES_USER:-forms_denuncia}
- POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-change-me}
```
**O que faz:** Script `docker-entrypoint.sh` do Postgres oficial lê essas vars e:
1. Cria database `forms_denuncia`
2. Cria usuário `forms_denuncia` com senha
3. Concede privilégios no database

**`${VAR:-default}`** = usa variável do `.env` ou default se não definida.

**⚠️ `change-me`** = **NUNCA use em produção**. Defina `POSTGRES_PASSWORD` no `.env`.

### `volumes:`
```yaml
- postgres_data:/var/lib/postgresql/data
- ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
```

| Volume | Função |
|--------|--------|
| `postgres_data:/var/lib/postgresql/data` | **Persistência** - dados sobrevivem a rebuild/restart |
| `./init.sql:/docker-entrypoint-initdb.d/init.sql:ro` | **Inicialização** - roda SQL na **primeira criação** do banco |

#### `init.sql` - Extensões Necessárias
```sql
-- init.sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

| Extensão | Para que serve no projeto |
|----------|---------------------------|
| `uuid-ossp` | Gera `uuid_generate_v4()` para PK `Denuncia.protocolo` |
| `pg_trgm` | Busca textual trigram (futuro: busca por descrição similar) |

**Só roda na PRIMEIRA vez** que o volume `postgres_data` é criado. Se já existe, ignora.

### `ports: - "5432:5432"`
Expõe porta 5432 no host. **Útil para:**
- Debug local: `psql -h localhost -U forms_denuncia`
- Ferramentas GUI: DBeaver, pgAdmin, TablePlus
- **Em produção:** Nginx/app acessam via rede interna `db:5432` (não expõe no host).

### `restart: always`
Sempre reinicia (crash, OOM, host reboot).

### `healthcheck:` - Crítico para `depends_on`
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-forms_denuncia} -d ${POSTGRES_DB:-forms_denuncia}"]
  interval: 10s
  timeout: 5s
  retries: 5
```

| Parâmetro | Valor | Significado |
|-----------|-------|-------------|
| `test` | `pg_isready` | Verifica se Postgres aceita conexões |
| `interval` | 10s | Verifica a cada 10s |
| `timeout` | 5s | Falha se `pg_isready` > 5s |
| `retries` | 5 | Marca "unhealthy" após 5 falhas (50s total) |

**Estados:**
```
starting → (healthcheck passa) → healthy → outros serviços iniciam
         → (5 falhas) → unhealthy → containers dependentes não sobem
```

---

## 🔗 Integração com Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                      DB CONTAINER                           │
│  PostgreSQL 16 on Alpine                                    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Volumes                                            │   │
│  │  postgres_data  ──▶ /var/lib/postgresql/data        │   │
│  │  (Persistência: tabelas, índices, WAL, configs)     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Init Script (uma vez)                              │   │
│  │  init.sql ──▶ CREATE EXTENSION uuid-ossp, pg_trgm   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Portas:                                                    │
│  ├─ 5432 (interno) ──▶ Django ORM, Celery, Beat            │
│  └─ 5432 (host) ──▶ Debug, DBeaver, pgAdmin                │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Tabelas Principais (Criadas por Migrations)

| Tabela (Model) | Descrição |
|----------------|-----------|
| `core_denuncia` | Denúncias (PK UUID, FK cidade, tipo, status) |
| `core_evidencia` | Imagens (FK denuncia, ImageField) |
| `core_cidade` | Cidades (FK estado) |
| `core_estado` | Estados (UF) |
| `django_celery_beat_*` | Agendamentos Beat (PeriodicTask, Crontab, etc) |
| `django_session` | Sessões (se não usar Redis) |
| `auth_user`, `auth_group` | Admin users |

---

## ⚙️ Configurações de Produção (Não Aplicadas Ainda)

```yaml
# postgres.conf customizado
command: >
  postgres
  -c max_connections=200
  -c shared_buffers=256MB
  -c effective_cache_size=1GB
  -c maintenance_work_mem=64MB
  -c checkpoint_completion_target=0.9
  -c wal_buffers=16MB
  -c default_statistics_target=100
  -c random_page_cost=1.1
  -c effective_io_concurrency=200
  -c work_mem=4MB
  -c min_wal_size=1GB
  -c max_wal_size=4GB
```

**Como aplicar:** Crie `postgres.conf` e monte:
```yaml
volumes:
  - ./postgres.conf:/etc/postgresql/postgresql.conf:ro
command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

---

## 🛠️ Comandos Úteis

```bash
# Conectar no psql
docker compose exec db psql -U forms_denuncia -d forms_denuncia

# Ver tamanho tabelas
docker compose exec db psql -U forms_denuncia -d forms_denuncia -c "
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables WHERE schemaname='public' ORDER BY size DESC;"

# Backup
docker compose exec db pg_dump -U forms_denuncia forms_denuncia > backup_$(date +%F).sql

# Restore
cat backup_2026-07-28.sql | docker compose exec -T db psql -U forms_denuncia -d forms_denuncia

# Ver logs
docker compose logs -f db

# Ver healthcheck status
docker compose ps db
```

---

## 📚 Referências
- [PostgreSQL Docker Official](https://hub.docker.com/_/postgres)
- [PostgreSQL 16 Docs](https://www.postgresql.org/docs/16/index.html)
- [pg_trgm](https://www.postgresql.org/docs/16/pgtrgm.html)
- [uuid-ossp](https://www.postgresql.org/docs/16/uuid-ossp.html)
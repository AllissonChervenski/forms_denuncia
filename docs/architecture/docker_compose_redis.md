# Docker Compose - Redis (Broker, Cache, Sessions, Results)

## 📍 Arquivo: `docker-compose.yml` (serviço `redis`)

## 🎯 O que é
Container **Redis 7 Alpine** que atua como:
1. **Message Broker** - Filas Celery (DB 0)
2. **Result Backend** - Resultados tasks (DB 0)
3. **Cache Framework** - Django cache, rate limit (DB 1)
4. **Session Store** - Sessões admin/dashboard (DB 1)

---

## 💻 Código Completo

```yaml
# 2. Redis (Message Broker + Cache + Celery Result Backend)
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
  volumes:
    - redis_data:/data
  ports:
    - "6379:6379"
  restart: always
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

---

## 🔍 Linha por Linha

### `image: redis:7-alpine`
- **Redis 7** (versão estável LTS).
- **Alpine** = imagem mínima (~30MB).

### `command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru`

| Flag | Valor | Função |
|------|-------|--------|
| `--appendonly yes` | AOF | **Persistência** - append-only file (cada write no disco) |
| `--maxmemory 256mb` | Limite | Máximo RAM antes de evictar |
| `--maxmemory-policy allkeys-lru` | Política | Remove **menos usado** (LRU) entre **todas chaves** |

#### AOF (Append Only File) vs RDB
| Aspecto | AOF (`--appendonly yes`) | RDB (padrão) |
|---------|--------------------------|--------------|
| Persistência | Cada comando escrito | Snapshot periódico |
| Perda de dados | **Zero** (fsync everysec) | Últimos segundos/minutos |
| Tamanho arquivo | Maior | Menor |
| Recuperação | Replay comandos | Carrega dump |
| **Escolha aqui** | ✅ AOF | - |

**Por que AOF?** Celery broker **não pode perder tasks**. RDB perde últimos writes se crash.

#### `allkeys-lru` - Política de Evicção
```
Memória > 256MB → Redis escolhe chave → Remove LRU (Least Recently Used)
```
- `allkeys` = considera **todas chaves** (não só com TTL).
- `lru` = remove a menos acessada recentemente.
- **Ideal para cache:** Dados antigos/menos usados saem primeiro.

### `volumes: - redis_data:/data`
- Persiste **AOF file** + **RDB dump** + **config**.
- Sobrevive a `docker compose down`, rebuild, restart.

### `ports: - "6379:6379"`
- Expõe no host para debug: `redis-cli -h localhost`
- **Internamente:** serviços usam `redis:6379` (DNS Docker).

### `healthcheck:`
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```
- `redis-cli ping` → retorna `PONG` se vivo.
- `depends_on: condition: service_healthy` garante que Web/Celery/Beat só sobem com Redis pronto.

---

## 🗄️ Databases Lógicos (0-15)

Redis suporta **16 databases** (0-15), isolados por número.

| DB | Uso no Projeto | Configuração |
|----|----------------|--------------|
| **DB 0** | Celery Broker + Result Backend | `CELERY_BROKER_URL=redis://redis:6379/0` |
| **DB 1** | Django Cache + Sessions + Rate Limit | `REDIS_URL=redis://redis:6379/1` |

**Por que separar?**
- `FLUSHDB` no cache (DB 1) **não apaga** filas Celery (DB 0).
- Monitoramento isolado: `INFO keyspace` mostra keys por DB.
- Políticas de memória diferentes se necessário.

---

## 🔗 Integração com Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                      REDIS CONTAINER                        │
│  redis-server --appendonly yes --maxmemory 256mb --lru      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  DB 0: Celery                                       │   │
│  │  ├─ Keys: celery, _kombu.binding.*, celeryev.*     │   │
│  │  ├─ Lists: celery (fila principal)                  │   │
│  │  └─ Strings: celery-task-meta-* (resultados)        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  DB 1: Django Cache/Sessions                        │   │
│  │  ├─ forms_denuncia:cache_key (view cache)           │   │
│  │  ├─ forms_denuncia:rl:ip:... (rate limit)           │   │
│  │  └─ forms_denuncia:session_key (sessões admin)      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Persistência:                                              │
│  ├─ AOF: /data/appendonly.aof (cada write)                 │
│  ├─ RDB: /data/dump.rdb (snapshot)                         │
│  └─ Volume: redis_data:/data                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Monitoramento Redis

```bash
# Conectar
docker compose exec redis redis-cli

# Info geral
> INFO memory
> INFO keyspace
> INFO stats

# Ver chaves DB 0 (Celery)
> SELECT 0
> KEYS *
> LRANGE celery 0 -1

# Ver chaves DB 1 (Cache)
> SELECT 1
> KEYS forms_denuncia:*

# Monitor tempo real (Ctrl+C para sair)
> MONITOR

# Memória por key
> MEMORY USAGE forms_denuncia:cache_key
```

---

## ⚙️ Configurações Avançadas (Produção)

```yaml
command: >
  redis-server
  --appendonly yes
  --appendfsync everysec
  --maxmemory 512mb
  --maxmemory-policy allkeys-lru
  --save 900 1
  --save 300 10
  --save 60 10000
  --tcp-backlog 511
  --timeout 300
  --tcp-keepalive 60
```

| Parâmetro | Produção |
|-----------|----------|
| `--appendfsync everysec` | Balance durabilidade/performance |
| `--save` | RDB snapshots (backup adicional) |
| `--tcp-backlog` | Conexões pendidas altas |
| `--timeout 300` | Fecha conexões ociosas 5min |

---

## 📚 Referências
- [Redis Docker Official](https://hub.docker.com/_/redis)
- [Redis Persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
- [Redis Memory Optimization](https://redis.io/docs/latest/operate/oss_and_stack/management/memory-optimization/)
- [Celery Redis Broker](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html)
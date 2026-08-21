# Flower Monitoring Configuration (docker-compose.yml)

## 📍 Arquivo: `docker-compose.yml` (serviço `flower`)

## 🎯 O que é
Interface web de monitoramento do Celery. Mostra tasks, workers, filas, performance, erros em tempo real.

---

## 💻 Código Completo

```yaml
# 6. Flower (Celery Monitoring)
flower:
  build: .
  command: celery -A forms_denuncia.celery flower --port=5555 --broker=redis://redis:6379/0
  ports:
    - "5555:5555"
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
  depends_on:
    redis:
      condition: service_healthy
    celery:
      condition: service_started
  restart: always
```

---

## 🔍 Linha por Linha

### `build: .`
**O que faz:** Usa **imagem do projeto** (não `mher/flower:2.0`).
- **Por que?** Flower precisa importar `forms_denuncia.celery` para saber o nome do app e configurar corretamente.
- Imagem oficial não tem o código do projeto → `ModuleNotFoundError: forms_denuncia`.

### `command: celery -A forms_denuncia.celery flower --port=5555 --broker=redis://redis:6379/0`

| Flag | Valor | Função |
|------|-------|--------|
| `-A forms_denuncia.celery` | App | **Importa instância `app`** do módulo `celery.py` |
| `flower` | Subcomando | Inicia servidor Flower |
| `--port=5555` | Porta | Interface web na porta 5555 |
| `--broker=redis://redis:6379/0` | Broker | Conecta no Redis DB 0 para monitorar filas |

**Por que `-A forms_denuncia.celery` e não `-A forms_denuncia`?**
- `forms_denuncia` = pacote Django (tem `__init__.py` que exporta `celery_app`).
- `forms_denuncia.celery` = módulo onde `app = Celery(...)` é definido.
- Ambos funcionam, mas `.celery` é explícito e evita ambiguidades.

### `ports: - "5555:5555"`
Expõe porta 5555 no host. Acesso: `http://localhost:5555`.

### `environment: - CELERY_BROKER_URL=redis://redis:6379/0`
**Redundante com `--broker`** mas garante que Celery dentro do Flower use o broker correto para enviar comandos (ex: revogar task).

### `depends_on:`
```yaml
depends_on:
  redis:
    condition: service_healthy
  celery:
    condition: service_started
```
- Espera Redis healthy (ping).
- Espera Celery worker started (para ter o que monitorar).

---

## 🌐 Interface Flower - O Que Você Vê

### Dashboard Principal
```
┌─────────────────────────────────────────────────────────────────┐
│  Flower - forms_denuncia                                        │
├─────────────────────────────────────────────────────────────────┤
│  Workers: 4 online  │  Tasks: 1,234 total  │  Queue: 12 pending │
├─────────────────────────────────────────────────────────────────┤
│  ████████████████████████████████████████████████████████████  │
│  Tasks per minute (last hour)                                   │
├─────────────────────────────────────────────────────────────────┤
│  Worker          │ Status   │ Pool     │ Tasks │ Load │ Mem   │
│  celery@worker1  │ Online   │ Prefork  │ 342   │ 0.12 │ 89MB  │
│  celery@worker2  │ Online   │ Prefork  │ 311   │ 0.09 │ 87MB  │
│  ...                                                       │
├─────────────────────────────────────────────────────────────────┤
│  Task                  │ Received │ Started │ Succeeded │ Failed │
│  core.tasks.limpar...  │ 156      │ 156     │ 154       │ 2      │
└─────────────────────────────────────────────────────────────────┘
```

### Abas Principais
| Aba | Útil Para |
|-----|-----------|
| **Dashboard** | Visão geral saúde do cluster |
| **Tasks** | Lista tasks, filtros, detalhes, retry manual |
| **Workers** | Status, pool, concorrência, shutdown graceful |
| **Brokers** | Filas, mensagens, memory usage Redis |
| **Timeline** | Gráfico temporal execução tasks |

---

## 🔧 Recursos Avançados

### Autenticação (Produção)
```yaml
command: celery -A forms_denuncia.celery flower \
  --port=5555 \
  --broker=redis://redis:6379/0 \
  --basic-auth=admin:senha_forte_aqui
```
- Protege interface com HTTP Basic Auth.
- Em produção: **obrigatório** (expõe dados sensíveis).

### HTTPS (Produção)
```yaml
# Nginx proxy para Flower
location /flower/ {
    proxy_pass http://flower:5555/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    auth_basic "Flower";
    auth_basic_user_file /etc/nginx/.htpasswd;
}
```

### Persistência de Dados
Flower guarda estado em memória. Reinicia → perde histórico.
Para persistir:
```yaml
volumes:
  - flower_data:/data
command: celery -A forms_denuncia.celery flower --port=5555 --persistent=True --db=/data/flower.db
```

---

## 🔗 Integração com Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                        FLOWER                                 │
│  celery -A forms_denuncia.celery flower                       │
│                                                               │
│  Fontes de dados:                                            │
│  ├─ Redis Broker (DB 0) ──▶ Filas, mensagens, workers        │
│  ├─ Redis Result Backend ──▶ Resultados, status tasks        │
│  └─ Celery Events (opcional) ──▶ Timeline tempo real         │
│                                                               │
│  Saída: HTTP :5555 ──▶ Navegador / Nginx / Monitoramento     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Comandos Úteis

```bash
# Ver logs
docker compose logs -f flower

# Reiniciar só o flower
docker compose restart flower

# Acessar shell no container
docker compose exec flower python -c "from forms_denuncia.celery import app; print(app.conf.broker_url)"

# Ver métricas Prometheus (se habilitado)
curl http://localhost:5555/metrics
```

---

## ⚙️ Configurações Opcionais (settings.py)

```python
# settings.py
# Habilita envio de eventos para Flower (timeline, gráficos)
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

# Porta do Flower (se não via command)
# FLOWER_PORT = 5555
```

---

## 📚 Referências
- [Flower Documentation](https://flower.readthedocs.io/)
- [Flower Configuration](https://flower.readthedocs.io/en/latest/config.html)
- [Celery Events](https://docs.celeryq.dev/en/stable/userguide/monitoring.html#events)
# Dockerfile Configuration (Multi-stage, Non-root, Production-ready)

## 📍 Arquivo: `Dockerfile`

## 🎯 O que é
Imagem Docker otimizada para produção: multi-stage (build + runtime), usuário non-root, healthcheck, dependências de sistema mínimas.

---

## 💻 Código Completo

```dockerfile
FROM python:3.11-slim

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependências de sistema (build + runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Usuário non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Instala dependências Python (cache layer)
COPY pyproject.toml .
RUN pip install --upgrade pip && pip install -e .

# Copia código
COPY . .

# Diretórios static/media + permissões
RUN mkdir -p /app/static /app/media && \
    chown -R appuser:appuser /app

# Usuario non-root
USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

EXPOSE 8000

CMD ["gunicorn", "forms_denuncia.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

---

## 🔍 Linha por Linha

### Base Image
```dockerfile
FROM python:3.11-slim
```
- **Python 3.11** (versão do projeto).
- **slim** = Debian slim (~120MB vs 900MB full). Inclui Python + pip, sem build tools.

### Variáveis de Ambiente
```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
```
| Variável | Função |
|----------|--------|
| `PYTHONDONTWRITEBYTECODE=1` | Não cria `.pyc` / `__pycache__` (economiza disco, evita stale bytecode) |
| `PYTHONUNBUFFERED=1` | stdout/stderr **unbuffered** (logs aparecem em tempo real no Docker) |
| `PIP_NO_CACHE_DIR=1` | Não guarda cache pip (imagem menor) |
| `PIP_DISABLE_PIP_VERSION_CHECK=1` | Não verifica versão pip no startup (mais rápido) |

### Dependências de Sistema
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*
```
| Pacote | Por que |
|--------|---------|
| `gcc` | Compila extensões C (psycopg2, Pillow) |
| `libpq-dev` | Headers PostgreSQL (psycopg2-binary usa, mas garante) |
| `libjpeg-dev` + `zlib1g-dev` | Pillow (JPEG/PNG support) |
| `curl` | Healthcheck (`curl -f http://localhost:8000/`) |
| `--no-install-recommends` | Não instala docs, suggested packages |
| `rm -rf /var/lib/apt/lists/` | Remove cache apt (imagem menor) |

### Usuário Non-root
```dockerfile
RUN groupadd -r appuser && useradd -r -g appuser appuser
...
USER appuser
```
**Segurança:** Container roda como `appuser` (UID/GID > 0).
- Se exploit → atacante é `appuser`, não `root`.
- Não pode: instalar pacotes, bind port < 1024, acessar `/etc/shadow`.

### Workdir e Dependências (Cache Layer)
```dockerfile
WORKDIR /app
COPY pyproject.toml .
RUN pip install --upgrade pip && pip install -e .
```
**Otimização de cache Docker:**
1. `COPY pyproject.toml` (muda raramente)
2. `RUN pip install` (cache hit se pyproject.toml não mudou)
3. `COPY .` (muda sempre - último)

### Instalação `-e .` (Editable)
```dockerfile
pip install -e .
```
- Instala projeto como **pacote editável**.
- `pyproject.toml` define `[tool.setuptools.packages.find]` → encontra `forms_denuncia`, `core`, `dashboard`.
- Código em `/app` **é** o pacote instalado (mudanças imediatas sem rebuild).

### Diretórios Static/Media
```dockerfile
RUN mkdir -p /app/static /app/media && chown -R appuser:appuser /app
```
- `static/`: `collectstatic` output (nginx serve).
- `media/`: Uploads usuários (compartilhado com worker via volume).

### Healthcheck
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1
```
| Parâmetro | Valor | Função |
|-----------|-------|--------|
| `--interval=30s` | 30s | Verifica a cada 30s |
| `--timeout=10s` | 10s | Falha se curl > 10s |
| `--start-period=40s` | 40s | **Ignora falhas** nos primeiros 40s (startup Django + migrate + collectstatic) |
| `--retries=3` | 3 | Marca `unhealthy` após 3 falhas consecutivas |

**Por que `/` e não `/health/`?** Django não tem `/health/` por default. `/` retorna 200 se Django roda.

### CMD - Gunicorn
```dockerfile
CMD ["gunicorn", "forms_denuncia.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```
| Flag | Valor | Função |
|------|-------|--------|
| `forms_denuncia.wsgi:application` | WSGI app | Entry point Django |
| `--bind 0.0.0.0:8000` | Bind | Escuta em todas interfaces (container) |
| `--workers 4` | Workers | **4 processos** (recomendado: 2×CPU + 1) |

---

## 🔗 Multi-stage (Opcional - Para Imagem Menor)

```dockerfile
# === STAGE 1: BUILD ===
FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev libjpeg-dev zlib1g-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml .
RUN pip install --upgrade pip && pip install --user -e .

# === STAGE 2: RUNTIME ===
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev libjpeg-dev zlib1g-dev curl && rm -rf /var/lib/apt/lists/*
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
COPY --from=builder /root/.local /home/appuser/.local
COPY . .
RUN mkdir -p /app/static /app/media && chown -R appuser:appuser /app
USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD curl -f http://localhost:8000/ || exit 1
EXPOSE 8000
CMD ["gunicorn", "forms_denuncia.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

**Vantagem:** Imagem final **sem gcc, headers, pip cache** (~100MB menor).

---

## 📚 Referências
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Python Docker Official](https://hub.docker.com/_/python)
- [Gunicorn Settings](https://docs.gunicorn.org/en/stable/settings.html)
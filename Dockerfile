# ==============================================================================
# ESTÁGIO 1: BUILDER (Compilação e Resolução de Dependências)
# Motivo: Compilar extensões C (como psycopg2 e Pillow) sem deixar compiladores
# (gcc, build-essential) na imagem final de produção, reduzindo tamanho e vulnerabilidades.
# ==============================================================================
FROM python:3.11-slim AS builder

# Variáveis de ambiente para otimizar instalação do Python/Pip:
# - PYTHONDONTWRITEBYTECODE=1: Evita escrita de arquivos .pyc no build
# - PYTHONUNBUFFERED=1: Garante logs imediatos no console sem buffer
# - PIP_NO_CACHE_DIR=1: Não mantém cache do pip para economizar espaço
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instala pacotes do sistema necessários para compilar bibliotecas C (PostgreSQL, Pillow/JPEG/Zlib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copia arquivo de especificação de dependências pyproject.toml
COPY pyproject.toml .

# Cria um virtualenv isolado no builder para conter todas as dependências instaladas
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instala as dependências de produção do projeto
RUN pip install --upgrade pip && \
    pip install .

# ==============================================================================
# ESTÁGIO 2: RUNNER (Imagem Final de Produção)
# Motivo: Imagem mínima e limpa apenas com os binários de runtime e código fonte.
# ==============================================================================
FROM python:3.11-slim AS runner

# Variáveis de ambiente de execução
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE="forms_denuncia.settings.production"

# Instala apenas as bibliotecas dinâmicas de runtime necessárias e o curl para healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    zlib1g \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root (appuser: UID 1000) por segurança operacional (Least Privilege Principle)
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m -s /bin/bash appuser

WORKDIR /app

# Copia o ambiente virtual com as dependências instaladas no estágio anterior
COPY --from=builder /opt/venv /opt/venv

# Copia o código-fonte da aplicação (respeitando as exclusões do .dockerignore)
COPY . /app

# Cria diretórios de arquivos estáticos e de mídia e concede permissão ao appuser
RUN mkdir -p /app/static /app/media /app/staticfiles && \
    chmod +x /app/scripts/entrypoint.sh && \
    chown -R appuser:appuser /app

# Define o usuário padrão para execução (nunca rodar containers em produção como root)
USER appuser

# Healthcheck do container: Verifica periodicamente se o serviço HTTP responde
# start-period longo (90s) para permitir que migrações e seed de cidades terminem
HEALTHCHECK --interval=15s --timeout=10s --start-period=90s --retries=5 \
    CMD curl -f http://localhost:8000/ || exit 1

# Expõe a porta 8000 na rede interna do Docker
EXPOSE 8000

# Script de entrada: só o container web roda migrações (CONTAINER_ROLE=web)
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# Comando padrão: Gunicorn com timeout de 120s para evitar WORKER TIMEOUT
CMD ["gunicorn", "forms_denuncia.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--max-requests", "1000", "--timeout", "120", "--graceful-timeout", "30", "--keep-alive", "5"]

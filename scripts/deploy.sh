#!/usr/bin/env bash
# ==============================================================================
# Script de Deploy de Produção - forms_denuncia
# Executado no servidor de produção pelo GitHub Actions ou manualmente.
# ==============================================================================

set -euo pipefail

# Cores para saída no terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Sem Cor

echo -e "${YELLOW}[1/6] Verificando arquivo de ambiente .env...${NC}"
if [ ! -f .env ]; then
    echo -e "${RED}ERRO: Arquivo .env não encontrado no servidor! Abortando deploy.${NC}"
    exit 1
fi

COMPOSE_FILE="docker-compose.prod.yml"

echo -e "${YELLOW}[2/6] Baixando as novas imagens do Container Registry (GHCR)...${NC}"
docker compose -f "${COMPOSE_FILE}" pull web celery celery-beat

echo -e "${YELLOW}[3/6] Executando migrações do banco de dados (PostgreSQL)...${NC}"
docker compose -f "${COMPOSE_FILE}" run --rm web python manage.py migrate --noinput

echo -e "${YELLOW}[4/6] Coletando e compactando arquivos estáticos...${NC}"
docker compose -f "${COMPOSE_FILE}" run --rm web python manage.py collectstatic --noinput

echo -e "${YELLOW}[5/6] Reiniciando containers atualizados em segundo plano...${NC}"
docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans web celery celery-beat nginx

echo -e "${YELLOW}[6/6] Executando Health Check no serviço em produção...${NC}"
MAX_RETRIES=10
RETRY_COUNT=0
HEALTH_URL="http://localhost/pesquisar/"

until curl -f -s -o /dev/null "${HEALTH_URL}" || [ $RETRY_COUNT -eq $MAX_RETRIES ]; do
    echo "Aguardando inicialização da aplicação ($((RETRY_COUNT+1))/$MAX_RETRIES)..."
    sleep 3
    RETRY_COUNT=$((RETRY_COUNT+1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}ERRO: Health Check falhou após ${MAX_RETRIES} tentativas! Verifique os logs dos containers.${NC}"
    docker compose -f "${COMPOSE_FILE}" logs --tail=50 web
    exit 1
fi

echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}✓ Deploy de Produção concluído com sucesso!           ${NC}"
echo -e "${GREEN}======================================================${NC}"

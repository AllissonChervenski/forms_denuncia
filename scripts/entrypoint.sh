#!/usr/bin/env bash
# ==============================================================================
# Entrypoint para Container Docker
# Apenas o container com CONTAINER_ROLE=web executa migrações e seed de cidades.
# Os demais (celery, celery-beat, flower) pulam direto para o comando.
# ==============================================================================

set -e

if [ "${CONTAINER_ROLE}" = "web" ]; then

  echo "==> [1/4] Aguardando PostgreSQL aceitar conexões..."
  python -c "
import os, time, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'forms_denuncia.settings.production'))
django.setup()
from django.db import connection
for i in range(60):
    try:
        connection.ensure_connection()
        print('✓ PostgreSQL conectado!')
        break
    except Exception:
        if i % 5 == 0:
            print(f'  Tentativa {i+1}/60...')
        time.sleep(1)
else:
    print('ERRO: PostgreSQL não respondeu em 60 segundos.')
    exit(1)
"

  echo "==> [2/4] Executando migrações..."
  python manage.py migrate --noinput

  echo "==> [3/4] Coletando arquivos estáticos..."
  python manage.py collectstatic --noinput

  echo "==> [4/4] Populando cidades e estados brasileiros..."
  python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'forms_denuncia.settings.production'))
django.setup()
from core.models import Cidades, Estado
total = Cidades.objects.count()
if total == 0:
    import csv
    for path in ['data/Municipios_normalizados.csv', '/app/data/Municipios_normalizados.csv']:
        if os.path.exists(path):
            with open(path, 'r', encoding='latin-1') as f:
                reader = csv.DictReader(f)
                cache_uf = {}
                lote = []
                for row in reader:
                    uf = row['Chave'].strip()
                    if uf not in cache_uf:
                        cache_uf[uf], _ = Estado.objects.get_or_create(uf=uf)
                    for nome in (c.strip() for c in row['Valores'].split(',') if c.strip()):
                        lote.append(Cidades(nome=nome, estado=cache_uf[uf]))
                Cidades.objects.bulk_create(lote, ignore_conflicts=True)
            print(f'✓ {Cidades.objects.count()} cidades cadastradas!')
            break
    else:
        print('Aviso: CSV de cidades não encontrado.')
else:
    print(f'✓ Base de cidades já populada ({total} municípios).')
"

else
  echo "==> Container [${CONTAINER_ROLE:-unknown}]: pulando migrações e seed (somente web executa)."
fi

echo "==> Iniciando: $@"
exec "$@"

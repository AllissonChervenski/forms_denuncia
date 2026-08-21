#!/usr/bin/env bash
# ==============================================================================
# Entrypoint para Container de Produção / Render / Docker
# ==============================================================================

set -e

echo "==> [1/3] Executando migrações do banco de dados (PostgreSQL)..."
python manage.py migrate --noinput

echo "==> [2/3] Coletando arquivos estáticos (WhiteNoise / Select2 / Admin)..."
python manage.py collectstatic --noinput

echo "==> [3/3] Verificando base de dados de Cidades e Estados..."
python -c "
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'forms_denuncia.settings.production'))
django.setup()
from core.models import Cidades, Estado
try:
    total_cidades = Cidades.objects.count()
    if total_cidades == 0:
        print('Base de cidades vazia. Populando municípios a partir de data/Municipios_normalizados.csv...')
        import csv
        csv_file = 'data/Municipios_normalizados.csv'
        if os.path.exists(csv_file):
            with open(csv_file, 'r', encoding='latin-1') as f:
                reader = csv.DictReader(f)
                estados_criados = {}
                cidades_para_criar = []
                for row in reader:
                    uf = row['Chave'].strip()
                    if uf not in estados_criados:
                        estado_obj, _ = Estado.objects.get_or_create(uf=uf)
                        estados_criados[uf] = estado_obj
                    else:
                        estado_obj = estados_criados[uf]
                    
                    cidades_nomes = [c.strip() for c in row['Valores'].split(',') if c.strip()]
                    for nome_cid in cidades_nomes:
                        cidades_para_criar.append(Cidades(nome=nome_cid, estado=estado_obj))
                
                Cidades.objects.bulk_create(cidades_para_criar, ignore_conflicts=True)
            print(f'✓ Sucesso: {Cidades.objects.count()} cidades e estados populados!')
    else:
        print(f'✓ Base de cidades já populada ({total_cidades} municípios cadastrados).')
except Exception as e:
    print(f'Aviso ao popular cidades: {e}')
" 2>/dev/null || true

echo "==> Iniciando o servidor de aplicação Gunicorn..."
exec "$@"

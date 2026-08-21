"""Testes para a migração 0002 e função popular_cidades_estados (IEEE 829 - Fase 2)."""
import importlib
from unittest.mock import patch
import pytest
from django.apps import apps
from core.models import Estado, Cidades

migration_0002 = importlib.import_module('core.migrations.0002_add_trgm_indexes_')
popular_cidades_estados = migration_0002.popular_cidades_estados


@pytest.mark.django_db
class TestMigration0002:
    """Suite de Testes para Migração 0002 (Carga de Estados e Cidades)."""

    def test_popular_cidades_estados_csv_existente(self):
        """TC-MIG.1: Executa popular_cidades_estados com o CSV real e valida criação no banco."""
        popular_cidades_estados(apps, None)

        # Valida que todos os 27 estados/DF foram cadastrados
        assert Estado.objects.count() >= 27
        assert Estado.objects.filter(uf='PR').exists()
        assert Estado.objects.filter(uf='SP').exists()
        assert Estado.objects.filter(uf='RJ').exists()

        # Valida que cidades conhecidas foram criadas e vinculadas aos respectivos estados
        assert Cidades.objects.count() >= 5000
        assert Cidades.objects.filter(nome='Curitiba', estado__uf='PR').exists()
        assert Cidades.objects.filter(nome='São Paulo', estado__uf='SP').exists()
        assert Cidades.objects.filter(nome='Rio de Janeiro', estado__uf='RJ').exists()

    def test_popular_cidades_estados_idempotencia(self):
        """TC-MIG.2: Executa duas vezes consecutivas para garantir que não duplica registros."""
        popular_cidades_estados(apps, None)
        estados_count_1 = Estado.objects.count()
        cidades_count_1 = Cidades.objects.count()

        # Segunda execução
        popular_cidades_estados(apps, None)
        estados_count_2 = Estado.objects.count()
        cidades_count_2 = Cidades.objects.count()

        assert estados_count_1 == estados_count_2
        assert cidades_count_1 == cidades_count_2

    @patch('os.path.exists', return_value=False)
    def test_popular_cidades_estados_csv_inexistente(self, mock_exists, capsys):
        """TC-MIG.3: Simula ausência do CSV e valida que a função trata o aviso sem exceções."""
        # Não deve lançar FileNotFoundError ou qualquer exceção
        popular_cidades_estados(apps, None)

        captured = capsys.readouterr()
        assert "AVISO: CSV não encontrado" in captured.out

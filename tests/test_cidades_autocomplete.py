"""Testes para a view CidadesAutocomplete (IEEE 829 - Fase 2)."""
import pytest
from django.urls import reverse
from django.test import Client, RequestFactory
from core.models import Cidades, Estado
from core.views import CidadesAutocomplete
from .factories import CidadeFactory, EstadoFactory


@pytest.mark.django_db
class TestCidadesAutocomplete:
    """Suite de Testes para Autocomplete de Cidades."""

    def test_autocomplete_sem_query(self, rf: RequestFactory):
        """TC-AC.1: Retorna queryset base sem filtro quando não há parâmetro q."""
        estado, _ = Estado.objects.get_or_create(uf='PR')
        c1, _ = Cidades.objects.get_or_create(nome='Curitiba', estado=estado)
        c2, _ = Cidades.objects.get_or_create(nome='Londrina', estado=estado)
        c3, _ = Cidades.objects.get_or_create(nome='Maringá', estado=estado)

        request = rf.get('/cidades-autocomplete/')
        view = CidadesAutocomplete()
        view.setup(request)
        view.q = None

        qs = view.get_queryset()
        cidades_nomes = list(qs.values_list('nome', flat=True))

        assert len(qs) >= 3
        assert c1.nome in cidades_nomes
        assert c2.nome in cidades_nomes
        assert c3.nome in cidades_nomes

    def test_autocomplete_com_busca_exata(self, client: Client):
        """TC-AC.2: Busca exata por 'Curitiba', valida ordenação e similaridade."""
        estado, _ = Estado.objects.get_or_create(uf='PR')
        c_curitiba, _ = Cidades.objects.get_or_create(nome='Curitiba', estado=estado)

        url = reverse('core:cidades-autocomplete')
        response = client.get(url, {'q': 'Curitiba'})

        assert response.status_code == 200
        data = response.json()
        results = data.get('results', [])

        assert len(results) > 0
        # O primeiro resultado deve ser a cidade exata Curitiba
        assert 'Curitiba' in results[0]['text']
        cidade_top = Cidades.objects.get(id=int(results[0]['id']))
        assert cidade_top.nome == 'Curitiba'

    def test_autocomplete_com_acentuacao(self, client: Client):
        """TC-AC.3: Busca 'Sao Paulo' sem acento, deve retornar 'São Paulo' via Unaccent."""
        estado, _ = Estado.objects.get_or_create(uf='SP')
        c_sp, _ = Cidades.objects.get_or_create(nome='São Paulo', estado=estado)

        url = reverse('core:cidades-autocomplete')
        response = client.get(url, {'q': 'Sao Paulo'})

        assert response.status_code == 200
        data = response.json()
        results = data.get('results', [])

        assert len(results) > 0
        assert 'São Paulo' in results[0]['text']
        cidade_top = Cidades.objects.get(id=int(results[0]['id']))
        assert cidade_top.nome == 'São Paulo'

    def test_autocomplete_com_erro_ortografico(self, client: Client):
        """TC-AC.4: Busca 'Curtiba' com erro de digitação, deve retornar 'Curitiba' via TrigramSimilarity."""
        estado, _ = Estado.objects.get_or_create(uf='PR')
        c_curitiba, _ = Cidades.objects.get_or_create(nome='Curitiba', estado=estado)

        url = reverse('core:cidades-autocomplete')
        response = client.get(url, {'q': 'Curtiba'})

        assert response.status_code == 200
        data = response.json()
        results = data.get('results', [])

        assert len(results) > 0
        assert 'Curitiba' in results[0]['text']
        cidade_top = Cidades.objects.get(id=int(results[0]['id']))
        assert cidade_top.nome == 'Curitiba'

    def test_autocomplete_result_label(self):
        """TC-AC.5: Valida se o rótulo de retorno formatado contém Nome, Estado sem tags HTML."""
        estado, _ = Estado.objects.get_or_create(uf='PR')
        cidade, _ = Cidades.objects.get_or_create(nome='Curitiba', estado=estado)

        view = CidadesAutocomplete()
        label = view.get_result_label(cidade)

        expected_label = f"{cidade.nome}, {cidade.estado}"
        assert str(label) == expected_label
        assert "Curitiba, PR" == str(label)

    def test_autocomplete_query_vazia_ou_espacos(self, client: Client):
        """TC-AC.6: Busca apenas com espaços ou string vazia."""
        url = reverse('core:cidades-autocomplete')

        # Query vazia
        response_empty = client.get(url, {'q': ''})
        assert response_empty.status_code == 200
        data_empty = response_empty.json()
        assert len(data_empty.get('results', [])) >= 1

        # Query apenas com espaços
        response_spaces = client.get(url, {'q': '   '})
        assert response_spaces.status_code == 200

    @pytest.mark.parametrize("payload", [
        "' OR '1'='1",
        "%",
        "_",
        "<script>alert('xss')</script>",
        "SELECT * FROM core_cidades",
        "Curitiba'--",
    ])
    def test_autocomplete_caracteres_especiais(self, client: Client, payload: str):
        """TC-AC.7: Busca com caracteres SQL/REGEX e caracteres especiais."""
        url = reverse('core:cidades-autocomplete')
        response = client.get(url, {'q': payload})

        assert response.status_code == 200
        data = response.json()
        assert 'results' in data

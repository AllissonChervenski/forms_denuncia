"""Testes para a view index (IEEE 829 - Fase 2)."""
import io
from unittest.mock import patch
import pytest
from PIL import Image
from django.urls import reverse
from django.test import Client
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import Denuncia, Evidencia, Estado, Cidades
from .factories import CidadeFactory, EstadoFactory


def get_test_image(name: str = 'evidencia.jpg') -> SimpleUploadedFile:
    """Gera uma imagem JPEG válida em memória para testes de upload."""
    buffer = io.BytesIO()
    img = Image.new('RGB', (50, 50), color='red')
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type='image/jpeg')


@pytest.mark.django_db
class TestIndexView:
    """Suite de Testes para a View Index (Criação de Denúncias)."""

    def test_index_get_sucesso(self, client: Client):
        """TC-IDX.1: Requisição GET carrega formulários limpos e retorna status 200."""
        url = reverse('core:index')
        response = client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context
        assert 'files' in response.context
        assert response.context['title'] == 'Nova Denuncia'
        # O formulário não deve estar vinculado a dados anteriores
        assert not response.context['form'].is_bound
        content = response.content.decode('utf-8')
        assert 'Nome da Empresa' in content
        assert 'Endereço da Empresa' in content

    def test_index_post_sucesso_sem_arquivos(self, client: Client):
        """TC-IDX.2: Submissão do formulário de denúncia sem anexos de imagem."""
        estado, _ = Estado.objects.get_or_create(uf='PR')
        cidade, _ = Cidades.objects.get_or_create(nome='Curitiba', estado=estado)

        url = reverse('core:index')
        payload = {
            'nome_empresa': 'Tech Solutions Ltda',
            'endereco_empresa': 'Rua das Flores, 100',
            'cidade': cidade.pk,
            'tipo_denuncia': 'ASSEDIO',
            'descricao': 'Relato detalhado sobre condições inadequadas de trabalho.',
            'testemunhas': 'João e Maria',
            'acoes': 'Nenhuma ação tomada pela gerência.',
            'data_ocorrido': '2026-08-01',
            'anonimo': True,
            'email': '',
        }

        response = client.post(url, payload)

        assert response.status_code == 302
        denuncia = Denuncia.objects.filter(nome_empresa='Tech Solutions Ltda').first()
        assert denuncia is not None
        assert denuncia.tipo_denuncia == 'ASSEDIO'
        assert str(denuncia.cidade) == 'Curitiba'
        assert response.url == reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})
        assert Evidencia.objects.filter(denuncia=denuncia).count() == 0

    @patch('core.views.limpar_exif_imagem.delay')
    def test_index_post_sucesso_com_multiplas_imagens(self, mock_limpar_exif, client: Client):
        """TC-IDX.3: Submissão com múltiplos arquivos de imagem e valida enfileiramento das tarefas."""
        estado, _ = Estado.objects.get_or_create(uf='SC')
        cidade, _ = Cidades.objects.get_or_create(nome='Joinville', estado=estado)

        url = reverse('core:index')
        img1 = get_test_image('evidencia1.jpg')
        img2 = get_test_image('evidencia2.jpg')

        payload = {
            'nome_empresa': 'Indústria Mecânica Joinville',
            'endereco_empresa': 'Av. Industrial, 500',
            'cidade': cidade.pk,
            'tipo_denuncia': 'SEGURANCA',
            'descricao': 'Falta de equipamentos de proteção individual no setor de solda.',
            'testemunhas': '',
            'acoes': '',
            'data_ocorrido': '2026-08-10',
            'anonimo': True,
            'email': '',
            'imagem': [img1, img2],
        }

        response = client.post(url, payload)

        assert response.status_code == 302
        denuncia = Denuncia.objects.filter(nome_empresa='Indústria Mecânica Joinville').first()
        assert denuncia is not None
        assert response.url == reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})

        evidencias = Evidencia.objects.filter(denuncia=denuncia)
        assert evidencias.count() == 2

        # Valida que o Celery delay foi chamado para cada uma das evidências
        assert mock_limpar_exif.call_count == 2
        called_ids = [call.args[0] for call in mock_limpar_exif.call_args_list]
        for ev in evidencias:
            assert ev.id in called_ids

    def test_index_post_form_invalido(self, client: Client):
        """TC-IDX.4: Submissão com campos obrigatórios ausentes renderiza erros no form sem redirecionar."""
        url = reverse('core:index')
        payload = {
            'nome_empresa': '',  # Obrigatório ausente
            'endereco_empresa': '',
            'cidade': '',
            'tipo_denuncia': '',
            'descricao': '',
        }

        response = client.post(url, payload)

        assert response.status_code == 200
        assert 'form' in response.context
        form = response.context['form']
        assert not form.is_valid()
        assert 'nome_empresa' in form.errors
        assert 'endereco_empresa' in form.errors
        assert 'cidade' in form.errors
        assert 'tipo_denuncia' in form.errors
        assert 'descricao' in form.errors

    def test_index_post_rate_limit_excedido(self, client: Client):
        """TC-IDX.5: Dispara mais de 10 POSTs em 1 minuto e valida resposta 429 (ratelimited_error)."""
        cache.clear()
        try:
            estado, _ = Estado.objects.get_or_create(uf='PR')
            cidade, _ = Cidades.objects.get_or_create(nome='Curitiba', estado=estado)
            url = reverse('core:index')

            payload = {
                'nome_empresa': 'Empresa Rate Limit Test',
                'endereco_empresa': 'Rua Teste, 100',
                'cidade': cidade.pk,
                'tipo_denuncia': 'OUTROS',
                'descricao': 'Descrição de teste de rate limit',
                'anonimo': True,
            }

            # Envia 10 requisições POST válidas (limite é 10/m)
            for i in range(10):
                resp = client.post(url, payload)
                assert resp.status_code == 302, f"POST #{i+1} falhou com {resp.status_code}"

            # O 11º POST deve ser bloqueado com 429
            resp_bloqueado = client.post(url, payload)
            assert resp_bloqueado.status_code == 429
            assert "Muitas requisições" in resp_bloqueado.content.decode('utf-8')
        finally:
            cache.clear()

    def test_index_get_rate_limit_excedido(self, client: Client):
        """TC-IDX.6: Dispara mais de 30 GETs em 1 minuto e valida resposta 429."""
        cache.clear()
        try:
            url = reverse('core:index')

            # Envia 30 requisições GET válidas (limite é 30/m)
            for i in range(30):
                resp = client.get(url)
                assert resp.status_code == 200, f"GET #{i+1} falhou com {resp.status_code}"

            # O 31º GET deve ser bloqueado com 429
            resp_bloqueado = client.get(url)
            assert resp_bloqueado.status_code == 429
            assert "Muitas requisições" in resp_bloqueado.content.decode('utf-8')
        finally:
            cache.clear()

"""Testes de robustez e casos de borda (Suite 4 - IEEE 829)."""
import pytest
from django.urls import reverse
from django.test import Client
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from core.forms import UploadEvidencias
from .factories import DenunciaFactory, UserFactory


@pytest.mark.django_db
class TestRobustezECasosDeBorda:
    """Suite 4: Robustez e Casos de Borda (T4)."""

    def test_tc_t4_1_rate_limit_protocolo(self, client: Client):
        """TC-T4.1: Teste de Rate Limit: Exceder o limite de requisições na view protocolo."""
        cache.clear()
        try:
            admin_user = UserFactory()
            client.force_login(admin_user)

            denuncia = DenunciaFactory(situacao=True)
            url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})

            # Realiza 20 requisições POST válidas (limite é 20/m)
            for i in range(20):
                response = client.post(url, {'action': 'save', 'resposta': f'Atualização {i}'})
                assert response.status_code == 302, f"Requisição {i + 1} falhou com status {response.status_code}"

            # A 21ª requisição deve ser bloqueada pelo ratelimit (status 429)
            response_blocked = client.post(url, {'action': 'save', 'resposta': 'Tentativa bloqueada'})
            assert response_blocked.status_code == 429
            assert "Muitas requisições" in response_blocked.content.decode('utf-8')
        finally:
            cache.clear()

    def test_tc_t4_2_pesquisar_com_url(self, client: Client):
        """TC-T4.2: Pesquisa com URL: A view pesquisar redireciona corretamente com URL contendo UUID."""
        denuncia = DenunciaFactory()
        url_pesquisar = reverse('core:pesquisar')
        full_url_query = f"http://127.0.0.1:8000/protocolo/{denuncia.protocolo}/"

        response = client.get(url_pesquisar, {'query': full_url_query})

        expected_redirect_url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})
        assert response.status_code == 302
        assert response.url == expected_redirect_url

    def test_tc_t4_3_pesquisar_com_uuid(self, client: Client):
        """TC-T4.3: Pesquisa com UUID: A view pesquisar redireciona corretamente com UUID direto."""
        denuncia = DenunciaFactory()
        url_pesquisar = reverse('core:pesquisar')

        response = client.get(url_pesquisar, {'query': str(denuncia.protocolo)})

        expected_redirect_url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})
        assert response.status_code == 302
        assert response.url == expected_redirect_url

    def test_tc_t4_4_salvar_com_resposta_vazia(self, client: Client):
        """TC-T4.4: Salvar com Resposta Vazia: Admin clica em 'Salvar' com campo de resposta vazio."""
        admin_user = UserFactory()
        client.force_login(admin_user)

        denuncia = DenunciaFactory(situacao=True, resposta="Resposta prévia")
        url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})

        response = client.post(url, {
            'action': 'save',
            'resposta': '',
        })

        assert response.status_code == 302
        denuncia.refresh_from_db()
        # O campo de resposta é atualizado para vazio e situação permanece True (Aberta)
        assert denuncia.resposta == ''
        assert denuncia.situacao is True

    def test_tc_t4_5_upload_arquivo_invalido_nao_imagem(self):
        """TC-T4.5: Imagem Maliciosa/Inválida: Upload de arquivo que não é imagem."""
        fake_file = SimpleUploadedFile(
            name='exploit.sh',
            content=b'#!/bin/bash\necho "exploit"',
            content_type='text/plain',
        )

        form = UploadEvidencias(files={'imagem': fake_file})
        assert not form.is_valid()
        assert 'imagem' in form.errors

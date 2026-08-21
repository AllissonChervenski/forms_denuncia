"""Testes de segurança (Suite 3 - IEEE 829)."""
import html
import pytest
from django.conf import settings
from django.urls import reverse
from django.test import Client
from .factories import DenunciaFactory, UserFactory


@pytest.mark.django_db
class TestSeguranca:
    """Suite 3: Segurança (T3)."""

    def test_tc_t3_1_bola_anonimo_tenta_fechar_denuncia(self, client: Client):
        """TC-T3.1: BOLA (Anônimo -> Admin): Usuário anônimo tenta fechar uma denúncia."""
        denuncia = DenunciaFactory(situacao=True, resposta="Estado inicial")
        url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})

        response = client.post(url, {
            'action': 'close',
            'resposta': 'Tentativa não autorizada de fechar denúncia',
        })

        # Servidor deve redirecionar para a página de login (status 302)
        assert response.status_code == 302
        assert settings.LOGIN_URL in response.url

        # O estado da denúncia não deve ser alterado
        denuncia.refresh_from_db()
        assert denuncia.situacao is True
        assert denuncia.resposta == "Estado inicial"

    def test_tc_t3_2_bola_outro_admin(self, client: Client):
        """TC-T3.2: BOLA (Outro Admin): Verificação de controle de acesso entre admins (N/A no escopo atual)."""
        # Conforme o plano IEEE 829, não há controle por proprietário no escopo atual.
        # Qualquer admin autenticado possui permissão de gerência global de denúncias.
        admin_b = UserFactory()
        client.force_login(admin_b)

        denuncia = DenunciaFactory(situacao=True)
        url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})

        response = client.post(url, {
            'action': 'save',
            'resposta': 'Resposta pelo Admin B',
        })

        assert response.status_code == 302
        denuncia.refresh_from_db()
        assert denuncia.resposta == 'Resposta pelo Admin B'

    def test_tc_t3_3_xss_na_resposta(self, client: Client):
        """TC-T3.3: XSS na Resposta: Admin tenta injetar script no campo de resposta."""
        admin_user = UserFactory()
        client.force_login(admin_user)

        xss_payload = "<script>alert('XSS')</script>"
        denuncia = DenunciaFactory(situacao=True)
        url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})

        # Envia a resposta com o script malicioso
        post_response = client.post(url, {
            'action': 'save',
            'resposta': xss_payload,
        })
        assert post_response.status_code == 302

        # Acessa a página renderizada para verificar se o script foi escapado
        get_response = client.get(url)
        assert get_response.status_code == 200

        content = get_response.content.decode('utf-8')

        # A tag crua <script>alert('XSS')</script> não deve estar presente sem escape
        assert xss_payload not in content
        # O script deve ser devidamente escapado em entidades HTML
        escaped_payload = html.escape(xss_payload)
        assert escaped_payload in content or '&lt;script&gt;' in content

    @pytest.mark.parametrize("malicious_action", ["delete", "drop", "admin_override", "../exploit", "eval()"])
    def test_tc_t3_4_injecao_parametro_action(self, client: Client, malicious_action: str):
        """TC-T3.4: Injeção de Parâmetro: Envio de action inesperado ou malicioso."""
        admin_user = UserFactory()
        client.force_login(admin_user)

        denuncia = DenunciaFactory(situacao=True, resposta="Resposta intacta")
        url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})

        response = client.post(url, {
            'action': malicious_action,
            'resposta': 'Tentativa com action malicioso',
        })

        # Não deve ocorrer erro 500; a aplicação redireciona ou renderiza normalmente
        assert response.status_code != 500

        # O estado da denúncia e da situação permanece inalterado
        denuncia.refresh_from_db()
        assert denuncia.situacao is True
        assert denuncia.resposta == "Resposta intacta"

"""Testes para a view de protocolo (Suites 1 e 2 - IEEE 829)."""
import pytest
from django.urls import reverse
from django.test import Client
from .factories import DenunciaFactory, UserFactory


@pytest.mark.django_db
class TestGerenciamentoEstadoDenuncia:
    """Suite 1: Gerenciamento de Estado da Denúncia (T1)."""

    def test_tc_t1_1_salvar_resposta_admin(self, client: Client):
        """TC-T1.1: Salvar Resposta (Admin): Admin adiciona uma resposta sem fechar a denúncia."""
        admin_user = UserFactory()
        client.force_login(admin_user)

        denuncia = DenunciaFactory(situacao=True, resposta="")
        url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})

        response = client.post(url, {
            'action': 'save',
            'resposta': 'Análise em andamento.',
        })

        assert response.status_code == 302
        assert response.url == url

        denuncia.refresh_from_db()
        assert denuncia.resposta == 'Análise em andamento.'
        assert denuncia.situacao is True

    def test_tc_t1_2_fechar_denuncia_admin(self, client: Client):
        """TC-T1.2: Fechar Denúncia (Admin): Admin adiciona resposta e fecha a denúncia."""
        admin_user = UserFactory()
        client.force_login(admin_user)

        denuncia = DenunciaFactory(situacao=True, resposta="")
        url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})

        response = client.post(url, {
            'action': 'close',
            'resposta': 'Resolvido.',
        })

        assert response.status_code == 302
        assert response.url == url

        denuncia.refresh_from_db()
        assert denuncia.resposta == 'Resolvido.'
        assert denuncia.situacao is False

    def test_tc_t1_3_reabrir_denuncia_admin(self, client: Client):
        """TC-T1.3: Reabrir Denúncia (Admin): Admin reabre uma denúncia que estava fechada."""
        admin_user = UserFactory()
        client.force_login(admin_user)

        denuncia = DenunciaFactory(situacao=False, resposta="Resolvido anteriormente.")
        url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})

        response = client.post(url, {
            'action': 'reopen',
        })

        assert response.status_code == 302
        assert response.url == url

        denuncia.refresh_from_db()
        assert denuncia.situacao is True


@pytest.mark.django_db
class TestControleAcessoEUI:
    """Suite 2: Controle de Acesso e UI (T2)."""

    def test_tc_t2_1_ui_denuncia_aberta_admin(self, client: Client):
        """TC-T2.1: UI Denúncia Aberta (Admin): Visão do admin em uma denúncia aberta."""
        admin_user = UserFactory()
        client.force_login(admin_user)

        denuncia = DenunciaFactory(situacao=True)
        url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})

        response = client.get(url)
        assert response.status_code == 200

        content = response.content.decode('utf-8')
        # Exibe o campo 'resposta' e botões Salvar e Fechar Denúncia
        assert 'name="resposta"' in content
        assert 'value="save"' in content
        assert 'Salvar' in content
        assert 'value="close"' in content
        assert 'Fechar Denúncia' in content
        # Não exibe botão de reabrir nem caixa "Guarde seu link"
        assert 'value="reopen"' not in content
        assert 'Guarde o seu link de acompanhamento' not in content

    def test_tc_t2_2_ui_denuncia_fechada_admin(self, client: Client):
        """TC-T2.2: UI Denúncia Fechada (Admin): Visão do admin em uma denúncia fechada."""
        admin_user = UserFactory()
        client.force_login(admin_user)

        denuncia = DenunciaFactory(situacao=False)
        url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})

        response = client.get(url)
        assert response.status_code == 200

        content = response.content.decode('utf-8')
        # Não exibe o campo resposta nem botões Salvar/Fechar
        assert 'name="resposta"' not in content
        assert 'value="save"' not in content
        assert 'value="close"' not in content
        # Exibe o botão de reabrir
        assert 'value="reopen"' in content
        assert 'Reabrir Denúncia' in content
        # Não exibe a caixa "Guarde seu link"
        assert 'Guarde o seu link de acompanhamento' not in content

    def test_tc_t2_3_ui_denuncia_anonimo(self, client: Client):
        """TC-T2.3: UI Denúncia (Anônimo): Visão do usuário anônimo."""
        denuncia = DenunciaFactory(situacao=True)
        url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})

        response = client.get(url)
        assert response.status_code == 200

        content = response.content.decode('utf-8')
        # NÃO exibe nenhum dos botões de admin
        assert 'name="action"' not in content
        assert 'value="save"' not in content
        assert 'value="close"' not in content
        assert 'value="reopen"' not in content
        assert 'name="resposta"' not in content
        # Exibe a caixa "Guarde seu link"
        assert 'Guarde o seu link de acompanhamento' in content

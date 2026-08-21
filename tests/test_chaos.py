"""Testes de caos e cenários adversários (IEEE 829 - Fase 2)."""
import uuid
import pytest
from django.urls import reverse
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import Denuncia, Evidencia, Estado, Cidades
from core.tasks import limpar_exif_imagem
from .factories import DenunciaFactory, UserFactory
from django.db import OperationalError


@pytest.mark.django_db
class TestChaosEAdversarial:
    """Suite de Testes Adversariais e Casos Limítrofes (Chaos Testing)."""

    def test_denuncia_descricao_payload_gigante(self, client: Client):
        """TC-CHS.1: Submete denúncia com payload gigante de 500KB no campo descrição."""
        estado, _ = Estado.objects.get_or_create(uf='PR')
        cidade, _ = Cidades.objects.get_or_create(nome='Curitiba', estado=estado)

        url = reverse('core:index')
        payload_grande = "A" * (500 * 1024)  # 500 KB de texto

        data = {
            'nome_empresa': 'Empresa Grande Payload',
            'endereco_empresa': 'Rua Teste, 100',
            'cidade': cidade.pk,
            'tipo_denuncia': 'VIOLACAO',
            'descricao': payload_grande,
            'anonimo': True,
        }

        response = client.post(url, data)

        assert response.status_code == 302
        denuncia = Denuncia.objects.filter(nome_empresa='Empresa Grande Payload').first()
        assert denuncia is not None
        assert len(denuncia.descricao) == 500 * 1024

    def test_task_exif_com_imagem_corrompida(self):
        """TC-CHS.2: Executa limpar_exif_imagem com binário corrompido e valida tratamento de erro."""
        denuncia = DenunciaFactory()
        arquivo_corrompido = SimpleUploadedFile(
            name='corrompido.jpg',
            content=b'\x00\x01\x02\x03\xff\xfeNaoEhUmaImagemValida',
            content_type='image/jpeg',
        )
        evidencia = Evidencia.objects.create(denuncia=denuncia, imagem=arquivo_corrompido)

        resultado = limpar_exif_imagem(evidencia.id)

        assert isinstance(resultado, str)
        assert resultado.startswith("Erro ao processar imagem:")

    def test_task_exif_id_inexistente(self):
        """TC-CHS.3: Executa limpar_exif_imagem com ID inexistente na tabela Evidencia."""
        id_inexistente = 99999999
        resultado = limpar_exif_imagem(id_inexistente)

        assert resultado == f"Erro: Evidência #{id_inexistente} não encontrada."

    @pytest.mark.parametrize("query_param", [
        "\x00",
        "NULL",
        "A" * 10000,
        "🚀💥\u200b\ufeff\x1b[31m",
        "../../etc/passwd",
        "<script>alert(1)</script>",
        "'; DROP TABLE core_denuncia; --",
    ])
    def test_pesquisar_query_nula_e_caracteres_controle(self, client: Client, query_param: str):
        """TC-CHS.4: Busca no endpoint /pesquisar/ com caracteres de controle, unicode e strings imensas."""
        url = reverse('core:pesquisar')
        response = client.get(url, {'query': query_param})

        # Não deve retornar 500 (Internal Server Error)
        assert response.status_code in [200, 302]

    def test_protocolo_inexistente_retorna_404_ou_mensagem(self, client: Client):
        """TC-CHS.5: Busca um protocolo UUID válido porém inexistente e valida mensagem no template."""
        protocolo_aleatorio = uuid.uuid4()
        url = reverse('core:protocolo', kwargs={'protocolo': protocolo_aleatorio})

        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Nenhuma denúncia encontrada com o protocolo fornecido" in content

    def test_tc_chs_6_falha_db_durante_salvamento_resposta(self, client: Client, mocker):
        """TC-CHS.6: Simula falha de DB durante POST na view protocolo para garantir rollback."""
        # Configuração do cenário
        admin_user = UserFactory()
        client.force_login(admin_user)
        denuncia = DenunciaFactory(situacao=True, resposta="Resposta Original")
        url = reverse('core:protocolo', kwargs={'protocolo': denuncia.protocolo})

        # Mock para simular a falha no DB (OperationalError) durante o 'save'
        # A falha ocorrerá na chamada 'denuncia.save()' dentro da view
        mocker.patch(
            'core.models.Denuncia.save',
            side_effect=OperationalError("Simulação de falha de conexão com o banco de dados")
        )

        # Ação: Tenta salvar uma nova resposta, esperando que a falha no DB ocorra
        with pytest.raises(OperationalError):
            client.post(url, {
                'action': 'save',
                'resposta': 'Nova resposta que não deve ser salva',
            })

        # Verificação: Confirma que o estado da denúncia não foi alterado (rollback)
        denuncia.refresh_from_db()
        assert denuncia.resposta == "Resposta Original"

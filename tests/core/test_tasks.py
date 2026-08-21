"""Testes para as tarefas Celery do aplicativo core."""
import io
import os
import pytest
from PIL import Image
from core.tasks import limpar_exif_imagem, limpar_e_comprimir_imagem, MAX_IMAGE_DIMENSION
from core.models import Evidencia, Denuncia, Cidades, Estado
from django.core.files.uploadedfile import SimpleUploadedFile

@pytest.fixture
def denuncia_teste(db):
    """Fixture para criar uma denúncia base para os testes."""
    estado, _ = Estado.objects.get_or_create(uf='SP')
    cidade, _ = Cidades.objects.get_or_create(nome='São Paulo', estado=estado)
    return Denuncia.objects.create(
        nome_empresa='Empresa Teste',
        endereco_empresa='Rua Teste, 123',
        cidade=cidade,
        tipo_denuncia='ASSEDIO',
        descricao='Descrição',
    )

@pytest.fixture
def evidencia_com_imagem_real(db, denuncia_teste, tmp_path):
    """Fixture para criar uma Evidencia com uma imagem JPEG real em memória."""
    img = Image.new('RGB', (2400, 1600), color='red')
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=95)
    buf.seek(0)
    
    arquivo = SimpleUploadedFile('foto_teste.jpg', buf.read(), content_type='image/jpeg')
    return Evidencia.objects.create(denuncia=denuncia_teste, imagem=arquivo)

@pytest.mark.django_db
def test_limpar_exif_e_comprimir_imagem_real(evidencia_com_imagem_real):
    """Testa se a tarefa limpa EXIF, redimensiona e comprime com sucesso uma imagem real."""
    caminho = evidencia_com_imagem_real.imagem.path
    tamanho_antes = os.path.getsize(caminho)

    resultado = limpar_exif_imagem(evidencia_com_imagem_real.id)

    assert 'SUCESSO' in resultado
    assert 'limpo e imagem comprimida' in resultado
    assert os.path.exists(caminho)

    # Verifica se a imagem foi redimensionada respeitando o MAX_IMAGE_DIMENSION
    with Image.open(caminho) as img_processada:
        assert max(img_processada.width, img_processada.height) <= MAX_IMAGE_DIMENSION
        assert img_processada.format == 'JPEG'

    tamanho_depois = os.path.getsize(caminho)
    assert tamanho_depois <= tamanho_antes

@pytest.mark.django_db
def test_limpar_exif_imagem_png(db, denuncia_teste):
    """Testa o processamento e compressão de imagem no formato PNG."""
    img = Image.new('RGBA', (800, 600), color=(0, 128, 255, 200))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    arquivo = SimpleUploadedFile('documento.png', buf.read(), content_type='image/png')
    evidencia = Evidencia.objects.create(denuncia=denuncia_teste, imagem=arquivo)

    resultado = limpar_e_comprimir_imagem(evidencia.id)
    assert 'SUCESSO' in resultado

    with Image.open(evidencia.imagem.path) as img_processada:
        assert img_processada.format == 'PNG'

@pytest.mark.django_db
def test_limpar_exif_imagem_nao_encontrada():
    """Testa o comportamento da tarefa quando a Evidencia não é encontrada."""
    resultado = limpar_exif_imagem(99999)  # ID que não existe
    assert 'Erro' in resultado
    assert 'não encontrada' in resultado

@pytest.mark.django_db
def test_limpar_exif_imagem_arquivo_inexistente(db, denuncia_teste):
    """Testa o comportamento da tarefa quando o registro existe mas o arquivo não está no disco."""
    evidencia = Evidencia.objects.create(denuncia=denuncia_teste, imagem='inexistente.jpg')
    resultado = limpar_exif_imagem(evidencia.id)
    assert 'Erro' in resultado
    assert 'não encontrado' in resultado

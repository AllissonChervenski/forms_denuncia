"""Testes para os formulários do aplicativo core."""
import pytest
from core.forms import NewDenunciaForm, CloseDenunciaForm, UploadEvidencias
from core.models import Cidades, Estado, Denuncia
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile

def criar_imagem_teste():
    """Cria uma imagem JPEG em memória para testes de upload."""
    img = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return SimpleUploadedFile('test.jpg', buffer.read(), content_type='image/jpeg')

@pytest.fixture
def denuncia_teste(db):
    """Fixture para criar uma Denuncia base para os testes de formulário."""
    estado, _ = Estado.objects.get_or_create(uf='SP')
    cidade, _ = Cidades.objects.get_or_create(nome='São Paulo', estado=estado)
    return Denuncia.objects.create(
        nome_empresa='Empresa Teste',
        endereco_empresa='Rua Teste, 123',
        cidade=cidade,
        tipo_denuncia='ASSEDIO',
        descricao='Descrição do assédio',
    )

@pytest.fixture
def cidade(db):
    """Fixture para criar uma Cidade para ser usada nos formulários."""
    estado, _ = Estado.objects.get_or_create(uf='RJ')
    return Cidades.objects.get_or_create(nome='Rio de Janeiro', estado=estado)[0]

@pytest.mark.django_db
def test_new_denuncia_form_valido(cidade):
    """Testa se o formulário NewDenunciaForm é válido com dados corretos."""
    form_data = {
        'nome_empresa': 'Empresa Válida',
        'endereco_empresa': 'Rua Válida, 123',
        'cidade': cidade.id,
        'tipo_denuncia': 'ASSEDIO',
        'descricao': 'Descrição válida da denúncia',
        'anonimo': True,
    }
    form = NewDenunciaForm(data=form_data)
    assert form.is_valid(), form.errors

@pytest.mark.django_db
def test_new_denuncia_form_invalido_campos_obrigatorios():
    """Testa se o NewDenunciaForm é inválido quando campos obrigatórios estão ausentes."""
    form = NewDenunciaForm(data={})
    assert not form.is_valid()
    # Verifica se os erros esperados estão presentes
    assert 'nome_empresa' in form.errors
    assert 'endereco_empresa' in form.errors
    assert 'cidade' in form.errors
    assert 'tipo_denuncia' in form.errors
    assert 'descricao' in form.errors

@pytest.mark.django_db
def test_close_denuncia_form_valido():
    """Testa se o formulário CloseDenunciaForm é válido."""
    form = CloseDenunciaForm(data={'resposta': 'Encerrado.'})
    assert form.is_valid()

@pytest.mark.django_db
def test_upload_evidencias_form():
    """Testa se o formulário UploadEvidencias é válido ao receber uma imagem."""
    imagem = criar_imagem_teste()
    form = UploadEvidencias(files={'imagem': imagem})
    assert form.is_valid(), form.errors

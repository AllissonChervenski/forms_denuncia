"""Testes para os modelos do aplicativo core."""
import pytest
from core.models import Estado, Cidades, Denuncia, Evidencia
import uuid

@pytest.fixture
def estado_sp(db):
    """Fixture para criar um objeto Estado 'SP'."""
    estado, _ = Estado.objects.get_or_create(uf='SP')
    return estado

@pytest.fixture
def cidade_sp(db, estado_sp):
    """Fixture para criar um objeto Cidades 'São Paulo' associado ao estado 'SP'."""
    cidade, _ = Cidades.objects.get_or_create(nome='São Paulo', estado=estado_sp)
    return cidade

@pytest.mark.django_db
def test_criar_estado():
    """Testa a criação de um objeto Estado."""
    estado, created = Estado.objects.get_or_create(uf='RJ')
    assert str(estado) == 'RJ'
    assert estado.uf == 'RJ'

@pytest.mark.django_db
def test_uf_unico(estado_sp):
    """Testa a restrição de unicidade do campo 'uf' no modelo Estado."""
    from django.db import IntegrityError
    with pytest.raises(IntegrityError):
        # Tenta criar um estado com a mesma UF, o que deve levantar um IntegrityError
        Estado.objects.create(uf='SP')

@pytest.mark.django_db
def test_criar_cidade(estado_sp):
    """Testa a criação de um objeto Cidades e sua associação com um Estado."""
    cidade = Cidades.objects.create(nome='Campinas', estado=estado_sp)
    assert str(cidade) == 'Campinas'
    assert cidade.estado == estado_sp

@pytest.mark.django_db
def test_denuncia_model(cidade_sp):
    """Testa a criação de um objeto Denuncia com dados básicos."""
    denuncia = Denuncia.objects.create(
        nome_empresa='Empresa Teste',
        endereco_empresa='Rua Teste, 123',
        cidade=cidade_sp,
        tipo_denuncia='ASSEDIO',
        descricao='Descrição do assédio',
    )
    assert str(denuncia) == 'Empresa Teste'
    assert denuncia.tipo_denuncia == 'ASSEDIO'
    assert isinstance(denuncia.protocolo, uuid.UUID)

@pytest.mark.django_db
@pytest.mark.parametrize("tipo_denuncia, label", Denuncia.DENUNCIAS_CHOICES)
def test_denuncia_todos_tipos(cidade_sp, tipo_denuncia, label):
    """Testa a criação de uma Denuncia para cada tipo de denúncia disponível."""
    denuncia = Denuncia.objects.create(
        nome_empresa=f'Empresa {tipo_denuncia}',
        endereco_empresa='Rua Teste',
        cidade=cidade_sp,
        tipo_denuncia=tipo_denuncia,
        descricao='Descrição',
    )
    assert denuncia.tipo_denuncia == tipo_denuncia

@pytest.fixture
def denuncia_teste(db, cidade_sp):
    """Fixture para criar um objeto Denuncia para ser usado em outros testes."""
    return Denuncia.objects.create(
        nome_empresa='Empresa Evidencia',
        endereco_empresa='Rua Teste, 123',
        cidade=cidade_sp,
        tipo_denuncia='SEGURANCA',
        descricao='Descrição',
    )

@pytest.mark.django_db
def test_evidencia_model(denuncia_teste):
    """Testa a criação de um objeto Evidencia e sua associação com uma Denuncia."""
    from django.core.files.uploadedfile import SimpleUploadedFile
    imagem = SimpleUploadedFile('test.jpg', b'file_content', content_type='image/jpeg')
    evidencia = Evidencia.objects.create(denuncia=denuncia_teste, imagem=imagem)
    assert evidencia.denuncia == denuncia_teste
    assert evidencia.imagem.name.startswith('denuncia_images/')

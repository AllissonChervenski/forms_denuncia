"""Fábricas de dados de teste usando factory-boy."""
import factory
from django.contrib.auth.models import User
from core.models import Estado, Cidades, Denuncia, Evidencia


class UserFactory(factory.django.DjangoModelFactory):
    """Fábrica para o modelo User do Django."""
    class Meta:
        model = User
        django_get_or_create = ('username',)
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"admin_{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    is_staff = True
    is_superuser = True
    is_active = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        pwd = extracted or 'password123'
        self.set_password(pwd)
        self.save()


class EstadoFactory(factory.django.DjangoModelFactory):
    """Fábrica para o modelo Estado."""
    class Meta:
        model = Estado
        django_get_or_create = ('uf',)

    uf = factory.Sequence(lambda n: f"{chr(65 + (n % 26))}{chr(65 + ((n // 26) % 26))}")


class CidadeFactory(factory.django.DjangoModelFactory):
    """Fábrica para o modelo Cidades."""
    class Meta:
        model = Cidades

    nome = factory.Sequence(lambda n: f"Cidade {n}")
    estado = factory.SubFactory(EstadoFactory)


class DenunciaFactory(factory.django.DjangoModelFactory):
    """Fábrica para o modelo Denuncia."""
    class Meta:
        model = Denuncia

    nome_empresa = factory.Sequence(lambda n: f"Empresa {n} S/A")
    endereco_empresa = "Av. Principal, 1000"
    cidade = factory.SubFactory(CidadeFactory)
    tipo_denuncia = "ASSEDIO"
    descricao = "Condições abusivas no ambiente de trabalho relatadas para verificação."
    testemunhas = "Colegas de trabalho"
    acoes = "Conversa com supervisão sem sucesso"
    anonimo = True
    email = "denunciante@test.com"
    situacao = True
    resposta = ""


class EvidenciaFactory(factory.django.DjangoModelFactory):
    """Fábrica para o modelo Evidencia."""
    class Meta:
        model = Evidencia

    denuncia = factory.SubFactory(DenunciaFactory)
    imagem = factory.django.ImageField(color='blue', format='JPEG')

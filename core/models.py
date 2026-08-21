from django.db import models
import uuid
from django.contrib.postgres.indexes import GinIndex

class Estado(models.Model):
    """Representa um estado da federação brasileira."""
    uf = models.CharField(max_length=2, unique=True)

    def __str__(self):
        """Retorna a sigla do estado como sua representação string."""
        return self.uf

class Cidades(models.Model):
    """Representa uma cidade, associada a um estado."""
    nome = models.CharField(max_length=50)
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE)

    class Meta:
        """Metadados para o modelo Cidades."""
        indexes = [
            GinIndex(
                name='nome_cidade_trgm_idx',
                fields=['nome'],
                opclasses=['gin_trgm_ops']
            ),
        ]
    def __str__(self):
        """Retorna o nome da cidade como sua representação string."""
        return self.nome

    
class Denuncia(models.Model):
    """
    Modelo principal que armazena os dados de uma denúncia.
    
    Este modelo contém todas as informações relacionadas a uma denúncia, 
    incluindo detalhes da empresa, tipo de denúncia, descrição, e informações 
    de contato opcionais.
    """
    DENUNCIAS_CHOICES = [
        ("ASSEDIO", "ASSÉDIO (MORAL, SEXUAL, ETC.)"),
        ("DISCRIMINACAO", "DISCRIMINAÇÃO (RAÇA, GÊNERO, IDADE, ETC.)"),
        ("VIOLACAO", "VIOLAÇÕES DE POLÍTICAS DA EMPRESA"),
        ("SEGURANCA", "QUESTÕES DE SEGURANÇA NO TRABALHO"),
        ("OUTROS", "OUTRAS QUESTÕES ESPECÍFICAS"),
    ]
   
    nome_empresa = models.CharField(max_length=255)
    endereco_empresa = models.CharField(max_length=255)
    cidade = models.ForeignKey(Cidades, related_name='Denuncia', blank=False, null=False, on_delete=models.CASCADE)
    tipo_denuncia = models.CharField(
        max_length=13,
        choices=DENUNCIAS_CHOICES
    )
    descricao = models.TextField(blank=False, null=False)
    testemunhas = models.CharField(max_length=255, blank=True, null=True)
    acoes = models.CharField(max_length=255, blank=True, null=True)
    anonimo = models.BooleanField(default=True)
    email = models.EmailField(
        max_length=100,
        blank=True,
        null=True,
        unique=False,
    )
    data_ocorrido = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    protocolo = models.UUIDField(editable=False, default=uuid.uuid4, unique=True)
    situacao = models.BooleanField(default=True)
    resposta = models.TextField(blank=True, null=True)

    class Meta:
        """Metadados para o modelo Denuncia."""
        indexes = [
            GinIndex(
                name='nome_empresa_trgm_idx',
                fields=['nome_empresa'],
                opclasses=['gin_trgm_ops']
            ),
        ]
    def __str__(self):
        """Retorna o nome da empresa como representação string da denúncia."""
        return self.nome_empresa
    

class Evidencia(models.Model):
    """Armazena arquivos de imagem como evidência para uma denúncia."""
    imagem = models.ImageField(upload_to='denuncia_images', blank=True, null=True)
    denuncia = models.ForeignKey(Denuncia, on_delete=models.CASCADE)

    def __str__(self):
        """Retorna o caminho da imagem como sua representação string."""
        return str(self.imagem)

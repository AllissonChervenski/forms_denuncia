# Model Evidencia (core/models.py)

## 📍 Arquivo: `core/models.py`

## 🎯 O que é
Model que representa **arquivos de imagem** anexados a uma denúncia. Permite múltiplas evidências por denúncia.

---

## 💻 Código Completo

```python
class Evidencia(models.Model):
    imagem = models.ImageField(upload_to='denuncia_images', blank=True, null=True)
    denuncia = models.ForeignKey(Denuncia, on_delete=models.CASCADE)

    def __str__(self):
        return f"Evidência {self.id} - Denúncia {self.denuncia.protocolo}"
```

---

## 🔍 Campo por Campo

### `imagem = models.ImageField(upload_to='denuncia_images', blank=True, null=True)`

| Atributo | Valor | Função |
|----------|-------|--------|
| `ImageField` | Subclasse de `FileField` | Valida que arquivo é imagem (Pillow) |
| `upload_to='denuncia_images'` | Subpasta | Salva em `MEDIA_ROOT/denuncia_images/` |
| `blank=True` | Formulário | Permite campo vazio no form |
| `null=True` | Banco | Permite NULL no DB |

**Como funciona o path final:**
```
MEDIA_ROOT = /app/media/
upload_to = 'denuncia_images/'
Arquivo original: foto.jpg
Salvo como: /app/media/denuncia_images/foto_abc123.jpg
```

**Validação automática:** Pillow tenta abrir arquivo no `clean()`. Se falha → `ValidationError`.

---

### `denuncia = models.ForeignKey(Denuncia, on_delete=models.CASCADE)`

| Atributo | Valor | Função |
|----------|-------|--------|
| `ForeignKey` | Relacionamento N:1 | Muitas evidências → 1 denúncia |
| `on_delete=CASCADE` | Exclusão | Apaga denúncia → apaga evidências |

**Acesso reverso:** `denuncia.evidencia_set.all()` (default) ou `denuncia.evidencias.all()` se definisse `related_name='evidencias'`.

---

## 🔗 Fluxo de Upload

```
1. View (index) recebe request.FILES.getlist('imagem')
2. Para cada arquivo:
   evidencia = Evidencia(denuncia=denuncia, imagem=arquivo)
   evidencia.save()  → Salva arquivo em /media/denuncia_images/
3. Task assíncrona:
   limpar_exif_imagem.delay(evidencia.id)
4. Worker:
   - Busca Evidencia por ID
   - Abre imagem (Pillow)
   - Recria sem EXIF
   - Sobrescreve mesmo arquivo
```

---

## 📁 Estrutura de Arquivos no Volume

```
media_volume/
└── denuncia_images/
    ├── foto_1_a1b2c3.jpg
    ├── foto_2_d4e5f6.png
    └── documento_7_g7h8i9.pdf  (se validador permitir)
```

**Volume Docker:** `media_volume:/app/media` compartilhado entre `web` e `celery`.

---

## 📚 Referências
- [ImageField](https://docs.djangoproject.com/en/5.2/ref/models/fields/#imagefield)
- [File Uploads](https://docs.djangoproject.com/en/5.2/topics/http/file-uploads/)
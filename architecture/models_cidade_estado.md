# Models Cidade e Estado (core/models.py)

## 📍 Arquivo: `core/models.py`

## 🎯 O que é
Models de **normalização geográfica**. Evitam duplicação de strings ("São Paulo", "Sao Paulo", "SP") e permitem relacionamentos consistentes.

---

## 💻 Código Completo

```python
class Estado(models.Model):
    uf = models.CharField(max_length=2, unique=True)

    def __str__(self):
        return self.uf

    class Meta:
        verbose_name = "Estado"
        verbose_name_plural = "Estados"
        ordering = ['uf']


class Cidades(models.Model):
    nome = models.CharField(max_length=50)
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Cidade"
        verbose_name_plural = "Cidades"
        ordering = ['nome']
        indexes = [
            models.Index(fields=['estado', 'nome']),
        ]
```

---

## 🔍 Estado

### `uf = models.CharField(max_length=2, unique=True)`
- **2 caracteres:** 'SP', 'RJ', 'MG', 'RS', etc.
- **`unique=True`**: Não pode ter dois estados com mesma UF.
- **Índice único automático** (unique=True cria índice).

### `Meta`
```python
class Meta:
    verbose_name = "Estado"
    verbose_name_plural = "Estados"
    ordering = ['uf']  # Admin lista: AC, AL, AM... SP
```

---

## 🔍 Cidades

### `nome = models.CharField(max_length=50)`
- Nome completo: "São Paulo", "Rio de Janeiro", "Belo Horizonte".
- **Não único global** - pode ter "Santa Maria" no RS e no DF.
- Único **por estado** seria ideal (unique_together).

### `estado = models.ForeignKey(Estado, on_delete=models.CASCADE)`
- **Relacionamento:** Cada cidade pertence a 1 estado.
- **CASCADE:** Se apaga Estado → apaga suas Cidades.
- **Índice FK automático** no `estado_id`.

### `Meta`
```python
class Meta:
    verbose_name = "Cidade"
    verbose_name_plural = "Cidades"
    ordering = ['nome']  # Admin lista: A... Z
    indexes = [
        models.Index(fields=['estado', 'nome']),  # Busca: estado + nome
    ]
```

---

## 📊 População via CSV (`core/csv_reader.py`)

```python
# Municipios_normalizados.csv (76KB) → 5.500+ cidades
# Colunas: UF, Código IBGE, Nome

def importar_cidades():
    import csv
    from .models import Estado, Cidades
    
    with open('Municipios_normalizados.csv', encoding='latin-1') as f:
        reader = csv.DictReader(f)
        for row in reader:
            estado, _ = Estado.objects.get_or_create(uf=row['UF'])
            Cidades.objects.get_or_create(
                nome=row['Nome'],
                estado=estado
            )
```

**Fonte:** IBGE - Municípios normalizados.

---

## 🔗 Uso na Denúncia

```python
# core/models.py
class Denuncia(models.Model):
    cidade = models.ForeignKey(
        Cidades,
        related_name='Denuncia',  # cidade.Denuncia.all()
        on_delete=models.CASCADE
    )
```

**Autocomplete (Select2):**
```python
# core/views.py
class CidadesAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Cidades.objects.select_related('estado').all()
        if self.q:
            qs = qs.filter(nome__icontains=self.q)
        return qs

    def get_result_label(self, item):
        return format_html("<p>{}, {}</p>", item.nome, item.estado)
```

---

## 📚 Referências
- [Django Model Meta Options](https://docs.djangoproject.com/en/5.2/ref/models/options/)
- [ForeignKey](https://docs.djangoproject.com/en/5.2/ref/models/fields/#foreignkey)
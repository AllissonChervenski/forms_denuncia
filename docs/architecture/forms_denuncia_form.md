# Formulário de Denúncia (core/forms.py)

## 📍 Arquivo: `core/forms.py`

## 🎯 O que é
Forms Django para validação e renderização do formulário de denúncia, incluindo campos customizados (checkbox estilizado, upload múltiplo).

---

## 💻 Código Completo

```python
from django import forms
from dal import autocomplete
from django.utils.safestring import mark_safe
from .models import Denuncia, Cidades, Evidencia

INPUT_CLASSES = 'w-full py-4 px-6 border placeholder:font-[Roboto]'

class CustomCheckboxInput(forms.widgets.CheckboxInput):
    def render(self, name, value, attrs=None, renderer=None):
        checkbox_html = super().render(name, value, attrs, renderer)
        return mark_safe(f'''
            <label class="ml-10 mr-auto mb-4 mt-3 text-lg table cursor-pointer text-black rounded-sm">
                {checkbox_html}
                <span class="py-2 px-6 border-r-0 border-slate-300 rounded-sm bg-[#77EB83]" id="check_sim">Sim</span>
                <span class="py-2 px-6 border border-l-0 border-slate-300 rounded-sm" id="check_nao">Não</span>
            </label>
        ''')

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class NewDenunciaForm(forms.ModelForm):
    class Meta:
        model = Denuncia
        fields = ('nome_empresa', 'endereco_empresa', 'cidade', 'tipo_denuncia', 'descricao', 'testemunhas', 'acoes', 'data_ocorrido', 'anonimo', 'email')

        widgets = {
            'nome_empresa': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Nome da Empresa denunciada'}),
            'endereco_empresa': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Endereço da empresa denunciada'}),
            'cidade': autocomplete.ModelSelect2(url="core:cidades-autocomplete", attrs={
                'class': "w-full md:border placeholder:font-[Roboto] text-lg",
                'data-html': True,
                'data-minimum-input-length': 1,
            }),
            'tipo_denuncia': forms.Select(attrs={'class': INPUT_CLASSES, 'placeholder': 'Selecione o tipo de denúncia'}),
            'descricao': forms.Textarea(attrs={'class': INPUT_CLASSES, 'placeholder': 'Insira a descrição da situação denunciada'}),
            'testemunhas': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Testemunhas do ocorrido'}),
            'acoes': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Insira detalhes das ações já tomadas sobre o ocorrido'}),
            'data_ocorrido': forms.DateTimeInput(format='%d/%m/%Y', attrs={'class': INPUT_CLASSES, 'type': 'date', 'placeholder': '00/00/0000'}),
            'anonimo': CustomCheckboxInput(attrs={'class': 'hidden'}),
            'email': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Insira seu email para receber atualizações sobre a denúncia'}),
        }

        labels = {
            'nome_empresa': 'Nome da Empresa*',
            'endereco_empresa': 'Endereço da Empresa*',
            'cidade': 'Cidade*',
            'tipo_denuncia': 'Tipo de denúncia*',
            'descricao': 'Descrição da denúncia*',
            'testemunhas': 'Testemunhas da ocorrência',
            'anonimo': 'Denúncia anônima (caso marque "não", será requisitado o e-mail para envio de atualizações)',
            'acoes': 'Ações tomadas',
            'email': 'E-mail',
            'data_ocorrido': 'Data do ocorrido'
        }

class CloseDenunciaForm(forms.ModelForm):
    class Meta:
        model = Denuncia
        fields = ('resposta',)
        widgets = {
            "resposta": forms.Textarea(attrs={
                'class': INPUT_CLASSES,
                'style': 'resize:none;',
                'placeholder': "Resposta da situação da denúncia"
            })
        }

class UploadEvidencias(forms.ModelForm):
    class Meta:
        model = Evidencia
        fields = ('imagem',)
        widgets = {
            'imagem': MultipleFileInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Insira imagens de evidências da ocorrência'
            }),
        }
```

---

## 🔍 Componentes Principais

### `CustomCheckboxInput` - Checkbox Estilizado
```python
class CustomCheckboxInput(forms.widgets.CheckboxInput):
    def render(self, name, value, attrs=None, renderer=None):
        checkbox_html = super().render(name, value, attrs, renderer)
        return mark_safe(f'''
            <label class="...">
                {checkbox_html}
                <span class="... bg-[#77EB83]" id="check_sim">Sim</span>
                <span class="..." id="check_nao">Não</span>
            </label>
        ''')
```
- **`mark_safe`**: Diz ao Django "confie neste HTML, não escape".
- **CSS classes**: Tailwind para estilo visual (verde/vermelho).
- **`attrs={'class': 'hidden'}`** no form: esconde checkbox nativo, mostra spans.

### `MultipleFileInput` - Upload Múltiplo
```python
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True
```
- Herda de `ClearableFileInput` (mostra "atualmente: arquivo" + input).
- `allow_multiple_selected = True` → HTML `multiple` attribute.

---

## 🔍 NewDenunciaForm - Form Principal

### Widgets Especiais

| Campo | Widget | Por que |
|-------|--------|---------|
| `cidade` | `autocomplete.ModelSelect2` | Select2 AJAX - busca 5.500 cidades |
| `data_ocorrido` | `DateTimeInput(type='date')` | Date picker nativo do browser |
| `anonimo` | `CustomCheckboxInput` | UX visual (Sim/Não colorido) |
| `imagem` (UploadEvidencias) | `MultipleFileInput` | Múltiplos arquivos |

### Autocomplete Cidade
```python
'cidade': autocomplete.ModelSelect2(url="core:cidades-autocomplete", attrs={
    'class': "w-full md:border placeholder:font-[Roboto] text-lg",
    'data-html': True,
    'data-minimum-input-length': 1,
})
```
- **`url`**: View `CidadesAutocomplete` (retorna JSON).
- **`data-minimum-input-length: 1`**: Busca após 1 caractere.
- **`select_related('estado')`** na view evita N+1 queries.

### Labels Personalizadas
```python
labels = {
    'anonimo': 'Denúncia anônima (caso marque "não", será requisitado o e-mail para envio de atualizações)',
    ...
}
```
- Label longa explica consequência da escolha.

---

## 🔍 CloseDenunciaForm - Resposta da Equipe
```python
class CloseDenunciaForm(forms.ModelForm):
    class Meta:
        model = Denuncia
        fields = ('resposta',)
        widgets = {
            "resposta": forms.Textarea(attrs={
                'class': INPUT_CLASSES,
                'style': 'resize:none;',
                'placeholder': "Resposta da situação da denúncia"
            })
        }
```
- Só expõe `resposta` (text).
- `situacao` é togglada na view (não editável aqui).

---

## 🔍 UploadEvidencias - Evidências
```python
class UploadEvidencias(forms.ModelForm):
    class Meta:
        model = Evidencia
        fields = ('imagem',)
        widgets = {
            'imagem': MultipleFileInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Insira imagens de evidências da ocorrência'
            }),
        }
```
- Usa `MultipleFileInput` para `multiple` attribute.
- View faz `request.FILES.getlist('imagem')` para processar lista.

---

## 🔗 JavaScript no Template (index.html)

```javascript
// Toggle email visibility baseado no checkbox anonimo
$('#id_anonimo').change(function(){
    if ($(this).is(':checked')) {
        $('#id_email').closest('p').hide();  // Anônimo = esconde email
    } else {
        $('#id_email').closest('p').show();  // Não anônimo = mostra email
    }
});

// Click nos spans Sim/Não (checkbox hidden)
$('#check_sim').click(function() {
    $('#id_anonimo').prop('checked', true);
    $('#id_email').closest('p').hide();
    // Troca classes visuais...
});
```

---

## 📚 Referências
- [Django Forms](https://docs.djangoproject.com/en/5.2/topics/forms/)
- [ModelForm](https://docs.djangoproject.com/en/5.2/topics/forms/modelforms/)
- [django-autocomplete-light](https://django-autocomplete-light.readthedocs.io/)
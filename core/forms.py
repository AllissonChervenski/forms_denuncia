from django import forms
from dal import autocomplete
from django.utils.html import format_html
from .models import Denuncia, Cidades, Evidencia

INPUT_CLASSES = 'w-full max-w-full py-3 px-4 border border-slate-300 rounded-lg text-slate-800 text-sm sm:text-base placeholder:text-slate-400 focus:ring-2 focus:ring-emerald-400 focus:border-emerald-400 outline-none transition box-border'

class CustomCheckboxInput(forms.widgets.CheckboxInput):
    def render(self, name, value, attrs=None, renderer=None):
        checkbox_html = super().render(name, value, attrs, renderer)
        return format_html(
            '<div class="flex items-center gap-2 my-2 cursor-pointer">'
            '{} '
            '<span class="py-2 px-5 border border-slate-300 rounded-l-lg bg-[#77EB83] font-bold text-sm select-none" id="check_sim">Sim</span>'
            '<span class="py-2 px-5 border border-l-0 border-slate-300 rounded-r-lg font-bold text-sm select-none" id="check_nao">Não</span>'
            '</div>',
            checkbox_html
        )

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class NewDenunciaForm(forms.ModelForm):
    data_ocorrido = forms.DateField(
        required=False,
        input_formats=['%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d'],
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'dd/mm/aaaa',
            'maxlength': '10',
            'autocomplete': 'off',
            'id': 'id_data_ocorrido',
        })
    )

    cidade = forms.ModelChoiceField(
        queryset=Cidades.objects.all(),
        required=True,
        error_messages={
            'required': 'Insira uma cidade válida.',
            'invalid_choice': 'Insira uma cidade válida.',
            'null': 'Insira uma cidade válida.',
        },
        widget=forms.Select(attrs={
            'class': 'hidden',
            'id': 'id_cidade',
        })
    )

    class Meta:
        model = Denuncia
        fields = ('nome_empresa', 'endereco_empresa', 'cidade', 'tipo_denuncia', 'descricao', 'testemunhas', 'acoes', 'data_ocorrido', 'anonimo', 'email',)
        
        widgets = { 
            'nome_empresa': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Nome da Empresa denunciada',
            }),

            'endereco_empresa': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': "Endereço da empresa denunciada",
            }),

            'tipo_denuncia': forms.Select(attrs={
                'class': INPUT_CLASSES,
                'placeholder': "Selecione o tipo de denúncia",
            }),

            'descricao': forms.Textarea(attrs={
                'class': INPUT_CLASSES,
                'rows': 4,
                'placeholder': "Insira a descrição da situação denunciada",
            }),

            'testemunhas': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': "Testemunhas do ocorrido",
            }),
            'acoes': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': "Insira detalhes das ações já tomadas sobre o ocorrido"
            }),
            
            'anonimo': CustomCheckboxInput(attrs={
                'class': 'hidden',
            }),

            'email': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': "Insira seu email para receber atualizações sobre a denúncia"
            }),
            
        }    

        labels = {
            'nome_empresa': 'Nome da Empresa*',
            'endereco_empresa': 'Endereço da Empresa*',
            'cidade': 'Cidade*',
            'tipo_denuncia': 'Tipo de denúncia*',
            'descricao': 'Descrição da denúncia*',
            'testemunhas': 'Testemunhas da ocorrência',
            'anonimo': "Denúncia anônima (caso marque \"não\", será requisitado o e-mail para envio de atualizações)",
            'acoes': 'Ações tomadas',
            'email': 'E-mail para Acompanhamento',
            'data_ocorrido': "Data do Ocorrido (dd/mm/aaaa)"
        }

class CloseDenunciaForm(forms.ModelForm):

    class Meta:
        model = Denuncia
        fields = ('resposta',)

        widgets = {
            "resposta": forms.Textarea(attrs={
                'class': INPUT_CLASSES,
                'rows': 4,
                'placeholder': "Resposta oficial e parecer técnico da situação da denúncia"
            })
        }

class UploadEvidencias(forms.ModelForm):
    class Meta:
        model = Evidencia
        fields = ('imagem',)
        widgets = {
            'imagem': MultipleFileInput(attrs={
                'class': 'w-full max-w-full text-xs sm:text-sm text-slate-600 file:mr-3 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-xs file:sm:text-sm file:font-semibold file:bg-emerald-100 file:text-emerald-900 hover:file:bg-emerald-200 cursor-pointer border border-slate-300 rounded-lg p-2 bg-slate-50 box-border',
            })
        }
        labels = {
            'imagem': 'Anexar Fotos / Evidências'
        }
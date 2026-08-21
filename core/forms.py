from django import forms
from dal import autocomplete
from django.utils.html import format_html
from .models import Denuncia, Cidades, Evidencia

INPUT_CLASSES = 'w-full py-4 px-6 border placeholder:font-[Roboto]'
class CustomCheckboxInput(forms.widgets.CheckboxInput):
    def render(self, name, value, attrs=None, renderer=None):
        # Adapte este HTML conforme necessário para atender aos seus requisitos
        checkbox_html = super().render(name, value, attrs, renderer)
        return format_html(
            '<label class=" ml-10 mr-auto mb-4 mt-3 text-lg table cursor-pointer text-black rounded-sm">{} <span class="py-2 px-6  border-r-0 border-slate-300 rounded-sm bg-[#77EB83]" id="check_sim">Sim</span><span class="py-2 px-6 border border-l-0 border-slate-300 rounded-sm"  id="check_nao">Não</span></label>',
            checkbox_html
        )

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class NewDenunciaForm(forms.ModelForm):

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

            'cidade': autocomplete.ModelSelect2(url="core:cidades-autocomplete", 
                                                attrs={
                                                    'class': "w-full md:border placeholder:font-[Roboto] text-lg",
                                                    'data-html': True,
                                                    'data-minimum-input-length': 1,

                                                }),


            'tipo_denuncia': forms.Select(attrs={
                'class': INPUT_CLASSES,
                'placeholder': "Selecione o tipo de denúncia",
            }),

            'descricao': forms.Textarea(attrs={
                'class': INPUT_CLASSES,
                'placeholder': "Insira a descrição da situação denunciada",
            }),

            'testemunhas': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': "Testemunhas do ocorrido",
            }),
            'acoes': forms.TextInput(attrs={
                'class': INPUT_CLASSES ,
                'placeholder': "Insira detalhes das ações já tomadas sobre o ocorrido"
            }),
            'data_ocorrido': forms.DateTimeInput(format='%d/%m/%Y', attrs={
                'class': INPUT_CLASSES,
                'type': 'date',
                'placeholder': '00/00/0000'
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
            'anonimo':"Denúncia anônima (caso marque \"não\", será requisitado o e-mail para envio de atualizações)",
            'acoes': 'Ações tomadas',
            'email': 'E-mail',
            'data_ocorrido': "Data do ocorrido"
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
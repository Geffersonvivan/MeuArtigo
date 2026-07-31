from django import forms

from .models import Article, Estilo


class ArticleForm(forms.ModelForm):
    """Formulário dos parâmetros base de um artigo (PROJETO.md §4).

    Renderiza os campos e valida; a criação em si (pasta + registro) é feita
    pela service `create_article`, não por form.save().
    """

    class Meta:
        model = Article
        fields = ["titulo", "assunto", "area", "num_paginas", "num_linhas", "estilo"]
        labels = {
            "titulo": "Título (opcional)",
            "assunto": "Assunto",
            "area": "Área",
            "num_paginas": "Nº de páginas",
            "num_linhas": "Nº de linhas",
            "estilo": "Estilo",
        }
        help_texts = {
            "titulo": "Se vazio, usamos o assunto como título.",
            "area": "Filtra a memória relevante (ex.: Direito Eleitoral).",
        }
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Ex.: Impulsionamento eleitoral pago"}),
            "assunto": forms.TextInput(attrs={"placeholder": "Ex.: Impulsionamento eleitoral"}),
            "area": forms.TextInput(attrs={"placeholder": "Ex.: Direito Eleitoral"}),
            "num_paginas": forms.NumberInput(attrs={"min": 1}),
            "num_linhas": forms.NumberInput(attrs={"min": 1}),
            "estilo": forms.Select(choices=Estilo.choices),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["titulo"].required = False
        self.fields["num_paginas"].min_value = 1
        self.fields["num_linhas"].min_value = 1

    def clean_num_paginas(self):
        value = self.cleaned_data["num_paginas"]
        if value < 1:
            raise forms.ValidationError("Deve ser pelo menos 1 página.")
        return value

    def clean_num_linhas(self):
        value = self.cleaned_data["num_linhas"]
        if value < 1:
            raise forms.ValidationError("Deve ser pelo menos 1 linha.")
        return value

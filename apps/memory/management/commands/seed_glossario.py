"""Seed do glossário (vocabulário controlado) de Direito Eleitoral.

Uso: python manage.py seed_glossario
Cada termo tem a forma PREFERIDA + variantes que a detecção determinística sinaliza,
sugerindo o termo correto. Sem LLM. Expandir depois conforme o acervo cresce.
"""

from django.core.management.base import BaseCommand

from apps.memory.models import Term

AREA = "direito-eleitoral"

GLOSSARIO = [
    ("impulsionamento de conteúdo", ["impulsionamento pago", "post patrocinado", "conteúdo pago"],
     "Única publicidade eleitoral paga admitida na internet (Lei 9.504/97)."),
    ("propaganda eleitoral antecipada", ["propaganda antecipada", "campanha antecipada"],
     "Propaganda antes do período permitido; sujeita a sanção."),
    ("prestação de contas", ["prestacao de contas", "prestação de conta"],
     "Dever de reportar receitas e gastos de campanha à Justiça Eleitoral."),
    ("Justiça Eleitoral", ["justica eleitoral", "JE"], "Ramo do Judiciário competente para as eleições."),
    ("Tribunal Superior Eleitoral", ["TSE", "tribunal superior"], "Órgão de cúpula da Justiça Eleitoral."),
    ("Ministério Público Eleitoral", ["MPE", "promotoria eleitoral"], "Fiscaliza a lisura do pleito."),
    ("abuso de poder econômico", ["abuso economico", "abuso do poder economico"],
     "Uso desproporcional de recursos econômicos para influenciar o pleito."),
    ("captação ilícita de sufrágio", ["compra de voto", "captacao ilicita"],
     "Oferecer/prometer bem ou vantagem para obter voto (art. 41-A da Lei 9.504/97)."),
    ("propaganda irregular", ["propaganda ilegal"], "Propaganda em desacordo com as regras eleitorais."),
    ("direito de resposta", ["direito a resposta"], "Réplica a afirmação sabidamente inverídica ou ofensiva."),
    ("inelegibilidade", ["inelegivel", "inelegibilidades"], "Impedimento legal de concorrer a cargo eletivo."),
    ("registro de candidatura", ["registro de candidato"], "Pedido para concorrer, deferido pela Justiça Eleitoral."),
    ("fundo eleitoral", ["FEFC", "fundo especial"], "Fundo Especial de Financiamento de Campanha."),
    ("cota de gênero", ["cotas de genero", "cota de genero"], "Percentual mínimo de candidaturas por gênero."),
    ("desinformação", ["fake news", "noticia falsa"], "Conteúdo falso ou enganoso disseminado no contexto eleitoral."),
    ("boca de urna", ["boca-de-urna"], "Propaganda no dia da eleição, vedada por lei."),
    ("propaganda institucional", ["publicidade institucional"], "Publicidade de órgãos públicos, restrita em período eleitoral."),
    ("condutas vedadas", ["conduta vedada"], "Atos proibidos a agentes públicos em ano eleitoral."),
    ("recurso especial eleitoral", ["REspe", "recurso especial"], "Recurso ao TSE contra decisão de TRE."),
    ("propaganda paga na internet", ["anuncio eleitoral", "publicidade paga online"],
     "Vedada como regra; exceção é o impulsionamento de conteúdo."),
]


class Command(BaseCommand):
    help = "Semeia o glossário de Direito Eleitoral (vocabulário controlado)."

    def handle(self, *args, **opts):
        criados = atualizados = 0
        for termo, variantes, definicao in GLOSSARIO:
            obj, criado = Term.objects.update_or_create(
                area_slug=AREA, termo=termo,
                defaults={"variantes": "\n".join(variantes), "definicao": definicao},
            )
            criados += int(criado)
            atualizados += int(not criado)
        self.stdout.write(self.style.SUCCESS(
            f"Glossário '{AREA}': {criados} criados, {atualizados} atualizados "
            f"({Term.objects.filter(area_slug=AREA).count()} termos)."
        ))

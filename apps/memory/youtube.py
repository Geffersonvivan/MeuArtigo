"""Análise de vídeos do YouTube como fonte de IDEIAS para complementar o artigo.

Trabalhamos sobre a TRANSCRIÇÃO (legendas) — o Claude não assiste vídeo. A transcrição
é resumida em ideias (VideoIdea); o vídeo pode virar uma Reference audiovisual citável.
Nada de invenção: se não houver legenda, não há ideias (o vídeo entra só como referência).
"""

from __future__ import annotations

import json
import re

import httpx
from django.conf import settings
from django.utils import timezone

_YT_ID_RE = re.compile(
    r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/|v/)|[?&]v=)([A-Za-z0-9_-]{11})"
)


def parse_video_ids(texto: str) -> list[tuple[str, str]]:
    """Extrai (url, video_id) de um texto com UMA ou VÁRIAS URLs (uma por linha/espaço)."""
    out: list[tuple[str, str]] = []
    vistos: set[str] = set()
    for pedaco in re.split(r"[\s,]+", (texto or "").strip()):
        if not pedaco:
            continue
        m = _YT_ID_RE.search(pedaco)
        vid = m.group(1) if m else (pedaco if re.fullmatch(r"[A-Za-z0-9_-]{11}", pedaco) else None)
        if vid and vid not in vistos:
            vistos.add(vid)
            out.append((pedaco, vid))
    return out


def fetch_meta(video_id: str) -> dict:
    """Título e canal via oEmbed do YouTube (sem chave de API)."""
    try:
        r = httpx.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=10,
        )
        if r.status_code < 400:
            d = r.json()
            return {"titulo": d.get("title", ""), "canal": d.get("author_name", "")}
    except Exception:
        pass
    return {"titulo": "", "canal": ""}


def fetch_transcript(video_id: str, idiomas=("pt", "pt-BR", "en", "en-US")) -> str | None:
    """Transcrição (legendas) via youtube-transcript-api. None se não houver."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        fetched = YouTubeTranscriptApi().fetch(video_id, languages=list(idiomas))
        texto = " ".join(sn.text for sn in fetched).strip()
        return texto or None
    except Exception:
        return None


def _extrair_ideias(article, titulo: str, transcricao: str) -> dict:
    """Claude resume a transcrição em {resumo, ideias:[{texto, citavel}]}."""
    from apps.llm.models import LLMCall, Papel
    from apps.llm.providers import get_provider

    trecho = (transcricao or "")[:16000]  # limita o que enviamos ao modelo
    area = article.area or "conhecimento geral"
    system = (
        "Você extrai IDEIAS aproveitáveis da transcrição de um vídeo, para inspirar um artigo "
        f"da área de {area}. Responda SOMENTE JSON válido: "
        '{"resumo":"2-3 frases","ideias":[{"texto":"ideia em 1 frase","citavel":false}]}. '
        "Entre 6 e 10 ideias objetivas. Marque citavel=true quando for um dado/afirmação factual "
        "específica (número, estudo, fato) que poderia virar citação. Não invente nada além da "
        "transcrição."
    )
    user = f"VÍDEO: {titulo}\n\nTRANSCRIÇÃO:\n{trecho}"
    res = get_provider("anthropic").generate(
        system=system, prompt=user, max_tokens=1200,
        model=getattr(settings, "MODELO_REDATOR", "claude-sonnet-5"), thinking=False,
    )
    LLMCall.objects.create(
        article=article, papel=Papel.PESQUISA, provider=res.provider, model=res.model,
        input_tokens=res.input_tokens, output_tokens=res.output_tokens,
        cost_usd=res.cost_usd, ok=True,
    )
    txt = re.sub(r"^```(?:json)?|```$", "", res.text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", txt, re.DOTALL)
        return json.loads(m.group(0)) if m else {"resumo": "", "ideias": []}


def analisar_video(article, url: str):
    """Analisa UM vídeo: metadados + transcrição + extração de ideias. Cria/retorna o
    VideoSource (idempotente por article+video_id). Retorna None se a URL não for válida."""
    from .models import VideoIdea, VideoSource

    ids = parse_video_ids(url)
    if not ids:
        return None
    _, video_id = ids[0]

    existente = VideoSource.objects.filter(article=article, video_id=video_id).first()
    if existente:
        return existente

    meta = fetch_meta(video_id)
    transcricao = fetch_transcript(video_id)
    dados = {"resumo": "", "ideias": []}
    if transcricao:
        try:
            dados = _extrair_ideias(article, meta.get("titulo") or video_id, transcricao)
        except Exception:
            dados = {"resumo": "", "ideias": []}

    vs = VideoSource.objects.create(
        article=article, url=f"https://www.youtube.com/watch?v={video_id}", video_id=video_id,
        titulo=(meta.get("titulo") or "")[:400], canal=(meta.get("canal") or "")[:300],
        resumo=(dados.get("resumo") or "")[:2000], tem_transcricao=bool(transcricao),
    )
    for i, idea in enumerate((dados.get("ideias") or [])[:12]):
        txt = (idea.get("texto") if isinstance(idea, dict) else str(idea)).strip()
        if not txt:
            continue
        VideoIdea.objects.create(
            video=vs, texto=txt[:500], ordem=i,
            citavel=bool(idea.get("citavel")) if isinstance(idea, dict) else False,
        )
    return vs


def melhor_encaixe(texto_ideia: str, article) -> dict | None:
    """Aponta em qual parágrafo a ideia melhor encaixa, por similaridade semântica
    (embeddings Voyage). Devolve {paragraphId, pct, secao, preview} ou None."""
    import math

    from apps.articles.models import Paragraph
    from apps.memory.embeddings import get_embedder

    paras = list(Paragraph.objects.filter(section__article=article).select_related("section"))
    paras = [p for p in paras if (p.texto or "").strip()]
    if not paras:
        return None
    emb = get_embedder()
    qv = emb.embed_one(texto_ideia, input_type="query")
    doc_vecs = emb.embed([p.texto for p in paras], input_type="document").vectors

    def _cos(a, b):
        s = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(y * y for y in b)) or 1.0
        return s / (na * nb)

    best_i, best = 0, -1.0
    for i, dv in enumerate(doc_vecs):
        c = _cos(qv, dv)
        if c > best:
            best, best_i = c, i
    p = paras[best_i]
    return {
        "paragraphId": f"p{p.pk}", "pct": max(0, min(100, round(best * 100))),
        "secao": p.section.titulo, "preview": (p.texto or "")[:90],
    }


def melhor_encaixe_lote(article) -> dict:
    """Encaixe de TODAS as ideias do artigo de uma vez (2 chamadas Voyage — ideias e
    parágrafos em lote). Devolve {ideaId: {paragraphId, pct, secao}}."""
    import math

    from apps.articles.models import Paragraph

    from .embeddings import get_embedder
    from .models import VideoIdea

    paras = [p for p in Paragraph.objects.filter(section__article=article).select_related("section")
             if (p.texto or "").strip()]
    ideas = list(VideoIdea.objects.filter(video__article=article))
    if not paras or not ideas:
        return {}
    emb = get_embedder()
    pvecs = emb.embed([p.texto for p in paras], input_type="document").vectors
    ivecs = emb.embed([i.texto for i in ideas], input_type="query").vectors

    def _cos(a, b):
        s = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(y * y for y in b)) or 1.0
        return s / (na * nb)

    out = {}
    for idea, iv in zip(ideas, ivecs):
        bi, bc = 0, -1.0
        for j, pv in enumerate(pvecs):
            c = _cos(iv, pv)
            if c > bc:
                bc, bi = c, j
        p = paras[bi]
        out[str(idea.pk)] = {"paragraphId": f"p{p.pk}",
                             "pct": max(0, min(100, round(bc * 100))), "secao": p.section.titulo}
    return out


def video_para_referencia(video):
    """Cria (uma vez) a Reference audiovisual do vídeo — para citar no texto (ABNT)."""
    from .models import Reference, StatusVerif, TipoFonte
    from .verify import verificar_referencia

    if video.reference_id:
        return video.reference
    ref = Reference.objects.create(
        article=video.article, tipo=TipoFonte.VIDEO,
        titulo=video.titulo or f"Vídeo {video.video_id}", autor=video.canal,
        url=video.url, trecho=(video.resumo or "")[:300],
        data_acesso=timezone.now().date(), verificada=StatusVerif.PENDENTE,
    )
    try:
        verificar_referencia(ref, checar_conteudo=False)  # YouTube é verificável (URL existe)
    except Exception:
        pass
    video.reference = ref
    video.save(update_fields=["reference"])
    return ref

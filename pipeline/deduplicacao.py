"""
Evita publicar a mesma notícia duas vezes como se fossem matérias
diferentes. Antes de gerar o texto, compara o TÍTULO do candidato contra
os artigos que o site já publicou recentemente (difflib, $0, sem
dependência extra — mesma técnica já usada em similarity_check.py).

Se achar uma matéria já publicada muito parecida, ela é passada como
contexto extra pro Gemini (ver generate_text.py), que decide entre duas
saídas:
  - há fato novo relevante -> publica como ATUALIZAÇÃO (título deixa isso
    explícito, ex: "Atualização: ...");
  - não há nada de novo -> Gemini devolve {"duplicado": true} e o
    main.py descarta o candidato sem publicar.

Isso é diferente do `ja_publicado()` em publish.py, que só pega o EXATO
mesmo candidato (mesma URL/id de origem) reaparecendo numa coleta
posterior — aqui o objetivo é pegar uma notícia NOVA (fonte e id
diferentes) que cobre o mesmo fato que já viramos matéria antes.
"""
import difflib
from . import config


def _similaridade_titulo(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def encontrar_materia_relacionada(candidato: dict, artigos_publicados: list) -> dict | None:
    """Procura, entre os últimos `JANELA_DEDUPLICACAO_NOTICIA` artigos já
    publicados (mais recentes primeiro), o que mais se parece com o
    candidato atual pelo título. Retorna esse artigo se a semelhança
    passar do limiar (provável mesma notícia), senão None."""
    titulo_candidato = candidato.get("titulo", "")
    if not titulo_candidato:
        return None

    janela = artigos_publicados[: config.JANELA_DEDUPLICACAO_NOTICIA]
    melhor, melhor_score = None, 0.0
    for artigo in janela:
        score = _similaridade_titulo(titulo_candidato, artigo.get("titulo", ""))
        if score > melhor_score:
            melhor, melhor_score = artigo, score

    if melhor and melhor_score >= config.LIMIAR_MESMA_NOTICIA:
        return melhor
    return None

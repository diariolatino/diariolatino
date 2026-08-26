"""
Checagem de originalidade antes de publicar. Duas camadas, ambas $0:

1) difflib (sempre roda, embutido no Python, sem dependência extra) — pega
   cópia quase literal ou estrutura muito parecida com o material de origem.
2) embeddings locais via sentence-transformers (opcional, ativa com
   USAR_EMBEDDING_CHECK=true) — pega paráfrase disfarçada que o difflib
   não pegaria. Mais lento (baixa um modelo pequeno na primeira execução).

Se qualquer uma acender o alerta, o artigo vai pra fila de revisão manual
em vez de publicar automático.
"""
import difflib
from . import config

_modelo_embedding = None


def _similaridade_difflib(texto_a: str, texto_b: str) -> float:
    if not texto_a or not texto_b:
        return 0.0
    return difflib.SequenceMatcher(None, texto_a.lower(), texto_b.lower()).ratio()


def _carregar_modelo_embedding():
    global _modelo_embedding
    if _modelo_embedding is None:
        from sentence_transformers import SentenceTransformer
        _modelo_embedding = SentenceTransformer("all-MiniLM-L6-v2")
    return _modelo_embedding


def _similaridade_embedding(texto_a: str, texto_b: str) -> float:
    from sentence_transformers import util
    modelo = _carregar_modelo_embedding()
    emb = modelo.encode([texto_a, texto_b], convert_to_tensor=True)
    return float(util.cos_sim(emb[0], emb[1]))


def checar_originalidade(materia_gerada: dict, candidato_original: dict) -> dict:
    material_origem = f"{candidato_original.get('titulo', '')} {candidato_original.get('resumo', '')}"
    texto_gerado = f"{materia_gerada.get('titulo', '')} {materia_gerada.get('lead', '')} {materia_gerada.get('corpo', '')}"

    score_difflib = _similaridade_difflib(texto_gerado, material_origem)
    alerta = score_difflib > config.LIMIAR_DIFFLIB
    detalhes = {"difflib": round(score_difflib, 3)}

    if not alerta and config.USAR_EMBEDDING_CHECK and material_origem.strip():
        try:
            score_emb = _similaridade_embedding(texto_gerado, material_origem)
            detalhes["embedding"] = round(score_emb, 3)
            alerta = score_emb > config.LIMIAR_EMBEDDING
        except Exception as e:
            print(f"[similaridade] checagem por embedding falhou, seguindo só com difflib: {e}")

    return {"aprovado": not alerta, "detalhes": detalhes}

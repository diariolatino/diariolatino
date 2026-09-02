import json
import os
import uuid
from datetime import datetime, timezone
from . import config


def _carregar_json(caminho, padrao):
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return padrao


def _salvar_json(caminho, dados):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def ja_publicado(candidato_id: str) -> bool:
    vistos = _carregar_json(config.SEEN_IDS_PATH, [])
    return candidato_id in vistos


def carregar_artigos_publicados() -> list:
    return _carregar_json(config.ARTICLES_PATH, [])


def marcar_como_visto(candidato_id: str):
    vistos = _carregar_json(config.SEEN_IDS_PATH, [])
    vistos.append(candidato_id)
    _salvar_json(config.SEEN_IDS_PATH, vistos[-500:])  # mantém histórico enxuto


def publicar(materia_gerada: dict, candidato: dict, imagem: dict | None, materia_relacionada: dict | None = None):
    artigos = _carregar_json(config.ARTICLES_PATH, [])

    fontes = [candidato.get("fonte", "Fonte não identificada")]
    if candidato.get("url_original"):
        pass  # o link original fica guardado, mas não é reproduzido como conteúdo

    artigo = {
        "id": str(uuid.uuid4()),
        "titulo": materia_gerada["titulo"],
        "lead": materia_gerada["lead"],
        "corpo": materia_gerada["corpo"],
        "categoria": materia_gerada.get("categoria") or "Mundo",
        "pais": materia_gerada.get("pais") or "América Latina",
        "publicado_em": datetime.now(timezone.utc).isoformat(),
        "fontes": fontes,
        "url_fonte_original": candidato.get("url_original"),
        "imagem": imagem,
        "selo_ia": "Conteúdo redigido com auxílio de inteligência artificial, a partir de fontes verificadas",
        "traducoes": materia_gerada.get("traducoes", {}),
        "atualizacao_de": materia_relacionada["id"] if materia_relacionada else None,
    }

    artigos.insert(0, artigo)
    artigos = artigos[: config.MAX_ARTIGOS_NO_SITE]
    _salvar_json(config.ARTICLES_PATH, artigos)
    marcar_como_visto(candidato["id"])
    return artigo


def enviar_para_revisao(materia_gerada: dict, candidato: dict, detalhes_similaridade: dict):
    fila = _carregar_json(config.REVIEW_QUEUE_PATH, [])
    fila.append({
        "candidato": candidato,
        "materia_gerada": materia_gerada,
        "motivo": "similaridade_alta",
        "detalhes": detalhes_similaridade,
        "sinalizado_em": datetime.now(timezone.utc).isoformat(),
    })
    _salvar_json(config.REVIEW_QUEUE_PATH, fila)
    marcar_como_visto(candidato["id"])

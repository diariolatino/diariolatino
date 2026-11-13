import json
import os
import uuid
from datetime import datetime, timezone
from . import config
from .reconstruir_indice import ler_indice, escrever_json_atomico


def _carregar_json(caminho, padrao):
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return padrao


def _salvar_json(caminho, dados):
    escrever_json_atomico(caminho, dados)  # grava num temporário e troca: nunca deixa arquivo pela metade


def ja_publicado(candidato_id: str) -> bool:
    vistos = _carregar_json(config.SEEN_IDS_PATH, [])
    return candidato_id in vistos


def carregar_artigos_publicados() -> list:
    return ler_indice()  # se o índice estiver corrompido, reconstrói a partir de artigos/


def marcar_como_visto(candidato_id: str):
    vistos = _carregar_json(config.SEEN_IDS_PATH, [])
    vistos.append(candidato_id)
    _salvar_json(config.SEEN_IDS_PATH, vistos[-500:])  # mantém histórico enxuto


def publicar(materia_gerada: dict, candidato: dict, imagem: dict | None, materia_relacionada: dict | None = None):
    fontes = [candidato.get("fonte", "Fonte não identificada")]
    if candidato.get("url_original"):
        pass  # o link original fica guardado, mas não é reproduzido como conteúdo

    agora = datetime.now(timezone.utc).isoformat()
    artigo = {
        "id": str(uuid.uuid4()),
        "titulo": materia_gerada["titulo"],
        "lead": materia_gerada["lead"],
        "corpo": materia_gerada["corpo"],
        "categoria": materia_gerada.get("categoria") or "Mundo",
        "pais": materia_gerada.get("pais") or "América Latina",
        "publicado_em": agora,
        "fontes": fontes,
        "url_fonte_original": candidato.get("url_original"),
        "imagem": imagem,
        # dados para o sistema de reparo buscar nova foto pelo MESMO padrão se a atual sumir
        "imagem_busca": {
            "entidades": materia_gerada.get("imagem_entidades", []),
            "lugares": materia_gerada.get("imagem_lugares", []),
            "palavras_chave": materia_gerada.get("palavras_chave_imagem", []),
        },
        "imagem_tentativas": 0 if imagem else 1,
        "imagem_ultima_tentativa_em": None if imagem else agora,
        "selo_ia": "Conteúdo redigido com auxílio de inteligência artificial, a partir de fontes verificadas",
        "traducoes": materia_gerada.get("traducoes", {}),
        "atualizacao_de": materia_relacionada["id"] if materia_relacionada else None,
    }

    # arquivo individual (site/data/artigos/<id>.json): a matéria INTEIRA
    caminho_artigo = os.path.join(config.ARTIGOS_DIR, f"{artigo['id']}.json")
    _salvar_json(caminho_artigo, artigo)

    # índice enxuto (site/data/articles.json): todas as matérias, sem o corpo
    indice = ler_indice()
    entrada_indice = {k: v for k, v in artigo.items() if k != "corpo"}
    entrada_indice["traducoes"] = {
        idioma: {k: v for k, v in campos.items() if k != "corpo"}
        for idioma, campos in artigo.get("traducoes", {}).items()
    }
    indice.insert(0, entrada_indice)
    _salvar_json(config.ARTICLES_PATH, indice)

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

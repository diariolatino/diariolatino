"""
Busca imagem no Pexels via API. A licença do Pexels não exige atribuição
pra uso comum, MAS exige atribuição quando o acesso é via API — por isso
todo artigo carrega photographer/photographer_url pro crédito no rodapé.
"""
import json
import os
import requests
from . import config

PEXELS_SEARCH_ENDPOINT = "https://api.pexels.com/v1/search"


def _carregar_usadas() -> list:
    if os.path.exists(config.USED_IMAGES_PATH):
        with open(config.USED_IMAGES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _salvar_usadas(lista_ids: list):
    os.makedirs(os.path.dirname(config.USED_IMAGES_PATH), exist_ok=True)
    with open(config.USED_IMAGES_PATH, "w", encoding="utf-8") as f:
        json.dump(lista_ids[-20:], f)


def buscar_imagem(palavras_chave: list) -> dict | None:
    query = " ".join(palavras_chave) if palavras_chave else "latin america news"
    usadas = _carregar_usadas()

    try:
        resp = requests.get(
            PEXELS_SEARCH_ENDPOINT,
            headers={"Authorization": config.PEXELS_API_KEY},
            params={"query": query, "per_page": 15, "orientation": "landscape"},
            timeout=20,
        )
        resp.raise_for_status()
        fotos = resp.json().get("photos", [])
    except Exception as e:
        print(f"[pexels] falha na busca: {e}")
        return None

    for foto in fotos:
        if foto["id"] not in usadas:
            usadas.append(foto["id"])
            _salvar_usadas(usadas)
            return {
                "url": foto["src"]["large"],
                "photographer": foto["photographer"],
                "photographer_url": foto["photographer_url"],
                "pexels_url": foto["url"],
            }

    # todas as opções da busca já foram usadas nas últimas 20 — segue sem imagem
    print(f"[pexels] todas as opções para '{query}' já usadas recentemente")
    return None

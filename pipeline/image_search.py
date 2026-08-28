"""
Busca imagem editorial pra cada matéria, tentando várias fontes gratuitas
em sequência (Pexels -> Pixabay -> Unsplash -> Openverse) e várias frases
de busca, da mais específica pra mais genérica.

Por quê várias frases e várias fontes? Uma busca genérica demais (ex: só
"election") tende a trazer o que for mais popular no banco de imagens pra
aquele termo em inglês — que geralmente é conteúdo dos EUA. Isso já causou
casos como uma matéria sobre eleição no Brasil vir ilustrada com bandeira
americana. Pra evitar isso:

1. O Gemini (generate_text.py) agora é instruído a mandar frases de busca
   específicas, incluindo o nome do país em inglês quando a matéria for
   sobre um país determinado (ex: "Brazil presidential election rally").
2. Aqui, cada frase é tentada em TODAS as fontes antes de cair pra frase
   seguinte (mais genérica) — prioriza especificidade sobre a fonte.
3. Ter 4 bancos em vez de 1 aumenta a chance de achar algo realmente
   pertinente pra frase mais específica, em vez de já cair pra um termo
   genérico só porque uma única fonte não tinha nada pra aquela frase.

Nenhuma das 4 fontes exige atribuição obrigatória por lei pra esse uso,
mas todo artigo publicado carrega fotógrafo + link da fonte mesmo assim,
por transparência editorial.
"""
import json
import os
import requests
from . import config

USADAS_MAX_HISTORICO = 60


def _carregar_usadas() -> list:
    if os.path.exists(config.USED_IMAGES_PATH):
        with open(config.USED_IMAGES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _salvar_usadas(lista_ids: list):
    os.makedirs(os.path.dirname(config.USED_IMAGES_PATH), exist_ok=True)
    with open(config.USED_IMAGES_PATH, "w", encoding="utf-8") as f:
        json.dump(lista_ids[-USADAS_MAX_HISTORICO:], f)


def _marcar_usada(usadas: list, chave: str):
    usadas.append(chave)
    _salvar_usadas(usadas)


def _buscar_pexels(query: str, usadas: list) -> dict | None:
    if not config.PEXELS_API_KEY:
        return None
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": config.PEXELS_API_KEY},
            params={"query": query, "per_page": 15, "orientation": "landscape"},
            timeout=20,
        )
        resp.raise_for_status()
        fotos = resp.json().get("photos", [])
    except Exception as e:
        print(f"[pexels] falha na busca '{query}': {e}")
        return None

    for foto in fotos:
        chave = f"pexels:{foto['id']}"
        if chave not in usadas:
            _marcar_usada(usadas, chave)
            return {
                "url": foto["src"]["large"],
                "photographer": foto["photographer"],
                "photographer_url": foto["photographer_url"],
                "fonte_nome": "Pexels",
                "fonte_url": foto["url"],
            }
    return None


def _buscar_pixabay(query: str, usadas: list) -> dict | None:
    if not config.PIXABAY_API_KEY:
        return None
    try:
        resp = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": config.PIXABAY_API_KEY,
                "q": query,
                "image_type": "photo",
                "orientation": "horizontal",
                "safesearch": "true",
                "per_page": 15,
            },
            timeout=20,
        )
        resp.raise_for_status()
        fotos = resp.json().get("hits", [])
    except Exception as e:
        print(f"[pixabay] falha na busca '{query}': {e}")
        return None

    for foto in fotos:
        chave = f"pixabay:{foto['id']}"
        if chave not in usadas:
            _marcar_usada(usadas, chave)
            usuario = foto.get("user", "Pixabay")
            usuario_id = foto.get("user_id", "")
            perfil = f"https://pixabay.com/users/{usuario}-{usuario_id}/" if usuario_id else "https://pixabay.com/"
            return {
                "url": foto["largeImageURL"],
                "photographer": usuario,
                "photographer_url": perfil,
                "fonte_nome": "Pixabay",
                "fonte_url": foto["pageURL"],
            }
    return None


def _buscar_unsplash(query: str, usadas: list) -> dict | None:
    if not config.UNSPLASH_ACCESS_KEY:
        return None
    try:
        resp = requests.get(
            "https://api.unsplash.com/search/photos",
            headers={"Authorization": f"Client-ID {config.UNSPLASH_ACCESS_KEY}"},
            params={"query": query, "per_page": 15, "orientation": "landscape"},
            timeout=20,
        )
        resp.raise_for_status()
        fotos = resp.json().get("results", [])
    except Exception as e:
        print(f"[unsplash] falha na busca '{query}': {e}")
        return None

    for foto in fotos:
        chave = f"unsplash:{foto['id']}"
        if chave not in usadas:
            _marcar_usada(usadas, chave)
            # exigência da API do Unsplash: registrar o "download" quando a
            # foto é efetivamente usada, não só listada numa busca
            download_location = (foto.get("links") or {}).get("download_location")
            if download_location:
                try:
                    requests.get(
                        download_location,
                        headers={"Authorization": f"Client-ID {config.UNSPLASH_ACCESS_KEY}"},
                        timeout=10,
                    )
                except Exception:
                    pass
            return {
                "url": foto["urls"]["regular"],
                "photographer": foto["user"]["name"],
                "photographer_url": foto["user"]["links"]["html"],
                "fonte_nome": "Unsplash",
                "fonte_url": foto["links"]["html"],
            }
    return None


def _buscar_openverse(query: str, usadas: list) -> dict | None:
    # Openverse agrega conteúdo licenciado como CC de várias fontes
    # (Flickr, Wikimedia Commons, museus etc.) e não exige chave de API
    # pra buscas — funciona mesmo sem nenhuma das outras 3 configuradas.
    try:
        resp = requests.get(
            "https://api.openverse.org/v1/images/",
            params={"q": query, "license_type": "commercial", "page_size": 15, "mature": "false"},
            headers={"User-Agent": "DiarioLatino/1.0 (portal de noticias, uso editorial)"},
            timeout=20,
        )
        resp.raise_for_status()
        fotos = resp.json().get("results", [])
    except Exception as e:
        print(f"[openverse] falha na busca '{query}': {e}")
        return None

    for foto in fotos:
        chave = f"openverse:{foto['id']}"
        if chave not in usadas and foto.get("url"):
            _marcar_usada(usadas, chave)
            return {
                "url": foto["url"],
                "photographer": foto.get("creator") or "Openverse",
                "photographer_url": foto.get("creator_url") or foto.get("foreign_landing_url") or "https://openverse.org/",
                "fonte_nome": "Openverse",
                "fonte_url": foto.get("foreign_landing_url") or "https://openverse.org/",
            }
    return None


PROVEDORES = [_buscar_pexels, _buscar_pixabay, _buscar_unsplash, _buscar_openverse]


def buscar_imagem(palavras_chave, pais: str | None = None) -> dict | None:
    """
    `palavras_chave`: lista de frases de busca prontas, da mais específica
    pra mais genérica (é o que generate_text.py agora pede ao Gemini).

    Cada frase é tentada em TODAS as fontes antes de cair pra próxima
    frase — assim a especificidade da busca importa mais do que a ordem
    das fontes.
    """
    tentativas = [q for q in (palavras_chave or []) if q]
    if pais and pais != "América Latina":
        tentativas.append(f"{pais} news")
    tentativas.append("latin america news")

    usadas = _carregar_usadas()

    for query in tentativas:
        for provedor in PROVEDORES:
            resultado = provedor(query, usadas)
            if resultado:
                return resultado

    print(f"[image_search] nenhuma imagem inédita encontrada pra {tentativas}")
    return None

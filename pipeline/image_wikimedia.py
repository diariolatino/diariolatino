"""Busca de fotos ESPECÍFICAS na Wikimedia Commons, só 'No restrictions'
(CC0 / domínio público). Sem foto genérica: se não achar algo sobre o
assunto, devolve None e o post fica sem imagem (o reparo tenta de novo)."""
import re
import time
import unicodedata

import requests

try:
    from pipeline import config as _c
except Exception:  # permite testar isolado
    _c = None


def _cfg(nome, padrao):
    return getattr(_c, nome, padrao) if _c else padrao


API = _cfg("WIKIMEDIA_API", "https://commons.wikimedia.org/w/api.php")
# User-Agent genérico (a Wikimedia exige um descritivo). Não use e-mail pessoal.
UA = _cfg("WIKIMEDIA_USER_AGENT",
          "DiarioLatinoBot/1.0 (https://diariolatino.github.io/diariolatino/)")
LARGURA_MIN = _cfg("IMAGEM_LARGURA_MINIMA", 900)
PROPORCAO_MIN = _cfg("IMAGEM_PROPORCAO_MINIMA", 1.15)
RELEVANCIA_MIN = _cfg("IMAGEM_RELEVANCIA_MINIMA", 0.6)
JANELA = _cfg("IMAGEM_JANELA_NAO_REPETIR", 40)
LIMITE = _cfg("WIKIMEDIA_LIMITE_RESULTADOS", 15)

MIMES_OK = {"image/jpeg", "image/png", "image/webp"}
TITULO_RUIM = re.compile(
    r"\b(logo|flag|bandera|bandeira|map|mapa|diagram|diagrama|coat of arms|"
    r"escudo|seal|icon|banner|chart|graph|screenshot|poster|signature|"
    r"locator|svg|stamp|sello|selo)\b", re.I)
STOP = {"de", "da", "do", "das", "dos", "del", "la", "el", "los", "las", "of",
        "the", "and", "e", "y", "en", "em", "in", "a", "o", "para", "por"}
GENERICAS = {
    "america latina", "latin america", "caribe", "caribbean", "brasil", "brazil",
    "argentina", "bolivia", "chile", "colombia", "costa rica", "cuba", "equador",
    "ecuador", "el salvador", "guatemala", "haiti", "honduras", "mexico",
    "nicaragua", "panama", "paraguai", "paraguay", "peru", "porto rico",
    "puerto rico", "republica dominicana", "uruguai", "uruguay", "venezuela",
    "jamaica", "bahamas", "barbados", "suriname", "guiana", "guyana",
}


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def _tokens(s):
    return [t for t in _norm(s).split() if t not in STOP and len(t) > 1]


def _limpa_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def entidade_generica(ent):
    return _norm(ent) in GENERICAS


def _meta(info, chave):
    v = (info.get("extmetadata") or {}).get(chave)
    return (v.get("value") if isinstance(v, dict) else v) or ""


def licenca_sem_restricoes(info):
    """True só para CC0 / domínio público, sem exigência de crédito nem restrições."""
    lic = _meta(info, "License").strip().lower()
    curta = _meta(info, "LicenseShortName").strip().lower()
    ok = (lic in {"cc0", "pd", "pdm"} or lic.startswith("cc0") or lic.startswith("pd-")
          or "public domain" in curta or curta.startswith("cc0") or curta == "pd")
    if not ok:
        return False
    if _meta(info, "AttributionRequired").strip().lower() == "true":
        return False
    if _meta(info, "NonFree").strip().lower() == "true":
        return False
    if _meta(info, "Restrictions").strip():
        return False
    return True


def _qualidade_ok(titulo, info):
    if info.get("mime") not in MIMES_OK:
        return False
    w, h = info.get("width") or 0, info.get("height") or 0
    if w < LARGURA_MIN or not h or (w / h) < PROPORCAO_MIN:
        return False
    return not TITULO_RUIM.search(titulo or "")


def _relevancia(entidade, titulo, info):
    alvo = _tokens(entidade)
    if not alvo:
        return 0.0
    texto = " ".join([titulo, _limpa_html(_meta(info, "ImageDescription")),
                      _limpa_html(_meta(info, "ObjectName")),
                      _limpa_html(_meta(info, "Categories")).replace("|", " ")])
    tx = set(_tokens(texto))
    return sum(1 for t in alvo if t in tx) / len(alvo)


def _pesquisar(consulta):
    params = {
        "action": "query", "format": "json", "formatversion": 2,
        "generator": "search", "gsrsearch": f"{consulta} filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": LIMITE, "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1280,
        "iiextmetadatafilter": "License|LicenseShortName|UsageTerms|AttributionRequired|"
                               "Restrictions|NonFree|Artist|ImageDescription|ObjectName|Categories",
    }
    try:
        r = requests.get(API, params=params, headers={"User-Agent": UA}, timeout=20)
        r.raise_for_status()
        paginas = (r.json().get("query") or {}).get("pages") or []
    except Exception as e:
        print(f"[commons] erro na busca '{consulta}': {e}")
        return []
    saida = []
    for p in sorted(paginas, key=lambda x: x.get("index", 0)):
        infos = p.get("imageinfo") or []
        if infos:
            saida.append((p.get("title", ""), infos[0]))
    return saida


def buscar_imagem_wikimedia(entidades, urls_usadas=()):
    usadas = set(urls_usadas or ())
    for ent in entidades or []:
        if not ent or entidade_generica(ent):
            continue
        for consulta in (f'"{ent}"', ent):
            resultados = _pesquisar(consulta)
            print(f"[commons] '{consulta}': {len(resultados)} resultado(s)")
            for titulo, info in resultados:
                url = info.get("thumburl") or info.get("url")
                if not url or url in usadas or info.get("url") in usadas:
                    continue
                if not licenca_sem_restricoes(info) or not _qualidade_ok(titulo, info):
                    continue
                if _relevancia(ent, titulo, info) < RELEVANCIA_MIN:
                    continue
                autor = _limpa_html(_meta(info, "Artist")) or "Wikimedia Commons"
                pagina = info.get("descriptionurl") or "https://commons.wikimedia.org"
                print(f"[commons] escolhida: {titulo}")
                return {
                    "url": url, "fonte": "Wikimedia Commons",
                    "licenca": _meta(info, "LicenseShortName") or "CC0/Public domain",
                    "autor": autor, "url_pagina": pagina, "entidade": ent,
                    # chaves antigas, para o front-end atual não quebrar
                    "photographer": autor, "photographer_url": pagina, "pexels_url": pagina,
                }
            time.sleep(0.3)
    return None


def urls_recentes(artigos, n=None):
    n = n or JANELA
    out = []
    for a in (artigos or [])[:n]:
        u = (a.get("imagem") or {}).get("url")
        if u:
            out.append(u)
    return out


def buscar_imagem_relevante(materia, artigos_publicados=()):
    ents = list(materia.get("imagem_entidades") or [])
    img = buscar_imagem_wikimedia(ents, urls_recentes(artigos_publicados))
    if img or not _cfg("PERMITIR_IMAGEM_GENERICA_FALLBACK", False):
        return img
    from pipeline.image_search import buscar_imagem  # fallback opcional, desligado por padrão
    return buscar_imagem(materia.get("palavras_chave_imagem", []), pais=materia.get("pais"))

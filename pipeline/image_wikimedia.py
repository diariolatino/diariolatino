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


ACEITAR_CC_BY = _cfg("IMAGEM_ACEITAR_CC_BY", False)


def licenca_cc_by(info):
    """CC BY puro (uso comercial e adaptação permitidos, exige crédito). Sem SA/ND/NC."""
    lic = _meta(info, "License").strip().lower()
    if not re.match(r"^cc-by-\d", lic):
        return False
    if _meta(info, "NonFree").strip().lower() == "true" or _meta(info, "Restrictions").strip():
        return False
    return bool(_limpa_html(_meta(info, "Artist")))  # sem autor não dá para creditar


def _licenca_aceita(info, nivel):
    return licenca_sem_restricoes(info) if nivel == "sem_restricoes" else licenca_cc_by(info)


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


# ---- verificação de pessoas e de época ----
# Pessoas que NÃO podem aparecer na foto se a matéria não falar delas (evita
# foto do Biden em matéria sobre o Trump). Lista editável: acrescente nomes em
# config.IMAGEM_PESSOAS_EXTRAS = [("Nome", ["padrão normalizado", ...]), ...]
PESSOAS_CONHECIDAS = [
    ("Joe Biden", ["biden"]), ("Donald Trump", ["trump"]), ("Barack Obama", ["obama"]),
    ("Kamala Harris", ["kamala harris"]), ("JD Vance", ["vance"]), ("Marco Rubio", ["rubio"]),
    ("George W. Bush", ["george w bush", "george bush"]), ("Hillary Clinton", ["hillary clinton"]),
    ("Lula", ["lula"]), ("Bolsonaro", ["bolsonaro"]), ("Dilma Rousseff", ["dilma"]),
    ("Michel Temer", ["temer"]), ("Javier Milei", ["milei"]), ("Cristina Kirchner", ["kirchner"]),
    ("Maduro", ["maduro"]), ("Chávez", ["chavez"]), ("Gustavo Petro", ["gustavo petro"]),
    ("Boric", ["boric"]), ("Piñera", ["pinera"]), ("López Obrador", ["lopez obrador", "amlo"]),
    ("Sheinbaum", ["sheinbaum"]), ("Bukele", ["bukele"]), ("Daniel Ortega", ["daniel ortega"]),
    ("Díaz-Canel", ["diaz canel"]), ("Fidel/Raúl Castro", ["fidel castro", "raul castro"]),
    ("Noboa", ["noboa"]), ("Guillermo Lasso", ["guillermo lasso"]), ("Evo Morales", ["evo morales"]),
    ("Luis Arce", ["luis arce"]), ("Boluarte", ["boluarte"]), ("Pedro Castillo", ["pedro castillo"]),
    ("Fujimori", ["fujimori"]), ("Santiago Peña", ["santiago pena"]), ("Orsi", ["orsi"]),
    ("Lacalle Pou", ["lacalle"]), ("Putin", ["putin"]), ("Xi Jinping", ["xi jinping"]),
    ("Zelensky", ["zelensky", "zelenskyy"]), ("Macron", ["macron"]), ("Merkel", ["merkel"]),
    ("Netanyahu", ["netanyahu"]), ("Modi", ["narendra modi"]), ("Erdogan", ["erdogan"]),
    ("Guterres", ["guterres"]), ("Papa Francisco", ["papa francisco", "pope francis"]),
    ("Papa Leão XIV", ["leao xiv", "pope leo"]), ("Elon Musk", ["elon musk"]),
]
PESSOAS = PESSOAS_CONHECIDAS + list(_cfg("IMAGEM_PESSOAS_EXTRAS", []))

PANDEMIA_PALAVRAS = re.compile(
    r"\b(covid|covid 19|coronavirus|pandemi[ac]|pandemic|quarentena|cuarentena|lockdown|"
    r"mascara|mascaras|mask|masks|vacina|vacuna|vaccine|vaccination|sars cov|distanciamento|"
    r"distanciamiento|social distancing)\b")
PANDEMIA_INICIO, PANDEMIA_FIM = (2020, 3), (2022, 6)


def _tem_padrao(texto_norm, padrao):
    return re.search(rf"\b{re.escape(padrao)}\b", texto_norm) is not None


def _pessoas_em(texto):
    t = _norm(texto)
    return {nome for nome, pads in PESSOAS if any(_tem_padrao(t, p) for p in pads)}


def _texto_foto(titulo, info):
    return " ".join([titulo, _limpa_html(_meta(info, "ImageDescription")),
                     _limpa_html(_meta(info, "ObjectName")),
                     _limpa_html(_meta(info, "Categories")).replace("|", " ")])


def pessoa_errada(titulo, info, contexto):
    """True se a foto cita uma pessoa conhecida que a matéria não menciona."""
    return bool(_pessoas_em(_texto_foto(titulo, info)) - _pessoas_em(contexto))


def _data_foto(info):
    m = re.search(r"(\d{4})(?:-(\d{2}))?", _meta(info, "DateTimeOriginal") or _meta(info, "DateTime"))
    return (int(m.group(1)), int(m.group(2) or 6)) if m else None


def epoca_pandemia(titulo, info):
    if PANDEMIA_PALAVRAS.search(_norm(_texto_foto(titulo, info))):
        return True
    d = _data_foto(info)
    return bool(d and PANDEMIA_INICIO <= d <= PANDEMIA_FIM)


def materia_fala_de_pandemia(contexto):
    return bool(PANDEMIA_PALAVRAS.search(_norm(contexto)))


def _pesquisar(consulta):
    params = {
        "action": "query", "format": "json", "formatversion": 2,
        "generator": "search", "gsrsearch": f"{consulta} filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": LIMITE, "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1280,
        "iiextmetadatafilter": "License|LicenseShortName|UsageTerms|AttributionRequired|"
                               "Restrictions|NonFree|LicenseUrl|Artist|ImageDescription|ObjectName|Categories|DateTimeOriginal|DateTime",
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


def _escolher(grupo, tipo, nivel, usadas, contexto_total, pandemia_ok, cache):
    for ent in grupo or []:
        if not ent or entidade_generica(ent):
            continue
        for consulta in (f'"{ent}"', ent):
            if consulta not in cache:
                cache[consulta] = _pesquisar(consulta)
                print(f"[commons] '{consulta}': {len(cache[consulta])} resultado(s)")
                time.sleep(0.3)
            for titulo, info in cache[consulta]:
                url = info.get("thumburl") or info.get("url")
                if not url or url in usadas or info.get("url") in usadas:
                    continue
                if not _licenca_aceita(info, nivel) or not _qualidade_ok(titulo, info):
                    continue
                if _relevancia(ent, titulo, info) < RELEVANCIA_MIN:
                    continue
                if pessoa_errada(titulo, info, contexto_total):
                    print(f"[commons] recusada (pessoa que a matéria não cita): {titulo}")
                    continue
                if not pandemia_ok and epoca_pandemia(titulo, info):
                    print(f"[commons] recusada (época/tema de pandemia): {titulo}")
                    continue
                autor = _limpa_html(_meta(info, "Artist")) or "Wikimedia Commons"
                pagina = info.get("descriptionurl") or "https://commons.wikimedia.org"
                print(f"[commons] escolhida ({tipo}, {nivel}): {titulo}")
                return {
                    "url": url, "fonte": "Wikimedia Commons",
                    "licenca": _meta(info, "LicenseShortName") or "CC0/Public domain",
                    "licenca_url": _meta(info, "LicenseUrl"),
                    "nivel_licenca": nivel, "tipo_busca": tipo,
                    "autor": autor, "url_pagina": pagina, "entidade": ent,
                    "verificada_em": time.strftime("%Y-%m-%d"),
                    # chaves antigas, para o front-end atual não quebrar
                    "photographer": autor, "photographer_url": pagina, "pexels_url": pagina,
                    "fonte_nome": "Wikimedia Commons", "fonte_url": pagina,
                }
    return None


def buscar_imagem_wikimedia(entidades, urls_usadas=(), contexto="", lugares=()):
    """Ordem: (1) entidades e (2) lugares só CC0/domínio público; depois, se
    IMAGEM_ACEITAR_CC_BY=True, (3) entidades e (4) lugares em CC BY (com crédito)."""
    usadas = set(urls_usadas or ())
    contexto_total = f"{contexto} {' '.join(entidades or [])} {' '.join(lugares or [])}"
    pandemia_ok = materia_fala_de_pandemia(contexto_total)
    cache = {}
    niveis = ["sem_restricoes"] + (["cc_by"] if ACEITAR_CC_BY else [])
    for nivel in niveis:
        for grupo, tipo in ((entidades, "entidade"), (lugares, "lugar")):
            r = _escolher(grupo, tipo, nivel, usadas, contexto_total, pandemia_ok, cache)
            if r:
                return r
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
    contexto = " ".join(str(materia.get(k) or "") for k in ("titulo", "lead", "corpo"))
    img = buscar_imagem_wikimedia(ents, urls_recentes(artigos_publicados), contexto,
                                  list(materia.get("imagem_lugares") or []))
    if img or not _cfg("PERMITIR_IMAGEM_GENERICA_FALLBACK", False):
        return img
    from pipeline.image_search import buscar_imagem  # fallback opcional, desligado por padrão
    return buscar_imagem(materia.get("palavras_chave_imagem", []), pais=materia.get("pais"))

"""Detecta fotos quebradas em posts antigos e busca nova foto pelo MESMO padrão
(entidades guardadas em imagem_busca; se não houver, extrai do título)."""
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

import requests

from pipeline import config
from pipeline.reconstruir_indice import ler_indice, escrever_json_atomico
from pipeline.image_wikimedia import buscar_imagem_wikimedia, urls_recentes, UA

MAX_VERIFICACOES = getattr(config, "REPARO_MAX_VERIFICACOES", 60)
REVERIFICAR_DIAS = getattr(config, "REPARO_REVERIFICAR_DIAS", 14)
MAX_TENTATIVAS = getattr(config, "REPARO_MAX_TENTATIVAS_POR_POST", 6)
MAX_BUSCAS = getattr(config, "REPARO_MAX_BUSCAS", 12)
HORAS_ENTRE = 0 if os.environ.get("REPARO_FORCAR") else getattr(config, "REPARO_HORAS_ENTRE_TENTATIVAS", 20)
SITE_URL = getattr(config, "SITE_URL", "https://diariolatino.github.io/diariolatino/")


def agora():
    return datetime.now(timezone.utc)


def _iso(d):
    return d.isoformat(timespec="seconds")


def _parse(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _ler(p, padrao):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return padrao


def _gravar(p, d):
    escrever_json_atomico(p, d)


def imagem_quebrada(url):
    """True = quebrada, False = ok, None = inconclusivo (timeout/429/5xx)."""
    h = {"User-Agent": UA, "Referer": SITE_URL}
    try:
        r = requests.head(url, headers=h, timeout=15, allow_redirects=True)
        if r.status_code in (403, 405, 501):
            r = requests.get(url, headers=h, timeout=20, stream=True)
            r.close()
    except requests.RequestException:
        return None
    if r.status_code in (404, 410, 401, 403):
        return True
    if r.status_code == 429 or r.status_code >= 500 or r.status_code >= 400:
        return None
    ct = (r.headers.get("Content-Type") or "").lower()
    return bool(ct) and not ct.startswith("image/")


def entidades_do_titulo(titulo):
    """Sequências de palavras capitalizadas (nomes próprios), mais específicas primeiro."""
    seq = re.findall(r"(?:[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ'.-]+)(?:\s+(?:de|da|do|del|dos|das)?\s*"
                     r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ'.-]+)*", titulo or "")
    seq = [s.strip() for s in seq if len(s.strip()) > 3]
    return sorted(dict.fromkeys(seq), key=lambda s: -len(s.split()))[:4]


def _salvar_nos_dois(indice_item, indice, caminho_indice):
    arq = os.path.join(config.ARTIGOS_DIR, f"{indice_item['id']}.json")
    completo = _ler(arq, None)
    if completo is not None:
        for k in ("imagem", "imagem_anterior", "imagem_verificada_em",
                  "imagem_tentativas", "imagem_ultima_tentativa_em", "imagem_busca"):
            if k in indice_item:
                completo[k] = indice_item[k]
            else:
                completo.pop(k, None)
        _gravar(arq, completo)
    _gravar(caminho_indice, indice)


def executar():
    caminho = config.ARTICLES_PATH
    indice = ler_indice()
    if not indice:
        print("[reparo] índice vazio")
        return
    for a in indice:
        if not os.path.exists(os.path.join(config.ARTIGOS_DIR, f"{a['id']}.json")):
            print(f"[reparo] AVISO: sem arquivo de corpo para {a['id']} (post vazio)")

    # 1) verificar fotos existentes, as verificadas há mais tempo primeiro
    com_foto = [a for a in indice if a.get("imagem") and a["imagem"].get("url")]
    limite = agora() - timedelta(days=REVERIFICAR_DIAS)
    pend = [a for a in com_foto if not _parse(a.get("imagem_verificada_em") or "")
            or _parse(a["imagem_verificada_em"]) < limite]
    pend.sort(key=lambda a: a.get("imagem_verificada_em") or "")
    quebradas = 0
    for a in pend[:MAX_VERIFICACOES]:
        res = imagem_quebrada(a["imagem"]["url"])
        if res is None:
            continue
        if res:
            print(f"[reparo] foto quebrada: {a['id']}")
            a["imagem_anterior"] = a.pop("imagem")
            a["imagem_tentativas"] = 0
            quebradas += 1
        else:
            a["imagem_verificada_em"] = _iso(agora())
        time.sleep(0.2)
    _gravar(caminho, indice)

    # 2) buscar foto nova para posts sem imagem
    buscas = 0
    reparados = 0
    for a in indice:
        if a.get("imagem") or buscas >= MAX_BUSCAS:
            continue
        if (a.get("imagem_tentativas") or 0) >= MAX_TENTATIVAS:
            continue
        ult = _parse(a.get("imagem_ultima_tentativa_em") or "")
        if ult and agora() - ult < timedelta(hours=HORAS_ENTRE):
            continue
        ents = (a.get("imagem_busca") or {}).get("entidades") or \
               ((a.get("imagem_anterior") or {}).get("entidade") and
                [a["imagem_anterior"]["entidade"]]) or entidades_do_titulo(a.get("titulo"))
        buscas += 1
        contexto = f"{a.get('titulo', '')} {a.get('lead', '')}"
        lugares = (a.get('imagem_busca') or {}).get('lugares') or []
        nova = buscar_imagem_wikimedia(ents, urls_recentes(indice), contexto, lugares)
        a["imagem_tentativas"] = (a.get("imagem_tentativas") or 0) + 1
        a["imagem_ultima_tentativa_em"] = _iso(agora())
        if nova:
            a["imagem"] = nova
            a["imagem_verificada_em"] = _iso(agora())
            reparados += 1
        _salvar_nos_dois(a, indice, caminho)
    # grava também os que foram quebrados mas não buscados nesta rodada
    for a in indice:
        if "imagem_anterior" in a and not a.get("imagem"):
            _salvar_nos_dois(a, indice, caminho)
    print(f"[reparo] quebradas={quebradas} buscas={buscas} reparadas={reparados}")


if __name__ == "__main__":
    executar()

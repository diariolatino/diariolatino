"""Leitura segura do índice (site/data/articles.json) e reconstrução quando ele corrompe.

Se o JSON estiver quebrado, o site fica vazio e o pipeline cai. Aqui:
1) recupera todas as entradas que ainda estão válidas no arquivo quebrado;
2) para as entradas estragadas, refaz a partir de site/data/artigos/<id>.json;
3) acrescenta qualquer matéria que exista em artigos/ mas não esteja no índice;
4) grava o resultado de forma atômica e guarda o arquivo quebrado em articles.json.corrompido.

Uso manual:  python -m pipeline.reconstruir_indice
"""
import glob
import json
import os
import re

from . import config


def escrever_json_atomico(caminho, dados):
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    json.loads(open(tmp, encoding="utf-8").read())  # confere antes de trocar
    os.replace(tmp, caminho)


def resumir(artigo):
    """Versão enxuta (sem corpo) usada no índice."""
    e = {k: v for k, v in artigo.items() if k != "corpo"}
    e["traducoes"] = {i: {k: v for k, v in c.items() if k != "corpo"}
                      for i, c in (artigo.get("traducoes") or {}).items()}
    return e


def _ler_artigos_completos():
    saida = {}
    for arq in glob.glob(os.path.join(config.ARTIGOS_DIR, "*.json")):
        try:
            with open(arq, encoding="utf-8") as f:
                a = json.load(f)
            if a.get("id"):
                saida[a["id"]] = a
        except Exception as e:
            print(f"[índice] arquivo ilegível ignorado: {arq} ({e})")
    return saida


def _entradas_validas(texto):
    """Quebra o texto nas entradas do array (indent=2) e devolve (validas, ids_estragados)."""
    partes = re.split(r"\n  \{\n", texto)
    validas, estragados = [], []
    for i, parte in enumerate(partes[1:], 1):
        bruto = "  {\n" + parte
        bruto = re.sub(r"\n\]\s*$", "", bruto.rstrip()).rstrip().rstrip(",")
        try:
            obj = json.loads(bruto)
            if isinstance(obj, dict) and obj.get("id"):
                validas.append(obj)
                continue
        except Exception:
            pass
        m = re.search(r'"id"\s*:\s*"([0-9a-fA-F-]{36})"', bruto)
        if m:
            estragados.append(m.group(1))
    return validas, estragados


def reconstruir(texto_quebrado=""):
    completos = _ler_artigos_completos()
    validas, estragados = _entradas_validas(texto_quebrado) if texto_quebrado else ([], [])
    por_id = {}
    for e in validas:
        por_id[e["id"]] = e
    refeitas = 0
    for cid, a in completos.items():          # o arquivo individual é a fonte mais confiável
        if cid not in por_id or cid in estragados:
            refeitas += 1
        por_id[cid] = resumir(a) if cid in completos else por_id[cid]
    indice = sorted(por_id.values(), key=lambda a: a.get("publicado_em") or "", reverse=True)
    print(f"[índice] reconstruído: {len(indice)} matérias ({len(validas)} recuperadas do arquivo quebrado, "
          f"{refeitas} refeitas/acrescentadas a partir de artigos/, {len(estragados)} entradas estragadas)")
    return indice


def ler_indice():
    caminho = config.ARTICLES_PATH
    if not os.path.exists(caminho):
        return []
    with open(caminho, encoding="utf-8") as f:
        texto = f.read()
    try:
        dados = json.loads(texto)
        if isinstance(dados, list):
            return dados
        raise ValueError("o índice não é uma lista")
    except Exception as e:
        print(f"[índice] AVISO: {caminho} está corrompido ({e}). Reconstruindo...")
    indice = reconstruir(texto)
    if not indice:
        raise RuntimeError("índice corrompido e nenhuma matéria recuperável — não vou sobrescrever")
    with open(caminho + ".corrompido", "w", encoding="utf-8") as f:
        f.write(texto)
    escrever_json_atomico(caminho, indice)
    return indice


if __name__ == "__main__":
    ler_indice()
    print("[índice] ok")

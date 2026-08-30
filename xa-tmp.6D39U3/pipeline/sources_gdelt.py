"""
Fonte 1: GDELT Project — dado aberto, gratuito para qualquer uso.
Retorna apenas METADADOS (título, url, domínio, data) — nunca o texto do artigo.
Documentação: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
"""
import requests
from datetime import datetime, timezone
from . import config


def coletar_gdelt(max_resultados: int = 25):
    params = {
        "query": config.GDELT_QUERY,
        "mode": "artlist",
        "maxrecords": str(max_resultados),
        "format": "json",
        "sort": "datedesc",
    }
    try:
        resp = requests.get(config.GDELT_ENDPOINT, params=params, timeout=20)
        resp.raise_for_status()
        dados = resp.json()
    except Exception as e:
        print(f"[gdelt] falha ao consultar: {e}")
        return []

    candidatos = []
    for item in dados.get("articles", []):
        candidatos.append({
            "id": f"gdelt::{item.get('url')}",
            "fonte": "GDELT",
            "titulo": item.get("title", "").strip(),
            "resumo": "",  # GDELT não fornece lead/resumo, só metadados
            "url_original": item.get("url"),
            "dominio": item.get("domain"),
            "data": item.get("seendate"),
            "coletado_em": datetime.now(timezone.utc).isoformat(),
            "tipo": "metadado",  # sinaliza pro extrator de fatos que não há texto de origem
        })
    return candidatos

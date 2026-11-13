"""
Fonte 1: GDELT Project — dado aberto, gratuito para qualquer uso.
Retorna apenas METADADOS (título, url, domínio, data) — nunca o texto do artigo.
Documentação: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

Mudanças: (1) várias consultas menores, por região, para o conjunto de candidatos não ficar
dominado pelo Brasil; (2) espera entre consultas e nova tentativa quando o GDELT responde 429
(o limite deles é ~1 requisição a cada 5 s, e os servidores do GitHub dividem IP com muita gente).
"""
import time
import requests
from datetime import datetime, timezone
from . import config

ESPERA_ENTRE_CONSULTAS_S = 6
TENTATIVAS = 3

_PAISES_SUL = ("argentina OR chile OR colombia OR peru OR bolivia OR venezuela OR uruguay OR paraguay OR ecuador")
_PAISES_NORTE = ("mexico OR guatemala OR honduras OR \"el salvador\" OR nicaragua OR \"costa rica\" OR panama "
                 "OR cuba OR haiti OR \"republica dominicana\" OR \"puerto rico\"")

CONSULTAS = getattr(config, "GDELT_QUERIES", None) or [
    config.GDELT_QUERY,                                   # a original (pt + es, região inteira)
    f"({_PAISES_SUL}) sourcelang:spa",                    # Cone Sul e Andes
    f"({_PAISES_NORTE}) sourcelang:spa",                  # México, América Central e Caribe hispânico
]


def _consultar(query: str, max_resultados: int):
    params = {"query": query, "mode": "artlist", "maxrecords": str(max_resultados),
              "format": "json", "sort": "datedesc"}
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resp = requests.get(config.GDELT_ENDPOINT, params=params, timeout=25)
            if resp.status_code == 429 and tentativa < TENTATIVAS:
                espera = 8 * tentativa
                print(f"[gdelt] 429 (limite de requisições); nova tentativa em {espera}s...")
                time.sleep(espera)
                continue
            resp.raise_for_status()
            return resp.json().get("articles", [])
        except Exception as e:
            print(f"[gdelt] falha ao consultar: {str(e)[:160]}")
            return []
    return []


def coletar_gdelt(max_resultados: int = 25):
    vistos, candidatos = set(), []
    for n, query in enumerate(CONSULTAS):
        if n:
            time.sleep(ESPERA_ENTRE_CONSULTAS_S)
        for item in _consultar(query, max_resultados):
            url = item.get("url")
            if not url or url in vistos:
                continue
            vistos.add(url)
            candidatos.append({
                "id": f"gdelt::{url}",
                "fonte": "GDELT",
                "titulo": item.get("title", "").strip(),
                "resumo": "",  # GDELT não fornece lead/resumo, só metadados
                "url_original": url,
                "dominio": item.get("domain"),
                "data": item.get("seendate"),
                "coletado_em": datetime.now(timezone.utc).isoformat(),
                "tipo": "metadado",  # sinaliza pro extrator de fatos que não há texto de origem
            })
    return candidatos

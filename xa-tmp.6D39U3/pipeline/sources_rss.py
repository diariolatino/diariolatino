"""
Fonte 2: Agência Brasil (licença CC BY 2.5 — permite reprodução/derivação/uso
comercial mediante crédito). Aqui SIM podemos usar título + resumo como
insumo real, sempre creditando "Agência Brasil" no artigo final — EXCETO
itens creditados a agências como Reuters, que a própria Agência Brasil marca
como "proibida a reprodução" dentro do feed.

Fonte 3: feeds de jornal grande (BBC/MercoPress/Al Jazeera/DW/etc) — usados
só como RADAR de manchete. O texto desses feeds nunca é passado pro gerador
de texto; servem só pra sinalizar "algo aconteceu aqui, vá verificar no
GDELT/Agência Brasil/comunicado oficial".
"""
import feedparser
from datetime import datetime, timezone
from . import config


def item_permite_reproducao(entrada) -> bool:
    creditos = (entrada.get("dc_creator") or entrada.get("author") or "").lower()
    return not any(bloqueado in creditos for bloqueado in config.CREDITOS_BLOQUEADOS)


def coletar_agencia_brasil():
    candidatos = []
    for feed_url in config.AGENCIA_BRASIL_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"[agencia_brasil] falha ao ler {feed_url}: {e}")
            continue

        for entrada in feed.entries:
            if not item_permite_reproducao(entrada):
                continue  # ex: crédito Reuters — "proibida a reprodução"

            candidatos.append({
                "id": f"agenciabrasil::{entrada.get('link')}",
                "fonte": "Agência Brasil",
                "licenca": "CC BY 2.5 Brasil",
                "titulo": entrada.get("title", "").strip(),
                "resumo": entrada.get("summary", "").strip(),
                "url_original": entrada.get("link"),
                "data": entrada.get("published", ""),
                "coletado_em": datetime.now(timezone.utc).isoformat(),
                "tipo": "conteudo",  # pode virar insumo real, com crédito
            })
    return candidatos


def coletar_radar():
    """Só para detecção de pauta — NUNCA entra no prompt de geração de texto."""
    radar = []
    for feed_url in config.RADAR_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"[radar] falha ao ler {feed_url}: {e}")
            continue
        for entrada in feed.entries:
            radar.append({
                "titulo": entrada.get("title", "").strip(),
                "url": entrada.get("link"),
            })
    return radar

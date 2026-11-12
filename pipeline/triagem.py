"""Triagem editorial: antes de gastar tokens escrevendo uma matéria, um modelo
pequeno e barato dá nota 0-10 a vários candidatos de uma vez. Só o que passa da
nota mínima vira matéria; o resto fica de lado e a execução espera a próxima
notícia boa. As notas ficam em cache para não reavaliar a mesma notícia."""
import json
import os
import re
import time

from . import config, orcamento_ia
from .generate_text import (CotaIAExcedida, _chamar_chat_completion, _eh_erro_de_cota,
                            _eh_erro_definitivo, _extrair_json, _listar_modelos_candidatos,
                            _salvar_bloqueado)

NOTA_MINIMA = getattr(config, "TRIAGEM_NOTA_MINIMA", 7)
LOTE = getattr(config, "TRIAGEM_TAMANHO_LOTE", 12)
VALIDADE_S = getattr(config, "TRIAGEM_VALIDADE_DIAS", 3) * 86400
_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE = getattr(config, "TRIAGEM_CACHE_PATH", os.path.join(_RAIZ, ".estado", "triagem_cache.json"))

PROMPT = """Você é o editor-chefe do Diario Latino, portal de notícias para toda a \
América Latina. Avalie cada candidato (título + resumo curto) e dê uma nota de 0 a 10 \
para "vale a pena publicar agora?".

Dê nota ALTA (7-10) a: fatos concretos e recentes com impacto real em pessoas, \
governos, economia ou segurança da região; decisões, números, crises, acordos, \
eleições, descobertas; assuntos que o leitor latino-americano quer saber; material \
com informação suficiente para uma matéria factual sem inventar nada.
Dê nota BAIXA (0-6) a: fofoca e celebridades, esporte comum, horóscopo, \
publieditorial, listas e curiosidades, clickbait, opinião sem fato novo, notas \
policiais locais sem relevância regional, assunto sem ligação com a América Latina, \
material vago ou curto demais, notícia requentada.

Responda SOMENTE em JSON: {"avaliacoes": [{"i": 1, "nota": 8, "motivo": "até 12 palavras"}]}
Use o número "i" de cada candidato exatamente como recebido."""


def _ler_cache():
    try:
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _gravar_cache(c):
    agora = time.time()
    c = {k: v for k, v in c.items() if agora - v["em"] < VALIDADE_S}
    c = dict(sorted(c.items(), key=lambda kv: kv[1]["em"])[-800:])
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False)


# nomes que a Groq lista mas que NÃO são bons para esta tarefa (sistemas com ferramentas,
# modelos de voz/árabe etc.) — antes eles entravam na frente do llama-3.1-8b-instant
_NAO_TRIAGEM = re.compile(r"compound|orpheus|allam|playai|whisper|tts|guard|safeguard|embed", re.I)


def _modelos_triagem():
    pequenos = [m for m in _listar_modelos_candidatos("triagem") if not _NAO_TRIAGEM.search(m)]
    pequenos.sort(key=lambda m: (0 if "instant" in m.lower() else 1))  # llama-3.1-8b-instant primeiro
    reserva = list(reversed(_listar_modelos_candidatos("geracao")))      # o menor dos grandes primeiro
    vistos, ordem = set(), []
    for m in pequenos + reserva:
        if m not in vistos and not orcamento_ia.modelo_esgotado(m):
            vistos.add(m)
            ordem.append(m)
    return ordem


def _interpretar(texto, n):
    dados = _extrair_json(texto)
    avs = dados if isinstance(dados, list) else (dados.get("avaliacoes") or dados.get("avaliações")
                                                    or dados.get("evaluations") or [])
    saida = {}
    for a in avs:
        try:
            i = int(str(a.get("i", a.get("indice", ""))).strip().rstrip(".")) 
            if 1 <= i <= n:
                saida[i] = (float(str(a["nota"]).replace(",", ".")), str(a.get("motivo", "")))
        except (ValueError, KeyError, TypeError, AttributeError):
            continue
    return saida


def _pedir_notas(candidatos):
    linhas = []
    for n, c in enumerate(candidatos, 1):
        linhas.append(f"{n}. TÍTULO: {c.get('titulo', '')}\n   RESUMO: {(c.get('resumo') or '(sem resumo)')[:400]}\n"
                      f"   FONTE: {c.get('fonte', '?')}")
    corpo = {"messages": [{"role": "system", "content": PROMPT},
                          {"role": "user", "content": "\n".join(linhas)}],
             "temperature": 0.2, "max_tokens": 900, "response_format": {"type": "json_object"}}
    anterior, orcamento_ia.finalidade_atual = orcamento_ia.finalidade_atual, "triagem"
    cota = False
    try:
        for modelo in _modelos_triagem()[:5]:
            for usar_json_mode in (True, False):   # alguns modelos recusam response_format
                req = corpo if usar_json_mode else {k: v for k, v in corpo.items() if k != "response_format"}
                try:
                    dados = _chamar_chat_completion(modelo, req)
                    notas = _interpretar(dados["choices"][0]["message"]["content"], len(candidatos))
                    if not notas:
                        raise ValueError("resposta sem avaliações válidas")
                    print(f"[triagem] avaliado com '{modelo}'")
                    return {candidatos[i - 1]["id"]: v for i, v in notas.items()}
                except Exception as e:
                    resp = getattr(e, "response", None)
                    detalhe = str(getattr(resp, "text", "") or "")[:200] if resp is not None else ""
                    print(f"[triagem] modelo '{modelo}' falhou (json_mode={usar_json_mode}): {e} {detalhe}")
                    if _eh_erro_definitivo(e):
                        _salvar_bloqueado(modelo, "triagem")
                        break
                    if _eh_erro_de_cota(e):
                        cota = True
                        break
                    status = getattr(resp, "status_code", None)
                    if usar_json_mode and status == 400:
                        continue  # tenta o mesmo modelo sem response_format
                    break
    finally:
        orcamento_ia.finalidade_atual = anterior
    if cota:
        raise CotaIAExcedida("cota esgotada para a triagem")
    return None


def avaliar_e_filtrar(candidatos):
    """Devolve [(candidato, nota)] só com os que passaram, melhor nota primeiro.
    None = não foi possível avaliar agora (a execução deve esperar)."""
    cache = _ler_cache()
    novos = [c for c in candidatos if c["id"] not in cache][:LOTE]
    if novos:
        notas = _pedir_notas(novos)
        if notas is None and not any(c["id"] in cache for c in candidatos):
            return None
        for cid, (nota, motivo) in (notas or {}).items():
            cache[cid] = {"nota": nota, "motivo": motivo, "em": time.time()}
        _gravar_cache(cache)
    aprovados = []
    for pos, c in enumerate(candidatos):
        reg = cache.get(c["id"])
        if reg is None:
            continue
        ok = reg["nota"] >= NOTA_MINIMA
        if c in novos:
            print(f"  [triagem] {reg['nota']:.0f}/10 {'✔' if ok else '✘'} {c.get('titulo', '')[:70]} — {reg['motivo']}")
        if ok:
            aprovados.append((-reg["nota"], pos, c, reg["nota"]))
    aprovados.sort(key=lambda t: (t[0], t[1]))
    return [(c, nota) for _, _, c, nota in aprovados]

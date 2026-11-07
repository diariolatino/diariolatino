"""Controle do orçamento diário de tokens da IA (Groq, plano gratuito).

- registra os tokens gastos por modelo (a API devolve `usage` em cada resposta);
- aprende o limite diário real e o horário de liberação a partir dos erros 429;
- diz se vale a pena rodar agora: sobra de tokens para 1 matéria inteira E ritmo
  que faça a cota durar o dia todo.

O estado fica em .estado/uso_tokens.json (fora de site/, não vai pro commit;
o workflow guarda/restaura via actions/cache).
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

from . import config

_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAMINHO = getattr(config, "USO_TOKENS_PATH", os.path.join(_RAIZ, ".estado", "uso_tokens.json"))
MARGEM = getattr(config, "ORCAMENTO_MARGEM", 0.85)          # usa no máx. 85% da cota diária
FOLGA_RITMO = getattr(config, "ORCAMENTO_FOLGA_RITMO", 0.10)  # 1.0 desliga a distribuição ao longo do dia
CUSTO_PADRAO = getattr(config, "ORCAMENTO_CUSTO_PADRAO_POST", 6000)
FATOR_SEGURANCA = 1.3

# limite diário de tokens (TPD) assumido até a API informar o real
LIMITES_PADRAO = getattr(config, "ORCAMENTO_LIMITES_TPD", [("gpt-oss", 200_000), ("8b", 500_000), ("", 100_000)])

finalidade_atual = "geracao"   # a triagem troca para "triagem" enquanto roda


def _agora():
    return time.time()


def _dia_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _fracao_dia():
    t = datetime.now(timezone.utc)
    return (t.hour * 3600 + t.minute * 60 + t.second) / 86400


def limite_padrao(modelo):
    nome = modelo.lower()
    for padrao, lim in LIMITES_PADRAO:
        if padrao in nome:
            return lim
    return 100_000


def _vazio():
    return {"dia": _dia_utc(), "uso": {}, "posts_hoje": 0, "esgotado_ate": {},
            "limites": {}, "candidatos": [], "historico": []}


def carregar():
    try:
        with open(CAMINHO, encoding="utf-8") as f:
            e = json.load(f)
    except Exception:
        e = _vazio()
    for k, v in _vazio().items():
        e.setdefault(k, v)
    if e["dia"] != _dia_utc():  # virou o dia: arquiva o anterior e zera os contadores
        ger = sum(m.get("geracao", 0) for m in e["uso"].values())
        e["historico"] = (e["historico"] + [{"dia": e["dia"], "tokens_geracao": ger,
                                              "posts": e["posts_hoje"]}])[-7:]
        e["dia"], e["uso"], e["posts_hoje"] = _dia_utc(), {}, 0
    agora = _agora()
    e["esgotado_ate"] = {m: t for m, t in e["esgotado_ate"].items() if t > agora}
    return e


def salvar(e):
    os.makedirs(os.path.dirname(CAMINHO), exist_ok=True)
    with open(CAMINHO, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=2)


def registrar_uso(modelo, usage):
    if not usage:
        return
    total = usage.get("total_tokens") or (usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0))
    e = carregar()
    u = e["uso"].setdefault(modelo, {"tokens": 0, "geracao": 0, "chamadas": 0})
    u["tokens"] += total
    u["chamadas"] += 1
    if finalidade_atual == "geracao":
        u["geracao"] += total
    salvar(e)


def registrar_post():
    e = carregar()
    e["posts_hoje"] += 1
    salvar(e)


def definir_candidatos(nomes):
    e = carregar()
    e["candidatos"] = list(nomes)
    salvar(e)


def _duracao_segundos(texto):
    """'14m23.5s', '1h2m', '850ms' -> segundos."""
    total, achou = 0.0, False
    for valor, un in re.findall(r"(\d+(?:\.\d+)?)(ms|h|m|s)", texto or ""):
        achou = True
        v = float(valor)
        total += v * {"h": 3600, "m": 60, "s": 1, "ms": 0.001}[un]
    return total if achou else None


def registrar_429(modelo, resp):
    """Lê o 429: se for limite DIÁRIO, marca o modelo como esgotado até a liberação."""
    try:
        msg = (resp.json().get("error") or {}).get("message", "")
    except Exception:
        msg = ""
    espera = None
    try:
        espera = float(resp.headers.get("retry-after"))
    except (TypeError, ValueError):
        pass
    if espera is None:
        espera = _duracao_segundos(msg.split("try again in")[-1]) if "try again in" in msg else None
    diario = bool(re.search(r"per day|\(TPD\)|\(RPD\)", msg, re.I))
    e = carregar()
    if diario:
        e["esgotado_ate"][modelo] = _agora() + (espera if espera else 3600)
        m = re.search(r"Limit (\d+)", msg)
        if m:
            e["limites"][modelo] = int(m.group(1))
        print(f"[orçamento] '{modelo}' sem cota diária; volta em ~{int((espera or 3600) / 60)} min")
    else:
        e["esgotado_ate"][modelo] = _agora() + min(espera or 60, 120)
    salvar(e)


def marcar_esgotado(modelo, segundos):
    e = carregar()
    e["esgotado_ate"][modelo] = _agora() + segundos
    salvar(e)


def modelo_esgotado(modelo):
    return modelo in carregar()["esgotado_ate"]


def custo_medio_post(e=None):
    e = e or carregar()
    hist = e["historico"] + [{"tokens_geracao": sum(m.get("geracao", 0) for m in e["uso"].values()),
                              "posts": e["posts_hoje"]}]
    posts = sum(h["posts"] for h in hist)
    if posts < 3:
        return CUSTO_PADRAO
    return max(2000, sum(h["tokens_geracao"] for h in hist) / posts)


def pode_gerar():
    """(True/False, motivo). Barato: só lê o arquivo de estado."""
    e = carregar()
    cands = e["candidatos"]
    if not cands:
        return True, "primeira execução (sem histórico)"
    disponiveis = [m for m in cands if m not in e["esgotado_ate"]]
    if not disponiveis:
        return False, "todos os modelos esgotados por hoje"

    def lim(m):
        return e["limites"].get(m) or limite_padrao(m)

    uso = lambda m: e["uso"].get(m, {}).get("tokens", 0)
    saldo = sum(max(0, lim(m) * MARGEM - uso(m)) for m in disponiveis)
    custo = custo_medio_post(e)
    if saldo < custo * FATOR_SEGURANCA:
        return False, f"saldo de {int(saldo)} tokens < {int(custo * FATOR_SEGURANCA)} necessários"

    gasto = sum(e["uso"].get(m, {}).get("geracao", 0) for m in cands)
    teto_total = sum(lim(m) * MARGEM for m in cands)
    fracao_dia = _fracao_dia()
    permitido = teto_total * min(1.0, fracao_dia + FOLGA_RITMO)
    if gasto + custo > permitido and FOLGA_RITMO < 1.0:
        return False, (f"ritmo: gasto {int(gasto)} + {int(custo)} > {int(permitido)} "
                       f"permitido até agora (cota distribuída ao longo do dia)")
    return True, f"saldo {int(saldo)} tokens, custo médio {int(custo)}"


def _cli():
    try:
        ok, motivo = pode_gerar()
    except Exception as ex:  # na dúvida, roda
        ok, motivo = True, f"erro ao ler orçamento ({ex}); executando por segurança"
    print(f"[orçamento] {'EXECUTAR' if ok else 'PULAR'}: {motivo}")
    saida = os.environ.get("GITHUB_OUTPUT")
    if saida:
        with open(saida, "a") as f:
            f.write(f"executar={'true' if ok else 'false'}\n")


if __name__ == "__main__":
    if "--verificar" in sys.argv:
        _cli()

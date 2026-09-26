"""
Chama a API gratuita da Groq pra:
1) extrair fatos estruturados (o quê/quem/quando/onde/por quê) a partir
   só do título + resumo coletados (nunca do texto completo de terceiros);
2) escrever uma matéria original em português a partir desses fatos, já
   com traduções pra espanhol e inglês.

IMPORTANTE: o nome do modelo NÃO fica fixo no código, pelo mesmo motivo de
antes (quando o pipeline usava o Gemini): provedores de IA trocam/aposentam
modelos com frequência, e um dia a chave pode perder acesso a um modelo
específico sem aviso. Em vez de depender de alguém lembrar de atualizar
isso manualmente, o pipeline pergunta pra própria API da Groq quais
modelos de chat estão disponíveis HOJE, escolhe o melhor candidato (dando
preferência a modelos maiores/mais capazes), e guarda essa escolha num
cache local (site/data/groq_modelo.json) pra não redescobrir a cada
execução.

Se o modelo salvo no cache parar de funcionar (foi aposentado, a conta
perdeu acesso etc.), o código percebe pelo erro da chamada, redescobre a
lista de modelos disponíveis e tenta os próximos candidatos automaticamente
— sem precisar de intervenção manual.

Além disso, o código distingue dois tipos de falha bem diferentes:
- erro genérico ou transitório: só pula pro próximo candidato.
- 401/403 (sem permissão) ou 404 (modelo não existe/foi descontinuado): o
  nome vai pra uma lista de bloqueados persistida em
  site/data/groq_modelos_bloqueados.json, e passa a ser IGNORADO logo na
  hora de montar a lista de candidatos nas próximas execuções — sem isso,
  o pipeline ficaria toda hora gastando tentativas em modelos que já
  sabemos que não funcionam. O bloqueio expira sozinho depois de um tempo,
  caso o acesso seja liberado depois.

A API da Groq segue o mesmo formato da OpenAI (chat completions), o que
deixa esse arquivo mais simples que a versão anterior pro Gemini.
"""
import json
import os
import re
import time
import requests
from . import config

LIST_MODELS_ENDPOINT = "https://api.groq.com/openai/v1/models"
CHAT_COMPLETIONS_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

CACHE_VALIDADE_SEGUNDOS = 24 * 60 * 60  # 1 dia
# depois de quanto tempo vale a pena testar de novo um modelo que deu
# 401/403/404 — o acesso pode ter sido liberado/o modelo pode ter voltado.
BLOQUEIO_REVALIDAR_SEGUNDOS = 30 * 24 * 60 * 60  # 30 dias

# quantos modelos alternativos tentar, no máximo, quando o modelo em cache
# falha — sem esse teto, uma única "tentativa" (do ponto de vista do
# main.py) poderia disparar uma chamada pra CADA modelo listado pela API.
# Com a blocklist persistida, esse número só costuma precisar ser usado
# por inteiro nas primeiras execuções, antes da lista de bloqueados
# "esquentar".
MAX_MODELOS_TENTADOS = 6

PROMPT_SISTEMA = """Você é o redator do Diário Latino, portal de notícias que cobre \
toda a América Latina, com curadoria geopolítica focada em América Latina, Brics, \
Mercosul, G20 e Sul Global.

Você recebe apenas um TÍTULO e, quando disponível, um RESUMO curto vindos de uma fonte \
de metadados. Você NUNCA recebe o texto integral de terceiros.

Sua tarefa:
1. Extrair os fatos objetivos possíveis a partir do que foi fornecido (o quê, quem, \
quando, onde, por quê) — sem inventar detalhes que não constam no material fornecido.
2. Escrever uma matéria jornalística ORIGINAL em português brasileiro, com tom neutro \
e informativo, 250 a 450 palavras, com título, lead (1-2 frases) e corpo.
3. O texto deve ser uma expressão nova — nunca uma tradução, paráfrase próxima ou cópia \
estrutural do título/resumo fornecido. Se o material fornecido for muito escasso para \
sustentar uma matéria completa, escreva um texto mais curto e factualmente conservador \
em vez de inventar informação.
4. Depois de escrever a versão em português, produza TAMBÉM uma versão em espanhol \
neutro (latino-americano, não o de Espanha) e uma versão em inglês, ambas traduções \
fiéis e fluentes do título, lead e corpo em português — mesmo conteúdo factual, \
adaptado naturalmente ao idioma (não é preciso reextrair fatos, é tradução jornalística \
de qualidade).
5. Sugerir de 2 a 3 frases de busca em inglês pra encontrar uma foto editorial \
relevante em bancos de imagem (Pexels, Pixabay, Unsplash, Openverse), da mais \
específica pra mais genérica. Regras importantes pra evitar foto errada:
   - Cada item deve ser uma frase de busca pronta (ex: "Brazil presidential \
election campaign rally"), não uma palavra solta.
   - Se a matéria tem um país central, a frase MAIS específica deve incluir \
o nome desse país em inglês (ex: "Brazil election" e não só "election") — \
sem isso, bancos de imagem tendem a devolver o resultado mais popular pro \
termo em inglês, que costuma ser dos EUA, criando incoerências como uma \
matéria sobre eleição no Brasil vir ilustrada com bandeira americana.
   - Prefira termos concretos e fotografáveis (prédio, bandeira do país \
certo, multidão, tribunal, porto, plantação) a conceitos abstratos.
   - As frases seguintes podem afrouxar a especificidade (tirar o país, por \
exemplo) só como plano B, caso a mais específica não retorne nada.
6. Sugerir 1 categoria dentre exatamente estas opções (grafia exata, inclusive \
maiúsculas): Política, Economia, Mundo, Segurança, Mercosul, Sociedade, Ciência & Ambiente.
   - Política: eleições, governo, congresso, partidos, corrupção, crises institucionais.
   - Economia: inflação, câmbio, dívida, comércio, empresas, emprego, custo de vida.
   - Mundo: fatos fora da América Latina que impactam a região (EUA, China, UE, ONU, \
guerras, sanções) — nunca notícia internacional genérica sem ligação com a região.
   - Segurança: crime organizado, narcotráfico, violência, fronteiras, forças armadas.
   - Mercosul: o bloco em si — cúpulas, tarifas intrabloco, acordos com outros blocos.
   - Sociedade: saúde, educação, migração, direitos humanos, povos indígenas, moradia.
   - Ciência & Ambiente: pesquisa científica, tecnologia, clima, Amazônia, desmatamento.
7. Indicar o país principal ao qual a matéria se refere, escolhendo exatamente um nome \
dentre este catálogo fixo (grafia exata): Argentina, Bolívia, Brasil, Chile, Colômbia, \
Costa Rica, Cuba, Equador, El Salvador, Guatemala, Haiti, Honduras, México, Nicarágua, \
Panamá, Paraguai, Peru, Porto Rico, República Dominicana, Uruguai, Venezuela. Se a \
matéria for sobre um bloco regional ou tema continental sem um país central, use \
"América Latina".
8. Às vezes o material que você recebe inclui, além do TÍTULO/RESUMO da fonte, um \
bloco "NOTÍCIA JÁ PUBLICADA ANTERIORMENTE SOBRE O MESMO ASSUNTO" com o título e o \
lead de uma matéria que o Diário Latino já publicou. Quando isso acontecer:
   - Se o material novo trouxer um fato genuinamente novo em relação ao que já foi \
publicado (novo desdobramento, nova decisão, novo número, nova declaração, mudança \
de status), escreva a matéria normalmente seguindo as regras acima, MAS o título \
DEVE deixar claro que é uma atualização — comece com "Atualização:" ou "Novas \
informações:" (ou variação natural equivalente), seguido do fato novo em si.
   - Se o material novo NÃO trouxer nenhum fato relevante além do que já foi \
publicado (é essencialmente a mesma informação, só reformulada ou contada por outra \
fonte), NÃO escreva a matéria. Responda SOMENTE com este JSON mínimo, sem mais nada: \
{"duplicado": true}

9. Além disso, indicar se esta notícia tem "prioridade_maxima": true ou false. Marque \
true APENAS pra fatos de repercussão realmente excepcional e inequívoca — exemplos: \
morte ou renúncia de um chefe de Estado, golpe de Estado, catástrofe natural com muitas \
vítimas, atentado terrorista, declaração de guerra, decisão histórica de corte \
internacional. Na prática, a GRANDE MAIORIA das notícias do dia a dia (eleição comum, \
dado econômico, operação policial, decisão administrativa) deve ser marcada como false. \
Esse campo é usado só pra permitir, em casos raros, publicar duas matérias seguidas do \
mesmo país mesmo quando o site normalmente evita isso pra variar a cobertura.

Responda SOMENTE em JSON válido, neste formato exato, sem markdown, sem texto fora do JSON \
(exceto no caso do item 8, quando o material for duplicado — aí a resposta é só \
{"duplicado": true}):
{
  "titulo": "...",
  "lead": "...",
  "corpo": "...",
  "categoria": "...",
  "pais": "...",
  "prioridade_maxima": false,
  "palavras_chave_imagem": ["...", "..."],
  "fatos": {"o_que": "...", "quem": "...", "quando": "...", "onde": "...", "por_que": "..."},
  "traducoes": {
    "es": {"titulo": "...", "lead": "...", "corpo": "..."},
    "en": {"titulo": "...", "lead": "...", "corpo": "..."}
  }
}
"""


class CotaIAExcedida(Exception):
    """Levantada quando a API responde 429 (cota gratuita ou limite de
    taxa esgotado). Diferente de outras falhas (candidato ruim, JSON
    malformado etc.), não adianta insistir no próximo candidato — o
    chamador deve parar a execução mais cedo pra não desperdiçar chamadas
    contra uma cota que já está zerada."""
    pass


def _eh_erro_de_cota(e: Exception) -> bool:
    resp = getattr(e, "response", None)
    return resp is not None and getattr(resp, "status_code", None) == 429


def _eh_erro_definitivo(e: Exception) -> bool:
    """401/403 (sem permissão) OU 404 (modelo não existe/foi
    descontinuado) — em qualquer um desses casos, testar esse modelo de
    novo na próxima notícia da mesma execução (ou na próxima execução) não
    vai mudar nada, então vale a pena lembrar disso e pular direto. Bem
    diferente de erros transitórios (timeout, 5xx) ou de cota (429), que
    merecem nova chance mais tarde."""
    resp = getattr(e, "response", None)
    return resp is not None and getattr(resp, "status_code", None) in (401, 403, 404)


def _carregar_cache() -> dict | None:
    if os.path.exists(config.GROQ_MODEL_CACHE_PATH):
        try:
            with open(config.GROQ_MODEL_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _salvar_cache(nome_modelo: str):
    os.makedirs(os.path.dirname(config.GROQ_MODEL_CACHE_PATH), exist_ok=True)
    with open(config.GROQ_MODEL_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"modelo": nome_modelo, "descoberto_em": time.time()}, f)


def _carregar_bloqueados() -> dict:
    caminho = config.GROQ_MODELOS_BLOQUEADOS_PATH
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _salvar_bloqueado(nome_modelo: str, motivo: str):
    caminho = config.GROQ_MODELOS_BLOQUEADOS_PATH
    bloqueados = _carregar_bloqueados()
    bloqueados[nome_modelo] = {"motivo": motivo, "bloqueado_em": time.time()}
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(bloqueados, f, ensure_ascii=False, indent=2)


def _pontuar_modelo(nome_completo: str) -> float:
    """Pontua um modelo de chat da Groq pra escolher o melhor disponível
    sem precisar saber o nome de antemão. Descarta o que claramente não
    serve pra gerar texto em JSON (transcrição de áudio, TTS, moderação/
    guard), prioriza modelos maiores (melhor qualidade de escrita/tradução)
    e, entre os elegíveis, prefere os rótulos "flagship" da Groq."""
    nome = nome_completo.lower()

    bloqueado = ["whisper", "tts", "guard", "moderation", "embed", "transcribe", "safety"]
    if any(termo in nome for termo in bloqueado):
        return -10_000

    pontos = 0.0

    # tamanho do modelo — quanto maior, melhor tende a ser a qualidade de
    # redação/tradução (o que mais importa aqui). Números de parâmetros
    # costumam aparecer no próprio nome (ex: "70b", "120b", "8b").
    tamanhos = re.findall(r"(\d+)\s*b(?:illion)?(?:\b|-|_)", nome)
    maior_tamanho = max((int(t) for t in tamanhos), default=0)
    if maior_tamanho >= 100:
        pontos += 60
    elif maior_tamanho >= 60:
        pontos += 55
    elif maior_tamanho >= 30:
        pontos += 45
    elif maior_tamanho >= 15:
        pontos += 35
    elif maior_tamanho > 0:
        pontos += 20
    else:
        pontos += 15  # tamanho não identificado no nome — ainda tenta, com pontuação neutra

    if "versatile" in nome:
        pontos += 8  # rótulo "principal"/mais robusto que a Groq costuma usar
    if "instant" in nome:
        pontos -= 5  # otimizado pra velocidade, não pra qualidade de texto
    if "preview" in nome:
        pontos -= 20  # cota gratuita costuma ser bem mais curta em modelos preview

    return pontos


def _listar_modelos_candidatos() -> list:
    try:
        resp = requests.get(
            LIST_MODELS_ENDPOINT,
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
            timeout=20,
        )
        resp.raise_for_status()
        modelos = resp.json().get("data", [])
    except Exception as e:
        print(f"[groq] falha ao listar modelos disponíveis: {e}")
        return []

    agora = time.time()
    bloqueados = _carregar_bloqueados()

    candidatos = []
    for m in modelos:
        nome = m.get("id", "")
        if not nome:
            continue
        if m.get("active") is False:
            continue

        bloqueio = bloqueados.get(nome)
        if bloqueio and (agora - bloqueio.get("bloqueado_em", 0)) < BLOQUEIO_REVALIDAR_SEGUNDOS:
            continue  # já sabemos que não funciona — nem tenta

        pontuacao = _pontuar_modelo(nome)
        if pontuacao > -1000:
            candidatos.append((pontuacao, nome))

    candidatos.sort(key=lambda x: x[0], reverse=True)
    return [nome for _, nome in candidatos]


def _chamar_chat_completion(nome_modelo: str, corpo_requisicao: dict) -> dict:
    resp = requests.post(
        CHAT_COMPLETIONS_ENDPOINT,
        headers={
            "Authorization": f"Bearer {config.GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={**corpo_requisicao, "model": nome_modelo},
        timeout=45,
    )
    resp.raise_for_status()
    return resp.json()


def _obter_resposta_ia(corpo_requisicao: dict) -> dict:
    cache = _carregar_cache()
    modelo_cache = None
    if cache and (time.time() - cache.get("descoberto_em", 0)) < CACHE_VALIDADE_SEGUNDOS:
        modelo_cache = cache["modelo"]
        try:
            return _chamar_chat_completion(modelo_cache, corpo_requisicao)
        except Exception as e:
            if _eh_erro_definitivo(e):
                status = getattr(getattr(e, "response", None), "status_code", None)
                _salvar_bloqueado(modelo_cache, f"{status} no modelo em cache")
                motivo = "sem permissão pra essa chave" if status in (401, 403) else "modelo não existe mais"
            else:
                motivo = "cota/limite de taxa atingido" if _eh_erro_de_cota(e) else str(e)
            print(f"[groq] modelo em cache '{modelo_cache}' falhou ({motivo}); tentando outros modelos...")
            # IMPORTANTE: não desiste aqui mesmo se for erro de cota — a
            # cota da Groq é POR MODELO, não geral da conta. Um 429 no
            # modelo em cache não significa que os outros também estejam
            # esgotados.

    candidatos = _listar_modelos_candidatos()
    if modelo_cache:
        candidatos = [c for c in candidatos if c != modelo_cache]
    if not candidatos:
        raise RuntimeError("nenhum modelo de chat da Groq disponível foi encontrado")

    ultimo_erro = None
    algum_erro_de_cota = False
    for nome_modelo in candidatos[:MAX_MODELOS_TENTADOS]:
        try:
            dados = _chamar_chat_completion(nome_modelo, corpo_requisicao)
            _salvar_cache(nome_modelo)
            return dados
        except Exception as e:
            ultimo_erro = e
            if _eh_erro_definitivo(e):
                status = getattr(getattr(e, "response", None), "status_code", None)
                _salvar_bloqueado(nome_modelo, str(status))
                motivo = "sem permissão pra essa chave" if status in (401, 403) else "não existe mais (404)"
                print(f"[groq] modelo '{nome_modelo}' {motivo} — bloqueado pras próximas execuções; tentando o próximo...")
                continue
            if _eh_erro_de_cota(e):
                algum_erro_de_cota = True
            print(f"[groq] modelo '{nome_modelo}' indisponível ({e}); tentando o próximo...")

    if algum_erro_de_cota:
        raise CotaIAExcedida(
            f"cota/limite de taxa da Groq atingido em todos os modelos testados. Último erro: {ultimo_erro}"
        )
    raise RuntimeError(f"todos os modelos candidatos falharam. Último erro: {ultimo_erro}")


def _extrair_json(texto: str) -> dict:
    texto = texto.strip()
    texto = re.sub(r"^```json|^```|```$", "", texto, flags=re.MULTILINE).strip()
    return json.loads(texto)


def gerar_materia(candidato: dict, materia_relacionada: dict | None = None) -> dict | None:
    material = f"TÍTULO: {candidato.get('titulo', '')}\n"
    if candidato.get("resumo"):
        material += f"RESUMO: {candidato['resumo']}\n"
    material += f"FONTE: {candidato.get('fonte', 'desconhecida')}"

    if materia_relacionada:
        material += (
            "\n\nNOTÍCIA JÁ PUBLICADA ANTERIORMENTE SOBRE O MESMO ASSUNTO:\n"
            f"TÍTULO ANTERIOR: {materia_relacionada.get('titulo', '')}\n"
            f"LEAD ANTERIOR: {materia_relacionada.get('lead', '')}"
        )

    corpo_requisicao = {
        "messages": [
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": material},
        ],
        "temperature": 0.6,
        "max_tokens": 3500,
        "response_format": {"type": "json_object"},
    }

    try:
        dados = _obter_resposta_ia(corpo_requisicao)
        texto_bruto = dados["choices"][0]["message"]["content"]
        return _extrair_json(texto_bruto)
    except CotaIAExcedida:
        raise
    except Exception as e:
        print(f"[groq] falha ao gerar matéria para '{candidato.get('titulo')}': {e}")
        return None

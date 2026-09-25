"""
Chama a API gratuita do Gemini pra:
1) extrair fatos estruturados (o quê/quem/quando/onde/por quê) a partir
   só do título + resumo coletados (nunca do texto completo de terceiros);
2) escrever uma matéria original em português a partir desses fatos.

IMPORTANTE: o nome do modelo NÃO fica fixo no código. O Google costuma
trocar/aposentar modelos sem aviso (ex: o "gemini-2.0-flash" que era usado
aqui foi descontinuado em fev/2026). Em vez de depender de alguém lembrar
de atualizar isso manualmente, o pipeline pergunta pra própria API do
Gemini quais modelos existem HOJE com suporte a geração de texto, escolhe
o melhor candidato (dando preferência a modelos "flash", que costumam ter
cota gratuita mais generosa), e guarda essa escolha num cache local
(site/data/gemini_modelo.json) pra não redescobrir a cada execução.

Se o modelo salvo no cache parar de funcionar de um dia pro outro (foi
aposentado, renomeado etc.), o código percebe pelo erro da chamada,
redescobre a lista de modelos disponíveis e tenta os próximos candidatos
automaticamente — sem precisar de intervenção manual.

Além disso, o código distingue dois tipos de falha bem diferentes:
- 404 (modelo não existe) ou erro genérico: só pula pro próximo candidato.
- 403 (modelo existe, mas a chave não tem permissão de usá-lo — comum
  quando o Google lança uma geração nova e libera acesso aos poucos): o
  nome vai pra uma lista de bloqueados persistida em
  site/data/gemini_modelos_bloqueados.json, e passa a ser IGNORADO logo
  na hora de montar a lista de candidatos nas próximas execuções. Sem
  isso, se os modelos mais novos (que pontuam mais alto) forem bloqueados
  pra sua chave, o código ficaria toda hora gastando as tentativas
  disponíveis neles e nunca chegaria nos modelos mais antigos que
  realmente funcionam. O bloqueio expira sozinho depois de um tempo,
  caso o acesso seja liberado depois.
"""
import json
import os
import re
import time
import requests
from . import config

LIST_MODELS_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
GENERATE_ENDPOINT_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"

CACHE_VALIDADE_SEGUNDOS = 24 * 60 * 60  # 1 dia
# depois de quanto tempo vale a pena testar de novo um modelo que deu 403
# — o acesso pode ter sido liberado pra sua chave nesse meio tempo.
BLOQUEIO_REVALIDAR_SEGUNDOS = 30 * 24 * 60 * 60  # 30 dias

# quantos modelos alternativos tentar, no máximo, quando o modelo em cache
# falha — sem esse teto, uma única "tentativa" (do ponto de vista do
# main.py) poderia disparar uma chamada pra CADA modelo listado pela API,
# estourando o orçamento de chamadas por execução sem querer. Com a
# blocklist de 403 persistida, esse número tende a precisar ser usado por
# inteiro só nas primeiras execuções, antes da lista de bloqueados
# "esquentar" — por isso vale a pena ele não ser tão apertado.
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


class CotaGeminiExcedida(Exception):
    """Levantada quando a API do Gemini responde 429 (cota gratuita ou
    limite de taxa esgotado). Diferente de outras falhas (candidato ruim,
    JSON malformado etc.), não adianta insistir no próximo candidato —
    o chamador deve parar a execução mais cedo pra não desperdiçar
    chamadas contra uma cota que já está zerada."""
    pass


def _eh_erro_de_cota(e: Exception) -> bool:
    resp = getattr(e, "response", None)
    return resp is not None and getattr(resp, "status_code", None) == 429


def _eh_erro_de_permissao(e: Exception) -> bool:
    """403 (e o raro 401) significam 'esse modelo existe, mas a chave não
    tem permissão de usá-lo' — bem diferente de 404 (não existe) ou de um
    erro transitório. Vale a pena lembrar disso entre execuções."""
    resp = getattr(e, "response", None)
    return resp is not None and getattr(resp, "status_code", None) in (401, 403)


def _eh_erro_definitivo(e: Exception) -> bool:
    """401/403 (sem permissão) OU 404 (modelo não existe mais/foi
    descontinuado) — em nenhum dos dois casos adianta testar de novo esse
    modelo daqui a pouco, na próxima notícia da mesma execução. Sem tratar
    o 404 aqui também, um modelo aposentado (ex: descontinuado pelo Google)
    seria testado — e falharia — em TODA notícia processada, desperdiçando
    tentativas à toa em vez de chegar em algum candidato que ainda funciona.
    Bem diferente de erros transitórios (timeout, 5xx) ou de cota (429),
    que merecem nova chance mais tarde."""
    resp = getattr(e, "response", None)
    return resp is not None and getattr(resp, "status_code", None) in (401, 403, 404)


def _carregar_cache() -> dict | None:
    if os.path.exists(config.GEMINI_MODEL_CACHE_PATH):
        try:
            with open(config.GEMINI_MODEL_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _salvar_cache(nome_modelo: str):
    os.makedirs(os.path.dirname(config.GEMINI_MODEL_CACHE_PATH), exist_ok=True)
    with open(config.GEMINI_MODEL_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"modelo": nome_modelo, "descoberto_em": time.time()}, f)


def _carregar_bloqueados() -> dict:
    caminho = config.GEMINI_MODELOS_BLOQUEADOS_PATH
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _salvar_bloqueado(nome_modelo: str, motivo: str):
    caminho = config.GEMINI_MODELOS_BLOQUEADOS_PATH
    bloqueados = _carregar_bloqueados()
    bloqueados[nome_modelo] = {"motivo": motivo, "bloqueado_em": time.time()}
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(bloqueados, f, ensure_ascii=False, indent=2)


def _pontuar_modelo(nome_completo: str) -> int:
    nome = nome_completo.lower()

    bloqueado = [
        "embedding", "aqa", "gecko", "imagen", "tts", "veo", "gemma",
        "image-generation", "vision-only", "audio",
    ]
    if any(termo in nome for termo in bloqueado):
        return -10_000

    pontos = 0
    if "flash" in nome:
        pontos += 50
    elif "pro" in nome:
        pontos += 30
    else:
        pontos += 10

    if "lite" in nome:
        pontos -= 5
    # modelos "preview"/"exp"/"thinking" tendem a ter cota gratuita bem
    # mais curta do que os modelos já estabelecidos — penalidade forte o
    # bastante pra nunca vencer um "flash" estável equivalente.
    if "exp" in nome or "preview" in nome or "thinking" in nome:
        pontos -= 30

    # peso bem menor que antes: a versão numérica serve só de desempate
    # entre modelos da mesma categoria (ex: dois "flash"), não deve
    # sobrepor a diferença entre flash/pro nem a penalidade acima. Modelos
    # recém-lançados nem sempre vêm marcados como "preview" no nome, mas
    # tendem a ter cota gratuita inicial mais curta mesmo assim — por
    # isso não vale mais a pena apostar tudo no número mais alto.
    numeros = re.findall(r"(\d+)(?:\.(\d+))?", nome)
    if numeros:
        major, minor = numeros[0]
        pontos += int(major) * 2 + int(minor or 0) * 0.2

    return pontos


def _listar_modelos_candidatos() -> list:
    try:
        resp = requests.get(
            LIST_MODELS_ENDPOINT,
            params={"key": config.GEMINI_API_KEY},
            timeout=20,
        )
        resp.raise_for_status()
        modelos = resp.json().get("models", [])
    except Exception as e:
        print(f"[gemini] falha ao listar modelos disponíveis: {e}")
        return []

    agora = time.time()
    bloqueados = _carregar_bloqueados()

    candidatos = []
    for m in modelos:
        metodos = m.get("supportedGenerationMethods", [])
        if "generateContent" not in metodos:
            continue
        nome = m.get("name", "").replace("models/", "")

        bloqueio = bloqueados.get(nome)
        if bloqueio and (agora - bloqueio.get("bloqueado_em", 0)) < BLOQUEIO_REVALIDAR_SEGUNDOS:
            continue  # sem permissão pra essa chave, já sabemos — nem tenta

        pontuacao = _pontuar_modelo(nome)
        if pontuacao > -1000:
            candidatos.append((pontuacao, nome))

    candidatos.sort(key=lambda x: x[0], reverse=True)
    return [nome for _, nome in candidatos]


def _chamar_generate_content(nome_modelo: str, corpo_requisicao: dict) -> dict:
    resp = requests.post(
        GENERATE_ENDPOINT_TEMPLATE.format(modelo=nome_modelo),
        params={"key": config.GEMINI_API_KEY},
        json=corpo_requisicao,
        timeout=45,
    )
    resp.raise_for_status()
    return resp.json()


def _obter_resposta_gemini(corpo_requisicao: dict) -> dict:
    cache = _carregar_cache()
    modelo_cache = None
    if cache and (time.time() - cache.get("descoberto_em", 0)) < CACHE_VALIDADE_SEGUNDOS:
        modelo_cache = cache["modelo"]
        try:
            return _chamar_generate_content(modelo_cache, corpo_requisicao)
        except Exception as e:
            if _eh_erro_definitivo(e):
                status = getattr(getattr(e, "response", None), "status_code", None)
                _salvar_bloqueado(modelo_cache, f"{status} no modelo em cache")
                motivo = "sem permissão pra essa chave" if status in (401, 403) else "modelo não existe mais"
            else:
                motivo = "cota/limite de taxa atingido" if _eh_erro_de_cota(e) else str(e)
            print(f"[gemini] modelo em cache '{modelo_cache}' falhou ({motivo}); tentando outros modelos...")
            # IMPORTANTE: não desiste aqui mesmo se for erro de cota — a
            # cota do Gemini é POR MODELO, não geral da conta. Um 429 no
            # modelo em cache não significa que os outros também estejam
            # esgotados, então sempre cai pro fluxo abaixo antes de
            # declarar cota geral excedida.

    candidatos = _listar_modelos_candidatos()
    if modelo_cache:
        candidatos = [c for c in candidatos if c != modelo_cache]
    if not candidatos:
        raise RuntimeError("nenhum modelo Gemini com suporte a geração de texto foi encontrado")

    ultimo_erro = None
    algum_erro_de_cota = False
    for nome_modelo in candidatos[:MAX_MODELOS_TENTADOS]:
        try:
            dados = _chamar_generate_content(nome_modelo, corpo_requisicao)
            _salvar_cache(nome_modelo)
            return dados
        except Exception as e:
            ultimo_erro = e
            if _eh_erro_definitivo(e):
                status = getattr(getattr(e, "response", None), "status_code", None)
                _salvar_bloqueado(nome_modelo, str(status))
                motivo = "sem permissão pra essa chave" if status in (401, 403) else "não existe mais (404)"
                print(f"[gemini] modelo '{nome_modelo}' {motivo} — bloqueado pras próximas execuções; tentando o próximo...")
                continue
            if _eh_erro_de_cota(e):
                algum_erro_de_cota = True
            print(f"[gemini] modelo '{nome_modelo}' indisponível ({e}); tentando o próximo...")

    if algum_erro_de_cota:
        raise CotaGeminiExcedida(
            f"cota/limite de taxa do Gemini atingido em todos os modelos testados. Último erro: {ultimo_erro}"
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
        "system_instruction": {"parts": [{"text": PROMPT_SISTEMA}]},
        "contents": [{"parts": [{"text": material}]}],
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 3500},
    }

    try:
        dados = _obter_resposta_gemini(corpo_requisicao)
        texto_bruto = dados["candidates"][0]["content"]["parts"][0]["text"]
        return _extrair_json(texto_bruto)
    except CotaGeminiExcedida:
        raise
    except Exception as e:
        print(f"[gemini] falha ao gerar matéria para '{candidato.get('titulo')}': {e}")
        return None

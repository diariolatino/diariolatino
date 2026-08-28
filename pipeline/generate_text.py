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

Responda SOMENTE em JSON válido, neste formato exato, sem markdown, sem texto fora do JSON:
{
  "titulo": "...",
  "lead": "...",
  "corpo": "...",
  "categoria": "...",
  "pais": "...",
  "palavras_chave_imagem": ["...", "..."],
  "fatos": {"o_que": "...", "quem": "...", "quando": "...", "onde": "...", "por_que": "..."},
  "traducoes": {
    "es": {"titulo": "...", "lead": "...", "corpo": "..."},
    "en": {"titulo": "...", "lead": "...", "corpo": "..."}
  }
}
"""


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
    if "exp" in nome or "preview" in nome or "thinking" in nome:
        pontos -= 10

    numeros = re.findall(r"(\d+)(?:\.(\d+))?", nome)
    if numeros:
        major, minor = numeros[0]
        pontos += int(major) * 10 + int(minor or 0)

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

    candidatos = []
    for m in modelos:
        metodos = m.get("supportedGenerationMethods", [])
        if "generateContent" not in metodos:
            continue
        nome = m.get("name", "").replace("models/", "")
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
    if cache and (time.time() - cache.get("descoberto_em", 0)) < CACHE_VALIDADE_SEGUNDOS:
        try:
            return _chamar_generate_content(cache["modelo"], corpo_requisicao)
        except Exception as e:
            print(f"[gemini] modelo em cache '{cache['modelo']}' falhou ({e}); redescobrindo...")

    candidatos = _listar_modelos_candidatos()
    if not candidatos:
        raise RuntimeError("nenhum modelo Gemini com suporte a geração de texto foi encontrado")

    ultimo_erro = None
    for nome_modelo in candidatos:
        try:
            dados = _chamar_generate_content(nome_modelo, corpo_requisicao)
            _salvar_cache(nome_modelo)
            return dados
        except Exception as e:
            ultimo_erro = e
            print(f"[gemini] modelo '{nome_modelo}' indisponível ({e}); tentando o próximo...")

    raise RuntimeError(f"todos os modelos candidatos falharam. Último erro: {ultimo_erro}")


def _extrair_json(texto: str) -> dict:
    texto = texto.strip()
    texto = re.sub(r"^```json|^```|```$", "", texto, flags=re.MULTILINE).strip()
    return json.loads(texto)


def gerar_materia(candidato: dict) -> dict | None:
    material = f"TÍTULO: {candidato.get('titulo', '')}\n"
    if candidato.get("resumo"):
        material += f"RESUMO: {candidato['resumo']}\n"
    material += f"FONTE: {candidato.get('fonte', 'desconhecida')}"

    corpo_requisicao = {
        "system_instruction": {"parts": [{"text": PROMPT_SISTEMA}]},
        "contents": [{"parts": [{"text": material}]}],
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 3500},
    }

    try:
        dados = _obter_resposta_gemini(corpo_requisicao)
        texto_bruto = dados["candidates"][0]["content"]["parts"][0]["text"]
        return _extrair_json(texto_bruto)
    except Exception as e:
        print(f"[gemini] falha ao gerar matéria para '{candidato.get('titulo')}': {e}")
        return None

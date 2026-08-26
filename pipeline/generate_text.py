"""
Chama a API gratuita do Gemini pra:
1) extrair fatos estruturados (o quê/quem/quando/onde/por quê) a partir
   só do título + resumo coletados (nunca do texto completo de terceiros);
2) escrever uma matéria original em português a partir desses fatos.

O modelo abaixo (GEMINI_MODEL) muda de tempos em tempos — confira o nome
atual disponível no seu tier gratuito em https://ai.google.dev/gemini-api/docs/models
antes de rodar em produção pela primeira vez.
"""
import json
import re
import requests
from . import config

GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

PROMPT_SISTEMA = """Você é o redator do Diário Latino, portal de notícias brasileiro \
com curadoria geopolítica focada em América Latina, Brics, Mercosul, CPLP, G20 e Sul Global.

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
4. Sugerir 1 a 2 palavras-chave em inglês pra busca de imagem no banco Pexels (ex: \
"port cargo ship", "government building").
5. Sugerir 1 categoria dentre: América do Sul, Brics, Mercosul & UE, CPLP, G20 & Ibas, \
Economia Global, Ciência & Ambiente.

Responda SOMENTE em JSON válido, neste formato exato, sem markdown, sem texto fora do JSON:
{
  "titulo": "...",
  "lead": "...",
  "corpo": "...",
  "categoria": "...",
  "palavras_chave_imagem": ["...", "..."],
  "fatos": {"o_que": "...", "quem": "...", "quando": "...", "onde": "...", "por_que": "..."}
}
"""


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
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 1200},
    }

    try:
        resp = requests.post(
            GEMINI_ENDPOINT,
            params={"key": config.GEMINI_API_KEY},
            json=corpo_requisicao,
            timeout=45,
        )
        resp.raise_for_status()
        dados = resp.json()
        texto_bruto = dados["candidates"][0]["content"]["parts"][0]["text"]
        return _extrair_json(texto_bruto)
    except Exception as e:
        print(f"[gemini] falha ao gerar matéria para '{candidato.get('titulo')}': {e}")
        return None

import os

# ---- chaves (vêm dos GitHub Secrets em produção) ----
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
# Openverse não exige chave — funciona mesmo se nenhuma das acima estiver configurada.

# ---- limites por execução (proteger cota gratuita do Gemini/Pexels) ----
# 1 artigo por execução: o workflow já roda 1x/hora, então isso garante o
# ritmo de "1 notícia por hora" em vez de publicar várias de uma vez e
# esgotar a cota gratuita do Gemini ainda de manhã.
MAX_ARTIGOS_POR_EXECUCAO = int(os.environ.get("MAX_ARTIGOS_POR_EXECUCAO", "1"))
# quantas tentativas de geração (chamadas ao Gemini) o pipeline pode fazer
# numa única execução antes de desistir, mesmo que nenhuma vire matéria
# publicável (candidato ruim, muito parecido com outra matéria etc.) —
# sem isso, uma lista grande de candidatos poderia consumir dezenas de
# chamadas à API numa hora só e estourar a cota gratuita antes da hora
# seguinte.
MAX_TENTATIVAS_GEMINI_POR_EXECUCAO = int(os.environ.get("MAX_TENTATIVAS_GEMINI_POR_EXECUCAO", "3"))
MAX_ARTIGOS_NO_SITE = 60  # quantos artigos ficam guardados no articles.json

# ---- checagem de similaridade ----
LIMIAR_DIFFLIB = 0.55          # acima disso = parecido demais, vai pra revisão
USAR_EMBEDDING_CHECK = os.environ.get("USAR_EMBEDDING_CHECK", "false").lower() == "true"
LIMIAR_EMBEDDING = 0.86

# ---- arquivos de estado ----
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "site", "data")
ARTICLES_PATH = os.path.join(DATA_DIR, "articles.json")
SEEN_IDS_PATH = os.path.join(DATA_DIR, "seen_ids.json")
REVIEW_QUEUE_PATH = os.path.join(DATA_DIR, "review_queue.json")
USED_IMAGES_PATH = os.path.join(DATA_DIR, "used_images.json")
GEMINI_MODEL_CACHE_PATH = os.path.join(DATA_DIR, "gemini_modelo.json")

# ---- palavras-chave de relevância geopolítica (pt + es + en, minúsculas) ----
PALAVRAS_RELEVANTES = [
    # blocos e organismos
    "brics", "mercosul", "mercosur", "g20", "unasul", "unasur", "celac", "onu", "un ",
    # regiões
    "américa latina", "america latina", "latin america", "américa do sul", "sudamérica",
    "south america", "sul global", "sur global", "global south",
    # países da região (cobertura ampla, pt + es)
    "brasil", "brazil", "argentina", "chile", "uruguai", "uruguay", "paraguai", "paraguay",
    "bolívia", "bolivia", "peru", "colômbia", "colombia", "venezuela", "equador", "ecuador",
    "méxico", "mexico", "cuba", "guatemala", "honduras", "el salvador", "nicaragua",
    "costa rica", "panamá", "panama", "república dominicana", "republica dominicana",
    # temas (pt + es)
    "geopolítica", "geopolitica", "geopolitics", "comércio exterior", "comercio exterior",
    "relações internacionais", "relaciones internacionales", "diplomacia", "diplomacy",
    "cúpula", "cumbre", "summit", "acordo comercial", "acuerdo comercial",
    "sanções", "sanciones", "tarifas", "aranceles", "moeda", "moneda", "dólar", "dolar",
    "banco de desenvolvimento", "banco de desarrollo",
    "migração", "migración", "imigração", "inmigración", "fronteira", "frontera",
    "narcotráfico", "narcotrafico", "crime organizado", "crimen organizado",
]

# ---- fontes ----
# corrigido: antes só pegava sourcelang:por, o que excluía quase toda a
# imprensa em espanhol da região (Argentina, Chile, Colômbia, México etc.)
GDELT_QUERY = (
    "(brics OR mercosul OR mercosur OR \"america latina\" OR \"south america\" "
    "OR brasil OR brazil OR argentina OR chile OR colombia OR peru OR bolivia "
    "OR venezuela OR uruguay OR paraguay OR ecuador OR mexico) "
    "(sourcelang:por OR sourcelang:spa)"
)
GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"

# Agência Brasil — CC BY 2.5 Brasil, mesma licença nas 4 editorias
AGENCIA_BRASIL_FEEDS = [
    "https://agenciabrasil.ebc.com.br/rss/internacional/feed.xml",   # testado ao vivo
    "https://agenciabrasil.ebc.com.br/rss/geral/feed.xml",           # já em produção
    "https://agenciabrasil.ebc.com.br/rss/economia/feed.xml",        # índice oficial
    "https://agenciabrasil.ebc.com.br/rss/politica/feed.xml",        # índice oficial
]

# créditos que a própria Agência Brasil marca como "proibida a reprodução"
# dentro do feed (confirmado ao vivo num item assinado por repórter da Reuters)
CREDITOS_BLOQUEADOS = ["reuters"]

# radar de manchete — NUNCA entra no prompt de geração de texto, só sinaliza
# pauta pro GDELT/Agência Brasil investigar. Por isso aqui cabe fonte de
# qualquer lugar do mundo, sem restrição de licença.
RADAR_FEEDS = [
    # América Latina / Mercosul
    "http://feeds.bbci.co.uk/news/world/latin_america/rss.xml",      # já em produção
    "https://en.mercopress.com/rss/latin-america",                   # testado ao vivo
    "https://en.mercopress.com/rss/mercosur",                        # índice oficial
    "https://en.mercopress.com/rss/brazil",                          # índice oficial
    "https://en.mercopress.com/rss/argentina",                       # índice oficial
    "https://buenosairesherald.com/feed",                            # site oficial
    "https://mexiconewsdaily.com/feed",                              # site oficial
    "https://cnnespanol.cnn.com/feed",                               # site oficial

    # BRICS / geopolítica global (Rússia, Índia, China, África do Sul, Oriente Médio)
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/mundo/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://rss.dw.com/xml/rss-en-all",
    "https://www.france24.com/en/rss",
    "https://www.telesurenglish.net/rss/RssTelesur.xml",             # viés: mídia estatal venezuelana

    # organismos multilaterais
    "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
]

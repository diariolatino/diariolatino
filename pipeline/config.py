import os

# ---- chaves (vêm dos GitHub Secrets em produção) ----
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

# ---- limites por execução (proteger cota gratuita do Gemini/Pexels) ----
MAX_ARTIGOS_POR_EXECUCAO = int(os.environ.get("MAX_ARTIGOS_POR_EXECUCAO", "3"))
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

# ---- palavras-chave de relevância geopolítica (pt + es + en, minúsculas) ----
PALAVRAS_RELEVANTES = [
    # blocos e organismos
    "brics", "mercosul", "mercosur", "cplp", "g20", "ibas", "unasul", "celac", "onu", "un ",
    # regiões
    "américa latina", "america latina", "latin america", "américa do sul", "south america",
    "sul global", "global south",
    # países da região (cobertura ampla)
    "brasil", "brazil", "argentina", "chile", "uruguai", "uruguay", "paraguai", "paraguay",
    "bolívia", "bolivia", "peru", "colômbia", "colombia", "venezuela", "equador", "ecuador",
    "méxico", "mexico", "cuba",
    # temas
    "geopolítica", "geopolitica", "geopolitics", "comércio exterior", "relações internacionais",
    "diplomacia", "cúpula", "cumbre", "summit", "acordo comercial", "sanções", "tarifas",
    "moeda", "dólar", "banco de desenvolvimento",
]

# ---- fontes ----
GDELT_QUERY = (
    "(brics OR mercosul OR mercosur OR \"america latina\" OR \"south america\" "
    "OR brasil OR brazil) sourcelang:por"
)
GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"

AGENCIA_BRASIL_FEEDS = [
    "https://agenciabrasil.ebc.com.br/rss/internacional/feed.xml",
    "https://agenciabrasil.ebc.com.br/rss/geral/feed.xml",
]

# feeds de jornal grande = só "radar de manchete", nunca vira insumo de texto
RADAR_FEEDS = [
    "http://feeds.bbci.co.uk/news/world/latin_america/rss.xml",
]

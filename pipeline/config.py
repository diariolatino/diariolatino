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
GEMINI_MODEL_CACHE_PATH = os.path.join(DATA_DIR, "gemini_modelo.json")

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

# config.py — trecho atualizado

# ---- Agência Brasil: mesma licença CC BY 2.5, mais editorias ----
# (internacional e geral já testados ao vivo nesta sessão; economia/política
# vêm do índice oficial https://agenciabrasil.ebc.com.br/feed/ — rodar 1x pra confirmar)
AGENCIA_BRASIL_FEEDS = [
    "https://agenciabrasil.ebc.com.br/rss/internacional/feed.xml",   # testado ao vivo
    "https://agenciabrasil.ebc.com.br/rss/geral/feed.xml",           # já em produção
    "https://agenciabrasil.ebc.com.br/rss/economia/feed.xml",        # índice oficial
    "https://agenciabrasil.ebc.com.br/rss/politica/feed.xml",        # índice oficial
]

# créditos que a própria Agência Brasil marca como "proibida a reprodução"
# (vi isso ao vivo num item assinado por repórteres da Reuters dentro do
# feed internacional — precisa filtrar por dc:creator antes de usar como insumo)
CREDITOS_BLOQUEADOS = ["reuters"]

# ---- Radar de manchete — NUNCA entra no prompt de geração de texto,
# só sinaliza pauta. Por isso aqui cabe qualquer fonte do mundo. ----
RADAR_FEEDS = [
    # América Latina / Mercosul
    "http://feeds.bbci.co.uk/news/world/latin_america/rss.xml",      # já em produção
    "https://en.mercopress.com/rss/latin-america",                   # testado ao vivo
    "https://en.mercopress.com/rss/mercosur",                        # índice oficial mercopress.com/feeds
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

    # ONU / organismos multilaterais (radar, não conteúdo)
    "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
]

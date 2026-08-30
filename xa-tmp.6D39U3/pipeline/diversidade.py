"""
Estimativa rápida de tema por palavra-chave, usada só pra ORDENAR a fila de
candidatos antes de gastar chamada do Gemini (intercalando temas em vez de
processar tudo agrupado no mesmo assunto). A categoria OFICIAL de cada
matéria continua sendo a que o Gemini decide depois de ler os fatos — esta
estimativa nunca decide o que é publicado nem qual categoria vai no artigo.
"""
from collections import defaultdict

CATEGORIAS_PALAVRAS_CHAVE = {
    "Política": [
        "eleições", "elecciones", "presidente", "governo", "gobierno", "congresso",
        "parlamento", "partido político", "impeachment", "corrupção", "corrupción",
        "protesto", "manifestação", "ministro", "reforma constitucional",
    ],
    "Economia": [
        "pib", "inflação", "inflación", "juros", "câmbio", "dólar", "dolar",
        "dívida pública", "imposto", "bolsa de valores", "investimento",
        "exportação", "importação", "comércio", "petróleo", "mineração", "emprego",
    ],
    "Mundo": [
        "estados unidos", "eua", "china", "união europeia", "unión europea",
        "rússia", "rusia", "onu", "oea", "fmi", "banco mundial", "sanções",
        "sanciones", "tratado internacional", "casa branca", "otan",
    ],
    "Segurança": [
        "crime organizado", "crimen organizado", "narcotráfico", "narcotrafico",
        "cartel", "facção", "tráfico de armas", "violência", "homicídio",
        "operação policial", "fronteira", "frontera", "forças armadas", "guerrilha",
    ],
    "Mercosul": [
        "mercosul", "mercosur", "bloco econômico", "integração regional",
        "cúpula do mercosul", "cumbre del mercosur", "tarifa intrabloco",
    ],
    "Sociedade": [
        "saúde pública", "salud pública", "educação", "educación", "pobreza",
        "desigualdade", "desigualdad", "migração", "migración", "refugiados",
        "direitos humanos", "derechos humanos", "povos indígenas", "moradia",
    ],
    "Ciência & Ambiente": [
        "clima", "aquecimento global", "amazônia", "desmatamento", "científic",
        "pesquisa científica", "universidade", "tecnologia", "energia renovável",
        "biodiversidade", "seca", "enchente",
    ],
}


def estimar_categoria(candidato: dict) -> str:
    texto = f"{candidato.get('titulo', '')} {candidato.get('resumo', '')}".lower()
    melhor_categoria, melhor_pontuacao = "Mundo", 0
    for categoria, palavras in CATEGORIAS_PALAVRAS_CHAVE.items():
        pontos = sum(1 for p in palavras if p in texto)
        if pontos > melhor_pontuacao:
            melhor_categoria, melhor_pontuacao = categoria, pontos
    return melhor_categoria


def intercalar_por_categoria(candidatos: list) -> list:
    baldes = defaultdict(list)
    for c in candidatos:
        baldes[estimar_categoria(c)].append(c)

    ordem_categorias = list(baldes.keys())
    resultado = []
    while any(baldes[cat] for cat in ordem_categorias):
        for cat in ordem_categorias:
            if baldes[cat]:
                resultado.append(baldes[cat].pop(0))
    return resultado

"""
Estimativa rápida de tema por palavra-chave, usada só pra ORDENAR a fila de
candidatos antes de gastar chamada do Gemini (intercalando temas em vez de
processar tudo agrupado no mesmo assunto). A categoria OFICIAL de cada
matéria continua sendo a que o Gemini decide depois de ler os fatos — esta
estimativa nunca decide o que é publicado nem qual categoria vai no artigo.
"""
from collections import defaultdict

CATEGORIAS_PALAVRAS_CHAVE = {
    "Ciência & Ambiente": [
        "clima", "aquecimento global", "meio ambiente", "ambiental", "científic",
        "vacina", "desmatamento", "energia renovável", "terremoto", "enchente", "seca",
    ],
    "Economia Global": [
        "pib", "inflação", "inflación", "juros", "câmbio", "dólar", "dolar",
        "comércio exterior", "comercio exterior", "tarifa", "arancel", "exportação",
        "importação", "banco central", "dívida pública", "investimento estrangeiro",
    ],
    "Mercosul & UE": [
        "mercosul", "mercosur", "união europeia", "unión europea", "bruxelas",
        "parlamento europeu",
    ],
    "América do Sul": [
        "argentina", "chile", "uruguai", "uruguay", "paraguai", "paraguay",
        "bolívia", "bolivia", "peru", "colômbia", "colombia", "venezuela",
        "equador", "ecuador",
    ],
    "Migração & Fronteiras": [
        "migração", "migración", "migrantes", "imigração", "inmigración",
        "refugiados", "fronteira", "frontera", "deportação", "deportación", "vistos",
    ],
    "Segurança & Crime Organizado": [
        "crime organizado", "crimen organizado", "narcotráfico", "narcotrafico",
        "facção", "violência", "homicídio", "segurança pública", "tráfico de armas",
    ],
    "Diplomacia & Relações Internacionais": [
        "itamaraty", "embaixador", "embajador", "relações bilaterais",
        "relaciones bilaterales", "relações internacionais", "relaciones internacionales",
        "cúpula", "cumbre", "sanções", "sanciones", "onu", "casa branca", "chanceler", "canciller",
    ],
}


def estimar_categoria(candidato: dict) -> str:
    texto = f"{candidato.get('titulo', '')} {candidato.get('resumo', '')}".lower()
    melhor_categoria, melhor_pontuacao = "América do Sul", 0
    for categoria, palavras in CATEGORIAS_PALAVRAS_CHAVE.items():
        pontos = sum(1 for p in palavras if p in texto)
        if pontos > melhor_pontuacao:
            melhor_categoria, melhor_pontuacao = categoria, pontos
    return melhor_categoria


def intercalar_por_categoria(candidatos: list) -> list:
    """Reordena os candidatos pra alternar entre temas estimados, em vez de
    vir tudo agrupado no mesmo assunto (ex: 5 notícias de segurança seguidas)."""
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

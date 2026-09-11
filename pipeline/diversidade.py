"""
Estimativa rápida de tema/país por palavra-chave, usada só pra ORDENAR a
fila de candidatos antes de gastar chamada do Gemini (intercalando temas e
países em vez de processar tudo agrupado no mesmo assunto/país). A
categoria e o país OFICIAIS de cada matéria continuam sendo os que o
Gemini decide depois de ler os fatos — esta estimativa nunca decide o que
é publicado nem o que vai no artigo, só a ORDEM de tentativa.
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

# nomes + gentílicos/adjetivos comuns, pt e es, pra pegar tanto "no Brasil"
# quanto "brasileiro(a)"/"brasileño(a)" no título ou resumo
PAISES_PALAVRAS_CHAVE = {
    "Argentina": ["argentina", "argentino", "buenos aires"],
    "Bolívia": ["bolívia", "bolivia", "boliviano", "la paz", "sucre"],
    "Brasil": ["brasil", "brazil", "brasileiro", "brasileira", "brasília"],
    "Chile": ["chile", "chileno", "chilena", "santiago"],
    "Colômbia": ["colômbia", "colombia", "colombiano", "colombiana", "bogotá"],
    "Costa Rica": ["costa rica", "costarriquenho", "costarricense", "san josé"],
    "Cuba": ["cuba", "cubano", "cubana", "havana", "habana"],
    "Equador": ["equador", "ecuador", "equatoriano", "ecuatoriano", "quito"],
    "El Salvador": ["el salvador", "salvadorenho", "salvadoreño", "san salvador"],
    "Guatemala": ["guatemala", "guatemalteco", "guatemalteca"],
    "Haiti": ["haiti", "haitiano", "haitiana", "porto príncipe"],
    "Honduras": ["honduras", "hondurenho", "hondureño", "tegucigalpa"],
    "México": ["méxico", "mexico", "mexicano", "mexicana"],
    "Nicarágua": ["nicarágua", "nicaragua", "nicaraguense", "managua"],
    "Panamá": ["panamá", "panama", "panamenho", "panameño"],
    "Paraguai": ["paraguai", "paraguay", "paraguaio", "paraguayo", "assunção", "asunción"],
    "Peru": ["peru", "peruano", "peruana", "lima"],
    "Porto Rico": ["porto rico", "puerto rico", "porto-riquenho", "puertorriqueño"],
    "República Dominicana": ["república dominicana", "dominicano", "dominicana", "santo domingo"],
    "Uruguai": ["uruguai", "uruguay", "uruguaio", "uruguayo", "montevidéu", "montevideo"],
    "Venezuela": ["venezuela", "venezuelano", "venezuelana", "caracas"],
}


def estimar_categoria(candidato: dict) -> str:
    texto = f"{candidato.get('titulo', '')} {candidato.get('resumo', '')}".lower()
    melhor_categoria, melhor_pontuacao = "Mundo", 0
    for categoria, palavras in CATEGORIAS_PALAVRAS_CHAVE.items():
        pontos = sum(1 for p in palavras if p in texto)
        if pontos > melhor_pontuacao:
            melhor_categoria, melhor_pontuacao = categoria, pontos
    return melhor_categoria


def estimar_pais(candidato: dict) -> str:
    """Chute rápido (por palavra-chave) de qual país o candidato cobre —
    só pra ordenar a fila e variar os países desde a tentativa. Não é o
    país oficial (esse é o que o Gemini decide, olhando o fato todo)."""
    texto = f"{candidato.get('titulo', '')} {candidato.get('resumo', '')}".lower()
    melhor_pais, melhor_pontuacao = None, 0
    for pais, palavras in PAISES_PALAVRAS_CHAVE.items():
        pontos = sum(1 for p in palavras if p in texto)
        if pontos > melhor_pontuacao:
            melhor_pais, melhor_pontuacao = pais, pontos
    # Agência Brasil é o grosso das fontes com texto completo — se nenhum
    # outro país aparecer explicitamente no texto, o chute mais provável
    # é Brasil mesmo (evita cair sempre no mesmo balde "desconhecido").
    if not melhor_pais and candidato.get("fonte") == "Agência Brasil":
        return "Brasil"
    return melhor_pais or "América Latina"


def evitar_repeticao_consecutiva(candidatos: list, chave) -> list:
    """Reordena minimamente a lista pra que dois itens consecutivos nunca
    tenham a mesma chave (categoria, país etc.), quando der pra evitar.
    Greedy: anda pela lista e, se o próximo item repetir a chave do
    anterior, troca de lugar com o primeiro item mais à frente que tiver
    uma chave diferente. Se não achar nenhum, deixa como está (às vezes
    não dá pra evitar, ex: só sobrou candidato do mesmo país)."""
    lista = list(candidatos)
    n = len(lista)
    for i in range(1, n):
        if chave(lista[i]) == chave(lista[i - 1]):
            for j in range(i + 1, n):
                if chave(lista[j]) != chave(lista[i - 1]):
                    lista[i], lista[j] = lista[j], lista[i]
                    break
    return lista


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


def intercalar_por_categoria_e_pais(candidatos: list) -> list:
    """Ordena a fila de tentativa pra variar tema E país desde o início:
    primeiro intercala por categoria (como antes), depois reordena pra
    evitar dois candidatos seguidos com o mesmo país estimado. A garantia
    de verdade (com o país que o Gemini realmente escolheu) é aplicada
    depois, em main.py, comparando com o último artigo publicado."""
    candidatos = intercalar_por_categoria(candidatos)
    candidatos = evitar_repeticao_consecutiva(candidatos, estimar_pais)
    return candidatos

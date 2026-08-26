from . import config


def eh_relevante(candidato: dict) -> bool:
    texto = f"{candidato.get('titulo', '')} {candidato.get('resumo', '')}".lower()
    return any(palavra in texto for palavra in config.PALAVRAS_RELEVANTES)


def filtrar(candidatos: list) -> list:
    return [c for c in candidatos if eh_relevante(c)]

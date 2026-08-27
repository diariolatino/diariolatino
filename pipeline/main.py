from . import config
from .sources_gdelt import coletar_gdelt
from .sources_rss import coletar_agencia_brasil, coletar_radar
from .filter_relevance import filtrar
from .diversidade import intercalar_por_categoria
from .generate_text import gerar_materia
from .similarity_check import checar_originalidade
from .image_pexels import buscar_imagem
from .publish import ja_publicado, publicar, enviar_para_revisao


def rodar():
    if not config.GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY não configurada (confira os GitHub Secrets).")
    if not config.PEXELS_API_KEY:
        raise SystemExit("PEXELS_API_KEY não configurada (confira os GitHub Secrets).")

    print("Coletando candidatos...")
    candidatos = coletar_gdelt() + coletar_agencia_brasil()
    _radar = coletar_radar()  # só logado/monitorado, nunca vira insumo de texto
    print(f"  {len(candidatos)} candidatos brutos, {len(_radar)} manchetes no radar")

    candidatos = filtrar(candidatos)
    candidatos = [c for c in candidatos if not ja_publicado(c["id"])]
    candidatos = intercalar_por_categoria(candidatos)  # varia o tema desde a ordem de tentativa
    print(f"  {len(candidatos)} candidatos relevantes, inéditos e intercalados por tema")

    publicados = 0
    categorias_usadas_nesta_execucao = set()

    for candidato in candidatos:
        if publicados >= config.MAX_ARTIGOS_POR_EXECUCAO:
            break

        # GDELT só dá metadado (sem resumo) — pula se não tiver material mínimo
        if candidato["tipo"] == "metadado" and not candidato.get("titulo"):
            continue

        materia = gerar_materia(candidato)
        if not materia:
            continue

        categoria = materia.get("categoria", "América do Sul")
        if categoria in categorias_usadas_nesta_execucao:
            # trava de segurança final: a intercalação já tenta evitar isso,
            # mas o Gemini pode classificar diferente do estimado
            print(f"  [pulado] '{materia.get('titulo')}' — tema '{categoria}' já usado nesta execução")
            continue

        resultado_check = checar_originalidade(materia, candidato)
        if not resultado_check["aprovado"]:
            print(f"  [revisão] '{materia.get('titulo')}' sinalizado: {resultado_check['detalhes']}")
            enviar_para_revisao(materia, candidato, resultado_check["detalhes"])
            continue

        imagem = buscar_imagem(materia.get("palavras_chave_imagem", []))
        artigo = publicar(materia, candidato, imagem)
        categorias_usadas_nesta_execucao.add(categoria)
        publicados += 1
        print(f"  [publicado] {artigo['titulo']} — {categoria}")

    print(f"Concluído: {publicados} artigo(s) publicado(s) nesta execução.")


if __name__ == "__main__":
    rodar()

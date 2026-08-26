from . import config
from .sources_gdelt import coletar_gdelt
from .sources_rss import coletar_agencia_brasil, coletar_radar
from .filter_relevance import filtrar
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
    print(f"  {len(candidatos)} candidatos relevantes e inéditos")

    publicados = 0
    for candidato in candidatos:
        if publicados >= config.MAX_ARTIGOS_POR_EXECUCAO:
            break

        # GDELT só dá metadado (sem resumo) — pula se não tiver material mínimo
        if candidato["tipo"] == "metadado" and not candidato.get("titulo"):
            continue

        materia = gerar_materia(candidato)
        if not materia:
            continue

        resultado_check = checar_originalidade(materia, candidato)
        if not resultado_check["aprovado"]:
            print(f"  [revisão] '{materia.get('titulo')}' sinalizado: {resultado_check['detalhes']}")
            enviar_para_revisao(materia, candidato, resultado_check["detalhes"])
            continue

        imagem = buscar_imagem(materia.get("palavras_chave_imagem", []))
        artigo = publicar(materia, candidato, imagem)
        publicados += 1
        print(f"  [publicado] {artigo['titulo']}")

    print(f"Concluído: {publicados} artigo(s) publicado(s) nesta execução.")


if __name__ == "__main__":
    rodar()

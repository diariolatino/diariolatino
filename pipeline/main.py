from . import config
from .sources_gdelt import coletar_gdelt
from .sources_rss import coletar_agencia_brasil, coletar_radar
from .filter_relevance import filtrar
from .diversidade import intercalar_por_categoria
from .generate_text import gerar_materia, CotaGeminiExcedida
from .similarity_check import checar_originalidade
from .deduplicacao import encontrar_materia_relacionada
from .image_search import buscar_imagem
from .publish import ja_publicado, marcar_como_visto, publicar, enviar_para_revisao, carregar_artigos_publicados


def rodar():
    if not config.GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY não configurada (confira os GitHub Secrets).")
    if not (config.PEXELS_API_KEY or config.PIXABAY_API_KEY or config.UNSPLASH_ACCESS_KEY):
        print("[aviso] nenhuma chave de banco de imagem paga configurada (Pexels/Pixabay/Unsplash) — "
              "seguindo só com Openverse, que não exige chave.")

    print("Coletando candidatos...")
    candidatos = coletar_gdelt() + coletar_agencia_brasil()
    _radar = coletar_radar()  # só logado/monitorado, nunca vira insumo de texto
    print(f"  {len(candidatos)} candidatos brutos, {len(_radar)} manchetes no radar")

    candidatos = filtrar(candidatos)
    candidatos = [c for c in candidatos if not ja_publicado(c["id"])]
    candidatos = intercalar_por_categoria(candidatos)  # varia o tema desde a ordem de tentativa
    print(f"  {len(candidatos)} candidatos relevantes, inéditos e intercalados por tema")

    artigos_publicados = carregar_artigos_publicados()

    publicados = 0
    tentativas_gemini = 0
    categorias_usadas_nesta_execucao = set()

    for candidato in candidatos:
        if publicados >= config.MAX_ARTIGOS_POR_EXECUCAO:
            break
        if tentativas_gemini >= config.MAX_TENTATIVAS_GEMINI_POR_EXECUCAO:
            print(f"  [limite] {tentativas_gemini} tentativas de geração nesta execução — "
                  f"parando por aqui pra preservar cota das próximas horas.")
            break

        # GDELT só dá metadado (sem resumo) — pula se não tiver material mínimo
        if candidato["tipo"] == "metadado" and not candidato.get("titulo"):
            continue

        tentativas_gemini += 1
        try:
            materia_relacionada = encontrar_materia_relacionada(candidato, artigos_publicados)
            materia = gerar_materia(candidato, materia_relacionada)
        except CotaGeminiExcedida as e:
            print(f"  [cota] limite gratuito do Gemini atingido nesta janela ({e}). "
                  f"Encerrando a execução mais cedo — a próxima hora tenta de novo.")
            break
        if not materia:
            continue

        if materia.get("duplicado"):
            print(f"  [duplicado] candidato '{candidato.get('titulo')}' já coberto por "
                  f"'{materia_relacionada.get('titulo') if materia_relacionada else '?'}' "
                  f"sem fato novo relevante — descartado, não publicado.")
            marcar_como_visto(candidato["id"])
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

        imagem = buscar_imagem(materia.get("palavras_chave_imagem", []), pais=materia.get("pais"))
        artigo = publicar(materia, candidato, imagem, materia_relacionada)
        artigos_publicados.insert(0, artigo)
        categorias_usadas_nesta_execucao.add(categoria)
        publicados += 1
        print(f"  [publicado] {artigo['titulo']} — {categoria}")

    print(f"Concluído: {publicados} artigo(s) publicado(s) nesta execução.")


if __name__ == "__main__":
    rodar()

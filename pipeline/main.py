from . import config
from .sources_gdelt import coletar_gdelt
from .sources_rss import coletar_agencia_brasil, coletar_radar
from .filter_relevance import filtrar
from .diversidade import intercalar_por_categoria_e_pais
from .generate_text import gerar_materia, CotaIAExcedida
from . import orcamento_ia
from .triagem import avaliar_e_filtrar
from .similarity_check import checar_originalidade
from .deduplicacao import encontrar_materia_relacionada
from .image_wikimedia import buscar_imagem_relevante
from .publish import ja_publicado, marcar_como_visto, publicar, enviar_para_revisao, carregar_artigos_publicados


def rodar():
    if not config.GROQ_API_KEY:
        raise SystemExit("GROQ_API_KEY não configurada (confira os GitHub Secrets).")

    pode, motivo = orcamento_ia.pode_gerar()
    if not pode:
        print(f"[orçamento] sem fôlego de tokens agora ({motivo}) — esperando a próxima execução.")
        return
    print(f"[orçamento] ok: {motivo}")

    print("Coletando candidatos...")
    candidatos = coletar_gdelt() + coletar_agencia_brasil()
    _radar = coletar_radar()  # só logado/monitorado, nunca vira insumo de texto
    print(f"  {len(candidatos)} candidatos brutos, {len(_radar)} manchetes no radar")

    candidatos = filtrar(candidatos)
    candidatos = [c for c in candidatos if not ja_publicado(c["id"])]
    candidatos = intercalar_por_categoria_e_pais(candidatos)  # varia tema E país desde a ordem de tentativa
    print(f"  {len(candidatos)} candidatos relevantes, inéditos e intercalados por tema")

    # triagem editorial barata: só vira matéria o que o editor-IA considera que vale a pena
    try:
        avaliados = avaliar_e_filtrar(candidatos)
    except CotaIAExcedida as e:
        print(f"  [cota] triagem sem cota agora ({e}) — esperando a próxima execução.")
        return
    if avaliados is None:
        print("  [triagem] não foi possível avaliar agora — esperando a próxima execução.")
        return
    candidatos = [c for c, _ in avaliados]
    if not candidatos:
        print("  [triagem] nenhuma notícia boa o bastante por enquanto — esperando a próxima.")
        return
    print(f"  {len(candidatos)} notícia(s) aprovada(s) na triagem (melhor nota primeiro)")

    artigos_publicados = carregar_artigos_publicados()

    publicados = 0
    tentativas_ia = 0
    categorias_usadas_nesta_execucao = set()

    for candidato in candidatos:
        if publicados >= config.MAX_ARTIGOS_POR_EXECUCAO:
            break
        if tentativas_ia >= config.MAX_TENTATIVAS_IA_POR_EXECUCAO:
            print(f"  [limite] {tentativas_ia} tentativas de geração nesta execução — "
                  f"parando por aqui pra preservar cota das próximas horas.")
            break

        # GDELT só dá metadado (sem resumo) — pula se não tiver material mínimo
        if candidato["tipo"] == "metadado" and not candidato.get("titulo"):
            continue

        tentativas_ia += 1
        try:
            materia_relacionada = encontrar_materia_relacionada(candidato, artigos_publicados)
            materia = gerar_materia(candidato, materia_relacionada)
        except CotaIAExcedida as e:
            print(f"  [cota] limite gratuito da IA atingido nesta janela ({e}). "
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
            # mas a IA pode classificar diferente do estimado
            print(f"  [pulado] '{materia.get('titulo')}' — tema '{categoria}' já usado nesta execução")
            continue

        pais = materia.get("pais") or "América Latina"
        ultimo_pais_publicado = artigos_publicados[0]["pais"] if artigos_publicados else None
        if pais == ultimo_pais_publicado and not materia.get("prioridade_maxima"):
            # trava de verdade: usa o país que a IA realmente escolheu
            # (a intercalação por país só reduz a CHANCE de chegar aqui,
            # não garante — a IA pode classificar diferente do chute).
            # Não marca como visto: o candidato pode virar matéria ótima
            # assim que o país do topo mudar (próximo candidato agora, ou
            # próxima execução).
            print(f"  [país repetido] '{materia.get('titulo')}' é do mesmo país do último "
                  f"publicado ({pais}) e não é prioridade máxima — pulando pra variar os países.")
            continue

        resultado_check = checar_originalidade(materia, candidato)
        if not resultado_check["aprovado"]:
            print(f"  [revisão] '{materia.get('titulo')}' sinalizado: {resultado_check['detalhes']}")
            enviar_para_revisao(materia, candidato, resultado_check["detalhes"])
            continue

        imagem = buscar_imagem_relevante(materia, artigos_publicados)
        artigo = publicar(materia, candidato, imagem, materia_relacionada)
        artigos_publicados.insert(0, artigo)
        orcamento_ia.registrar_post()
        categorias_usadas_nesta_execucao.add(categoria)
        publicados += 1
        print(f"  [publicado] {artigo['titulo']} — {categoria} — {pais}")

    print(f"Concluído: {publicados} artigo(s) publicado(s) nesta execução.")


if __name__ == "__main__":
    rodar()

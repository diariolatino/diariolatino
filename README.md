# Diário Latino — pipeline automatizado

Portal de notícias com curadoria geopolítica brasileira, publicado sozinho
via GitHub Actions, $0 de custo.

## Como colocar pra rodar (passo a passo)

### 1. Criar o repositório
Suba esta pasta inteira num repositório novo no GitHub (pode ser privado).

### 2. Ativar o GitHub Pages (pra servir o site)
Settings → Pages → Source: "Deploy from a branch" → branch `main`, pasta `/site`.
Depois de alguns minutos o site fica em `https://SEU-USUARIO.github.io/SEU-REPO/`
(ou no domínio próprio, se você configurar `diariolatino.com.br` como custom domain
nessa mesma tela).

### 3. Conseguir as duas chaves gratuitas

**Gemini (Google AI Studio)**
1. Acesse https://aistudio.google.com/apikey
2. Crie uma chave gratuita (tier gratuito, sem cartão de crédito)
3. Copie a chave

**Pexels**
1. Acesse https://www.pexels.com/api/
2. Crie uma conta e peça sua chave de API (aprovação é praticamente instantânea)
3. Copie a chave

### 4. Guardar as chaves como Secrets no GitHub
No repositório: Settings → Secrets and variables → Actions → New repository secret
- `GEMINI_API_KEY` → cole a chave do Gemini
- `PEXELS_API_KEY` → cole a chave do Pexels

**Nunca** coloque essas chaves direto no código.

### 5. Rodar pela primeira vez
Vá na aba **Actions** do repositório → workflow "Publicar notícias Diário Latino"
→ "Run workflow" (isso dispara manualmente, sem esperar a próxima hora cheia).

Se tudo estiver certo, em 1–2 minutos o `site/data/articles.json` vai ser
atualizado com os primeiros artigos e o site (via GitHub Pages) vai mostrar
as notícias.

Depois disso, o workflow roda sozinho a cada hora (`cron: "0 * * * *"` no
arquivo `.github/workflows/publicar.yml`).

## Como testar localmente (opcional, antes de subir pro GitHub)

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="sua_chave"
export PEXELS_API_KEY="sua_chave"
python -m pipeline.main
```

Depois abra `site/index.html` num servidor local simples (o `fetch` do
articles.json não funciona abrindo o arquivo direto no navegador via
`file://`):

```bash
cd site && python3 -m http.server 8000
# depois abra http://localhost:8000
```

## O que o pipeline faz a cada execução (resumo)

1. Coleta metadados no **GDELT** (aberto) e título+resumo na **Agência
   Brasil** (CC BY 2.5) — nunca copia texto de jornal fechado.
2. Filtra por relevância geopolítica (Brics, Mercosul, América Latina etc).
3. Ignora o que já foi publicado antes (`seen_ids.json`).
4. Pede pro Gemini extrair fatos e escrever uma matéria original (até
   `MAX_ARTIGOS_POR_EXECUCAO`, hoje 3, pra não estourar cota gratuita).
5. Roda o checador de similaridade (`difflib`, sempre; embeddings, se
   `USAR_EMBEDDING_CHECK=true`). Se ficar parecido demais com a fonte,
   vai pra `review_queue.json` em vez de publicar.
6. Busca imagem no Pexels, evitando repetir as últimas 20 usadas
   (`used_images.json`), e guarda o crédito do fotógrafo.
7. Grava tudo em `site/data/articles.json`, que o site lê direto — sem
   banco de dados, sem servidor.

## Coisas que ainda dependem de você (não são automáticas)

- **`review_queue.json`**: precisa ser revisado manualmente de vez em
  quando — artigos que caíram ali não foram publicados.
- **Comunicados oficiais (Itamaraty, Mercosul, cúpulas do Brics)**: ainda
  não têm um coletor automático neste pipeline (cada órgão tem seu próprio
  formato de site, sem feed padronizado) — hoje é um coletor a menos, pode
  ser adicionado depois seguindo o mesmo padrão de `sources_rss.py`.
- **Licença de outras agências oficiais latino-americanas** (Andina,
  Prensa Latina etc.): já verificamos que a maioria é fechada — por isso
  não entraram como fonte de conteúdo, só a Agência Brasil.
- **Ativar `USAR_EMBEDDING_CHECK`**: deixa a checagem de originalidade mais
  forte, mas deixa a Action mais lenta (baixa um modelo na primeira vez).
  Ative no `publicar.yml` quando quiser essa camada extra.

# Diario Latino
 
Portal de notícias da América Latina, com recorte geopolítico do Sul. Cobre política, economia, diplomacia, segurança e sociedade da região — Brics, Mercosul, G20, Celac — em português, espanhol e inglês.
 
O site não tem redação no sentido clássico. A cada hora, um pipeline coleta pauta pública, pede a uma IA que escreva uma matéria original a partir só de título e resumo, checa se o texto não copia a fonte, ilustra com foto licenciada e publica. Sem banco de dados, sem servidor de aplicação: o resultado vira HTML estático.
 
Site: https://diariolatino.com.br
 
## O que é (e o que não é)
 
Diario Latino é um jornal digital automatizado sobre a América Latina, escrito sob a perspectiva da própria região — não um agregador de manchetes, nem um clone de agência.
 
O texto publicado é sempre uma matéria nova. O pipeline nunca recebe o texto integral de jornal fechado. As únicas fontes que viram insumo de conteúdo são:
 
- **GDELT** — metadados abertos (título, veículo, link). Sem corpo da matéria original.
- **Agência Brasil** — título e resumo, licença CC BY 2.5, com crédito. Itens assinados por Reuters (e equivalentes bloqueados no feed) são descartados.
 
Feeds da BBC, MercoPress, Al Jazeera, DW e outros entram só como **radar de manchete**: sinalizam que algo aconteceu. Esse texto nunca vai para o gerador.
 
Cada matéria sai com selo de que foi redigida com auxílio de IA, a partir de fontes verificadas, e com o link da fonte original no rodapé.
 
## Como o site funciona
 
A pasta `site/` é o jornal inteiro: HTML, CSS e JavaScript estáticos. A home lê `site/data/articles.json` (índice enxuto, sem o corpo das matérias). Abrir uma notícia busca `site/data/artigos/<id>.json`, com texto completo e traduções.
 
Não há CMS, API nem banco. Publicar é commitar JSON no repositório. O frontend faz o resto: categorias, busca, filtro por país, paginação, seletor de idioma (pt / es / en) e tempo de leitura.
 
O site pode ser servido por qualquer host estático. No GitHub Pages a pasta publicada é `/site`. Na Vercel, o Root Directory do projeto precisa ser `site` — o `requirements.txt` na raiz é do pipeline, não de um app Python.
 
## Como nasce uma notícia
 
O workflow `.github/workflows/publicar.yml` roda a cada hora (UTC) e também pode ser disparado na aba Actions.
 
1. **Coleta** candidatos no GDELT e nos RSS da Agência Brasil.
2. **Filtra** por relevância geopolítica (América Latina, Brics, Mercosul, diplomacia, comércio, segurança etc.).
3. **Descarta** o que já foi visto (`site/data/seen_ids.json`) e intercala tema e país para a cobertura não ficar presa num só lugar.
4. **Gera** a matéria com a Groq: fatos extraídos do título/resumo, texto original em português, traduções para espanhol latino-americano e inglês, categoria, país e termos de busca da foto. No máximo 1 artigo por execução (e poucas tentativas de IA), para não estourar cota gratuita.
5. **Deduplica**. Se for o mesmo fato de uma matéria recente, só publica se houver desdobramento novo — e o título deixa isso explícito. Sem fato novo, descarta.
6. **Checa originalidade** contra o material de origem (`difflib`; embeddings são opcionais). Texto demais parecido vai para `site/data/review_queue.json` e não entra no ar.
7. **Ilustra** com Pexels, Pixabay, Unsplash ou Openverse, evitando repetir foto recente, e guarda crédito do fotógrafo.
8. **Grava** o arquivo da matéria, atualiza o índice e commita `site/data` de volta no repositório. A Vercel ou o GitHub Pages republicam sozinhos.
 
Travas extras: não publica duas matérias do mesmo tema na mesma hora; não publica dois países iguais em sequência, salvo fato de prioridade máxima (golpe, morte de chefe de Estado, catástrofe etc.). Notícia antiga nunca é apagada.
 
## Estrutura do repositório
 
```
pipeline/                 coleta, filtro, geração, checagem e publicação
site/                     o jornal (HTML/CSS/JS estático)
  data/articles.json      índice de todas as matérias (sem corpo)
  data/artigos/           uma matéria por arquivo, com texto e traduções
  data/seen_ids.json      candidatos já processados
  data/review_queue.json  textos retidos por similaridade
.github/workflows/        publicação automática de hora em hora
```
 
O código do jornal está em `site/index.html`, `site/artigo.html`, `site/header.js`, `site/i18n.js` e `site/styles.css`. A lógica editorial está em `pipeline/`.
 
## Rodar o pipeline localmente
 
O site em si não precisa de build. O pipeline sim, se você quiser gerar notícia na máquina:
 
```bash
pip install -r requirements.txt
export GROQ_API_KEY="sua_chave"
export PEXELS_API_KEY="sua_chave"
python -m pipeline.main
```
 
Pexels é opcional se houver Pixabay, Unsplash ou só Openverse. Groq não é: sem `GROQ_API_KEY` o pipeline não escreve.
 
Para ver o site:
 
```bash
python3 -m http.server 8000 --directory site
```
 
Abrir o HTML direto pelo `file://` quebra o `fetch` do JSON.
 
Chaves de produção ficam em GitHub Secrets (`GROQ_API_KEY`, `PEXELS_API_KEY`). Nunca no código.
 
## O que ainda é manual
 
- `review_queue.json` — matérias que o checador reteve. Não entram no ar sozinhas.
- Comunicados oficiais (Itamaraty, Mercosul, cúpulas do Brics) — ainda não há coletor; cada órgão tem site próprio, sem feed padronizado.
- Outras agências oficiais da região (Andina, Prensa Latina etc.) — licença fechada, por isso não viram fonte de texto.

name: Reparar imagens dos posts

on:
  workflow_dispatch:
  schedule:
    - cron: "30 6 * * *"

concurrency:
  group: publicar-noticias
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  reparar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install requests
      - name: Reparar imagens
        env:
          REPARO_FORCAR: ${{ github.event_name == 'workflow_dispatch' && '1' || '' }}   # rodada manual ignora a espera de 20h
        run: python -m pipeline.reparar_imagens
      - name: Commit
        run: |
          git config user.name "diario-latino-bot"
          git config user.email "bot@users.noreply.github.com"
          python3 -c "import json; json.load(open('site/data/articles.json', encoding='utf-8'))" || { echo "articles.json inválido — NÃO vou commitar" >&2; exit 1; }
          git add site/data
          if git diff --cached --quiet; then echo "Nada a commitar"; exit 0; fi
          git commit -m "Reparo automático de imagens"
          for i in 1 2 3; do
            git pull --rebase && python3 -c "import json; json.load(open('site/data/articles.json', encoding='utf-8'))" && git push && exit 0
            sleep 5
          done
          exit 1

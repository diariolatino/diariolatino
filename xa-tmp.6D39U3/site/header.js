/* ============================================================
   Diário Latino — cabeçalho compartilhado (topbar + masthead)
   ------------------------------------------------------------
   Um único lugar pra manter a home e todas as outras páginas
   com o mesmo header, sempre — sem precisar copiar/colar HTML.

   Como usar numa página nova:
   1. Coloque um <div id="cabecalho-app"></div> onde o header deve
      aparecer (no lugar do <div class="topbar"> + <header class="masthead">).
   2. Inclua <script src="header.js"></script> antes do script da página.
   3. Chame montarCabecalho() como a primeira coisa dentro de iniciar(),
      antes de aplicarTextosEstaticos() (que preenche os textos do header).
   ============================================================ */

function montarCabecalho() {
  const alvo = document.getElementById('cabecalho-app');
  if (!alvo) return;

  alvo.innerHTML = `
    <div class="topbar">
      <div class="wrap">
        <span class="edicao" id="edicao-local"></span>
        <div class="topbar-direita">
          <div class="seletor-idioma" id="seletor-idioma-topo"></div>
        </div>
      </div>
    </div>

    <header class="masthead">
      <div class="kicker" id="masthead-kicker"></div>
      <div class="masthead-titulo">
        <a href="index.html" class="masthead-link">
          <img src="diariolatino-logo.png" alt="Diário Latino" class="masthead-logo masthead-logo--home">
          <h1>Diário Latino</h1>
        </a>
      </div>
      <div class="tagline" id="masthead-tagline"></div>
    </header>
  `;
}

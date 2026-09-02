let TODOS_ARTIGOS = [];
    let CATEGORIA_ATIVA = "todas";
    let FILTRO_LOCAL = { tipo: "todos", valor: null };
    let TERMO_BUSCA = "";
    
    function figuraImagem(imagem, artigo) {
      if (!imagem) return "";
      const foto = artigo
        ? `<a href="${linkMateria(artigo)}"><img src="${imagem.url}" alt="" loading="lazy"></a>`
        : `<img src="${imagem.url}" alt="" loading="lazy">`;
      const nomeFonte = imagem.fonte_nome || 'Pexels';
      const linkFonte = imagem.fonte_url || imagem.pexels_url;
      return `${foto}
        <figcaption class="credito-foto">Foto: <a href="${imagem.photographer_url}" target="_blank" rel="noopener">${imagem.photographer}</a> / <a href="${linkFonte}" target="_blank" rel="noopener">${nomeFonte}</a><br>${t('notaIlustrativa')}</figcaption>`;
    }
    
    function linkMateria(artigo) {
      return `artigo.html?id=${encodeURIComponent(artigo.id)}`;
    }
    
    function linkFontes(artigo) {
      const nomes = (artigo.fontes && artigo.fontes.length) ? artigo.fontes.join(' · ') : t('fontes');
      if (artigo.url_fonte_original) {
        return `${t('fontes')}: <a class="link-fonte" href="${artigo.url_fonte_original}" target="_blank" rel="noopener">${nomes}</a>`;
      }
      return `${t('fontes')}: ${nomes}`;
    }
    
    function aplicarTextosEstaticos() {
      document.getElementById('edicao-local').textContent = `${t('edicaoLocal')} · ${dataEdicaoCompleta()}`;
      document.getElementById('masthead-kicker').textContent = t('kicker');
      document.getElementById('masthead-tagline').textContent = t('tagline');
      document.getElementById('estado-vazio').textContent = t('estadoVazio');
      document.getElementById('sem-resultados').textContent = t('semResultados');
      document.getElementById('titulo-ultimas').textContent = t('ultimas');
      document.getElementById('titulo-mais-noticias').textContent = t('maisNoticias');
      document.getElementById('campo-busca').placeholder = t('buscarPlaceholder');
      document.getElementById('footer-desc').textContent = t('footerDesc');
      document.getElementById('footer-secoes-titulo').textContent = t('footerSecoes');
      document.getElementById('footer-transparencia-titulo').textContent = t('footerTransparencia');
      document.getElementById('footer-ia').textContent = t('footerIa');
      document.getElementById('footer-fontes').textContent = t('footerFontes');
      document.getElementById('footer-referencia').textContent = t('footerReferencia');
      document.getElementById('footer-imagens').textContent = t('footerImagens');
      document.getElementById('footer-dev-linha').innerHTML = `${t('footerDev')} <a href="https://hefezzia.com.br" style="border-bottom:1px dotted rgba(244,243,239,0.6);">Hefezzia</a>`;
    
      document.querySelectorAll('.footer-secao-item').forEach((el) => {
        el.textContent = traduzirCategoria(el.dataset.pt);
      });
    }
    
    function montarNavCategorias() {
      const container = document.getElementById('lista-categorias');
      const itens = [`<li><button type="button" class="categoria-link${CATEGORIA_ATIVA === 'todas' ? ' ativo' : ''}" data-categoria="todas">${t('todas')}</button></li>`]
        .concat(CATEGORIAS_ORDEM.map(cat => `
          <li><button type="button" class="categoria-link${CATEGORIA_ATIVA === cat ? ' ativo' : ''}" data-categoria="${cat}">${traduzirCategoria(cat)}</button></li>
        `));
      container.innerHTML = itens.join('');
    
      container.querySelectorAll('.categoria-link').forEach(btn => {
        btn.addEventListener('click', () => {
          CATEGORIA_ATIVA = btn.dataset.categoria;
          window.location.hash = CATEGORIA_ATIVA === 'todas' ? '' : encodeURIComponent(CATEGORIA_ATIVA);
          montarNavCategorias();
          renderizarConteudo();
        });
      });
    }

    function montarFiltroPais() {
      const dropdown = document.getElementById('filtro-pais-dropdown');
      const botao = document.getElementById('filtro-pais-botao');
      const painel = document.getElementById('filtro-pais-painel');

      botao.classList.toggle('ativo', FILTRO_LOCAL.tipo !== 'todos');
      botao.title = FILTRO_LOCAL.tipo === 'pais' ? traduzirPais(FILTRO_LOCAL.valor)
        : FILTRO_LOCAL.tipo === 'regiao' ? traduzirRegiao(FILTRO_LOCAL.valor)
        : t('filtroPaisTodos');

      const itemTodos = `
        <button type="button" class="filtro-pais-item filtro-pais-item--todos${FILTRO_LOCAL.tipo === 'todos' ? ' ativo' : ''}" data-tipo="todos">${t('filtroPaisTodos')}</button>`;

      const grupos = REGIOES_ORDEM.map(regiao => `
        <div class="filtro-pais-grupo">
          <button type="button" class="filtro-pais-regiao${FILTRO_LOCAL.tipo === 'regiao' && FILTRO_LOCAL.valor === regiao ? ' ativo' : ''}" data-tipo="regiao" data-valor="${regiao}">${traduzirRegiao(regiao)}</button>
          ${PAISES_POR_REGIAO[regiao].map(pais => `
            <button type="button" class="filtro-pais-item${FILTRO_LOCAL.tipo === 'pais' && FILTRO_LOCAL.valor === pais ? ' ativo' : ''}" data-tipo="pais" data-valor="${pais}">${traduzirPais(pais)}</button>
          `).join('')}
        </div>`).join('');

      painel.innerHTML = itemTodos + grupos;

      painel.querySelectorAll('[data-tipo]').forEach(el => {
        el.addEventListener('click', () => {
          const tipo = el.dataset.tipo;
          FILTRO_LOCAL = tipo === 'todos' ? { tipo: 'todos', valor: null } : { tipo, valor: el.dataset.valor };
          fecharFiltroPais();
          montarFiltroPais();
          renderizarConteudo();
        });
      });

      if (!botao.dataset.ligado) {
        botao.dataset.ligado = '1';
        botao.addEventListener('click', (e) => {
          e.stopPropagation();
          const aberto = dropdown.classList.toggle('aberto');
          botao.setAttribute('aria-expanded', aberto ? 'true' : 'false');
        });
        document.addEventListener('click', (e) => {
          if (!dropdown.contains(e.target)) fecharFiltroPais();
        });
        document.addEventListener('keydown', (e) => {
          if (e.key === 'Escape') fecharFiltroPais();
        });
      }
    }

    function fecharFiltroPais() {
      const dropdown = document.getElementById('filtro-pais-dropdown');
      dropdown.classList.remove('aberto');
      document.getElementById('filtro-pais-botao').setAttribute('aria-expanded', 'false');
    }
    
    function artigosFiltrados() {
      let lista = TODOS_ARTIGOS;
      if (CATEGORIA_ATIVA !== 'todas') {
        lista = lista.filter(a => a.categoria === CATEGORIA_ATIVA);
      }
      if (FILTRO_LOCAL.tipo === 'pais') {
        lista = lista.filter(a => a.pais === FILTRO_LOCAL.valor);
      } else if (FILTRO_LOCAL.tipo === 'regiao') {
        const paisesDaRegiao = PAISES_POR_REGIAO[FILTRO_LOCAL.valor] || [];
        lista = lista.filter(a => paisesDaRegiao.includes(a.pais));
      }
      if (TERMO_BUSCA.trim()) {
        const termo = TERMO_BUSCA.trim().toLowerCase();
        lista = lista.filter(a => {
          const titulo = (campoIdioma(a, 'titulo') || '').toLowerCase();
          const lead = (campoIdioma(a, 'lead') || '').toLowerCase();
          return titulo.includes(termo) || lead.includes(termo);
        });
      }
      return lista;
    }
    
    function renderizarConteudo() {
      const artigos = artigosFiltrados();
    
      document.getElementById('estado-vazio').style.display = 'none';
      document.getElementById('sem-resultados').style.display = 'none';
      document.getElementById('secao-destaque').style.display = 'none';
      document.getElementById('secao-mosaico').style.display = 'none';
      document.getElementById('secao-digest').style.display = 'none';
      document.getElementById('secao-radar').style.display = 'none';
      document.getElementById('secao-grade').innerHTML = '';
    
      if (!TODOS_ARTIGOS.length) {
        document.getElementById('estado-vazio').style.display = 'block';
        return;
      }
      if (!artigos.length) {
        document.getElementById('sem-resultados').style.display = 'block';
        return;
      }
    
      const [principal, ...resto] = artigos;
    
      document.getElementById('secao-destaque').style.display = 'grid';
      document.getElementById('destaque-categoria').textContent = rotuloCategoriaPais(principal);
      document.getElementById('destaque-figura').innerHTML = figuraImagem(principal.imagem, principal);
      document.getElementById('destaque-titulo').innerHTML = `<a class="link-esticado" href="${linkMateria(principal)}">${campoIdioma(principal, 'titulo')}</a>`;
      document.getElementById('destaque-lead').textContent = campoIdioma(principal, 'lead');
      document.getElementById('destaque-redacao').textContent = t('redacao');
      document.getElementById('destaque-data').textContent = formatarData(principal.publicado_em);
      document.getElementById('destaque-fontes').innerHTML = linkFontes(principal);
    
      const ultimas = resto.slice(0, 5);
      document.getElementById('lista-ultimas').innerHTML = ultimas.map(a => `
        <div class="item-ultima">
          ${a.imagem ? `<a class="item-ultima-foto" href="${linkMateria(a)}"><img src="${a.imagem.url}" alt="" loading="lazy"></a>` : ''}
          <div class="item-ultima-corpo">
            <span class="selo">${rotuloCategoriaPais(a)}</span>
            <h4><a class="link-esticado" href="${linkMateria(a)}">${campoIdioma(a, 'titulo')}</a></h4>
            <div class="hora">${formatarData(a.publicado_em)}</div>
          </div>
        </div>`).join('');
    
      const grade = resto.slice(5, 29);
      document.getElementById('secao-grade').innerHTML = grade.map(a => `
        <article class="coluna">
          <span class="selo">${rotuloCategoriaPais(a)}</span>
          ${a.imagem ? `<a href="${linkMateria(a)}"><img src="${a.imagem.url}" alt="" loading="lazy"></a>` : ''}
          <h3><a class="link-esticado" href="${linkMateria(a)}">${campoIdioma(a, 'titulo')}</a></h3>
          <p class="dek">${campoIdioma(a, 'lead')}</p>
          <div class="meta"><span>${formatarData(a.publicado_em)}</span></div>
        </article>`).join('');
    
      // ===== MOSAICO (opção B): grande + linha + 3 sem foto + linha + grande =====
      const mosaico = resto.slice(29, 34);
      const elMosaico = document.getElementById('secao-mosaico');
      if (mosaico.length) {
        elMosaico.style.display = 'grid';
        const grandeEsq = mosaico[0];
        const grandeDir = mosaico.length > 1 ? mosaico[mosaico.length - 1] : null;
        const meio = mosaico.length > 2 ? mosaico.slice(1, mosaico.length - 1) : [];

        const materiaGrande = a => `
          <span class="selo">${rotuloCategoriaPais(a)}</span>
          ${a.imagem ? `<a href="${linkMateria(a)}"><img src="${a.imagem.url}" alt="" loading="lazy"></a>` : ''}
          <h3><a class="link-esticado" href="${linkMateria(a)}">${campoIdioma(a, 'titulo')}</a></h3>
          <p class="dek">${campoIdioma(a, 'lead')}</p>
          <div class="meta"><span>${formatarData(a.publicado_em)}</span></div>`;

        document.getElementById('mosaico-esquerda').innerHTML = materiaGrande(grandeEsq);

        const elMeio = document.getElementById('mosaico-meio');
        elMeio.style.display = meio.length ? 'flex' : 'none';
        elMeio.innerHTML = meio.map(a => `
          <div class="mosaico-item">
            <span class="selo">${rotuloCategoriaPais(a)}</span>
            <h4><a class="link-esticado" href="${linkMateria(a)}">${campoIdioma(a, 'titulo')}</a></h4>
            <div class="hora">${formatarData(a.publicado_em)}</div>
          </div>`).join('');

        const elDireita = document.getElementById('mosaico-direita');
        if (grandeDir) {
          elDireita.style.display = 'block';
          elDireita.innerHTML = materiaGrande(grandeDir);
        } else {
          elDireita.style.display = 'none';
        }
      } else {
        elMosaico.style.display = 'none';
      }
    
      // ===== DIGEST (opção A): lista compacta com foto, 5 linhas x 3 =====
      const digest = resto.slice(34, 49);
      const elDigest = document.getElementById('secao-digest');
      if (digest.length) {
        elDigest.style.display = 'block';
        document.getElementById('digest-grade').innerHTML = digest.map(a => `
          <div class="digest-item">
            ${a.imagem ? `<a class="digest-foto" href="${linkMateria(a)}"><img src="${a.imagem.url}" alt="" loading="lazy"></a>` : ''}
            <div class="digest-corpo">
              <span class="selo">${rotuloCategoriaPais(a)}</span>
              <h4><a class="link-esticado" href="${linkMateria(a)}">${campoIdioma(a, 'titulo')}</a></h4>
              <div class="hora">${formatarData(a.publicado_em)}</div>
            </div>
          </div>`).join('');
      } else {
        elDigest.style.display = 'none';
      }
    
      const maisNoticias = resto.slice(49);
      if (maisNoticias.length) {
        document.getElementById('secao-radar').style.display = 'block';
        document.getElementById('radar-lista').innerHTML = maisNoticias.map(a => `
          <a class="radar-item" href="${linkMateria(a)}"><span class="pais">${a.pais ? traduzirPais(a.pais) : traduzirCategoria(a.categoria)}</span>${campoIdioma(a, 'titulo')}</a>`).join('');
      }
    }
    
    async function carregarArtigos() {
      try {
        const resp = await fetch('data/articles.json', { cache: 'no-store' });
        if (resp.ok) TODOS_ARTIGOS = await resp.json();
      } catch (e) {
        console.error('Falha ao carregar articles.json', e);
      }
    }
    
    function inicializarBusca() {
      const campo = document.getElementById('campo-busca');
      let temporizador;
      campo.addEventListener('input', () => {
        clearTimeout(temporizador);
        temporizador = setTimeout(() => {
          TERMO_BUSCA = campo.value;
          renderizarConteudo();
        }, 150);
      });
    }
    
    function inicializarVoltarTopo() {
      const botao = document.getElementById('voltar-topo');
      window.addEventListener('scroll', () => {
        botao.classList.toggle('visivel', window.scrollY > 500);
      });
      botao.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
    }
    
    async function iniciar() {
      const hash = decodeURIComponent(window.location.hash.replace('#', ''));
      if (hash && CATEGORIAS_ORDEM.includes(hash)) CATEGORIA_ATIVA = hash;
    
      montarCabecalho();
      aplicarTextosEstaticos();
      montarSeletorIdioma(document.getElementById('seletor-idioma-topo'), () => {
        aplicarTextosEstaticos();
        montarNavCategorias();
        montarFiltroPais();
        renderizarConteudo();
      });
      montarNavCategorias();
      montarFiltroPais();
      await carregarArtigos();
      renderizarConteudo();
      inicializarBusca();
      inicializarVoltarTopo();
      document.getElementById('ano-copyright').textContent = new Date().getFullYear();
    }
    
    iniciar();

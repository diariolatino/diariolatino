/* ============================================================
   Diário Latino — i18n compartilhado (pt / es / en)
   ============================================================ */

const IDIOMAS = ["pt", "es", "en"];
const IDIOMA_PADRAO = "pt";

const NOMES_IDIOMA = { pt: "PT", es: "ES", en: "EN" };

const I18N = {
  pt: {
    kicker: "Uma só América Latina",
    tagline: "Notícias e geopolítica sob a perspectiva do Sul",
    edicaoLocal: "Rio de Janeiro",
    todas: "Todas",
    buscarPlaceholder: "Buscar matérias…",
    filtroPaisTodos: "Todos os países",
    ultimas: "Últimas",
    maisNoticias: "Mais notícias",
    leiaTambem: "Continue lendo",
    redacao: "Redação Diário Latino",
    estadoVazio: "Ainda não há notícias publicadas. O pipeline roda a cada hora — volte em breve.",
    semResultados: "Nenhuma matéria encontrada para esse filtro.",
    fontes: "Fontes",
    voltar: "← Voltar para a home",
    naoEncontrada: "Matéria não encontrada.",
    carregando: "Carregando matéria…",
    compartilhar: "Compartilhar",
    copiarLink: "Copiar link",
    linkCopiado: "Link copiado!",
    minLeitura: "min de leitura",
    topo: "Voltar ao topo",
    footerDesc: "Portal de notícias independente com curadoria geopolítica sob a perspectiva latino-americana — América Latina, Sul Global, Brics e relações internacionais.",
    footerSecoes: "Seções",
    footerTransparencia: "Transparência",
    footerIa: "Conteúdo redigido com auxílio de inteligência artificial, a partir de fontes verificadas",
    footerFontes: "Fontes: Agência Brasil, GDELT, comunicados oficiais de governos da América Latina",
    footerReferencia: "Referência linguística: ASALE (Associação de Academias da Língua Espanhola)",
    footerImagens: "Imagens: Pexels, com crédito ao fotógrafo em cada matéria",
    footerDev: "Desenvolvido por",
    notaIlustrativa: "Imagem meramente ilustrativa.",
    categorias: {
      "Política": "Política",
      "Economia": "Economia",
      "Mundo": "Mundo",
      "Segurança": "Segurança",
      "Mercosul": "Mercosul",
      "Sociedade": "Sociedade",
      "Ciência & Ambiente": "Ciência & Ambiente",
    },
  },
  es: {
    kicker: "Una sola América Latina",
    tagline: "Noticias y geopolítica desde la perspectiva del Sur",
    edicaoLocal: "Río de Janeiro",
    todas: "Todas",
    buscarPlaceholder: "Buscar noticias…",
    filtroPaisTodos: "Todos los países",
    ultimas: "Últimas",
    maisNoticias: "Más noticias",
    leiaTambem: "Sigue leyendo",
    redacao: "Redacción Diário Latino",
    estadoVazio: "Todavía no hay noticias publicadas. El proceso se ejecuta cada hora — vuelve pronto.",
    semResultados: "No se encontraron noticias para ese filtro.",
    fontes: "Fuentes",
    voltar: "← Volver al inicio",
    naoEncontrada: "Noticia no encontrada.",
    carregando: "Cargando noticia…",
    compartilhar: "Compartir",
    copiarLink: "Copiar enlace",
    linkCopiado: "¡Enlace copiado!",
    minLeitura: "min de lectura",
    topo: "Volver arriba",
    footerDesc: "Portal de noticias independiente con curaduría geopolítica desde una perspectiva latinoamericana — América Latina, Sur Global, Brics y relaciones internacionales.",
    footerSecoes: "Secciones",
    footerTransparencia: "Transparencia",
    footerIa: "Contenido redactado con ayuda de inteligencia artificial, a partir de fuentes verificadas",
    footerFontes: "Fuentes: Agência Brasil, GDELT, comunicados oficiales de gobiernos de América Latina",
    footerReferencia: "Referencia lingüística: ASALE (Asociación de Academias de la Lengua Española)",
    footerImagens: "Imágenes: Pexels, con crédito al fotógrafo en cada noticia",
    footerDev: "Desarrollado por",
    notaIlustrativa: "Imagen meramente ilustrativa.",
    categorias: {
      "Política": "Política",
      "Economia": "Economía",
      "Mundo": "Mundo",
      "Segurança": "Seguridad",
      "Mercosul": "Mercosur",
      "Sociedade": "Sociedad",
      "Ciência & Ambiente": "Ciencia & Ambiente",
    },
  },
  en: {
    kicker: "One Latin America",
    tagline: "News and geopolitics from a Southern perspective",
    edicaoLocal: "Rio de Janeiro",
    todas: "All",
    buscarPlaceholder: "Search stories…",
    filtroPaisTodos: "All countries",
    ultimas: "Latest",
    maisNoticias: "More stories",
    leiaTambem: "Keep reading",
    redacao: "Diário Latino Newsroom",
    estadoVazio: "No stories published yet. The pipeline runs every hour — check back soon.",
    semResultados: "No stories found for this filter.",
    fontes: "Sources",
    voltar: "← Back to home",
    naoEncontrada: "Story not found.",
    carregando: "Loading story…",
    compartilhar: "Share",
    copiarLink: "Copy link",
    linkCopiado: "Link copied!",
    minLeitura: "min read",
    topo: "Back to top",
    footerDesc: "Independent news outlet with geopolitical curation from a Latin American perspective — Latin America, the Global South, Brics and international relations.",
    footerSecoes: "Sections",
    footerTransparencia: "Transparency",
    footerIa: "Content written with the help of artificial intelligence, based on verified sources",
    footerFontes: "Sources: Agência Brasil, GDELT, official statements from Latin American governments",
    footerReferencia: "Language reference: ASALE (Association of Academies of the Spanish Language)",
    footerImagens: "Images: Pexels, with photographer credit on every story",
    footerDev: "Built by",
    notaIlustrativa: "Image for illustrative purposes only.",
    categorias: {
      "Política": "Politics",
      "Economia": "Economy",
      "Mundo": "World",
      "Segurança": "Security",
      "Mercosul": "Mercosur",
      "Sociedade": "Society",
      "Ciência & Ambiente": "Science & Environment",
    },
  },
};

const LOCALE_POR_IDIOMA = { pt: "pt-BR", es: "es-419", en: "en-US" };

function idiomaAtual() {
  const salvo = localStorage.getItem("dl_idioma");
  return IDIOMAS.includes(salvo) ? salvo : IDIOMA_PADRAO;
}

function definirIdioma(idioma) {
  if (!IDIOMAS.includes(idioma)) idioma = IDIOMA_PADRAO;
  localStorage.setItem("dl_idioma", idioma);
  return idioma;
}

function t(chave) {
  const idioma = idiomaAtual();
  return (I18N[idioma] && I18N[idioma][chave]) || I18N.pt[chave] || chave;
}

function traduzirCategoria(categoriaPt) {
  const idioma = idiomaAtual();
  const mapa = I18N[idioma] && I18N[idioma].categorias;
  return (mapa && mapa[categoriaPt]) || categoriaPt;
}

function campoIdioma(artigo, campo) {
  const idioma = idiomaAtual();
  if (idioma === "pt") return artigo[campo];
  const trad = artigo.traducoes && artigo.traducoes[idioma];
  return (trad && trad[campo]) || artigo[campo];
}

function formatarData(iso) {
  if (!iso) return "";
  const idioma = idiomaAtual();
  const locale = LOCALE_POR_IDIOMA[idioma];
  const diffMin = (Date.now() - new Date(iso).getTime()) / 60000;

  if (diffMin < 60) {
    const min = Math.max(1, Math.round(diffMin));
    if (idioma === "pt") return `há ${min} min`;
    if (idioma === "es") return `hace ${min} min`;
    return `${min} min ago`;
  }
  if (diffMin < 1440) {
    const h = Math.round(diffMin / 60);
    if (idioma === "pt") return `há ${h}h`;
    if (idioma === "es") return `hace ${h}h`;
    return `${h}h ago`;
  }
  return new Date(iso).toLocaleDateString(locale, { day: "2-digit", month: "long", year: "numeric" });
}

function dataEdicaoCompleta() {
  const idioma = idiomaAtual();
  const locale = LOCALE_POR_IDIOMA[idioma];
  const agora = new Date();
  const texto = agora.toLocaleDateString(locale, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function tempoLeitura(corpo) {
  if (!corpo) return null;
  const palavras = corpo.trim().split(/\s+/).length;
  return Math.max(1, Math.round(palavras / 200));
}

function montarSeletorIdioma(container, onTrocar) {
  if (!container) return;
  const atual = idiomaAtual();
  container.innerHTML = IDIOMAS.map(id => `
    <button type="button" class="botao-idioma${id === atual ? ' ativo' : ''}" data-idioma="${id}">${NOMES_IDIOMA[id]}</button>
  `).join('<span class="separador-idioma">/</span>');

  container.querySelectorAll(".botao-idioma").forEach(btn => {
    btn.addEventListener("click", () => {
      const novo = definirIdioma(btn.dataset.idioma);
      container.querySelectorAll(".botao-idioma").forEach(b => b.classList.toggle("ativo", b.dataset.idioma === novo));
      document.documentElement.lang = novo === "pt" ? "pt-BR" : (novo === "es" ? "es" : "en");
      if (typeof onTrocar === "function") onTrocar(novo);
    });
  });
}

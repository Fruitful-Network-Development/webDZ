(function () {
  const PAGE_SIZE = 10;

  const LOGICAL_CORPUS = [
    { type: "page", label: "Home", path: "index.html" },
    { type: "page", label: "Services", path: "services.html" },
    { type: "page", label: "Research", path: "research.html" },
    { type: "page", label: "About", path: "about.html" },
    { type: "page", label: "Contact", path: "contact.html" },
    { type: "page", label: "POS", path: "subpages/pos.html" },
    { type: "page", label: "Payment Processing", path: "subpages/payment-processing.html" },
    { type: "page", label: "Read More", path: "subpages/articles.html" },

    { type: "doc", label: "README", path: "assets/docs/README.md" },
    { type: "doc", label: "Agronomic Micro Structure", path: "assets/docs/agronomic_mirco_structure.md" },
    { type: "doc", label: "Cuyahoga Valley Countryside Initiative", path: "assets/docs/cuyahoga_valley_countryside_initiative.md" },
    { type: "doc", label: "Fiscal Sponsorship Programs and Taxes", path: "assets/docs/fiscal_sponsorship_programs_taxes.md" },
    { type: "doc", label: "Food System Value Dimensions", path: "assets/docs/food_system_value_dimentions.md" },
    { type: "doc", label: "Interoperability in Socio-Technical Networks", path: "assets/docs/interoperability_in_socio-technical_networks.md" },
    { type: "doc", label: "Market Transparency", path: "assets/docs/market_transparency.md" },
    { type: "doc", label: "Modern Models in Local Agriculture", path: "assets/docs/modern_models_in_local_agriculture.md" },
    { type: "doc", label: "Northeast Ohio Greenhouse Industry", path: "assets/docs/ne_ohio_greenhouse_industry.md" },
    { type: "doc", label: "Northeast Ohio Historic Local Food System", path: "assets/docs/ne_ohio_historic_local_food_system.md" },
    { type: "doc", label: "Open Source Competition", path: "assets/docs/opensource_competition.md" },
    { type: "doc", label: "Regenerative Farming Market Recapture", path: "assets/docs/regenerative_farming_market_recapture.md" },
    { type: "doc", label: "Rubber Made Caution Tail", path: "assets/docs/rubber_made_caution_tail.md" },
    { type: "doc", label: "Self-Describing Semantic Grammars", path: "assets/docs/self-describing_semantic_grammars.md" }
  ];

  const state = {
    indexed: [],
    indexedReady: false,
    lastResults: [],
    renderedCount: 0,
    overlay: null,
    input: null,
    summary: null,
    resultsWrap: null,
    moreWrap: null,
    moreBtn: null
  };

  const isSubpage = window.location.pathname.includes("/subpages/");
  const rootPrefix = isSubpage ? "../" : "./";
  const iconPrefix = "/assets/icon/";

  const normalizeWhitespace = (value) => value.replace(/\s+/g, " ").trim();

  const escapeHtml = (value) => value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");

  const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  const readPageText = (htmlText) => {
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlText, "text/html");
    const root = doc.querySelector("main") || doc.body;
    return normalizeWhitespace(root ? root.textContent || "" : "");
  };

  const readDocText = (docText) => normalizeWhitespace(docText.replace(/```[\s\S]*?```/g, " "));

  const tokenizeQuery = (query) => normalizeWhitespace(query)
    .toLowerCase()
    .split(" ")
    .filter((token) => token.length > 1);

  const computeSentenceSnippet = (text, index) => {
    if (index < 0 || text.length === 0) {
      return text.slice(0, 220);
    }

    const left = text.slice(0, index);
    const right = text.slice(index);

    const prevBoundary = Math.max(left.lastIndexOf("."), left.lastIndexOf("!"), left.lastIndexOf("?"));
    const nextBoundaryOffset = Math.max(right.indexOf("."), right.indexOf("!"), right.indexOf("?"));

    const start = prevBoundary >= 0 ? prevBoundary + 1 : Math.max(0, index - 120);
    const end = nextBoundaryOffset >= 0 ? index + nextBoundaryOffset + 1 : Math.min(text.length, index + 140);

    let snippet = normalizeWhitespace(text.slice(start, end));
    if (snippet.length > 260) {
      snippet = snippet.slice(0, 257) + "...";
    }
    return snippet;
  };

  const highlightTokens = (text, tokens) => {
    if (tokens.length === 0) {
      return escapeHtml(text);
    }
    const pattern = new RegExp(`(${tokens.map((token) => escapeRegExp(token)).join("|")})`, "gi");
    return escapeHtml(text).replace(pattern, "<mark>$1</mark>");
  };

  const toFetchPath = (logicalPath) => `${rootPrefix}${logicalPath}`;

  const toOpenPath = (item) => {
    if (item.type === "doc") {
      const docName = item.path.replace("assets/docs/", "");
      return `${isSubpage ? "./articles.html" : "./subpages/articles.html"}?doc=${encodeURIComponent(docName)}`;
    }
    return `${rootPrefix}${item.path}`;
  };

  const renderLocation = (item) => (item.type === "doc" ? `Article: ${item.label}` : `Page: ${item.label}`);
  const locationIcon = (item) => (item.type === "doc" ? `${iconPrefix}icon-archive.png` : `${iconPrefix}icon-webpage.png`);

  const renderResultCard = (result) => {
    const linkHref = toOpenPath(result);
    return `
      <article class="search-result-card">
        <div class="search-result-card__left">
          <h3 class="search-result-card__title"><a href="${linkHref}">${escapeHtml(result.label)}</a></h3>
          <p class="search-result-card__snippet">${highlightTokens(result.snippet, result.tokens)}</p>
        </div>
        <div class="search-result-card__right">
          <p class="search-result-card__location">
            <span class="search-result-card__location-icon ui-icon-box ui-icon-box--md ui-icon-box--muted" aria-hidden="true"><img src="${locationIcon(result)}" alt="" /></span>
            <span>${escapeHtml(renderLocation(result))}</span>
          </p>
          <p class="search-result-card__path">${escapeHtml(result.path)}</p>
        </div>
      </article>
    `;
  };

  const findMatches = (items, query) => {
    const tokens = tokenizeQuery(query);
    if (tokens.length === 0) {
      return [];
    }

    return items
      .map((item) => {
        const haystack = `${item.label} ${item.text}`.toLowerCase();
        const matches = tokens.reduce((count, token) => {
          const pattern = new RegExp(escapeRegExp(token), "g");
          const found = haystack.match(pattern);
          return count + (found ? found.length : 0);
        }, 0);

        if (matches === 0) {
          return null;
        }

        const firstToken = tokens.find((token) => haystack.includes(token)) || tokens[0];
        const firstIndex = haystack.indexOf(firstToken);
        const snippet = computeSentenceSnippet(item.text, Math.max(0, firstIndex - item.label.length));

        return { ...item, score: matches, snippet, tokens };
      })
      .filter(Boolean)
      .sort((a, b) => b.score - a.score || a.label.localeCompare(b.label));
  };

  const buildOverlay = () => {
    const wrap = document.createElement("div");
    wrap.className = "search-overlay";
    wrap.id = "site-search-overlay";
    wrap.setAttribute("aria-hidden", "true");

    wrap.innerHTML = `
      <section class="search-panel" role="dialog" aria-modal="true" aria-label="Site Search">
        <div class="search-panel__header">
          <p class="search-panel__title">Search</p>
          <button class="search-panel__close" type="button" aria-label="Close search">&times;</button>
        </div>

        <form id="site-search-form" class="search-form" role="search" aria-label="Site Search">
          <label class="search-form__label ui-label-with-icon" for="site-search-input">
            <span class="ui-icon-box ui-icon-box--sm ui-icon-box--muted" aria-hidden="true"><img src="${iconPrefix}icon-tag.png" alt="" /></span>
            Search keywords
          </label>
          <div class="search-form__row">
            <input id="site-search-input" class="search-form__input" type="search" placeholder="Try: fiscal sponsorship, volatility, POS, hosting" autocomplete="off" />
            <button class="button" type="submit">Search</button>
          </div>
        </form>

        <p id="site-search-summary" class="search-summary"></p>
        <section id="site-search-results" class="search-results" aria-live="polite"></section>

        <div id="site-search-more-wrap" class="search-more-wrap" hidden>
          <button id="site-search-more" class="button" type="button">See More</button>
        </div>
      </section>
    `;

    document.body.appendChild(wrap);

    state.overlay = wrap;
    state.input = wrap.querySelector("#site-search-input");
    state.summary = wrap.querySelector("#site-search-summary");
    state.resultsWrap = wrap.querySelector("#site-search-results");
    state.moreWrap = wrap.querySelector("#site-search-more-wrap");
    state.moreBtn = wrap.querySelector("#site-search-more");

    const closeBtn = wrap.querySelector(".search-panel__close");
    closeBtn.addEventListener("click", closeOverlay);

    wrap.addEventListener("click", (event) => {
      if (event.target === wrap) {
        closeOverlay();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && wrap.classList.contains("is-open")) {
        closeOverlay();
      }
    });

    const form = wrap.querySelector("#site-search-form");
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      runSearch(state.input.value);
    });

    state.moreBtn.addEventListener("click", renderBatch);
  };

  const openOverlay = async () => {
    if (!state.overlay) {
      buildOverlay();
    }

    state.overlay.classList.add("is-open");
    state.overlay.setAttribute("aria-hidden", "false");
    document.body.classList.add("search-open");

    state.input.focus();

    if (!state.indexedReady) {
      state.summary.textContent = "Indexing site content...";
      await indexCorpus();
      if (!state.input.value.trim()) {
        state.summary.textContent = "Search across website pages and article markdown files.";
      } else {
        runSearch(state.input.value);
      }
    }
  };

  const closeOverlay = () => {
    if (!state.overlay) {
      return;
    }
    state.overlay.classList.remove("is-open");
    state.overlay.setAttribute("aria-hidden", "true");
    document.body.classList.remove("search-open");
  };

  const renderBatch = () => {
    const next = state.lastResults.slice(state.renderedCount, state.renderedCount + PAGE_SIZE);
    if (next.length === 0) {
      state.moreWrap.hidden = true;
      return;
    }

    state.resultsWrap.insertAdjacentHTML("beforeend", next.map(renderResultCard).join(""));
    state.renderedCount += next.length;
    state.moreWrap.hidden = state.renderedCount >= state.lastResults.length;
  };

  const runSearch = (query) => {
    state.resultsWrap.innerHTML = "";
    state.renderedCount = 0;

    const trimmed = normalizeWhitespace(query);
    if (!trimmed) {
      state.summary.textContent = "Enter keywords to search pages and articles.";
      state.moreWrap.hidden = true;
      return;
    }

    state.lastResults = findMatches(state.indexed, trimmed);
    state.summary.textContent = `${state.lastResults.length} result${state.lastResults.length === 1 ? "" : "s"} for \"${trimmed}\"`;

    if (state.lastResults.length === 0) {
      state.resultsWrap.innerHTML = '<p class="search-result-empty">No matches found. Try a broader keyword.</p>';
      state.moreWrap.hidden = true;
      return;
    }

    renderBatch();
  };

  const indexCorpus = async () => {
    const indexed = await Promise.all(
      LOGICAL_CORPUS.map(async (item) => {
        const fetchPath = toFetchPath(item.path);
        try {
          const response = await fetch(fetchPath, { cache: "no-store" });
          if (!response.ok) {
            throw new Error(`Failed to read ${fetchPath}`);
          }

          const raw = await response.text();
          const text = item.type === "doc" ? readDocText(raw) : readPageText(raw);
          return { ...item, text };
        } catch (error) {
          console.warn("Search index skipped", fetchPath, error);
          return null;
        }
      })
    );

    state.indexed = indexed.filter(Boolean);
    state.indexedReady = true;
  };

  const wireHeaderSearchButtons = () => {
    const buttons = Array.from(document.querySelectorAll('.topbar__icon[aria-label="Search"]'));
    if (buttons.length === 0) {
      return;
    }

    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        if (state.overlay && state.overlay.classList.contains("is-open")) {
          closeOverlay();
        } else {
          openOverlay();
        }
      });
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    wireHeaderSearchButtons();
  });
})();

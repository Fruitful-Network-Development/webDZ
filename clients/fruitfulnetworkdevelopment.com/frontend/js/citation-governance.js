(function () {
  const TRACKING_PARAMS = new Set([
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "mc_cid",
    "mc_eid"
  ]);

  const REQUIRED_REL = ["noopener", "noreferrer", "external"];

  const isExternal = (url) => url.origin !== window.location.origin;

  const normalizeUrl = (rawUrl) => {
    try {
      const url = new URL(rawUrl, window.location.origin);
      if (!["http:", "https:"].includes(url.protocol)) {
        return rawUrl;
      }

      Array.from(url.searchParams.keys()).forEach((key) => {
        if (TRACKING_PARAMS.has(key.toLowerCase())) {
          url.searchParams.delete(key);
        }
      });

      const sorted = Array.from(url.searchParams.entries()).sort(([a], [b]) => a.localeCompare(b));
      url.search = "";
      sorted.forEach(([key, value]) => url.searchParams.append(key, value));

      if (url.pathname !== "/" && url.pathname.endsWith("/")) {
        url.pathname = url.pathname.slice(0, -1);
      }

      return url.toString();
    } catch (_err) {
      return rawUrl;
    }
  };

  const applyOutboundLinkGovernance = (root = document) => {
    const anchors = root.querySelectorAll("a[href]");
    anchors.forEach((anchor) => {
      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) {
        return;
      }

      const normalized = normalizeUrl(href);
      if (normalized !== href) {
        anchor.setAttribute("href", normalized);
      }

      let parsed;
      try {
        parsed = new URL(normalized, window.location.origin);
      } catch (_err) {
        return;
      }

      if (!isExternal(parsed)) {
        return;
      }

      const relExisting = (anchor.getAttribute("rel") || "")
        .split(/\s+/)
        .map((value) => value.trim())
        .filter(Boolean);
      const relFinal = Array.from(new Set([...relExisting, ...REQUIRED_REL]));
      anchor.setAttribute("rel", relFinal.join(" "));
      anchor.setAttribute("target", "_blank");
      anchor.dataset.linkGovernance = "external";
    });
  };

  const loadJson = async (path) => {
    const response = await fetch(path);
    if (!response.ok) {
      throw new Error(`Failed to load ${path}: ${response.status} ${response.statusText}`);
    }
    return response.json();
  };

  const loadReferences = async () => loadJson("/assets/docs/citations/references.json");
  const loadArticleReferences = async () => loadJson("/assets/docs/citations/article-references.json");

  const renderCitationMachineBlock = (mountPoint, payload) => {
    if (!mountPoint) return;
    mountPoint.innerHTML = `
      <section class="machine-citation-block" hidden aria-hidden="true" data-machine="citations">
        <h2>Evidence References</h2>
        <script type="application/json">${JSON.stringify(payload)}</script>
      </section>
    `;
  };

  window.FNDCitations = {
    normalizeUrl,
    applyOutboundLinkGovernance,
    loadReferences,
    loadArticleReferences,
    renderCitationMachineBlock
  };
})();

(() => {
  const MD_PATH = "assets/content/happennings.md";

  function slugify(raw, used) {
    let base = String(raw)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 56);
    if (!base) base = "section";
    let id = base;
    let n = 0;
    while (used.has(id)) {
      n += 1;
      id = `${base}-${n}`;
    }
    used.add(id);
    return id;
  }

  function assignHeadingIds(root) {
    const used = new Set();
    root.querySelectorAll("h1, h2, h3").forEach((h) => {
      if (!h.id) h.id = slugify(h.textContent, used);
    });
  }

  function buildToc(tocEl, bodyEl) {
    tocEl.innerHTML = "";
    const nav = document.createElement("nav");
    nav.className = "happening-toc__inner";
    nav.setAttribute("aria-label", "Sections");

    bodyEl.querySelectorAll("h2").forEach((h) => {
      const a = document.createElement("a");
      a.href = `#${h.id}`;
      a.className = "happening-toc__link";
      a.textContent = h.textContent.replace(/\s+/g, " ").trim().slice(0, 72);
      nav.appendChild(a);
    });

    tocEl.appendChild(nav);

    nav.querySelectorAll("a").forEach((a) => {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        const id = a.getAttribute("href").slice(1);
        const t = document.getElementById(id);
        if (t) {
          t.scrollIntoView({ behavior: "smooth", block: "start" });
          history.pushState(null, "", `#${id}`);
        }
      });
    });
  }

  async function init() {
    const bodyEl = document.getElementById("happeningBody");
    const tocEl = document.getElementById("happeningToc");
    if (!bodyEl) return;

    if (typeof marked === "undefined" || typeof sanitizeMdArtifacts !== "function") {
      bodyEl.innerHTML =
        "<p>Content could not load. <a href=\"assets/content/happennings.md\">Open happenings.md</a>.</p>";
      return;
    }

    try {
      const res = await fetch(MD_PATH);
      if (!res.ok) throw new Error(String(res.status));
      let md = await res.text();
      md = sanitizeMdArtifacts(md);
      bodyEl.innerHTML = marked.parse(md);
      const docTitle = bodyEl.querySelector("h1");
      if (docTitle) {
        const h2 = document.createElement("h2");
        h2.className = "prose-md__doctitle";
        h2.innerHTML = docTitle.innerHTML;
        docTitle.replaceWith(h2);
      }
    } catch {
      bodyEl.innerHTML =
        "<p class=\"card-farm\">Events content could not be loaded. Read <a href=\"assets/content/happennings.md\">happennings.md</a> directly.</p>";
      return;
    }

    assignHeadingIds(bodyEl);
    if (tocEl) buildToc(tocEl, bodyEl);

    if (location.hash) {
      const t = document.getElementById(location.hash.slice(1));
      if (t) requestAnimationFrame(() => t.scrollIntoView({ block: "start" }));
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();

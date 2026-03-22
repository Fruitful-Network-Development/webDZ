(() => {
  const MD_PATH = "assets/content/Agriculture_timeline.md";

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

  function injectHeritageFigures(root) {
    const fig = (src, alt, cap, extraClass) => {
      const wrap = document.createElement("figure");
      wrap.className = `figure figure--mounted ${extraClass || ""}`.trim();
      const img = document.createElement("img");
      img.className = "figure__img";
      img.src = src;
      img.alt = alt;
      const fc = document.createElement("figcaption");
      fc.className = "figure__cap";
      fc.textContent = cap;
      wrap.append(img, fc);
      return wrap;
    };

    const h2s = [...root.querySelectorAll("h2")];
    const find = (sub) => h2s.find((h) => h.textContent.includes(sub));

    const canal = find("Canal-era");
    if (canal) {
      canal.insertAdjacentElement(
        "afterend",
        fig(
          "assets/image/countryside/img-cvcc-historicbridge.avif",
          "Historic bridge and canal corridor",
          "Canal and rail corridors shaped the valley’s farm economy.",
          "photo--sepia"
        )
      );
    }

    const tw = find("Twentieth-century");
    if (tw) {
      tw.insertAdjacentElement(
        "afterend",
        fig(
          "assets/image/countryside/img-cvcc-historicgreenhouse.avif",
          "Historic Cleveland greenhouse",
          "Regional greenhouse and specialty crop history.",
          "photo--bw photo--taped"
        )
      );
    }

    const fp = find("Farmland preservation");
    if (fp) {
      fp.insertAdjacentElement(
        "afterend",
        fig(
          "assets/image/countryside/img-cvcc-aerialfarm.avif",
          "Aerial view of farmland in the valley",
          "Reestablished farms pursue sustainable practices.",
          "photo--desat"
        )
      );
    }
  }

  function assignIds(root) {
    const used = new Set();
    root.querySelectorAll("h1, h2, h3").forEach((h) => {
      if (!h.id) h.id = slugify(h.textContent, used);
    });

    root.querySelectorAll("p").forEach((p) => {
      const st = p.firstElementChild;
      if (!st || st.tagName !== "STRONG") return;
      const label = st.textContent.trim();
      if (!label.includes(":") || label.length < 12) return;
      p.classList.add("history-event");
      if (!p.id) p.id = slugify(label, used);
    });
  }

  function buildToc(tocEl, bodyEl) {
    tocEl.innerHTML = "";
    const nav = document.createElement("nav");
    nav.className = "history-toc__inner";
    nav.setAttribute("aria-label", "Timeline");

    const h2s = [...bodyEl.querySelectorAll("h2")];
    h2s.forEach((h) => {
      const a = document.createElement("a");
      a.href = `#${h.id}`;
      a.className = "history-toc__link history-toc__link--section";
      a.textContent = h.textContent.replace(/\s+/g, " ").trim().slice(0, 80);
      nav.appendChild(a);

      let el = h.nextElementSibling;
      while (el && el.tagName !== "H2") {
        if (el.matches?.("p.history-event")) {
          const ea = document.createElement("a");
          ea.href = `#${el.id}`;
          ea.className = "history-toc__link history-toc__link--event";
          const strong = el.querySelector("strong");
          ea.textContent = (strong?.textContent || el.textContent).replace(/\s+/g, " ").trim().slice(0, 64);
          nav.appendChild(ea);
        }
        el = el.nextElementSibling;
      }
    });

    tocEl.appendChild(nav);
  }

  function setupScrollSpy(tocEl) {
    const links = [...tocEl.querySelectorAll("a[href^='#']")];
    const targets = links
      .map((a) => document.getElementById(a.getAttribute("href").slice(1)))
      .filter(Boolean);
    if (!targets.length) return;

    const headerOffset = 130;

    function updateActive() {
      const y = window.scrollY + headerOffset;
      let current = targets[0];
      for (const t of targets) {
        if (t.offsetTop <= y) current = t;
        else break;
      }
      const id = current?.id;
      links.forEach((a) => {
        a.classList.toggle("is-active", id && a.getAttribute("href") === `#${id}`);
      });
    }

    window.addEventListener("scroll", () => requestAnimationFrame(updateActive), { passive: true });
    window.addEventListener("resize", updateActive, { passive: true });
    updateActive();

    links.forEach((a) => {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        const id = a.getAttribute("href").slice(1);
        const target = document.getElementById(id);
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "start" });
          history.pushState(null, "", `#${id}`);
          links.forEach((x) => x.classList.toggle("is-active", x === a));
        }
      });
    });
  }

  async function init() {
    const bodyEl = document.getElementById("chronoBody") || document.getElementById("historyBody");
    const tocEl = document.getElementById("chronoToc") || document.getElementById("historyToc");
    if (!bodyEl || !tocEl) return;

    if (bodyEl.id === "chronoBody") {
      bodyEl.classList.add("prose-md--chrono");
    }

    if (typeof marked === "undefined" || typeof sanitizeMdArtifacts !== "function") {
      bodyEl.innerHTML =
        "<p>Timeline could not load (missing script). <a href=\"assets/content/Agriculture_timeline.md\">Open the source markdown</a>.</p>";
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
        "<p class=\"card-farm\">The timeline could not be loaded. You can still read the <a href=\"assets/content/Agriculture_timeline.md\">source markdown file</a>.</p>";
      return;
    }

    assignIds(bodyEl);
    injectHeritageFigures(bodyEl);
    buildToc(tocEl, bodyEl);
    setupScrollSpy(tocEl);

    if (location.hash) {
      const t = document.getElementById(location.hash.slice(1));
      if (t) requestAnimationFrame(() => t.scrollIntoView({ block: "start" }));
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();

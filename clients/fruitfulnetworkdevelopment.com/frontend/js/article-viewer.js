/**
 * article-viewer.js
 * -----------------
 * Lightweight Markdown article viewer.
 *   – Fetches .md files and renders them inside a dossier-styled overlay.
 *   – Relies on css/dossier.css for presentation.
 *
 * Usage:
 *   Add links with data-article="path/to/file.md" on the articles page.
 *   Include this script with defer.
 */

/* ========================================
   SIMPLE MARKDOWN → HTML CONVERTER
   Covers: headings, bold, italic, links,
   images, blockquotes, code blocks, inline
   code, hr, ordered/unordered lists, tables.
======================================== */

const mdToHtml = (md) => {
  let html = "";
  const lines = md.split("\n");
  let i = 0;

  const escHtml = (s) =>
    s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

  /* inline formatting */
  const inline = (text) => {
    let out = escHtml(text);
    // images: ![alt](src)
    out = out.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" />');
    // links: [text](href)
    out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    // bold + italic
    out = out.replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>");
    // bold
    out = out.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    // italic
    out = out.replace(/\*(.+?)\*/g, "<em>$1</em>");
    // inline code
    out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
    return out;
  };

  while (i < lines.length) {
    const line = lines[i];

    /* --- Fenced code blocks --- */
    if (line.trimStart().startsWith("```")) {
      i++;
      let code = "";
      while (i < lines.length && !lines[i].trimStart().startsWith("```")) {
        code += escHtml(lines[i]) + "\n";
        i++;
      }
      i++; // skip closing ```
      html += `<pre><code>${code.trimEnd()}</code></pre>\n`;
      continue;
    }

    /* --- Blank line --- */
    if (line.trim() === "") {
      i++;
      continue;
    }

    /* --- Horizontal rule --- */
    if (/^---+$/.test(line.trim()) || /^\*\*\*+$/.test(line.trim())) {
      html += "<hr />\n";
      i++;
      continue;
    }

    /* --- Headings --- */
    const headMatch = line.match(/^(#{1,6})\s+(.*)/);
    if (headMatch) {
      const level = headMatch[1].length;
      html += `<h${level}>${inline(headMatch[2])}</h${level}>\n`;
      i++;
      continue;
    }

    /* --- Blockquote --- */
    if (line.trimStart().startsWith("> ") || line.trim() === ">") {
      let bqLines = [];
      while (i < lines.length && (lines[i].trimStart().startsWith("> ") || lines[i].trim() === ">" || lines[i].trim() === "")) {
        if (lines[i].trim() === "") {
          // look ahead — if next is still blockquote, keep going
          if (i + 1 < lines.length && lines[i + 1].trimStart().startsWith(">")) {
            bqLines.push("");
            i++;
            continue;
          }
          break;
        }
        bqLines.push(lines[i].replace(/^>\s?/, ""));
        i++;
      }
      const inner = bqLines.map((l) => (l.trim() === "" ? "</p><p>" : inline(l))).join(" ");
      html += `<blockquote><p>${inner}</p></blockquote>\n`;
      continue;
    }

    /* --- Table --- */
    if (line.includes("|") && i + 1 < lines.length && /^\s*\|?\s*[-:]+/.test(lines[i + 1])) {
      const parseRow = (r) =>
        r
          .split("|")
          .map((c) => c.trim())
          .filter((c) => c !== "");
      const headers = parseRow(line);
      i += 2; // skip header + separator
      let rows = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim() !== "") {
        rows.push(parseRow(lines[i]));
        i++;
      }
      html += "<table><thead><tr>";
      headers.forEach((h) => (html += `<th>${inline(h)}</th>`));
      html += "</tr></thead><tbody>";
      rows.forEach((r) => {
        html += "<tr>";
        r.forEach((c) => (html += `<td>${inline(c)}</td>`));
        html += "</tr>";
      });
      html += "</tbody></table>\n";
      continue;
    }

    /* --- Unordered list --- */
    if (/^[\s]*[-*+]\s/.test(line)) {
      html += "<ul>\n";
      while (i < lines.length && /^[\s]*[-*+]\s/.test(lines[i])) {
        html += `<li>${inline(lines[i].replace(/^[\s]*[-*+]\s/, ""))}</li>\n`;
        i++;
      }
      html += "</ul>\n";
      continue;
    }

    /* --- Ordered list --- */
    if (/^\s*\d+[.)]\s/.test(line)) {
      html += "<ol>\n";
      while (i < lines.length && /^\s*\d+[.)]\s/.test(lines[i])) {
        html += `<li>${inline(lines[i].replace(/^\s*\d+[.)]\s/, ""))}</li>\n`;
        i++;
      }
      html += "</ol>\n";
      continue;
    }

    /* --- Paragraph (default) --- */
    let para = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !lines[i].startsWith("#") &&
      !lines[i].trimStart().startsWith("```") &&
      !/^---+$/.test(lines[i].trim()) &&
      !/^[\s]*[-*+]\s/.test(lines[i]) &&
      !/^\s*\d+[.)]\s/.test(lines[i]) &&
      !lines[i].trimStart().startsWith(">")
    ) {
      para.push(lines[i]);
      i++;
    }
    if (para.length) {
      html += `<p>${para.map(inline).join(" ")}</p>\n`;
    }
  }

  return html;
};

const parseFrontMatter = (md) => {
  if (!md.startsWith("---\n")) {
    return { metadata: {}, body: md };
  }

  const end = md.indexOf("\n---\n", 4);
  if (end === -1) {
    return { metadata: {}, body: md };
  }

  const frontMatter = md.slice(4, end);
  const body = md.slice(end + 5);
  const metadata = {};

  frontMatter.split("\n").forEach((line) => {
    const idx = line.indexOf(":");
    if (idx === -1) return;

    const key = line.slice(0, idx).trim();
    let value = line.slice(idx + 1).trim();

    if (!key) return;
    if (value === "[]") {
      metadata[key] = [];
      return;
    }

    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    metadata[key] = value;
  });

  return { metadata, body };
};

const toCanonicalArticleUrl = (path) => {
  const docName = (path.split("/").pop() || "").replace(/^\/+/, "");
  return `https://www.fruitfulnetworkdevelopment.com/subpages/articles.html?doc=${encodeURIComponent(docName)}`;
};

/* ========================================
   OVERLAY MANAGEMENT
======================================== */

let overlay = null;
let viewerBody = null;
let viewerTitle = null;
let viewerMachine = null;
let docManifest = null;
let manifestRequested = false;

const loadManifest = async () => {
  if (manifestRequested) return;
  manifestRequested = true;

  try {
    const res = await fetch("../assets/docs/manifest.json");
    if (!res.ok) return;
    const payload = await res.json();
    if (payload && Array.isArray(payload.documents)) {
      docManifest = payload.documents;
    }
  } catch (_err) {
    docManifest = null;
  }
};

const buildOverlay = () => {
  const el = document.createElement("div");
  el.className = "article-overlay";
  el.id = "article-overlay";
  el.innerHTML = `
    <div class="article-viewer" role="dialog" aria-modal="true" aria-label="Article viewer">
      <div class="article-viewer__toolbar">
        <p class="article-viewer__title" id="article-viewer-title">Article</p>
        <button class="article-viewer__close" type="button" aria-label="Close article">&times;</button>
      </div>
      <div class="article-viewer__body" id="article-viewer-body"></div>
      <script id="article-machine-metadata" type="application/json" hidden>{}</script>
    </div>
  `;
  document.body.appendChild(el);

  overlay = el;
  viewerBody = el.querySelector("#article-viewer-body");
  viewerTitle = el.querySelector("#article-viewer-title");
  viewerMachine = el.querySelector("#article-machine-metadata");

  /* Close handlers */
  const closeBtn = el.querySelector(".article-viewer__close");
  const close = () => {
    overlay.classList.remove("is-open");
    document.body.style.overflow = "";
    document.body.classList.remove("has-article-open");
  };

  closeBtn.addEventListener("click", close);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) close();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && overlay.classList.contains("is-open")) close();
  });
};

const openArticle = async (path) => {
  if (!overlay) buildOverlay();
  if (!manifestRequested) loadManifest();

  viewerBody.innerHTML = '<p style="text-align:center;color:#717171;">Loading…</p>';
  viewerTitle.textContent = "Loading…";
  viewerMachine.textContent = "{}";
  overlay.classList.add("is-open");
  document.body.style.overflow = "hidden";
  document.body.classList.add("has-article-open");

  try {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const md = await res.text();
    const { metadata, body } = parseFrontMatter(md);

    /* Derive title from first H1 or filename */
    const h1Match = body.match(/^#\s+(.*)/m);
    const fallbackTitle = h1Match
      ? h1Match[1]
      : path.split("/").pop().replace(/\.md$/, "").replace(/_/g, " ");
    const manifestEntry = Array.isArray(docManifest)
      ? docManifest.find((doc) => doc.path === path.replace(/^\.\.\//, ""))
      : null;
    const title = metadata.title || manifestEntry?.title || fallbackTitle;

    viewerTitle.textContent = title;
    viewerBody.innerHTML = mdToHtml(body);
    const machinePayload = {
      title,
      slug: metadata.slug || manifestEntry?.slug || path.split("/").pop().replace(/\.md$/, ""),
      summary: metadata.summary || manifestEntry?.summary || "",
      entity_type: metadata.entity_type || manifestEntry?.entity_type || "article",
      topics: metadata.topics || manifestEntry?.topics || [],
      claims: metadata.claims || manifestEntry?.claims || [],
      source_links: metadata.source_links || manifestEntry?.source_links || [],
      last_reviewed: metadata.last_reviewed || manifestEntry?.last_reviewed || "",
      status: metadata.status || manifestEntry?.status || "active",
      related_docs: metadata.related_docs || manifestEntry?.related_docs || [],
      supports_claims: metadata.supports_claims || manifestEntry?.supports_claims || [],
      supersedes: metadata.supersedes || manifestEntry?.supersedes || [],
      doc_path: path,
      canonical_url: manifestEntry?.canonical_url || toCanonicalArticleUrl(path),
    };
    viewerMachine.textContent = JSON.stringify(machinePayload);
    viewerBody.scrollTop = 0;
  } catch (err) {
    viewerBody.innerHTML = `<p style="color:#a32023;text-align:center;">Failed to load article.<br><small>${err.message}</small></p>`;
    viewerTitle.textContent = "Error";
    viewerMachine.textContent = "{}";
  }
};

/* ========================================
   INIT — bind [data-article] links
======================================== */

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-article]").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const path = link.getAttribute("data-article");
      if (path) openArticle(path);
    });
  });

  document.querySelectorAll(".article-tile[data-article]").forEach((tile) => {
    tile.addEventListener("click", (e) => {
      if (e.target.closest("[data-article]")) return;
      const path = tile.getAttribute("data-article");
      if (path) openArticle(path);
    });

    tile.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      e.preventDefault();
      const path = tile.getAttribute("data-article");
      if (path) openArticle(path);
    });
  });

  const params = new URLSearchParams(window.location.search);
  const doc = params.get("doc");
  if (doc) {
    const safeDoc = doc.replace(/^\/+/, "").replace(/\.\./g, "");
    openArticle(`../assets/docs/${safeDoc}`);
  }
});

(() => {
  const BLOG_MD_DIR = "assets/blogs";
  const BLOG_IMG_DIR = "assets/blogs/imgs";
  const POST_FILES = [
    "20-10-15.md",
    "20-10-20.md",
    "20-10-23.md",
    "20-10-27.md",
    "20-11-03.md",
    "20-11-04.md",
    "20-11-05.md",
    "20-11-09.md",
    "20-11-12.md",
    "20-11-17.md",
    "20-11-20.md",
    "20-11-25.md",
    "20-12-01.md",
    "21-01-12.md",
    "21-01-27.md",
    "21-02-03.md",
    "21-02-04.md",
    "21-02-10.md",
    "21-02-17.md",
    "21-02-23.md",
    "21-03-24.md",
    "21-04-21.md",
    "21-04-27.md",
    "21-04-28.md",
    "21-06-24.md",
    "21-06-25.md",
    "21-06-30.md",
    "21-07-02.md",
    "21-07-07.md",
    "21-07-15.md",
    "21-07-16.md",
    "21-07-20.md",
    "21-07-23.md",
    "22-02-08.md",
    "22-03-12.md",
    "22-04-13.md",
    "22-04-18.md",
    "22-05-02.md",
    "22-05-06.md",
    "22-05-17.md",
    "22-05-25.md",
    "22-06-18.md",
    "22-08-03.md",
    "22-08-16.md",
    "22-08-29.md",
    "22-09-06.md",
    "22-09-19.md",
    "22-10-04.md",
    "22-11-09.md",
    "22-12-05.md",
    "22-12-14.md",
  ];

  const galleryEl = document.getElementById("blogGallery");
  const readerEl = document.getElementById("blogReader");
  if (!galleryEl || !readerEl) return;

  const monthMap = {
    Jan: 0,
    Feb: 1,
    Mar: 2,
    Apr: 3,
    May: 4,
    Jun: 5,
    Jul: 6,
    Aug: 7,
    Sep: 8,
    Oct: 9,
    Nov: 10,
    Dec: 11,
  };

  const defaultThumb = "assets/image/img-countryside-pictoral_map.png";

  let posts = [];
  let postsById = new Map();
  let selectedPostId = null;

  function escapeHtml(input) {
    return String(input)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function parseDateWritten(dateText) {
    const cleaned = String(dateText || "").trim();
    const match = cleaned.match(/^([A-Za-z]{3})\s+(\d{1,2}),\s*(\d{4})$/);
    if (!match) return null;
    const month = monthMap[match[1]];
    if (month === undefined) return null;
    const day = Number(match[2]);
    const year = Number(match[3]);
    const date = new Date(year, month, day);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function formatDateLong(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "";
    return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  function parseByline(markdown) {
    const match = markdown.match(/^\*by\s+(.+?)\*$/m);
    if (!match) return null;
    const byline = match[1].trim();
    const parts = byline.split("|").map((p) => p.trim());
    const authorPart = parts[0] || "";
    const author = authorPart.replace(/^by\s+/i, "").trim();
    const dateText = (parts[1] || "").trim();
    const tagsText = (parts[2] || "").trim();
    const tags = tagsText
      ? tagsText.split(",").map((t) => t.trim()).filter(Boolean)
      : [];
    return { byline, author, dateText, tags };
  }

  function firstMarkdownHeading(markdown) {
    const match = markdown.match(/^#\s+(.+)$/m);
    return match ? match[1].trim() : "";
  }

  function findFirstImageHref(markdown) {
    const match = markdown.match(/!\[[^\]]*?\]\(([^)]+)\)/m);
    return match ? match[1].trim() : "";
  }

  function pickExcerpt(markdown) {
    const lines = markdown.split(/\r?\n/);
    let bylineIndex = -1;
    for (let i = 0; i < lines.length; i += 1) {
      if (/^\*by\s+.+\*$/.test(lines[i].trim())) {
        bylineIndex = i;
        break;
      }
    }
    const start = bylineIndex >= 0 ? bylineIndex + 1 : 0;
    for (let i = start; i < lines.length; i += 1) {
      const line = lines[i].trim();
      if (!line) continue;
      if (/^#{1,6}\s/.test(line)) continue;
      if (line.startsWith("![")) continue;
      if (/^\*.*\*$/.test(line)) continue;
      return line;
    }
    return "";
  }

  function postIdFromFile(fileName) {
    return fileName.replace(/\.md$/i, "");
  }

  async function fetchMarkdown(fileName) {
    const res = await fetch(`${BLOG_MD_DIR}/${fileName}`);
    if (!res.ok) throw new Error(`Failed to load ${fileName} (${res.status})`);
    return res.text();
  }

  function parsePost(markdown, fileName) {
    const id = postIdFromFile(fileName);
    const title = firstMarkdownHeading(markdown);
    const byline = parseByline(markdown);
    const dateWritten = parseDateWritten(byline?.dateText || "");
    const excerpt = pickExcerpt(markdown);
    const thumbnailOriginal = findFirstImageHref(markdown) || "";
    return {
      id,
      fileName,
      markdown,
      title,
      author: byline?.author || "",
      dateText: byline?.dateText || "",
      dateWritten,
      tags: byline?.tags || [],
      excerpt,
      thumbnailOriginal,
    };
  }

  function getHashPostId() {
    const raw = (location.hash || "").replace(/^#/, "").trim();
    return raw || null;
  }

  function isExternalHref(href) {
    return /^https?:\/\//i.test(href);
  }

  function stripQueryHash(path) {
    return String(path || "").split("#")[0].split("?")[0];
  }

  function basename(path) {
    const cleaned = stripQueryHash(path);
    const parts = cleaned.split("/").filter(Boolean);
    return parts.length ? parts[parts.length - 1] : cleaned;
  }

  function buildImageCandidates(originalSrc) {
    const src = String(originalSrc || "").trim();
    if (!src) return [];
    if (isExternalHref(src)) return [src];
    if (/^assets\//i.test(src)) return [src];

    const name = basename(src);
    if (!name) return [];
    const dot = name.lastIndexOf(".");
    const base = dot > 0 ? name.slice(0, dot) : name;

    return [
      `${BLOG_IMG_DIR}/${name}`,
      `${BLOG_IMG_DIR}/${base}.jpg`,
      `${BLOG_IMG_DIR}/${base}.jpeg`,
      `${BLOG_IMG_DIR}/${base}.png`,
    ];
  }

  function applyImageFallback(imgEl, originalSrc) {
    const candidates = buildImageCandidates(originalSrc);
    if (!candidates.length) return;

    let index = 0;
    imgEl.onerror = () => {
      index += 1;
      if (index >= candidates.length) {
        imgEl.onerror = null;
        return;
      }
      imgEl.src = candidates[index];
    };
    imgEl.src = candidates[0];
  }

  function setSelectedCard(postId) {
    const cards = galleryEl.querySelectorAll("[data-post-id]");
    cards.forEach((card) => {
      const isSelected = card.getAttribute("data-post-id") === postId;
      card.classList.toggle("is-selected", isSelected);
      card.setAttribute("aria-current", isSelected ? "true" : "false");
    });
  }

  function renderGallery() {
    galleryEl.innerHTML = "";

    posts.forEach((post) => {
      const card = document.createElement("article");
      card.className = "card-farm blog-card";
      card.setAttribute("data-post-id", post.id);
      card.setAttribute("role", "button");
      card.setAttribute("tabindex", "0");
      card.setAttribute("aria-current", "false");

      const media = document.createElement("div");
      media.className = "card-farm__media blog-card__media";

      const img = document.createElement("img");
      img.className = "figure__img blog-card__img";
      img.alt = post.title || "Blog post image";
      img.loading = "lazy";
      media.appendChild(img);

      const thumbSrc = post.thumbnailOriginal || defaultThumb;
      applyImageFallback(img, thumbSrc);

      const content = document.createElement("div");
      content.className = "card-farm__content";

      const title = document.createElement("h3");
      title.className = "card-farm__title";
      title.textContent = post.title || post.id;

      const bio = document.createElement("p");
      bio.className = "card-farm__bio";
      bio.textContent = post.excerpt || "Read more…";

      const meta = document.createElement("div");
      meta.className = "card-farm__meta";

      const metaLabel = document.createElement("div");
      metaLabel.className = "meta-label";
      metaLabel.textContent = "Written";

      const metaValue = document.createElement("span");
      metaValue.textContent = `${formatDateLong(post.dateWritten) || post.dateText}${post.author ? ` • ${post.author}` : ""}`;

      const tagLine = document.createElement("span");
      tagLine.className = "blog-card__tags";
      tagLine.textContent = post.tags.length ? post.tags.join(", ") : "";

      meta.appendChild(metaLabel);
      meta.appendChild(metaValue);
      if (tagLine.textContent) meta.appendChild(tagLine);

      content.appendChild(title);
      content.appendChild(bio);
      content.appendChild(meta);

      card.appendChild(media);
      card.appendChild(content);

      card.addEventListener("click", () => selectPost(post.id, { updateHash: true, scroll: true }));
      card.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          selectPost(post.id, { updateHash: true, scroll: true });
        }
      });

      galleryEl.appendChild(card);
    });
  }

  function configureMarked() {
    if (!window.marked || !window.marked.Renderer) return;
    const renderer = new window.marked.Renderer();
    renderer.html = (html) => escapeHtml(html);
    window.marked.setOptions({ renderer });
  }

  function postProcessReader() {
    const anchors = readerEl.querySelectorAll("a[href]");
    anchors.forEach((a) => {
      const href = a.getAttribute("href") || "";
      if (isExternalHref(href)) {
        a.setAttribute("target", "_blank");
        a.setAttribute("rel", "noopener noreferrer");
      }
    });

    const imgs = readerEl.querySelectorAll("img");
    imgs.forEach((img) => {
      img.classList.add("figure__img");
      const originalSrc = img.getAttribute("src") || "";
      applyImageFallback(img, originalSrc);
    });
  }

  async function selectPost(postId, { updateHash, scroll } = { updateHash: false, scroll: false }) {
    const post = postsById.get(postId);
    if (!post) return;

    selectedPostId = postId;
    setSelectedCard(postId);

    if (updateHash && location.hash !== `#${postId}`) {
      location.hash = postId;
    }

    readerEl.innerHTML = window.marked
      ? window.marked.parse(post.markdown)
      : `<p>${escapeHtml(post.markdown)}</p>`;

    postProcessReader();

    if (scroll) {
      const rect = readerEl.getBoundingClientRect();
      const needsScroll = rect.top > window.innerHeight * 0.75 || rect.top < 0;
      if (needsScroll) {
        readerEl.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  }

  async function init() {
    configureMarked();
    readerEl.innerHTML = "<div class=\"kicker\">Loading…</div>";

    const results = await Promise.allSettled(
      POST_FILES.map(async (fileName) => {
        const markdown = await fetchMarkdown(fileName);
        return parsePost(markdown, fileName);
      }),
    );

    posts = results
      .filter((r) => r.status === "fulfilled")
      .map((r) => r.value)
      .filter((p) => p && p.dateWritten instanceof Date);

    posts.sort((a, b) => b.dateWritten.getTime() - a.dateWritten.getTime());
    postsById = new Map(posts.map((p) => [p.id, p]));

    if (!posts.length) {
      readerEl.innerHTML = "<p>Unable to load blog posts. Make sure you are serving this site over HTTP (not <code>file://</code>).</p>";
      return;
    }

    renderGallery();

    const initial = getHashPostId() || posts[0].id;
    await selectPost(initial, { updateHash: false, scroll: false });

    window.addEventListener("hashchange", async () => {
      const nextId = getHashPostId();
      if (!nextId || nextId === selectedPostId) return;
      if (!postsById.has(nextId)) return;
      await selectPost(nextId, { updateHash: false, scroll: false });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

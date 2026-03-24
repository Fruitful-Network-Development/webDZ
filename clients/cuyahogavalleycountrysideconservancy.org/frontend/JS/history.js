(() => {
  const DATA_PATH = "assets/timeline.json";
  const SECTION_META = [
    {
      title: "Indigenous pre-contact lifeways and agriculture",
      id: "era-indigenous",
      number: "01",
      shortLabel: "Origins",
      aliases: ["indigenous-pre-contact-lifeways-and-agriculture"]
    },
    {
      title: "Treaties, land transfer, and settler farming",
      id: "era-settler",
      number: "02",
      shortLabel: "Settler farms",
      aliases: ["treaties-land-transfer-and-settler-farming"]
    },
    {
      title: "Canal-era and nineteenth-century diversification",
      id: "era-canal",
      number: "03",
      shortLabel: "Canal era",
      aliases: ["canal-era-and-nineteenth-century-diversification"]
    },
    {
      title: "Twentieth-century mechanization, markets, and land-use change",
      id: "era-modern",
      number: "04",
      shortLabel: "Mechanization",
      aliases: [
        "twentieth-century-mechanization-markets-and-land-use-change",
        "valley-views",
        "history-oral",
        "history-sources"
      ]
    },
    {
      title: "Farmland preservation, the park, and the Countryside program",
      id: "era-park",
      number: "05",
      shortLabel: "Countryside era",
      aliases: ["farmland-preservation-the-park-and-the-countryside-program", "farm-sites"]
    }
  ];

  const SECTION_BY_TITLE = new Map(SECTION_META.map((section) => [section.title, section]));

  const state = {
    items: [],
    sections: [],
    currentIndex: 0,
    cardEls: [],
    trackEls: [],
    railEls: [],
    railSectionEls: [],
    widgetCardEl: null,
    trackScrollerEl: null,
    scrollBound: false
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function slugify(value) {
    return String(value ?? "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  }

  function shorten(value, maxLength) {
    const text = String(value ?? "").trim();
    if (text.length <= maxLength) return text;
    return `${text.slice(0, Math.max(0, maxLength - 1)).trim()}…`;
  }

  function pluralize(count, label) {
    return `${count} ${label}${count === 1 ? "" : "s"}`;
  }

  function formatHost(url) {
    try {
      return new URL(url, window.location.href).hostname.replace(/^www\./, "");
    } catch {
      return url;
    }
  }

  function uniqueUrls(urls) {
    const seen = new Set();
    return urls.filter((url) => {
      if (!url || seen.has(url)) return false;
      seen.add(url);
      return true;
    });
  }

  function extractUrls(text) {
    return uniqueUrls(String(text ?? "").match(/https?:\/\/[^\s;,)]+/g) || []);
  }

  function renderLinkedText(text) {
    const value = String(text ?? "");
    if (!value) return "";

    const urlRegex = /https?:\/\/[^\s;,)]+/g;
    let cursor = 0;
    let html = "";

    value.replace(urlRegex, (match, offset) => {
      html += escapeHtml(value.slice(cursor, offset));
      html += `<a href="${escapeHtml(match)}" target="_blank" rel="noreferrer">${escapeHtml(formatHost(match))}</a>`;
      cursor = offset + match.length;
      return match;
    });

    html += escapeHtml(value.slice(cursor));
    return html;
  }

  function getSectionMeta(sectionTitle) {
    if (SECTION_BY_TITLE.has(sectionTitle)) return SECTION_BY_TITLE.get(sectionTitle);

    const fallbackId = `section-${slugify(sectionTitle || "timeline") || "timeline"}`;
    return {
      title: sectionTitle || "Timeline",
      id: fallbackId,
      number: "00",
      shortLabel: "Timeline",
      aliases: [slugify(sectionTitle || "timeline")]
    };
  }

  function getDisplayTitle(item) {
    const rawTitle = String(item.title || "").trim();
    if (rawTitle && rawTitle.toLowerCase() !== "recent") return rawTitle;

    const display = String(item.display_heading || "").trim();
    if (display) return display.split(" (")[0].trim();

    return "Untitled record";
  }

  function getFeatureImage(item) {
    if (item.image_paths && item.image_paths.length) return item.image_paths[0];

    if (item.related_farm_paths && item.related_farm_paths.length) {
      const related = item.related_farm_paths[0];
      return {
        title: related.title,
        meta: "Related farm record",
        description: "Linked from the working farm registry.",
        path: related.image_path,
        alt: related.title,
        profile_path: related.profile_path
      };
    }

    return null;
  }

  function collectFactRows(item) {
    const details = item.details || {};
    const rows = [];

    if (details.practical_locations || details.practical_location) {
      rows.push({
        label: "Location",
        html: renderLinkedText(details.practical_locations || details.practical_location)
      });
    }

    if (details.practical_details) {
      rows.push({
        label: "Directions",
        html: renderLinkedText(details.practical_details)
      });
    }

    if (Array.isArray(details.notes) && details.notes.length) {
      rows.push({
        label: "Notes",
        html: details.notes.map((note) => escapeHtml(note)).join(" ")
      });
    }

    if (details.primary_documentation_links) {
      const urls = extractUrls(details.primary_documentation_links);
      const html = urls.length
        ? urls
            .map(
              (url) =>
                `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(formatHost(url))}</a>`
            )
            .join(" · ")
        : renderLinkedText(details.primary_documentation_links);

      rows.push({
        label: "Primary docs",
        html
      });
    }

    return rows;
  }

  function getSourceUrls(item) {
    const details = item.details || {};
    return uniqueUrls([
      ...(item.source_links || []).map((source) => source.url),
      ...extractUrls(details.primary_documentation_links)
    ]);
  }

  function renderStatChips(item) {
    const sourceCount = getSourceUrls(item).length + (item.additional_source_links || []).length;
    const stats = [
      item.image_paths?.length ? pluralize(item.image_paths.length, "visual") : null,
      item.audio_paths?.length ? pluralize(item.audio_paths.length, "audio clip") : null,
      item.related_farm_paths?.length ? pluralize(item.related_farm_paths.length, "farm link") : null,
      sourceCount ? pluralize(sourceCount, "source") : null
    ].filter(Boolean);

    if (!stats.length) return "";

    return `
      <div class="history-chip-row">
        ${stats.map((stat) => `<span class="history-chip">${escapeHtml(stat)}</span>`).join("")}
      </div>
    `;
  }

  function renderImageCards(entries, limit = 2) {
    if (!entries || !entries.length) return "";

    const visible = entries.slice(0, limit);
    const overflow = entries.length - visible.length;

    return `
      <section class="history-entry-card__block history-entry-card__block--media">
        <div class="history-entry-card__block-head">
          <h4>Image artifacts</h4>
          <p>Selected visuals attached to this record.</p>
        </div>
        <div class="history-media-grid">
          ${visible
            .map((image) => {
              const isSvg = /\.svg$/i.test(String(image.path || ""));
              const imageClass = isSvg ? "history-media-card__img history-media-card__img--icon" : "history-media-card__img";
              const body = `
                <figure class="history-media-card">
                  <img class="${imageClass}" src="${escapeHtml(image.path || "")}" alt="${escapeHtml(image.alt || image.title || "")}" loading="lazy" decoding="async" />
                  <figcaption class="history-media-card__copy">
                    <p class="history-media-card__title">${escapeHtml(image.title || "Archival image")}</p>
                    ${image.meta ? `<p class="history-media-card__meta">${escapeHtml(image.meta)}</p>` : ""}
                    ${image.description ? `<p class="history-media-card__desc">${escapeHtml(image.description)}</p>` : ""}
                  </figcaption>
                </figure>
              `;

              if (image.profile_path) {
                return `<a class="history-media-link" href="${escapeHtml(image.profile_path)}">${body}</a>`;
              }

              return body;
            })
            .join("")}
        </div>
        ${
          overflow > 0
            ? `<p class="history-entry-card__more">+ ${overflow} more visual attachments are associated with this record.</p>`
            : ""
        }
      </section>
    `;
  }

  function renderAudioCards(entries, limit = 2) {
    if (!entries || !entries.length) return "";

    const visible = entries.slice(0, limit);
    const overflow = entries.length - visible.length;

    return `
      <section class="history-entry-card__block history-entry-card__block--audio">
        <div class="history-entry-card__block-head">
          <h4>Audio</h4>
          <p>Short oral-history or archival listening excerpts.</p>
        </div>
        <div class="audio-shelf">
          ${visible
            .map(
              (audio) => `
                <div class="oral-player">
                  <button class="oral-player__button" type="button">Play</button>
                  <div class="oral-player__meta">
                    <div class="oral-player__title">${escapeHtml(audio.title || "Audio excerpt")}</div>
                    <div class="oral-player__bar">
                      <div class="oral-player__progress" style="width: 0%;"></div>
                    </div>
                    <div class="oral-player__time">${escapeHtml(audio.time_label || "00:00 / --:--")}</div>
                    <audio src="${escapeHtml(audio.path || "")}" preload="metadata"></audio>
                  </div>
                </div>
              `
            )
            .join("")}
        </div>
        ${
          overflow > 0
            ? `<p class="history-entry-card__more">+ ${overflow} more audio excerpts are linked to this record.</p>`
            : ""
        }
      </section>
    `;
  }

  function renderRelatedFarmCards(entries, limit = 3) {
    if (!entries || !entries.length) return "";

    const visible = entries.slice(0, limit);
    const overflow = entries.length - visible.length;

    return `
      <section class="history-entry-card__block">
        <div class="history-entry-card__block-head">
          <h4>Related farms</h4>
          <p>Current farm records linked to this moment in the story.</p>
        </div>
        <div class="history-link-grid history-link-grid--farm">
          ${visible
            .map((farm) => {
              const isSvg = /\.svg$/i.test(String(farm.image_path || ""));
              const imageClass = isSvg ? "history-link-card__thumb history-link-card__thumb--icon" : "history-link-card__thumb";
              return `
                <a class="history-link-card" href="${escapeHtml(farm.profile_path || "#")}">
                  <img class="${imageClass}" src="${escapeHtml(farm.image_path || "")}" alt="${escapeHtml(farm.title || "")}" loading="lazy" decoding="async" />
                  <span class="history-link-card__label">${escapeHtml(farm.title || "Farm record")}</span>
                </a>
              `;
            })
            .join("")}
        </div>
        ${
          overflow > 0
            ? `<p class="history-entry-card__more">+ ${overflow} more farm links are attached to this record.</p>`
            : ""
        }
      </section>
    `;
  }

  function renderAdditionalSourceCards(entries, limit = 4) {
    if (!entries || !entries.length) return "";

    const visible = entries.slice(0, limit);
    const overflow = entries.length - visible.length;

    return `
      <section class="history-entry-card__block">
        <div class="history-entry-card__block-head">
          <h4>Linked collections</h4>
          <p>Partner pages, finding aids, and context pages connected to this entry.</p>
        </div>
        <div class="history-link-grid">
          ${visible
            .map((source) => {
              const thumb = source.thumb_path
                ? `<img class="history-link-card__thumb" src="${escapeHtml(source.thumb_path)}" alt="" loading="lazy" decoding="async" />`
                : `<div class="history-link-card__thumb history-link-card__thumb--placeholder" aria-hidden="true">${escapeHtml(
                    source.collection || "Link"
                  )}</div>`;

              return `
                <a class="history-link-card history-link-card--source" href="${escapeHtml(source.url || "#")}" target="_blank" rel="noreferrer">
                  ${thumb}
                  <span class="history-link-card__collection">${escapeHtml(source.collection || "Collection")}</span>
                  <span class="history-link-card__label">${escapeHtml(source.title || formatHost(source.url || ""))}</span>
                  ${source.meta ? `<span class="history-link-card__meta">${escapeHtml(source.meta)}</span>` : ""}
                  ${source.description ? `<span class="history-link-card__desc">${escapeHtml(source.description)}</span>` : ""}
                </a>
              `;
            })
            .join("")}
        </div>
        ${
          overflow > 0
            ? `<p class="history-entry-card__more">+ ${overflow} more linked resources accompany this record.</p>`
            : ""
        }
      </section>
    `;
  }

  function renderSourceList(item) {
    const urls = getSourceUrls(item);
    if (!urls.length) return "";

    return `
      <section class="history-entry-card__block">
        <div class="history-entry-card__block-head">
          <h4>Core sources</h4>
          <p>Primary source trail for the dating and interpretation on this card.</p>
        </div>
        <ul class="history-source-list">
          ${urls
            .map(
              (url) => `
                <li>
                  <a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(formatHost(url))}</a>
                </li>
              `
            )
            .join("")}
        </ul>
      </section>
    `;
  }

  function buildFeatureCard(item) {
    const featureImage = getFeatureImage(item);
    const facts = collectFactRows(item).slice(0, 2);
    const quickSources = getSourceUrls(item).slice(0, 2);
    const imageMarkup = featureImage
      ? `
          <figure class="history-widget__figure">
            ${
              featureImage.profile_path
                ? `<a class="history-widget__figure-link" href="${escapeHtml(featureImage.profile_path)}">`
                : ""
            }
            <img
              class="history-widget__figure-img${/\.svg$/i.test(String(featureImage.path || "")) ? " history-widget__figure-img--icon" : ""}"
              src="${escapeHtml(featureImage.path || "")}"
              alt="${escapeHtml(featureImage.alt || featureImage.title || "")}"
              loading="lazy"
              decoding="async"
            />
            ${
              featureImage.profile_path
                ? "</a>"
                : ""
            }
            <figcaption class="history-widget__figure-cap">
              <span>${escapeHtml(featureImage.title || "Featured artifact")}</span>
              ${featureImage.meta ? `<span>${escapeHtml(featureImage.meta)}</span>` : ""}
            </figcaption>
          </figure>
        `
      : `
          <div class="history-widget__artifact" aria-hidden="true">
            <div class="history-widget__artifact-card"></div>
            <div class="history-widget__artifact-card"></div>
            <div class="history-widget__artifact-card history-widget__artifact-card--front"></div>
          </div>
        `;

    return `
      <div class="history-widget__card-top">
        <div>
          <p class="history-widget__sequence">Era ${escapeHtml(item.section.number)} · Entry ${escapeHtml(item.entryNumber)}</p>
          <p class="history-widget__section">${escapeHtml(item.section.shortLabel)}</p>
        </div>
        <a class="history-widget__jump" href="#${escapeHtml(item.slug)}" data-story-jump="${escapeHtml(item.slug)}">Open full entry</a>
      </div>
      <div class="history-widget__card-grid">
        <div class="history-widget__copy">
          <p class="history-widget__timestamp">${escapeHtml(item.timestamp_label || "Date not stated")}</p>
          <h3>${escapeHtml(getDisplayTitle(item))}</h3>
          <p class="history-widget__summary">${escapeHtml(item.paragraph || "")}</p>
          ${renderStatChips(item)}
          ${
            facts.length
              ? `
                  <dl class="history-widget__facts">
                    ${facts
                      .map(
                        (fact) => `
                          <div>
                            <dt>${escapeHtml(fact.label)}</dt>
                            <dd>${fact.html}</dd>
                          </div>
                        `
                      )
                      .join("")}
                  </dl>
                `
              : ""
          }
          ${
            quickSources.length
              ? `
                  <div class="history-widget__source-row">
                    ${quickSources
                      .map(
                        (url) =>
                          `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(formatHost(url))}</a>`
                      )
                      .join("")}
                  </div>
                `
              : ""
          }
        </div>
        ${imageMarkup}
      </div>
    `;
  }

  function buildTrack(items) {
    return `
      <button type="button" class="history-widget__arrow" id="historyPrev" aria-label="Previous event">←</button>
      <div class="history-widget__track" id="historyTrack" aria-label="Horizontal timeline">
        <div class="history-widget__track-inner">
          ${items
            .map(
              (item, index) => `
                <button type="button" class="history-track-item" data-index="${index}" aria-label="Focus ${escapeHtml(getDisplayTitle(item))}">
                  <span class="history-track-item__date">${escapeHtml(shorten(item.timestamp_label || "Undated", 28))}</span>
                  <span class="history-track-item__title">${escapeHtml(shorten(getDisplayTitle(item), 28))}</span>
                </button>
              `
            )
            .join("")}
        </div>
      </div>
      <button type="button" class="history-widget__arrow" id="historyNext" aria-label="Next event">→</button>
    `;
  }

  function buildRail(sections) {
    return `
      <div class="history-rail__groups">
        ${sections
          .map(
            (section) => `
              <section class="history-rail__group">
                <a class="history-rail__section" href="#${escapeHtml(section.id)}" data-section-id="${escapeHtml(section.id)}">
                  <span class="history-rail__section-number">${escapeHtml(section.number)}</span>
                  <span>${escapeHtml(section.shortLabel)}</span>
                </a>
                <div class="history-rail__events">
                  ${section.items
                    .map(
                      (item) => `
                        <a class="history-rail__item" href="#${escapeHtml(item.slug)}" data-index="${item.index}" data-target-id="${escapeHtml(item.slug)}">
                          <span class="history-rail__dot" aria-hidden="true"></span>
                          <span class="history-rail__text">
                            <span class="history-rail__timestamp">${escapeHtml(shorten(item.timestamp_label || "Undated", 24))}</span>
                            <span class="history-rail__label">${escapeHtml(shorten(getDisplayTitle(item), 28))}</span>
                          </span>
                        </a>
                      `
                    )
                    .join("")}
                </div>
              </section>
            `
          )
          .join("")}
      </div>
    `;
  }

  function buildStory(sections) {
    return sections
      .map(
        (section) => `
          <section class="history-group" id="${escapeHtml(section.id)}" data-section-id="${escapeHtml(section.id)}">
            ${section.aliases
              .filter((alias) => alias && alias !== section.id)
              .map((alias) => `<span class="history-anchor" id="${escapeHtml(alias)}" aria-hidden="true"></span>`)
              .join("")}
            <div class="history-group__header">
              <div class="history-group__index">${escapeHtml(section.number)}</div>
              <div class="history-group__copy">
                <p class="history-group__eyebrow">${escapeHtml(section.shortLabel)} · ${escapeHtml(
                  pluralize(section.items.length, "entry")
                )}</p>
                <h2>${escapeHtml(section.title)}</h2>
                <p>${escapeHtml(section.about || "")}</p>
              </div>
            </div>

            <div class="history-card-stack">
              ${section.items
                .map(
                  (item) => `
                    <article class="history-entry-card" id="${escapeHtml(item.slug)}" data-index="${item.index}" data-section-id="${escapeHtml(
                      section.id
                    )}">
                      <div class="history-entry-card__header">
                        <div class="history-entry-card__stamp">${escapeHtml(item.entryNumber)}</div>
                        <div class="history-entry-card__head">
                          <p class="history-entry-card__timestamp">${escapeHtml(item.timestamp_label || "Date not stated")}</p>
                          <h3>${escapeHtml(getDisplayTitle(item))}</h3>
                          ${
                            item.display_heading && item.display_heading !== getDisplayTitle(item)
                              ? `<p class="history-entry-card__display">${escapeHtml(item.display_heading)}</p>`
                              : ""
                          }
                        </div>
                      </div>

                      <p class="history-entry-card__summary">${escapeHtml(item.paragraph || "")}</p>
                      ${renderStatChips(item)}

                      ${
                        collectFactRows(item).length
                          ? `
                              <dl class="history-fact-grid">
                                ${collectFactRows(item)
                                  .map(
                                    (fact) => `
                                      <div class="history-fact">
                                        <dt>${escapeHtml(fact.label)}</dt>
                                        <dd>${fact.html}</dd>
                                      </div>
                                    `
                                  )
                                  .join("")}
                              </dl>
                            `
                          : ""
                      }

                      ${renderImageCards(item.image_paths, 2)}
                      ${renderAudioCards(item.audio_paths, 2)}
                      ${renderRelatedFarmCards(item.related_farm_paths, 3)}
                      ${renderAdditionalSourceCards(item.additional_source_links, 4)}
                      ${renderSourceList(item)}
                    </article>
                  `
                )
                .join("")}
            </div>
          </section>
        `
      )
      .join("");
  }

  function groupItems(items) {
    const groups = [];

    items.forEach((item) => {
      const lastGroup = groups[groups.length - 1];
      if (lastGroup && lastGroup.title === item.section_title) {
        lastGroup.items.push(item);
        return;
      }

      groups.push({
        ...item.section,
        about: item.section_about,
        items: [item]
      });
    });

    return groups;
  }

  function setActive(index, options = {}) {
    const nextIndex = Math.max(0, Math.min(state.items.length - 1, index));
    state.currentIndex = nextIndex;

    const item = state.items[nextIndex];
    if (!item) return;

    if (state.widgetCardEl) {
      state.widgetCardEl.innerHTML = buildFeatureCard(item);
    }

    state.trackEls.forEach((button, buttonIndex) => {
      const isActive = buttonIndex === nextIndex;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", isActive ? "true" : "false");
    });

    state.cardEls.forEach((card, cardIndex) => {
      card.classList.toggle("is-active", cardIndex === nextIndex);
    });

    state.railEls.forEach((link) => {
      link.classList.toggle("is-active", Number(link.dataset.index) === nextIndex);
    });

    state.railSectionEls.forEach((link) => {
      link.classList.toggle("is-active", link.dataset.sectionId === item.section.id);
    });

    if (options.centerTrack !== false) {
      const activeTrackButton = state.trackEls[nextIndex];
      activeTrackButton?.scrollIntoView({ block: "nearest", inline: "center" });
    }
  }

  function scrollToId(id, behavior = "smooth") {
    const target = document.getElementById(id);
    if (!target) return;

    const top = target.getBoundingClientRect().top + window.scrollY - 120;
    window.scrollTo({ top, behavior });
  }

  function bindControls() {
    const prevButton = document.getElementById("historyPrev");
    const nextButton = document.getElementById("historyNext");

    prevButton?.addEventListener("click", () => {
      setActive(state.currentIndex - 1);
    });

    nextButton?.addEventListener("click", () => {
      setActive(state.currentIndex + 1);
    });

    state.trackEls.forEach((button) => {
      button.addEventListener("click", () => {
        setActive(Number(button.dataset.index));
      });
    });

    state.railEls.forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        const index = Number(link.dataset.index);
        const targetId = link.dataset.targetId;
        setActive(index);
        if (targetId) {
          scrollToId(targetId);
          window.history.replaceState(null, "", `#${targetId}`);
        }
      });
    });

    state.railSectionEls.forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        const sectionId = link.dataset.sectionId;
        const section = state.sections.find((entry) => entry.id === sectionId);
        const firstItem = section?.items?.[0];
        if (firstItem) {
          setActive(firstItem.index);
        }
        if (sectionId) {
          scrollToId(sectionId);
          window.history.replaceState(null, "", `#${sectionId}`);
        }
      });
    });

    document
      .getElementById("historyWidgetMount")
      ?.addEventListener("click", (event) => {
        const jumpLink = event.target.closest("[data-story-jump]");
        if (!jumpLink) return;
        event.preventDefault();
        const targetId = jumpLink.getAttribute("data-story-jump");
        const target = document.getElementById(targetId || "");
        if (!target) return;
        const index = Number(target.dataset.index);
        if (Number.isFinite(index)) {
          setActive(index);
        }
        scrollToId(targetId);
        window.history.replaceState(null, "", `#${targetId}`);
      });
  }

  function bindScrollSync() {
    if (state.scrollBound) return;
    state.scrollBound = true;

    let ticking = false;

    const updateFromScroll = () => {
      ticking = false;
      if (!state.cardEls.length) return;

      const anchor = window.scrollY + Math.min(window.innerHeight * 0.32, 250);
      let activeIndex = 0;

      for (const card of state.cardEls) {
        if (card.offsetTop <= anchor) {
          activeIndex = Number(card.dataset.index);
        } else {
          break;
        }
      }

      setActive(activeIndex, { centerTrack: false });
    };

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(updateFromScroll);
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    updateFromScroll();
  }

  function handleInitialHash() {
    const hash = window.location.hash.replace(/^#/, "");
    if (!hash) {
      setActive(0);
      return;
    }

    const target = document.getElementById(hash);
    if (!target) {
      setActive(0);
      return;
    }

    const card = target.closest(".history-entry-card");
    if (card) {
      const index = Number(card.dataset.index);
      setActive(index);
      scrollToId(card.id, "auto");
      return;
    }

    const section = target.closest(".history-group");
    if (section) {
      const firstCard = section.querySelector(".history-entry-card");
      if (firstCard) {
        setActive(Number(firstCard.dataset.index));
      }
      scrollToId(hash, "auto");
      return;
    }

    setActive(0);
  }

  function renderTimeline(items) {
    const widgetMount = document.getElementById("historyWidgetMount");
    const railMount = document.getElementById("historyRailMount");
    const storyMount = document.getElementById("historyStoryMount");

    if (!widgetMount || !railMount || !storyMount) return;

    state.items = items.map((item, index) => {
      const section = getSectionMeta(item.section_title);
      return {
        ...item,
        index,
        entryNumber: String(index + 1).padStart(2, "0"),
        section
      };
    });

    state.sections = groupItems(state.items);

    widgetMount.innerHTML = `
      <div class="history-widget__frame">
        <div class="history-widget__stack">
          <article class="history-widget__card" id="historyWidgetCard"></article>
        </div>
        <div class="history-widget__controls">
          ${buildTrack(state.items)}
        </div>
      </div>
    `;

    railMount.innerHTML = buildRail(state.sections);
    storyMount.innerHTML = buildStory(state.sections);

    state.widgetCardEl = document.getElementById("historyWidgetCard");
    state.trackScrollerEl = document.getElementById("historyTrack");
    state.trackEls = Array.from(document.querySelectorAll(".history-track-item"));
    state.railEls = Array.from(document.querySelectorAll(".history-rail__item"));
    state.railSectionEls = Array.from(document.querySelectorAll(".history-rail__section"));
    state.cardEls = Array.from(document.querySelectorAll(".history-entry-card"));

    bindControls();
    if (typeof window.initOralPlayers === "function") {
      window.initOralPlayers(document);
    }
    handleInitialHash();
    bindScrollSync();
  }

  function renderError(message) {
    const markup = `<p class="card-farm">${escapeHtml(message)} <a href="${DATA_PATH}">Open the source dataset</a>.</p>`;
    const widgetMount = document.getElementById("historyWidgetMount");
    const railMount = document.getElementById("historyRailMount");
    const storyMount = document.getElementById("historyStoryMount");

    if (widgetMount) widgetMount.innerHTML = markup;
    if (railMount) railMount.innerHTML = markup;
    if (storyMount) storyMount.innerHTML = markup;
  }

  async function init() {
    try {
      const response = await fetch(DATA_PATH);
      if (!response.ok) {
        throw new Error(`Unable to load timeline data (${response.status}).`);
      }

      const payload = await response.json();
      const items = Array.isArray(payload) ? payload.filter((item) => item?.type === "timeline_event") : [];

      if (!items.length) {
        throw new Error("Timeline data is empty.");
      }

      renderTimeline(items);
    } catch (error) {
      renderError(error instanceof Error ? error.message : "Unable to load the combined history timeline.");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

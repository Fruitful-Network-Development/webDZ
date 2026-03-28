(function () {
  "use strict";

  var LAYOUT_URL = "assets/docs/layout.json";

  var NAV_MAP = {
    "MAKING THE CROPS": "crops.html",
    "ANIMAL HUSBANDRY": "animals.html",
    "FOR YOUR HOMESTEAD": "homestead.html",
    "NEWSLETTERS": "newsletter.html",
    "MORE INFO": "info.html"
  };

  var NAV_LABEL_DISPLAY = {
    "MAKING THE CROPS": "Making the Crops",
    "ANIMAL HUSBANDRY": "Animal Husbandry",
    "FOR YOUR HOMESTEAD": "For Your Homestead",
    "NEWSLETTERS": "Newsletters",
    "MORE INFO": "More Info"
  };

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function paragraphHtml(text) {
    return "<p>" + escapeHtml(text) + "</p>";
  }

  function bodyParagraphs(body) {
    if (!body || !body.length) return "";
    return body.map(paragraphHtml).join("");
  }

  function renderImages(paths, className) {
    if (!paths || !paths.length) return "";
    var cls = className ? " " + className : "";
    return paths
      .map(function (src) {
        return (
          '<figure class="json-figure' +
          cls +
          '"><img src="' +
          escapeHtml(src.replace(/^\//, "")) +
          '" alt=""></figure>'
        );
      })
      .join("");
  }

  function renderBlocks(blocks) {
    if (!blocks || !blocks.length) return "";
    var html = "";
    blocks.forEach(function (block) {
      var keys = Object.keys(block);
      keys.forEach(function (k) {
        var paras = block[k];
        html += '<section class="json-subsection"><h3 class="json-subheading">' + escapeHtml(k) + "</h3>";
        html += bodyParagraphs(paras);
        html += "</section>";
      });
    });
    return html;
  }

  function renderPodcastEntry(entry) {
    var keys = Object.keys(entry).filter(function (k) {
      return k !== "image";
    });
    if (!keys.length) return "";
    var title = keys[0];
    var lines = entry[title];
    var img = entry.image
      ? '<div class="json-podcast-media"><img src="' +
        escapeHtml(entry.image.replace(/^\//, "")) +
        '" alt=""></div>'
      : "";
    var url = lines[lines.length - 1];
    var urlIsHttp = /^https?:\/\//i.test(url);
    var bodyLines = urlIsHttp ? lines.slice(0, -1) : lines.slice();
    var inner = "";
    if (title === "CLE Foodcast" && lines.length === 4) {
      inner =
        "<h3>" +
        escapeHtml(lines[0]) +
        "</h3>" +
        '<p class="json-meta">' +
        escapeHtml(lines[1]) +
        " · " +
        escapeHtml(lines[2]) +
        "</p>" +
        '<p class="json-podcast-link"><a href="' +
        escapeHtml(url) +
        '" target="_blank" rel="noopener">Listen on Apple Podcasts</a></p>';
    } else if (lines.length === 3) {
      inner =
        "<h3>" +
        escapeHtml(title) +
        "</h3>" +
        paragraphHtml(lines[0]) +
        '<p class="json-meta">' +
        escapeHtml(lines[1]) +
        "</p>" +
        '<p class="json-podcast-link"><a href="' +
        escapeHtml(url) +
        '" target="_blank" rel="noopener">Listen or visit</a></p>';
    } else {
      inner =
        "<h3>" +
        escapeHtml(title) +
        "</h3>" +
        bodyLines.map(paragraphHtml).join("") +
        (urlIsHttp
          ? '<p class="json-podcast-link"><a href="' +
            escapeHtml(url) +
            '" target="_blank" rel="noopener">Open link</a></p>'
          : "");
    }
    return '<article class="json-podcast">' + img + '<div class="json-podcast-body">' + inner + "</div></article>";
  }

  function renderAnimalIntro(intro) {
    var body = intro.body;
    if (!body || !body.length) return "";
    var navLabels = ["LAYERS", "BROILERS", "TURKEYS", "SHEEP", "HORSES"];
    var i = 0;
    var out = "";
    for (; i < body.length; i++) {
      if (navLabels.indexOf(body[i]) !== -1) break;
      out += paragraphHtml(body[i]);
    }
    if (i < body.length) {
      out += '<ul class="json-animal-toc">';
      for (; i < body.length; i++) {
        var label = body[i];
        var href = "#";
        if (label === "LAYERS") href = "#layers";
        else if (label === "BROILERS") href = "#broilers";
        else if (label === "TURKEYS") href = "#turkeys";
        else if (label === "SHEEP") href = "#sheep";
        else if (label === "HORSES") href = "home.html#draft-horses";
        var isExternal = href.indexOf("http") === 0 || href.indexOf("home.html") === 0;
        out +=
          '<li><a href="' +
          href +
          '"' +
          (isExternal ? "" : "") +
          ">" +
          escapeHtml(label) +
          "</a></li>";
      }
      out += "</ul>";
    }
    return (
      '<div class="json-intro-prose">' +
      out +
      "</div>" +
      renderImages(intro.images, "json-intro-images")
    );
  }

  function renderSectionBlock(title, inner, id) {
    var idAttr = id ? ' id="' + escapeHtml(id) + '"' : "";
    return (
      '<section class="page-section json-page-section"' +
      idAttr +
      '><div class="container json-container"><h2 class="json-section-title">' +
      escapeHtml(title) +
      "</h2>" +
      inner +
      "</div></section>"
    );
  }

  function renderHome(layout) {
    var h = layout.home;
    var heroKicker = h.about_our_farm.body[0];
    var aboutRest = h.about_our_farm.body.slice(1);
    var journeyItems = h.our_journey.body.map(function (line) {
      return "<li>" + escapeHtml(line) + "</li>";
    }).join("");
    return (
      '<section class="hero json-home-hero">' +
      '<div class="hero-parallax" role="img" aria-label="Farm"></div>' +
      '<div class="hero-body">' +
      '<p class="hero-kicker">' +
      escapeHtml(heroKicker) +
      "</p>" +
      "<h1>Trapp Family Farm</h1>" +
      '<div class="json-home-grid">' +
      '<div class="json-home-col json-home-story">' +
      bodyParagraphs(aboutRest) +
      renderImages(h.about_our_farm.images) +
      "</div>" +
      '<aside class="json-home-col json-home-aside">' +
      '<div class="json-panel json-panel-journey">' +
      "<h2>Our journey</h2>" +
      "<ul>" +
      journeyItems +
      "</ul>" +
      renderImages(h.our_journey.images, "json-journey-img") +
      "</div>" +
      '<div class="json-panel json-panel-horses" id="draft-horses">' +
      "<h2>" +
      escapeHtml(h.draft_horses.body[0]) +
      "</h2>" +
      "<p class=\"json-pullquote\">" +
      escapeHtml(h.draft_horses.body[1]) +
      "</p>" +
      paragraphHtml(h.draft_horses.body[2]) +
      renderImages(h.draft_horses.images) +
      "</div>" +
      "</aside>" +
      "</div>" +
      "</div>" +
      "</section>"
    );
  }

  function renderCrops(layout) {
    var m = layout.making_the_crops;
    var parts = [];
    parts.push(
      renderSectionBlock(
        "Making the Crops",
        '<div class="json-split">' +
          renderImages(m.intro.images) +
          '<div class="json-prose">' +
          bodyParagraphs(m.intro.body) +
          "</div></div>",
        "intro"
      )
    );
    parts.push(
      renderSectionBlock(
        "Vegetables",
        '<div class="json-split json-split-reverse">' +
          '<div class="json-prose">' +
          bodyParagraphs(m.vegetables.body) +
          "</div>" +
          renderImages(m.vegetables.images) +
          "</div>",
        "vegetables"
      )
    );
    parts.push(
      renderSectionBlock(
        "At the Stand Now",
        renderImages(m.at_the_stand_now.images) + renderBlocks(m.at_the_stand_now.blocks),
        "at-the-stand-now"
      )
    );
    parts.push(
      renderSectionBlock(
        "Setting the Table",
        renderImages(m.setting_the_table.images) + renderBlocks(m.setting_the_table.blocks),
        "setting-the-table"
      )
    );
    return parts.join("");
  }

  function renderAnimals(layout) {
    var a = layout.animal_husbandry;
    var parts = [];
    parts.push(
      renderSectionBlock(
        "Animal Husbandry",
        renderAnimalIntro(a.intro),
        "intro"
      )
    );
    parts.push(
      renderSectionBlock(
        "Layers",
        '<div class="json-split">' +
          renderImages(a.layers.images) +
          '<div class="json-prose">' +
          bodyParagraphs(a.layers.body) +
          "</div></div>",
        "layers"
      )
    );
    parts.push(
      renderSectionBlock(
        "Broilers",
        '<div class="json-split json-split-reverse">' +
          '<div class="json-prose">' +
          bodyParagraphs(a.broilers.body) +
          "</div>" +
          renderImages(a.broilers.images) +
          "</div>",
        "broilers"
      )
    );
    parts.push(
      renderSectionBlock(
        "Turkeys",
        '<div class="json-split">' +
          renderImages(a.turkeys.images) +
          '<div class="json-prose">' +
          bodyParagraphs(a.turkeys.body) +
          "</div></div>",
        "turkeys"
      )
    );
    parts.push(
      renderSectionBlock(
        "Sheep",
        '<div class="json-split json-split-reverse">' +
          '<div class="json-prose">' +
          bodyParagraphs(a.sheep.body) +
          "</div>" +
          renderImages(a.sheep.images) +
          "</div>",
        "sheep"
      )
    );
    return parts.join("");
  }

  function renderHomestead(layout) {
    var f = layout.for_your_homestead;
    var parts = [];
    parts.push(
      renderSectionBlock(
        "For Your Homestead",
        '<div class="json-split">' +
          renderImages(f.intro.images) +
          '<div class="json-prose">' +
          bodyParagraphs(f.intro.body) +
          "</div></div>",
        "intro"
      )
    );
    parts.push(
      renderSectionBlock(
        "Ready-to-Lay Hens",
        '<div class="json-split json-split-reverse">' +
          '<div class="json-prose">' +
          bodyParagraphs(f.ready_to_lay_hens.body) +
          "</div>" +
          renderImages(f.ready_to_lay_hens.images) +
          "</div>",
        "ready-to-lay-hens"
      )
    );
    parts.push(
      renderSectionBlock(
        "Transplants",
        '<div class="json-split">' +
          renderImages(f.transplants.images) +
          '<div class="json-prose">' +
          bodyParagraphs(f.transplants.body) +
          "</div></div>",
        "transplants"
      )
    );
    return parts.join("");
  }

  function renderNewsletters(layout) {
    var n = layout.newsletters;
    var parts = [];
    Object.keys(n).forEach(function (key) {
      if (/-LEAVE_OUT$/.test(key)) return;
      var val = n[key];
      if (Array.isArray(val) && val.length === 0) return;
      if (key === "fall_2024" && val && val.files) {
        parts.push(
          renderSectionBlock(
            "Fall 2024 newsletter",
            renderImages(val.images) +
              '<div class="json-newsletter-md" data-md-src="' +
              escapeHtml(val.files[0].replace(/^\//, "")) +
              '"></div>',
            "fall-2024"
          )
        );
      }
    });
    return parts.join("");
  }

  function renderMoreInfo(layout) {
    var mi = layout.more_info;
    var pods = (mi.podcasts || []).map(renderPodcastEntry).join("");
    var out =
      '<section class="page-section json-page-section" id="podcasts"><div class="container json-container">' +
      '<div class="json-prose json-more-intro">' +
      bodyParagraphs(mi.intro.body) +
      "</div>" +
      '<h2 class="json-section-title">Podcasts, Talks & Tours</h2>' +
      '<div class="json-podcast-list">' +
      pods +
      "</div>" +
      "</div></section>";
    if (mi.news && mi.news.length) {
      out += renderSectionBlock("News", bodyParagraphs(mi.news), "news");
    }
    return out;
  }

  function fetchMarkdownInto(el, url) {
    fetch(url)
      .then(function (r) {
        return r.text();
      })
      .then(function (text) {
        var blocks = text.split(/\n\n+/);
        el.innerHTML = blocks
          .map(function (b) {
            return b.trim() ? paragraphHtml(b.trim()) : "";
          })
          .join("");
      })
      .catch(function () {
        el.innerHTML = "<p>Unable to load newsletter file.</p>";
      });
  }

  function renderFooter(layout, root) {
    var ft = layout.footer;
    var graphic = ft.graphic && ft.graphic[0] ? ft.graphic[0].path.replace(/^\//, "") : "";
    var ig = ft.social[0] || "";
    var igUrl = ig.indexOf("http") === 0 ? ig : "https://www.instagram.com/" + ig.replace(/^instagram\.com\//, "").replace(/^\//, "");
    var copy = ft.copyright && ft.copyright[0] ? ft.copyright[0] : "";
    root.innerHTML =
      '<div class="footer-inner">' +
      '<div class="footer-illustration">' +
      (graphic ? '<img src="' + escapeHtml(graphic) + '" alt="">' : "") +
      "</div>" +
      '<div class="footer-col footer-details">' +
      "<h3>Visit &amp; contact</h3>" +
      "<p>" +
      ft.details
        .map(function (line) {
          if (line.indexOf("@") !== -1) {
            return '<a href="mailto:' + escapeHtml(line) + '">' + escapeHtml(line) + "</a>";
          }
          if (/\(\d{3}\)/.test(line) && /\d{3}[-\s]?\d{4}/.test(line)) {
            var digits = line.replace(/\D/g, "");
            return '<a href="tel:+1' + digits + '">' + escapeHtml(line) + "</a>";
          }
          return escapeHtml(line);
        })
        .join("<br>") +
      "</p>" +
      "</div>" +
      '<div class="footer-col footer-hours">' +
      "<h3>" +
      escapeHtml(ft.farm_stand[0]) +
      "</h3>" +
      "<p>" +
      escapeHtml(ft.farm_stand[1]) +
      "<br>" +
      escapeHtml(ft.farm_stand[2]) +
      "<br>" +
      escapeHtml(ft.farm_stand[3]) +
      "</p>" +
      "</div>" +
      '<div class="footer-col footer-follow">' +
      "<h3>Follow along</h3>" +
      '<p><a class="instagram-link" href="' +
      escapeHtml(igUrl) +
      '" target="_blank" rel="noopener" aria-label="Instagram"><img src="assets/icon/logos/logo-instagram.svg" alt=""></a></p>' +
      "</div>" +
      "</div>" +
      '<div class="footer-bottom"><p>' +
      escapeHtml(copy) +
      "</p></div>";
  }

  function renderNav(layout, navRoot, currentFile) {
    var labels = layout.header.navigation || [];
    var items = labels
      .map(function (label) {
        var href = NAV_MAP[label] || "#";
        var active = href === currentFile;
        var display = NAV_LABEL_DISPLAY[label] || label;
        var cls = active ? ' class="active"' : "";
        return (
          "<li><a href=\"" +
          href +
          '"' +
          cls +
          ">" +
          escapeHtml(display) +
          "</a></li>"
        );
      })
      .join("");
    navRoot.innerHTML = items;
  }

  function setHeroBackground(layout) {
    var path = (layout.site && layout.site.hero_background) || "";
    if (!path) return;
    var rel = path.replace(/^\//, "");
    document.documentElement.style.setProperty("--hero-bg-image", "url('" + rel + "')");
  }

  function renderHeader(layout, headerGraphic, navRoot, currentFile) {
    var g = layout.header.graphic && layout.header.graphic[0];
    var showGraphic =
      currentFile === "home.html" || currentFile === "index.html";
    if (headerGraphic && g) {
      headerGraphic.src = String(g).replace(/^\//, "");
      var wrap = headerGraphic.closest(".header-graphic");
      if (wrap) wrap.style.display = showGraphic ? "" : "none";
    } else if (headerGraphic) {
      var wrapOff = headerGraphic.closest(".header-graphic");
      if (wrapOff) wrapOff.style.display = "none";
    }
    renderNav(layout, navRoot, currentFile);
  }

  function run(layout) {
    var page = document.body.getAttribute("data-page");
    var main = document.getElementById("main-root");
    var footer = document.getElementById("footer-root");
    var nav = document.getElementById("nav-root");
    var headerImg = document.querySelector(".header-graphic img");
    var path = window.location.pathname.split("/").pop() || "index.html";

    setHeroBackground(layout);

    if (page === "home" || page === "index") {
      document.body.classList.add("home-page");
    }

    if (nav) {
      renderHeader(layout, headerImg, nav, path);
    }

    if (main) {
      if (page === "home") main.innerHTML = renderHome(layout);
      else if (page === "crops") main.innerHTML = renderCrops(layout);
      else if (page === "animals") main.innerHTML = renderAnimals(layout);
      else if (page === "homestead") main.innerHTML = renderHomestead(layout);
      else if (page === "newsletters") main.innerHTML = renderNewsletters(layout);
      else if (page === "more_info") main.innerHTML = renderMoreInfo(layout);
      else if (page === "index") {
        main.innerHTML =
          '<section class="hero"><div class="hero-parallax"></div><div class="hero-body"><p class="hero-kicker">Website update in progress</p><h1>Coming soon</h1></div></section>';
      }
    }

    if (footer) renderFooter(layout, footer);

    document.querySelectorAll("[data-md-src]").forEach(function (el) {
      fetchMarkdownInto(el, el.getAttribute("data-md-src"));
    });
  }

  function init() {
    fetch(LAYOUT_URL)
      .then(function (r) {
        if (!r.ok) throw new Error("layout");
        return r.json();
      })
      .then(run)
      .catch(function () {
        var main = document.getElementById("main-root");
        if (main) {
          main.innerHTML =
            '<div class="container"><p>Unable to load site content. Please try again later.</p></div>';
        }
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();

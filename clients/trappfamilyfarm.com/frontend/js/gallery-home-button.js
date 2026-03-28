(function () {
  var script =
    document.currentScript ||
    (function () {
      var scripts = document.getElementsByTagName("script");
      return scripts[scripts.length - 1] || null;
    })();

  if (!script || !script.src) {
    return;
  }

  var frontendRootUrl = new URL("../", script.src);
  var homeUrl = new URL("home.html", frontendRootUrl);
  var indexUrl = new URL("index.html", frontendRootUrl);
  var defaultFaviconUrl = new URL("favicon.svg", frontendRootUrl);

  function resolveFaviconHref() {
    var link = document.querySelector("link[rel='icon']");
    if (link && link.getAttribute("href")) {
      try {
        return new URL(link.getAttribute("href"), window.location.href).href;
      } catch (e) {}
    }
    return defaultFaviconUrl.href;
  }
  var pathname = window.location.pathname;
  var isHomePage =
    pathname === homeUrl.pathname ||
    pathname === indexUrl.pathname ||
    /\/frontend\/$/.test(pathname);

  function ensureFavicon() {
    var selectors = [
      "link[rel='icon']",
      "link[rel='shortcut icon']",
      "link[rel='apple-touch-icon']"
    ];

    selectors.forEach(function (selector) {
      var link = document.querySelector(selector);

      if (!link) {
        link = document.createElement("link");
        if (selector.indexOf("apple-touch-icon") !== -1) {
          link.rel = "apple-touch-icon";
        } else if (selector.indexOf("shortcut") !== -1) {
          link.rel = "shortcut icon";
        } else {
          link.rel = "icon";
          link.type = "image/svg+xml";
        }
        document.head.appendChild(link);
      }

      link.href = resolveFaviconHref();
      if (link.rel === "icon") {
        link.type = "image/svg+xml";
      }
    });
  }

  function ensureStyles() {
    if (document.getElementById("gallery-home-button-styles")) {
      return;
    }

    var style = document.createElement("style");
    style.id = "gallery-home-button-styles";
    style.textContent =
      ".gallery-home-button{" +
      "position:fixed;" +
      "top:1rem;" +
      "right:1rem;" +
      "z-index:2147483647;" +
      "display:inline-flex;" +
      "align-items:center;" +
      "justify-content:center;" +
      "width:64px;" +
      "height:64px;" +
      "padding:0.6rem;" +
      "border-radius:999px;" +
      "background:rgba(255,255,255,0.94);" +
      "border:1px solid rgba(30,41,59,0.18);" +
      "box-shadow:0 12px 30px rgba(15,23,42,0.2);" +
      "backdrop-filter:blur(8px);" +
      "-webkit-backdrop-filter:blur(8px);" +
      "transition:transform 180ms ease, box-shadow 180ms ease, background 180ms ease;" +
      "}" +
      ".gallery-home-button:hover,.gallery-home-button:focus-visible{" +
      "transform:translateY(-2px) scale(1.03);" +
      "box-shadow:0 16px 36px rgba(15,23,42,0.24);" +
      "background:rgba(255,255,255,0.98);" +
      "outline:none;" +
      "}" +
      ".gallery-home-button img{" +
      "display:block;" +
      "width:100%;" +
      "height:100%;" +
      "object-fit:contain;" +
      "}" +
      "@media (max-width: 640px){" +
      ".gallery-home-button{" +
      "top:0.75rem;" +
      "right:0.75rem;" +
      "width:56px;" +
      "height:56px;" +
      "padding:0.5rem;" +
      "}" +
      "}";
    document.head.appendChild(style);
  }

  function ensureButton() {
    if (isHomePage || document.querySelector(".gallery-home-button")) {
      return;
    }

    var button = document.createElement("a");
    var image = document.createElement("img");

    button.className = "gallery-home-button";
    button.href = homeUrl.href;
    button.setAttribute("aria-label", "Back to home");
    button.title = "Back to home";

    image.src = resolveFaviconHref();
    image.alt = "";
    image.setAttribute("aria-hidden", "true");

    button.appendChild(image);
    document.body.appendChild(button);
  }

  function init() {
    if (!document.head || !document.body) {
      return;
    }

    ensureFavicon();
    ensureStyles();
    ensureButton();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();

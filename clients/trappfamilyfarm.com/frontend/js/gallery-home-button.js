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

  function init() {
    if (!document.head) {
      return;
    }
    ensureFavicon();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();

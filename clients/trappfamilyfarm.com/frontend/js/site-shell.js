(function () {
  "use strict";

  function initHeaderBehavior() {
    var header = document.querySelector(".site-header");
    var toggle = document.querySelector(".nav-toggle");
    var drawer = document.getElementById("site-nav-drawer");
    var overlay = document.getElementById("nav-overlay");
    var closeBtn = document.querySelector(".nav-drawer-close");

    if (header) {
      var threshold = 56;
      function updateCompact() {
        if (window.scrollY > threshold) {
          header.classList.add("site-header--compact");
        } else {
          header.classList.remove("site-header--compact");
        }
      }
      window.addEventListener("scroll", updateCompact, { passive: true });
      updateCompact();
    }

    if (!toggle || !drawer || !overlay || !closeBtn) {
      return;
    }

    var lastFocus = null;

    function openDrawer() {
      lastFocus = document.activeElement;
      document.body.classList.add("nav-drawer-open");
      toggle.setAttribute("aria-expanded", "true");
      drawer.setAttribute("aria-hidden", "false");
      overlay.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
      closeBtn.focus();
    }

    function closeDrawer() {
      document.body.classList.remove("nav-drawer-open");
      toggle.setAttribute("aria-expanded", "false");
      drawer.setAttribute("aria-hidden", "true");
      overlay.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
      if (lastFocus && typeof lastFocus.focus === "function") {
        lastFocus.focus();
      }
    }

    toggle.addEventListener("click", function () {
      if (document.body.classList.contains("nav-drawer-open")) {
        closeDrawer();
      } else {
        openDrawer();
      }
    });
    closeBtn.addEventListener("click", closeDrawer);
    overlay.addEventListener("click", closeDrawer);
    drawer.addEventListener("click", function (event) {
      if (event.target.closest("a")) {
        closeDrawer();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && document.body.classList.contains("nav-drawer-open")) {
        closeDrawer();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initHeaderBehavior, { once: true });
  } else {
    initHeaderBehavior();
  }
})();

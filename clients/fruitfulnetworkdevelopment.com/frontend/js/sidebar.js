/**
 * Sidebar Navigation
 * Loads the sidebar HTML and manages open/close behavior.
 * Works from any directory depth by computing the path dynamically.
 */

const getSidebarPath = () => {
  const path = window.location.pathname;
  // If the page is inside a subdirectory (e.g., /subpages/), adjust the path
  if (path.includes('/subpages/')) {
    return 'sidebar.html';
  }
  return 'subpages/sidebar.html';
};

const setExpanded = (buttons, isExpanded) => {
  buttons.forEach((button) => {
    button.setAttribute("aria-expanded", String(isExpanded));
  });
};

const setupSidebar = (overlay, toggleButtons) => {
  const closeButton = overlay.querySelector(".sidebar__close");

  const openSidebar = () => {
    overlay.classList.add("is-open");
    overlay.setAttribute("aria-hidden", "false");
    document.body.classList.add("sidebar-open");
    setExpanded(toggleButtons, true);
  };

  const closeSidebar = () => {
    overlay.classList.remove("is-open");
    overlay.setAttribute("aria-hidden", "true");
    document.body.classList.remove("sidebar-open");
    setExpanded(toggleButtons, false);
  };

  toggleButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (overlay.classList.contains("is-open")) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  });

  if (closeButton) {
    closeButton.addEventListener("click", closeSidebar);
  }

  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) {
      closeSidebar();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && overlay.classList.contains("is-open")) {
      closeSidebar();
    }
  });
};

document.addEventListener("DOMContentLoaded", () => {
  const toggleButtons = Array.from(document.querySelectorAll(".header__button--sidebar"));

  if (toggleButtons.length === 0) {
    return;
  }

  const sidebarPath = getSidebarPath();

  fetch(sidebarPath)
    .then((response) => response.text())
    .then((html) => {
      document.body.insertAdjacentHTML("beforeend", html);
      const overlay = document.getElementById("sidebar-overlay");

      if (!overlay) {
        return;
      }

      setupSidebar(overlay, toggleButtons);
    })
    .catch((error) => {
      console.warn("Sidebar failed to load", error);
    });
});

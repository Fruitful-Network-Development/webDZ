(() => {
  const navbar = document.querySelector(".navbar");
  if (!navbar) return;

  const toggle = navbar.querySelector("[data-nav-toggle]");
  const nav = navbar.querySelector(".nav");

  const setOpen = (isOpen) => {
    navbar.classList.toggle("is-open", isOpen);
    if (toggle) toggle.setAttribute("aria-expanded", String(isOpen));
  };

  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      setOpen(!navbar.classList.contains("is-open"));
    });

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      setOpen(false);
    });

    document.addEventListener("click", (event) => {
      if (!navbar.classList.contains("is-open")) return;
      if (navbar.contains(event.target)) return;
      setOpen(false);
    });
  }

  const path = (location.pathname || "").split("/").pop() || "index.html";
  for (const link of navbar.querySelectorAll(".nav a[href]")) {
    const href = link.getAttribute("href") || "";
    if (
      href.startsWith("http:") ||
      href.startsWith("https:") ||
      href.startsWith("mailto:") ||
      href.startsWith("tel:") ||
      href.startsWith("#")
    ) {
      continue;
    }
    const hrefFile = href.split("#")[0].split("?")[0].split("/").pop();
    if (!hrefFile) continue;
    if (hrefFile === path) link.classList.add("is-active");
    if ((path === "" || path === "/") && hrefFile === "index.html") link.classList.add("is-active");
  }
})();


(() => {
  async function submitNewsletterForm(form, ack) {
    const data = new FormData(form);
    const response = await fetch("/__fnd/newsletter/subscribe", {
      method: "POST",
      headers: {
        Accept: "application/json",
      },
      body: new URLSearchParams(data),
      credentials: "same-origin",
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload || payload.ok === false) {
      throw new Error(String((payload && (payload.error || payload.message)) || `HTTP ${response.status}`));
    }
    if (ack) {
      ack.hidden = false;
      ack.textContent = "Thanks. Your address is now in the live contact log and marked subscribed.";
    }
    form.reset();
  }

  function bindSignupForms() {
    [
      ["home-newsletter-form", "home-newsletter-ack"],
      ["newsletter-form", "newsletter-ack"],
    ].forEach(([formId, ackId]) => {
      const form = document.getElementById(formId);
      const ack = document.getElementById(ackId);
      if (!form || !ack) return;
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        try {
          await submitNewsletterForm(form, ack);
        } catch (error) {
          ack.hidden = false;
          ack.textContent = error && error.message ? error.message : "Signup failed.";
        }
      });
    });
    document.querySelectorAll(".footer-newsletter").forEach((form) => {
      let ack = form.nextElementSibling;
      if (!(ack instanceof HTMLElement) || !ack.classList.contains("form-note")) {
        ack = document.createElement("p");
        ack.className = "form-note";
        ack.hidden = true;
        form.insertAdjacentElement("afterend", ack);
      }
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        try {
          await submitNewsletterForm(form, ack);
        } catch (error) {
          ack.hidden = false;
          ack.textContent = error && error.message ? error.message : "Signup failed.";
        }
      });
    });
  }

  function bindFarmCards() {
    document.querySelectorAll(".card-farm[data-href]").forEach((card) => {
      card.tabIndex = 0;
      card.addEventListener("click", (event) => {
        if (event.target.closest("a")) return;
        window.location.href = card.dataset.href;
      });
      card.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          window.location.href = card.dataset.href;
        }
      });
    });
  }

  function bindNewsletterArchive() {
    const archive = document.querySelector("[data-newsletter-archive]");
    if (!(archive instanceof HTMLElement)) return;

    const viewer = document.getElementById("newsletter-viewer");
    if (!(viewer instanceof HTMLElement)) return;

    const defaultSlug = archive.dataset.defaultSlug || "";
    const templates = new Map(
      Array.from(archive.querySelectorAll("template[data-newsletter-template]"))
        .filter((template) => template instanceof HTMLTemplateElement)
        .map((template) => [template.dataset.newsletterTemplate || "", template]),
    );
    const cards = Array.from(archive.querySelectorAll(".newsletter-card--compact[data-post-id]"));
    const pageButtons = Array.from(archive.querySelectorAll("[data-newsletter-page]"));
    const prevButton = archive.querySelector("[data-newsletter-prev]");
    const nextButton = archive.querySelector("[data-newsletter-next]");

    let currentPage = 1;
    const maxPage = Math.max(
      1,
      ...cards.map((card) => Number.parseInt(card.dataset.page || "1", 10)).filter(Number.isFinite),
    );

    function setActiveCard(slug) {
      cards.forEach((card) => {
        const isActive = card.dataset.postId === slug;
        card.classList.toggle("is-active", isActive);
        if (card instanceof HTMLElement) {
          card.setAttribute("aria-current", isActive ? "true" : "false");
        }
      });
    }

    function renderPost(slug) {
      const template = templates.get(slug);
      if (!(template instanceof HTMLTemplateElement)) return false;
      viewer.innerHTML = template.innerHTML;
      setActiveCard(slug);
      return true;
    }

    function setPage(page) {
      currentPage = Math.min(Math.max(page, 1), maxPage);
      cards.forEach((card) => {
        card.hidden = Number.parseInt(card.dataset.page || "1", 10) !== currentPage;
      });
      pageButtons.forEach((button) => {
        const pageNumber = Number.parseInt(button.dataset.newsletterPage || "1", 10);
        const isCurrent = pageNumber === currentPage;
        button.classList.toggle("is-active", isCurrent);
        button.setAttribute("aria-current", isCurrent ? "page" : "false");
      });
      if (prevButton instanceof HTMLButtonElement) prevButton.disabled = currentPage <= 1;
      if (nextButton instanceof HTMLButtonElement) nextButton.disabled = currentPage >= maxPage;
    }

    function syncFromHash() {
      const slug = window.location.hash.replace(/^#/, "") || defaultSlug;
      if (!slug) return;
      if (renderPost(slug)) {
        const matchingCard = cards.find((card) => card.dataset.postId === slug);
        if (matchingCard) {
          const page = Number.parseInt(matchingCard.dataset.page || "1", 10);
          if (Number.isFinite(page)) setPage(page);
        }
      }
    }

    archive.addEventListener("click", (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const pageButton = target.closest("[data-newsletter-page]");
      if (pageButton instanceof HTMLButtonElement) {
        setPage(Number.parseInt(pageButton.dataset.newsletterPage || "1", 10));
        return;
      }
      if (target.closest("[data-newsletter-prev]")) {
        setPage(currentPage - 1);
        return;
      }
      if (target.closest("[data-newsletter-next]")) {
        setPage(currentPage + 1);
      }
    });

    setPage(1);
    syncFromHash();
    window.addEventListener("hashchange", syncFromHash);
  }

  function init() {
    bindSignupForms();
    bindFarmCards();
    bindNewsletterArchive();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

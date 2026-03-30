(() => {
  function bindSignupForms() {
    [
      ["home-newsletter-form", "home-newsletter-ack"],
      ["newsletter-form", "newsletter-ack"],
    ].forEach(([formId, ackId]) => {
      const form = document.getElementById(formId);
      const ack = document.getElementById(ackId);
      if (!form || !ack) return;
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        ack.hidden = false;
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

  function init() {
    bindSignupForms();
    bindFarmCards();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

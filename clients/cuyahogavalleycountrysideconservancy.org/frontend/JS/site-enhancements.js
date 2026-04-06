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

(function () {
  const collectCitationIds = (container) => {
    const direct = (container?.dataset?.citationIds || "")
      .split(",")
      .map((id) => id.trim())
      .filter(Boolean);

    const cards = Array.from(document.querySelectorAll("[data-citation-ids]"));
    const fromCards = cards.flatMap((node) =>
      (node.dataset.citationIds || "")
        .split(",")
        .map((id) => id.trim())
        .filter(Boolean)
    );

    return Array.from(new Set([...direct, ...fromCards]));
  };

  const render = async () => {
    const target = document.querySelector("[data-machine='citations']");
    if (!target || !window.FNDCitations) return;

    try {
      const [references] = await Promise.all([window.FNDCitations.loadReferences()]);
      const citationIds = collectCitationIds(target);
      const selected = citationIds.length
        ? (references.sources || []).filter((source) => citationIds.includes(source.id))
        : (references.sources || []);

      window.FNDCitations.renderCitationMachineBlock(target, {
        page: window.location.pathname,
        citation_ids: citationIds,
        references: selected,
        evidence_policy: "non-promotional, evidence-oriented references only"
      });

      window.FNDCitations.applyOutboundLinkGovernance(document);
    } catch (_err) {
      // intentionally silent: machine block is additive
    }
  };

  document.addEventListener("DOMContentLoaded", render);
})();

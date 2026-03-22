(function (global) {
  function sanitizeMdArtifacts(text) {
    if (!text) return "";
    let s = text
      .replace(/\uE200entity\uE202[\s\S]*?\]\uE201/g, "")
      .replace(/\uE200cite\uE202[\s\S]*?\uE201/g, "")
      .replace(
        /\uE200image_group\uE202\{[\s\S]*?\}\uE201/g,
        "\n\n*Illustration references are omitted here; use the linked primary sources in each section for images.*\n\n"
      );
    s = s.replace(
      /```mermaid[\s\S]*?```/g,
      "\n\n> *Diagram omitted; see the comparison table in this document for key dates.*\n\n"
    );
    s = s.replace(/^##\s+(.+?)\s+around\s*$/gm, "## $1");
    s = s.replace(/^##\s{2,}/gm, "## ");
    return s;
  }

  global.sanitizeMdArtifacts = sanitizeMdArtifacts;
})(typeof window !== "undefined" ? window : globalThis);

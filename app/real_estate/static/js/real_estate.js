/* Real estate analytics helpers. */
document.addEventListener("DOMContentLoaded", () => {
  const propertyCards = document.querySelectorAll(".property-card");
  const prospectRows = document.querySelectorAll(".prospects__table tbody tr");

  if (propertyCards.length) {
    const sorted = Array.from(propertyCards).sort((a, b) => {
      return Number(b.dataset.value || 0) - Number(a.dataset.value || 0);
    });
    sorted[0].classList.add("is-top");
  }

  prospectRows.forEach((row) => {
    const score = Number(row.dataset.score || 0);
    if (score >= 80) {
      row.classList.add("highlight");
    }
    row.querySelectorAll("td").forEach((cell) => {
      const label = cell.getAttribute("data-label");
      if (label) {
        cell.setAttribute("aria-label", `${label}: ${cell.textContent.trim()}`);
      }
    });
  });
});

/* Job workspace enhancements. */
document.addEventListener("DOMContentLoaded", () => {
  const rows = document.querySelectorAll(".schedule__table tbody tr");
  const toggle = document.querySelector(".hours-toggle");
  const weeklyTotal = document.getElementById("weekly-total");

  const calculateTotal = () => {
    const total = Array.from(rows).reduce((sum, row) => sum + Number(row.dataset.hours || 0), 0);
    if (weeklyTotal) {
      weeklyTotal.textContent = `${total} hrs`;
    }
  };

  const highlightFocus = (expanded) => {
    rows.forEach((row) => {
      const hours = Number(row.dataset.hours || 0);
      row.classList.toggle("focus", expanded && hours >= 4);
      row.querySelectorAll("td").forEach((cell) => {
        const label = cell.getAttribute("data-label");
        if (label) {
          cell.setAttribute("aria-label", `${label}: ${cell.textContent.trim()}`);
        }
      });
    });
  };

  if (toggle) {
    toggle.addEventListener("click", () => {
      const expanded = toggle.classList.toggle("is-expanded");
      toggle.textContent = expanded ? "Collapse hours" : "Expand hours";
      highlightFocus(expanded);
    });
  }

  calculateTotal();
  highlightFocus(false);
});

/* Job workspace enhancements. */
document.addEventListener("DOMContentLoaded", () => {
  const jobTabs = document.querySelectorAll("[data-job-tab]");
  const jobPanels = document.querySelectorAll("[data-job-panel]");
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

  const activateTab = (target) => {
    if (!target) {
      return;
    }

    jobTabs.forEach((tab) => {
      const isActive = tab.dataset.jobTab === target;
      tab.classList.toggle("is-active", isActive);
      if (isActive) {
        tab.setAttribute("aria-current", "page");
      } else {
        tab.removeAttribute("aria-current");
      }
    });

    jobPanels.forEach((panel) => {
      const show = panel.dataset.jobPanel === target;
      panel.classList.toggle("is-active", show);
      if (show) {
        panel.removeAttribute("hidden");
      } else {
        panel.setAttribute("hidden", "hidden");
      }
    });

    if (target === "manage") {
      calculateTotal();
      const expanded = toggle ? toggle.classList.contains("is-expanded") : false;
      highlightFocus(expanded);
    }
  };

  if (toggle) {
    toggle.addEventListener("click", () => {
      const expanded = toggle.classList.toggle("is-expanded");
      toggle.textContent = expanded ? "Collapse hours" : "Expand hours";
      highlightFocus(expanded);
    });
  }

  jobTabs.forEach((tab) => {
    tab.addEventListener("click", (event) => {
      event.preventDefault();
      activateTab(tab.dataset.jobTab);
    });
  });

  const initialTab = document.querySelector("[data-job-tab].is-active") || jobTabs[0];
  if (initialTab) {
    activateTab(initialTab.dataset.jobTab);
  }

  calculateTotal();
  highlightFocus(false);
});

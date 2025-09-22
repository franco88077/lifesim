/* Job workspace enhancements. */
document.addEventListener("DOMContentLoaded", () => {
  const jobTabs = document.querySelectorAll("[data-job-tab]");
  const jobPanels = document.querySelectorAll("[data-job-panel]");
  const rows = document.querySelectorAll(".schedule__table tbody tr");
  const toggle = document.querySelector(".hours-toggle");
  const weeklyTotal = document.getElementById("weekly-total");
  const toastContainer = document.getElementById("toast-container");

  const pushToast = (level, title, message) => {
    if (!toastContainer) {
      return;
    }

    const toast = document.createElement("div");
    toast.className = `toast ${level}`;
    toast.innerHTML = `<strong>${title}</strong><br />${message}`;
    toastContainer.append(toast);

    setTimeout(() => {
      toast.classList.add("fade");
      setTimeout(() => toast.remove(), 400);
    }, 4000);
  };

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

  const chipInputs = document.querySelectorAll(".job-chip input");
  const syncChipState = (input) => {
    if (!input) {
      return;
    }
    if (input.type === "radio") {
      const group = document.querySelectorAll(`input[name="${input.name}"]`);
      group.forEach((radio) => {
        const chip = radio.closest(".job-chip");
        if (chip) {
          chip.classList.toggle("is-active", radio.checked);
        }
      });
    } else {
      const chip = input.closest(".job-chip");
      if (chip) {
        chip.classList.toggle("is-active", input.checked);
      }
    }
  };

  chipInputs.forEach((input) => {
    syncChipState(input);
    input.addEventListener("change", () => syncChipState(input));
  });

  const payTypeRadios = document.querySelectorAll('input[name="pay_type"]');
  const payFields = document.querySelectorAll("[data-pay-field]");
  const hourlyInput = document.getElementById("job-hourly-rate");
  const taskInput = document.getElementById("job-task-rate");
  const dailyLimitInput = document.getElementById("job-daily-limit");
  const payPreview = document.querySelector("[data-pay-preview]");
  const currency = window.Intl
    ? new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      })
    : null;

  const setPayFieldVisibility = (type) => {
    payFields.forEach((field) => {
      const show = field.dataset.payField === type;
      if (show) {
        field.removeAttribute("hidden");
      } else {
        field.setAttribute("hidden", "hidden");
      }
    });
  };

  const enforceMinimum = (input) => {
    if (!input) {
      return;
    }
    const minimum = Number(input.dataset.minimum || 0);
    const value = Number(input.value || 0);
    if (minimum && value && value < minimum) {
      input.value = minimum;
      pushToast(
        "warn",
        "Minimum enforced",
        `Rates cannot fall below ${currency ? currency.format(minimum) : `$${minimum}`}.`
      );
    }
  };

  const describePay = (amount, unit) => {
    const formatted = currency ? currency.format(amount) : `$${amount}`;
    return `${formatted} per ${unit}`;
  };

  const updatePayPreview = () => {
    if (!payPreview) {
      return;
    }

    const selected = document.querySelector('input[name="pay_type"]:checked');
    const payType = selected ? selected.value : "hourly";
    const limit = dailyLimitInput ? Number(dailyLimitInput.value || dailyLimitInput.dataset.dailyLimit || 0) : 0;

    if (payType === "hourly" && hourlyInput) {
      const rate = Number(hourlyInput.value || 0);
      payPreview.textContent = rate
        ? `${describePay(rate, "hour")} · ${limit || "∞"} completions/day max.`
        : "Enter an hourly rate to calculate daily earnings.";
      return;
    }

    if (payType === "task" && taskInput) {
      const payout = Number(taskInput.value || 0);
      payPreview.textContent = payout
        ? `${describePay(payout, "task")} · ${limit || "∞"} completions/day max.`
        : "Enter a task payout to calculate daily earnings.";
      return;
    }

    payPreview.textContent = "Set a rate to preview projected earnings and guardrail checks.";
  };

  payTypeRadios.forEach((radio) => {
    radio.addEventListener("change", () => {
      setPayFieldVisibility(radio.value);
      syncChipState(radio);
      updatePayPreview();
    });
  });

  [hourlyInput, taskInput].forEach((input) => {
    if (!input) {
      return;
    }
    input.addEventListener("blur", () => {
      enforceMinimum(input);
      updatePayPreview();
    });
    input.addEventListener("input", updatePayPreview);
  });

  if (dailyLimitInput) {
    dailyLimitInput.addEventListener("input", updatePayPreview);
    dailyLimitInput.addEventListener("blur", () => {
      const minimum = Number(dailyLimitInput.min || 1);
      const current = Number(dailyLimitInput.value || 0);
      if (current < minimum) {
        dailyLimitInput.value = minimum;
        pushToast(
          "warn",
          "Daily limit enforced",
          `Jobs must allow at least ${minimum} completion${minimum === 1 ? "" : "s"} per day.`
        );
      }
      updatePayPreview();
    });
  }

  const initialPayType = document.querySelector('input[name="pay_type"]:checked');
  if (initialPayType) {
    setPayFieldVisibility(initialPayType.value);
  }
  updatePayPreview();

  const jobRows = document.querySelectorAll("[data-job-row]");
  jobRows.forEach((row) => {
    const completeButton = row.querySelector("[data-complete-job]");
    if (!completeButton) {
      return;
    }

    const limit = Number(row.dataset.limit || 0);
    const completed = Number(row.dataset.completed || 0);
    if (limit && completed >= limit) {
      row.classList.add("at-capacity");
      completeButton.setAttribute("disabled", "disabled");
    }

    completeButton.addEventListener("click", () => {
      const title = row.dataset.jobTitle || "Job";
      const max = Number(row.dataset.limit || 0);
      let current = Number(row.dataset.completed || 0);

      if (!max) {
        pushToast("warn", "Daily limit missing", `${title} does not have a daily limit configured.`);
        return;
      }

      if (current >= max) {
        row.classList.add("at-capacity");
        completeButton.setAttribute("disabled", "disabled");
        pushToast("warn", "Limit reached", `${title} has already hit its ${max}× daily limit.`);
        return;
      }

      current += 1;
      row.dataset.completed = String(current);
      const count = row.querySelector("[data-progress-count]");
      if (count) {
        count.textContent = current;
      }
      const fill = row.querySelector("[data-progress-fill]");
      if (fill) {
        const width = Math.min(100, Math.round((current / max) * 100));
        fill.style.width = `${width}%`;
      }
      const progress = row.querySelector(".job-progress");
      if (progress) {
        progress.setAttribute("aria-label", `${current} of ${max} complete`);
      }

      if (current >= max) {
        row.classList.add("at-capacity");
        completeButton.setAttribute("disabled", "disabled");
        pushToast("warn", "Limit reached", `${title} has reached its ${max}× daily limit.`);
      } else {
        const remaining = max - current;
        pushToast(
          "info",
          "Completion logged",
          `${title} marked complete. ${remaining} remaining today.`
        );
      }
    });
  });

  const initialTab = document.querySelector("[data-job-tab].is-active") || jobTabs[0];
  if (initialTab) {
    activateTab(initialTab.dataset.jobTab);
  }

  calculateTotal();
  highlightFocus(false);
});

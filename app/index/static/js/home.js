/* Interactions for the Lifesim home dashboard. */
document.addEventListener("DOMContentLoaded", () => {
  const metrics = document.querySelectorAll(".metric");
  const timelineItems = document.querySelectorAll(".timeline__list li");
  const openAccountButton = document.querySelector("[data-open-account]");
  const modal = document.getElementById("account-opening-modal");
  const modalBackdrop = document.querySelector("[data-modal-backdrop]");
  const modalForm = document.getElementById("account-opening-form");
  const modalFeedback = document.querySelector("[data-modal-feedback]");
  const closeModalButtons = document.querySelectorAll("[data-close-modal]");
  const submitButton = document.querySelector("[data-submit-button]");
  const configElement = document.getElementById("account-opening-config");
  const accountOptions = document.querySelectorAll("[data-account-option]");
  const depositSections = document.querySelectorAll("[data-deposit-section]");

  const defaultConfig = { available_cash: 0, requirements: {}, endpoint: "" };
  let openingConfig = defaultConfig;

  if (configElement) {
    try {
      const raw = configElement.textContent?.trim() || "";
      openingConfig = raw ? JSON.parse(raw) : defaultConfig;
    } catch (error) {
      openingConfig = defaultConfig;
      console.error("Failed to parse account opening config", error);
    }
  }

  const formatCurrency = (value) => {
    const number = Number.parseFloat(value);
    const safe = Number.isFinite(number) ? number : 0;
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(safe);
  };

  const showModal = () => {
    if (!modal || !modalBackdrop) {
      return;
    }
    modal.hidden = false;
    modalBackdrop.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    const focusTarget = modal.querySelector("[data-account-option]") || modal;
    focusTarget.focus();
  };

  const hideModal = () => {
    if (!modal || !modalBackdrop) {
      return;
    }
    modal.hidden = true;
    modalBackdrop.hidden = true;
    modal.setAttribute("aria-hidden", "true");
    if (modalForm) {
      modalForm.reset();
    }
    depositSections.forEach((section) => {
      section.hidden = true;
      const input = section.querySelector("input");
      if (input) {
        input.value = "";
      }
    });
    if (modalFeedback) {
      modalFeedback.hidden = true;
      modalFeedback.textContent = "";
      modalFeedback.dataset.state = "";
    }
  };

  const toggleDepositSection = (checkbox) => {
    if (!checkbox) return;
    const account = checkbox.value;
    const section = modal?.querySelector(`[data-deposit-section="${account}"]`);
    const input = modal?.querySelector(`[data-deposit-input="${account}"]`);
    if (!section || !input) {
      return;
    }
    if (checkbox.checked) {
      const minimum = openingConfig.requirements?.[account] ?? 0;
      section.hidden = false;
      input.value = minimum ? minimum.toFixed(2) : "";
      input.min = minimum ? minimum.toFixed(2) : "0";
      input.focus();
    } else {
      section.hidden = true;
      input.value = "";
    }
  };

  const hideFeedback = () => {
    if (!modalFeedback) return;
    modalFeedback.hidden = true;
    modalFeedback.textContent = "";
    modalFeedback.dataset.state = "";
  };

  const displayFeedback = (message, state = "error") => {
    if (!modalFeedback) return;
    modalFeedback.textContent = message;
    modalFeedback.dataset.state = state;
    modalFeedback.hidden = false;
  };

  const collectSelections = () => {
    const selections = {};
    accountOptions.forEach((option) => {
      if (!option.checked) {
        return;
      }
      const account = option.value;
      const input = modal?.querySelector(`[data-deposit-input="${account}"]`);
      if (!input) {
        return;
      }
      const value = Number.parseFloat(input.value);
      selections[account] = Number.isFinite(value) ? value : NaN;
    });
    return selections;
  };

  const validateSelections = (selections) => {
    const errors = [];
    const requirements = openingConfig.requirements || {};
    let total = 0;

    Object.entries(selections).forEach(([account, amount]) => {
      if (!Number.isFinite(amount) || amount <= 0) {
        errors.push(`Enter a valid deposit for the ${account} account.`);
        return;
      }
      const minimum = requirements?.[account] ?? 0;
      if (amount < minimum) {
        errors.push(
          `Deposit at least ${formatCurrency(minimum)} for the ${account} account.`
        );
      }
      total += amount;
    });

    if (!Object.keys(selections).length) {
      errors.push("Select at least one account to open.");
    }

    if (total > (openingConfig.available_cash ?? 0)) {
      errors.push(
        `Cash only has ${formatCurrency(openingConfig.available_cash)} available. Reduce the deposits.`
      );
    }

    return errors;
  };

  const submitForm = async (event) => {
    event.preventDefault();
    if (!modalForm || !submitButton) {
      return;
    }

    hideFeedback();
    const selections = collectSelections();
    const errors = validateSelections(selections);

    if (errors.length) {
      displayFeedback(errors.join(" "), "error");
      return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Opening...";

    try {
      const response = await fetch(openingConfig.endpoint || "/banking/api/accounts/open", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accounts: Object.fromEntries(
          Object.entries(selections).map(([account, amount]) => [account, { deposit: amount }])
        ) }),
      });

      const payload = await response.json();

      if (!response.ok || !payload.success) {
        const message = payload?.message || "Unable to open accounts right now.";
        displayFeedback(message, "error");
        return;
      }

      displayFeedback(payload.message || "Accounts opened successfully.", "success");
      setTimeout(() => {
        window.location.reload();
      }, 1200);
    } catch (error) {
      console.error("Failed to open accounts", error);
      displayFeedback("A network error occurred. Please try again shortly.", "error");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Open Selected Accounts";
    }
  };

  if (openAccountButton) {
    openAccountButton.addEventListener("click", () => {
      depositSections.forEach((section) => {
        section.hidden = true;
        const input = section.querySelector("input");
        if (input) {
          input.value = "";
        }
      });
      showModal();
    });
  }

  closeModalButtons.forEach((button) => {
    button.addEventListener("click", () => {
      hideModal();
      if (openAccountButton) {
        openAccountButton.focus();
      }
    });
  });

  if (modalBackdrop) {
    modalBackdrop.addEventListener("click", hideModal);
  }

  accountOptions.forEach((option) => {
    option.addEventListener("change", () => toggleDepositSection(option));
  });

  if (modalForm) {
    modalForm.addEventListener("submit", submitForm);
    modalForm.addEventListener("input", hideFeedback);
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal && !modal.hidden) {
      hideModal();
      if (openAccountButton) {
        openAccountButton.focus();
      }
    }
  });

  metrics.forEach((metric) => {
    metric.setAttribute("tabindex", "0");
    const toggleActive = () => metric.classList.toggle("is-active");
    metric.addEventListener("click", toggleActive);
    metric.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        toggleActive();
      }
    });
  });

  let highlightIndex = 0;
  const cycleTimeline = () => {
    timelineItems.forEach((item, index) => {
      item.classList.toggle("is-highlighted", index === highlightIndex);
    });
    highlightIndex = (highlightIndex + 1) % timelineItems.length;
  };

  if (timelineItems.length) {
    setInterval(cycleTimeline, 6000);
    cycleTimeline();
  }
});

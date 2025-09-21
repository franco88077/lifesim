/* Banking transfer interactivity. */
document.addEventListener("DOMContentLoaded", () => {
  const dataElement = document.getElementById("banking-data");
  const accountCards = document.querySelectorAll("[data-account-card]");
  const ledgerBody = document.querySelector("[data-ledger-body]");
  const ledgerEmpty = document.querySelector("[data-ledger-empty]");
  const transferForm = document.getElementById("form-account-transfer");
  const sourceSelect = document.querySelector("[data-transfer-source]");
  const destinationSelect = document.querySelector("[data-transfer-destination]");
  const amountInput = document.getElementById("account-transfer-amount");
  const summaryElement = document.querySelector("[data-transfer-summary]");
  const guidelinesContainer = document.querySelector("[data-transfer-guidelines]");
  const guidelineSource = guidelinesContainer?.querySelector('[data-guideline="source"]');
  const guidelineDestination = guidelinesContainer?.querySelector('[data-guideline="destination"]');

  const createEmptyState = () => ({ balances: {}, transactions: [], account_labels: {}, requirements: {} });
  let state = createEmptyState();

  if (dataElement) {
    try {
      const raw = dataElement.textContent.trim();
      state = raw ? JSON.parse(raw) : createEmptyState();
    } catch (error) {
      console.error("Failed to parse banking data", error);
      state = createEmptyState();
    }
  }

  const formatCurrency = (value) => {
    const number = Number.parseFloat(value);
    const safeNumber = Number.isFinite(number) ? number : 0;
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(safeNumber);
  };

  const getAccountLabel = (accountId) => {
    if (!accountId) return "";
    return state.account_labels?.[accountId] || accountId;
  };

  const getRequirements = (accountId) => {
    if (!accountId) return null;
    return state.requirements?.[accountId] || null;
  };

  const toOrdinal = (value) => {
    const number = Number.parseInt(value, 10);
    if (!Number.isFinite(number) || number <= 0) {
      return String(value);
    }
    const mod100 = number % 100;
    if (mod100 >= 11 && mod100 <= 13) {
      return `${number}th`;
    }
    const mod10 = number % 10;
    if (mod10 === 1) return `${number}st`;
    if (mod10 === 2) return `${number}nd`;
    if (mod10 === 3) return `${number}rd`;
    return `${number}th`;
  };

  const buildGuidelineMessage = (accountId, role) => {
    if (!accountId) {
      return "";
    }

    if (accountId === "hand") {
      if (role === "source") {
        return "Cash withdrawals are kept off the ledger; only the receiving account records the debit.";
      }
      return "Cash keeps day-to-day liquidity ready. Track purchases manually to stay aligned.";
    }

    const requirements = getRequirements(accountId);
    if (!requirements) {
      return role === "source"
        ? `Transfers from ${getAccountLabel(accountId)} are logged immediately.`
        : `Deposits into ${getAccountLabel(accountId)} appear in its transaction history.`;
    }

    const minimum = formatCurrency(requirements.minimum_balance);
    const fee = formatCurrency(requirements.fee);
    const anchor = toOrdinal(requirements.anchor_day);

    if (role === "source") {
      return `Keep ${minimum} in ${getAccountLabel(accountId)} or a ${fee} fee posts on the ${anchor} of each cycle.`;
    }
    return `Arriving funds help ${getAccountLabel(accountId)} stay above ${minimum} and dodge the ${fee} fee on the ${anchor}.`;
  };

  const updateCards = () => {
    accountCards.forEach((card) => {
      const accountId = card.dataset.account;
      const balance = state.balances?.[accountId]?.balance ?? 0;
      const display = card.querySelector("[data-balance-value]");
      if (display) {
        display.textContent = formatCurrency(balance);
      }
      card.setAttribute("data-balance", balance.toFixed(2));
    });
  };

  const renderTransactions = () => {
    if (!ledgerBody) {
      return;
    }

    ledgerBody.innerHTML = "";

    if (!state.transactions.length) {
      if (ledgerEmpty) {
        ledgerEmpty.hidden = false;
      }
      return;
    }

    if (ledgerEmpty) {
      ledgerEmpty.hidden = true;
    }

    state.transactions.forEach((transaction) => {
      const row = document.createElement("tr");
      row.dataset.direction = transaction.direction;
      const amountDisplay = `${transaction.direction === "credit" ? "+" : "−"}${formatCurrency(transaction.amount)}`;
      row.innerHTML = `
        <td>${transaction.name}</td>
        <td>${transaction.description}</td>
        <td>${getAccountLabel(transaction.account)}</td>
        <td class="transaction-amount ${transaction.direction}">${amountDisplay}</td>
      `;
      ledgerBody.append(row);
    });
  };

  const hideFeedback = (form) => {
    const feedback = form?.querySelector("[data-feedback]");
    if (feedback) {
      feedback.hidden = true;
      feedback.textContent = "";
      feedback.dataset.state = "";
    }
  };

  const showFeedback = (form, message, type) => {
    const feedback = form?.querySelector("[data-feedback]");
    if (!feedback) {
      return;
    }
    feedback.textContent = message;
    feedback.dataset.state = type;
    feedback.hidden = false;
    if (type === "success") {
      setTimeout(() => {
        feedback.hidden = true;
      }, 3500);
    }
  };

  const sanitizeAmount = (value) => {
    const parsed = Number.parseFloat(value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return NaN;
    }
    return Math.round(parsed * 100) / 100;
  };

  const syncDisabledOptions = () => {
    if (!sourceSelect || !destinationSelect) {
      return;
    }
    const sourceValue = sourceSelect.value;
    const destinationValue = destinationSelect.value;

    Array.from(sourceSelect.options).forEach((option) => {
      if (!option.value) return;
      option.disabled = option.value === destinationValue;
    });

    Array.from(destinationSelect.options).forEach((option) => {
      if (!option.value) return;
      option.disabled = option.value === sourceValue;
    });
  };

  const updateGuidelines = () => {
    if (!guidelinesContainer) {
      return;
    }

    const sourceValue = sourceSelect?.value;
    const destinationValue = destinationSelect?.value;

    if (guidelineSource) {
      if (sourceValue) {
        guidelineSource.textContent = buildGuidelineMessage(sourceValue, "source");
        guidelineSource.hidden = false;
      } else {
        guidelineSource.textContent = "";
        guidelineSource.hidden = true;
      }
    }

    if (guidelineDestination) {
      if (destinationValue) {
        guidelineDestination.textContent = buildGuidelineMessage(destinationValue, "destination");
        guidelineDestination.hidden = false;
      } else {
        guidelineDestination.textContent = "";
        guidelineDestination.hidden = true;
      }
    }

    const hasContent = Boolean(sourceValue || destinationValue);
    guidelinesContainer.dataset.state = hasContent ? "active" : "idle";
  };

  const updateSummary = () => {
    if (!summaryElement) {
      return;
    }

    const sourceValue = sourceSelect?.value;
    const destinationValue = destinationSelect?.value;
    const amountValue = amountInput?.value;
    const amount = sanitizeAmount(amountValue);

    summaryElement.dataset.state = "info";

    if (!sourceValue && !destinationValue) {
      summaryElement.textContent = "Select a source and destination to begin your transfer.";
      return;
    }

    if (sourceValue && destinationValue && sourceValue === destinationValue) {
      summaryElement.dataset.state = "warning";
      summaryElement.textContent = "Source and destination accounts must be different.";
      return;
    }

    if (sourceValue && destinationValue && Number.isFinite(amount)) {
      summaryElement.dataset.state = "ready";
      summaryElement.textContent = `Ready to move ${formatCurrency(amount)} from ${getAccountLabel(sourceValue)} to ${getAccountLabel(destinationValue)}.`;
      return;
    }

    if (sourceValue && destinationValue) {
      summaryElement.dataset.state = "ready";
      summaryElement.textContent = `Preparing to move funds from ${getAccountLabel(sourceValue)} to ${getAccountLabel(destinationValue)}. Enter an amount to continue.`;
      return;
    }

    if (sourceValue) {
      summaryElement.textContent = `Preparing to withdraw from ${getAccountLabel(sourceValue)}. Choose where the money should land.`;
      return;
    }

    summaryElement.textContent = `Preparing to deposit into ${getAccountLabel(destinationValue)}. Choose a source to continue.`;
  };

  const resetFormState = () => {
    syncDisabledOptions();
    updateGuidelines();
    updateSummary();
  };

  const sendTransferRequest = async (form, payload) => {
    const endpoint = form?.dataset.endpoint;
    if (!endpoint) {
      showFeedback(form, "Transfer endpoint is unavailable.", "error");
      return;
    }

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok || !data.success) {
        const message = data.message || "Unable to complete the transfer.";
        throw new Error(message);
      }

      state = data.state || state;
      updateCards();
      renderTransactions();
      form.reset();
      resetFormState();
      showFeedback(form, data.message, "success");
    } catch (error) {
      showFeedback(form, error.message || "Transfer failed. Try again.", "error");
    }
  };

  sourceSelect?.addEventListener("change", () => {
    syncDisabledOptions();
    updateGuidelines();
    updateSummary();
  });

  destinationSelect?.addEventListener("change", () => {
    syncDisabledOptions();
    updateGuidelines();
    updateSummary();
  });

  amountInput?.addEventListener("input", () => {
    updateSummary();
  });

  if (transferForm) {
    transferForm.addEventListener("submit", (event) => {
      event.preventDefault();
      hideFeedback(transferForm);

      const formData = new FormData(transferForm);
      const amount = sanitizeAmount(formData.get("amount"));
      const source = formData.get("source");
      const destination = formData.get("destination");

      if (!source) {
        showFeedback(transferForm, "Select a source account.", "error");
        return;
      }

      if (!destination) {
        showFeedback(transferForm, "Select a destination account.", "error");
        return;
      }

      if (source === destination) {
        showFeedback(transferForm, "Source and destination must be different.", "error");
        return;
      }

      if (!Number.isFinite(amount)) {
        showFeedback(transferForm, "Enter a valid transfer amount.", "error");
        return;
      }

      sendTransferRequest(transferForm, {
        amount,
        source,
        destination,
      });
    });
  }

  updateCards();
  renderTransactions();
  resetFormState();
});

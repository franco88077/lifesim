/* Banking transfer interactivity. */
document.addEventListener("DOMContentLoaded", () => {
  const dataElement = document.getElementById("banking-data");
  const accountCards = document.querySelectorAll("[data-account-card]");
  const ledgerBody = document.querySelector("[data-ledger-body]");
  const ledgerEmpty = document.querySelector("[data-ledger-empty]");
  const depositForm = document.getElementById("form-hand-to-account");
  const withdrawForm = document.getElementById("form-account-to-hand");
  const depositDestination = document.getElementById("hand-transfer-destination");
  const withdrawSource = document.getElementById("account-withdraw-source");
  const depositSummary = document.querySelector("[data-deposit-summary]");
  const withdrawSummary = document.querySelector("[data-withdraw-summary]");

  const createEmptyState = () => ({ balances: {}, transactions: [], account_labels: {} });
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

  const presets = {
    allocation: {
      name: "Cash Allocation",
      describe: (destination) => {
        if (!destination) {
          return "Wallet deposit into the selected account.";
        }
        return `Wallet deposit into ${getAccountLabel(destination)}`;
      },
      summaryElement: depositSummary,
    },
    withdrawal: {
      name: "Cash Withdrawal",
      describe: (source) => {
        if (!source) {
          return "Funds moved from the selected account to cash on hand.";
        }
        return `Funds moved from ${getAccountLabel(source)} to cash on hand.`;
      },
      summaryElement: withdrawSummary,
    },
  };

  const updatePresetSummaries = () => {
    if (presets.allocation.summaryElement) {
      const destination = depositDestination?.value;
      presets.allocation.summaryElement.textContent = `${presets.allocation.name} — ${presets.allocation.describe(destination)}`;
    }
    if (presets.withdrawal.summaryElement) {
      const source = withdrawSource?.value;
      presets.withdrawal.summaryElement.textContent = `${presets.withdrawal.name} — ${presets.withdrawal.describe(source)}`;
    }
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
      updatePresetSummaries();
      showFeedback(form, data.message, "success");
    } catch (error) {
      showFeedback(form, error.message || "Transfer failed. Try again.", "error");
    }
  };

  depositDestination?.addEventListener("change", updatePresetSummaries);
  withdrawSource?.addEventListener("change", updatePresetSummaries);

  if (depositForm) {
    depositForm.addEventListener("submit", (event) => {
      event.preventDefault();
      hideFeedback(depositForm);

      const formData = new FormData(depositForm);
      const amount = sanitizeAmount(formData.get("amount"));
      const destination = formData.get("destination");

      if (!destination) {
        showFeedback(depositForm, "Select a destination account.", "error");
        return;
      }

      if (!Number.isFinite(amount)) {
        showFeedback(depositForm, "Enter a valid transfer amount.", "error");
        return;
      }

      sendTransferRequest(depositForm, {
        amount,
        destination,
      });
    });
  }

  if (withdrawForm) {
    withdrawForm.addEventListener("submit", (event) => {
      event.preventDefault();
      hideFeedback(withdrawForm);

      const formData = new FormData(withdrawForm);
      const amount = sanitizeAmount(formData.get("amount"));
      const source = formData.get("source");

      if (!source) {
        showFeedback(withdrawForm, "Select a source account.", "error");
        return;
      }

      if (!Number.isFinite(amount)) {
        showFeedback(withdrawForm, "Enter a valid transfer amount.", "error");
        return;
      }

      sendTransferRequest(withdrawForm, {
        amount,
        source,
      });
    });
  }

  updateCards();
  renderTransactions();
  updatePresetSummaries();
});

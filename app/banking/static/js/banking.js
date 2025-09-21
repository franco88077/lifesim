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

  depositDestination?.addEventListener("change", updatePresetSummaries);
  withdrawSource?.addEventListener("change", updatePresetSummaries);

  if (depositForm) {
    depositForm.addEventListener("submit", (event) => {
      event.preventDefault();
      hideFeedback(depositForm);

      const formData = new FormData(depositForm);
      const amount = sanitizeAmount(formData.get("amount"));
      const destination = formData.get("destination");

      if (!state.balances?.hand) {
        showFeedback(depositForm, "Cash on hand balance is unavailable.", "error");
        return;
      }

      if (!destination || !state.balances?.[destination]) {
        showFeedback(depositForm, "Select a valid destination account.", "error");
        return;
      }

      if (!Number.isFinite(amount)) {
        showFeedback(depositForm, "Enter a valid transfer amount.", "error");
        return;
      }

      if (amount > state.balances.hand.balance) {
        showFeedback(
          depositForm,
          `Only ${formatCurrency(state.balances.hand.balance)} available in cash on hand.`,
          "error",
        );
        return;
      }

      state.balances.hand.balance = Number((state.balances.hand.balance - amount).toFixed(2));
      state.balances[destination].balance = Number((state.balances[destination].balance + amount).toFixed(2));

      state.transactions.unshift({
        name: presets.allocation.name,
        description: presets.allocation.describe(destination),
        amount,
        direction: "credit",
        account: destination,
      });

      updateCards();
      renderTransactions();
      depositForm.reset();
      updatePresetSummaries();
      showFeedback(
        depositForm,
        `Transferred ${formatCurrency(amount)} to ${getAccountLabel(destination)}.`,
        "success",
      );
    });
  }

  if (withdrawForm) {
    withdrawForm.addEventListener("submit", (event) => {
      event.preventDefault();
      hideFeedback(withdrawForm);

      const formData = new FormData(withdrawForm);
      const amount = sanitizeAmount(formData.get("amount"));
      const source = formData.get("source");

      if (!state.balances?.hand) {
        showFeedback(withdrawForm, "Cash on hand balance is unavailable.", "error");
        return;
      }

      if (!source || !state.balances?.[source]) {
        showFeedback(withdrawForm, "Select a valid source account.", "error");
        return;
      }

      if (!Number.isFinite(amount)) {
        showFeedback(withdrawForm, "Enter a valid transfer amount.", "error");
        return;
      }

      if (amount > state.balances[source].balance) {
        showFeedback(
          withdrawForm,
          `${getAccountLabel(source)} only has ${formatCurrency(state.balances[source].balance)} available.`,
          "error",
        );
        return;
      }

      state.balances[source].balance = Number((state.balances[source].balance - amount).toFixed(2));
      state.balances.hand.balance = Number((state.balances.hand.balance + amount).toFixed(2));

      state.transactions.unshift({
        name: presets.withdrawal.name,
        description: presets.withdrawal.describe(source),
        amount,
        direction: "debit",
        account: source,
      });

      updateCards();
      renderTransactions();
      withdrawForm.reset();
      updatePresetSummaries();
      showFeedback(
        withdrawForm,
        `Moved ${formatCurrency(amount)} from ${getAccountLabel(source)} to cash on hand.`,
        "success",
      );
    });
  }

  updateCards();
  renderTransactions();
  updatePresetSummaries();
});

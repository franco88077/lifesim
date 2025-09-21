/* Banking dashboard interactivity. */
document.addEventListener("DOMContentLoaded", () => {
  const goalToggle = document.querySelector(".goal-toggle");
  const goals = document.querySelectorAll(".goal");
  const dataElement = document.getElementById("banking-data");
  const accountCards = document.querySelectorAll("[data-account-card]");
  const ledgerBody = document.querySelector("[data-ledger-body]");
  const ledgerEmpty = document.querySelector("[data-ledger-empty]");
  const depositForm = document.getElementById("form-hand-to-account");
  const withdrawForm = document.getElementById("form-account-to-hand");

  const updateGoalProgress = (projected) => {
    goals.forEach((goal) => {
      const target = Number(goal.dataset.target || 0);
      const current = Number(goal.dataset.current || 0);
      const projectedTotal = projected ? target * 0.85 : current;
      const percent = target ? Math.min(100, Math.round((projectedTotal / target) * 100)) : 0;
      const bar = goal.querySelector(".goal__progress-bar");
      const progressContainer = goal.querySelector(".goal__progress");
      if (bar) {
        bar.style.width = `${percent}%`;
      }
      if (progressContainer) {
        progressContainer.setAttribute("aria-valuenow", String(projectedTotal));
        progressContainer.setAttribute("aria-valuetext", `${percent}% complete`);
      }
      goal.classList.toggle("projected", projected);
    });
  };

  if (goalToggle) {
    goalToggle.addEventListener("click", () => {
      const isProjected = goalToggle.classList.toggle("is-active");
      goalToggle.textContent = isProjected ? "Show live balances" : "Toggle projections";
      updateGoalProgress(isProjected);
    });
  }

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

  if (depositForm) {
    depositForm.addEventListener("submit", (event) => {
      event.preventDefault();
      hideFeedback(depositForm);

      const formData = new FormData(depositForm);
      const amount = sanitizeAmount(formData.get("amount"));
      const destination = formData.get("destination");
      const name = (formData.get("name") || "").trim();
      const description = (formData.get("description") || "").trim();

      if (!state.balances?.hand) {
        showFeedback(depositForm, "Cash on hand balance is unavailable.", "error");
        return;
      }

      if (!destination || !state.balances?.[destination]) {
        showFeedback(depositForm, "Select a valid destination account.", "error");
        return;
      }

      if (!name || !description) {
        showFeedback(depositForm, "Provide both a name and description for the transfer.", "error");
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
        name,
        description,
        amount,
        direction: "credit",
        account: destination,
      });

      updateCards();
      renderTransactions();
      depositForm.reset();
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
      const name = (formData.get("name") || "").trim();
      const description = (formData.get("description") || "").trim();

      if (!state.balances?.hand) {
        showFeedback(withdrawForm, "Cash on hand balance is unavailable.", "error");
        return;
      }

      if (!source || !state.balances?.[source]) {
        showFeedback(withdrawForm, "Select a valid source account.", "error");
        return;
      }

      if (!name || !description) {
        showFeedback(withdrawForm, "Provide both a name and description for the transfer.", "error");
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
        name,
        description,
        amount,
        direction: "debit",
        account: source,
      });

      updateCards();
      renderTransactions();
      withdrawForm.reset();
      showFeedback(
        withdrawForm,
        `Moved ${formatCurrency(amount)} from ${getAccountLabel(source)} to cash on hand.`,
        "success",
      );
    });
  }

  updateCards();
  renderTransactions();
  updateGoalProgress(false);
});

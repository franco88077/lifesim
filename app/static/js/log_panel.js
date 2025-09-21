/* Runtime log polling and toast notifications. */
document.addEventListener("DOMContentLoaded", () => {
  const results = document.getElementById("log-results");
  const levelFilter = document.getElementById("log-level");
  const componentFilter = document.getElementById("log-component");
  const searchInput = document.getElementById("log-search");
  const debugToggle = document.getElementById("debug-toggle");
  const toastContainer = document.getElementById("toast-container");

  if (!results || !levelFilter || !componentFilter || !searchInput || !debugToggle) {
    return;
  }

  const displayedAlerts = new Set();
  let searchTimer = null;

  const buildParams = () => {
    const params = new URLSearchParams();
    const level = levelFilter.value.trim();
    const component = componentFilter.value.trim();
    const search = searchInput.value.trim();
    const limit = debugToggle.checked ? "100" : "50";

    if (level) params.set("level", level);
    if (component) params.set("component", component);
    if (search) params.set("search", search);
    params.set("limit", limit);
    return params;
  };

  const copyTechnicalDetails = (button) => {
    const block = button.closest(".log-entry__technical");
    if (!block) return;
    const text = block.querySelector("pre").textContent;
    navigator.clipboard.writeText(text).then(() => {
      button.textContent = "Copied";
      setTimeout(() => {
        button.textContent = "Copy";
      }, 1500);
    });
  };

  const renderLogs = (logs) => {
    if (!logs.length) {
      results.innerHTML = '<p class="log-empty">No events recorded for the selected filters.</p>';
      return;
    }

    const markup = logs
      .map(
        (log) => `
          <article class="log-entry ${log.level}" data-log-id="${log.id}">
            <header class="log-entry__header">
              <span>[${log.level.toUpperCase()}] ${log.component} — ${log.title}</span>
              <span>${log.timestamp}</span>
            </header>
            <div class="log-entry__meta">
              <span>Action: ${log.action}</span>
              <span>Result: ${log.result}</span>
              <span>Env: ${log.environment}</span>
              <span>Correlation: ${log.correlation_id || "N/A"}</span>
            </div>
            <p>${log.user_summary}</p>
            <div class="log-entry__technical">
              <button type="button" class="copy-tech" aria-label="Copy technical details">Copy</button>
              <pre>${log.technical_details}</pre>
            </div>
          </article>
        `
      )
      .join("");

    results.innerHTML = markup;

    results.querySelectorAll(".copy-tech").forEach((button) => {
      button.addEventListener("click", () => copyTechnicalDetails(button));
    });
  };

  const updateComponentFilter = (logs) => {
    const known = new Set(Array.from(componentFilter.options, (opt) => opt.value));
    let shouldUpdate = false;
    logs.forEach((log) => {
      if (!known.has(log.component)) {
        shouldUpdate = true;
        const option = document.createElement("option");
        option.value = log.component;
        option.textContent = log.component;
        componentFilter.append(option);
      }
    });
    if (shouldUpdate) {
      const values = Array.from(componentFilter.options)
        .map((opt) => opt.value)
        .filter(Boolean)
        .sort();
      const preservedSelection = componentFilter.value;
      componentFilter.innerHTML = "";
      const all = document.createElement("option");
      all.value = "";
      all.textContent = "All";
      componentFilter.append(all);
      values.forEach((value) => {
        const opt = document.createElement("option");
        opt.value = value;
        opt.textContent = value;
        componentFilter.append(opt);
      });
      componentFilter.value = preservedSelection;
    }
  };

  const pushToast = (log) => {
    if (displayedAlerts.has(log.id)) return;
    displayedAlerts.add(log.id);

    const toast = document.createElement("div");
    toast.className = `toast ${log.level}`;
    toast.innerHTML = `
      <strong>${log.component}</strong><br />
      ${log.user_summary}
    `;
    toastContainer.append(toast);

    setTimeout(() => {
      toast.classList.add("fade");
      setTimeout(() => toast.remove(), 400);
    }, 5000);
  };

  const handleAlerts = (logs) => {
    logs
      .filter((log) => log.level === "warn" || log.level === "error")
      .forEach(pushToast);
  };

  const poll = () => {
    const url = `/logs/feed?${buildParams().toString()}`;
    fetch(url)
      .then((response) => response.json())
      .then((payload) => {
        renderLogs(payload.logs);
        updateComponentFilter(payload.logs);
        handleAlerts(payload.logs);
      })
      .catch((error) => {
        console.error("Log polling failed", error);
      });
  };

  levelFilter.addEventListener("change", poll);
  componentFilter.addEventListener("change", poll);
  debugToggle.addEventListener("change", poll);
  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(poll, 300);
  });

  poll();
  setInterval(poll, 6000);
});

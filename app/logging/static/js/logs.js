/* Dedicated log console experience. */
document.addEventListener("DOMContentLoaded", () => {
  const detailFeed = document.getElementById("log-detail-feed");
  const downloadButton = document.getElementById("download-logs");
  const infoCount = document.getElementById("log-info-count");
  const warnCount = document.getElementById("log-warn-count");
  const errorCount = document.getElementById("log-error-count");

  if (!detailFeed) {
    return;
  }

  const renderDetail = (logs) => {
    if (!logs.length) {
      detailFeed.innerHTML = '<p class="log-empty">No log entries yet.</p>';
      return;
    }

    detailFeed.innerHTML = logs
      .map(
        (log) => `
          <article class="${log.level}">
            <header>
              <strong>[${log.level.toUpperCase()}] ${log.component} — ${log.title}</strong>
              <span>${log.timestamp}</span>
            </header>
            <p>${log.user_summary}</p>
            <pre>${log.technical_details}</pre>
          </article>
        `
      )
      .join("");
  };

  const updateCounts = (logs) => {
    const base = { info: 0, warn: 0, error: 0 };
    logs.forEach((log) => {
      base[log.level] = (base[log.level] || 0) + 1;
    });
    if (infoCount) infoCount.textContent = base.info;
    if (warnCount) warnCount.textContent = base.warn;
    if (errorCount) errorCount.textContent = base.error;
  };

  const hydrate = () => {
    fetch("/logs/feed?limit=120")
      .then((response) => response.json())
      .then((payload) => {
        renderDetail(payload.logs);
        updateCounts(payload.logs);
        if (downloadButton) {
          downloadButton.dataset.payload = JSON.stringify(payload.logs, null, 2);
        }
      })
      .catch((error) => {
        console.error("Failed to load detailed logs", error);
      });
  };

  if (downloadButton) {
    downloadButton.addEventListener("click", () => {
      const payload = downloadButton.dataset.payload || "[]";
      navigator.clipboard.writeText(payload)
        .then(() => {
          downloadButton.textContent = "Copied";
          setTimeout(() => {
            downloadButton.textContent = "Copy latest payload";
          }, 1500);
        })
        .catch(() => {
          downloadButton.textContent = "Copy failed";
          setTimeout(() => {
            downloadButton.textContent = "Copy latest payload";
          }, 2000);
        });
    });
  }

  hydrate();
  setInterval(hydrate, 8000);
});

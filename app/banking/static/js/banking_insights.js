/* Interactive charts for the banking insights view. */
document.addEventListener("DOMContentLoaded", () => {
  const chartContainer = document.querySelector("[data-insight-chart]");
  const dataElement = document.getElementById("insight-chart-data");

  if (!chartContainer || !dataElement) {
    return;
  }

  let chartData = [];

  try {
    const raw = dataElement.textContent?.trim();
    chartData = raw ? JSON.parse(raw) : [];
  } catch (error) {
    console.error("Failed to parse insight chart data", error);
    chartData = [];
  }

  if (!Array.isArray(chartData) || !chartData.length) {
    return;
  }

  const focusSelect = chartContainer.querySelector("[data-chart-focus]");
  const rangeButtons = Array.from(
    chartContainer.querySelectorAll("[data-chart-range]")
  );
  const descriptionDisplay = chartContainer.querySelector(
    "[data-chart-description]"
  );
  const valueDisplay = chartContainer.querySelector("[data-chart-value]");
  const emptyDisplay = chartContainer.querySelector("[data-chart-empty]");
  const canvas = document.getElementById("insight-chart-canvas");

  if (!focusSelect || !rangeButtons.length || !canvas) {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return;
  }

  const currencyFormatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });

  const formatValue = (value, format) => {
    if (!Number.isFinite(value)) {
      return "—";
    }

    if (format === "currency") {
      return currencyFormatter.format(value);
    }

    return String(value);
  };

  const toTransparent = (hex, alpha) => {
    if (typeof hex !== "string" || !hex.startsWith("#")) {
      return "rgba(37, 99, 235, 0.15)"; // default blue accent
    }

    const normalized = hex.replace("#", "");
    const length = normalized.length;

    if (![3, 6].includes(length)) {
      return "rgba(37, 99, 235, 0.15)";
    }

    const expand = (value) =>
      value.length === 1 ? parseInt(value.repeat(2), 16) : parseInt(value, 16);
    const r = expand(normalized.slice(0, length === 3 ? 1 : 2));
    const g = expand(normalized.slice(length === 3 ? 1 : 2, length === 3 ? 2 : 4));
    const b = expand(normalized.slice(length === 3 ? 2 : 4));

    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  const getSeries = (slug) => chartData.find((entry) => entry.slug === slug);

  const parseDate = (isoString) => {
    const parsed = new Date(isoString);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  };

  const formatLabel = (isoString, range, dataset) => {
    const date = parseDate(isoString);
    if (!date) {
      return isoString;
    }

    if (range === "yearly") {
      return new Intl.DateTimeFormat("en-US", { year: "numeric" }).format(date);
    }

    if (range === "monthly") {
      return new Intl.DateTimeFormat("en-US", {
        month: "short",
        year: "numeric",
      }).format(date);
    }

    const firstDate = parseDate(dataset[0]?.date);
    const lastDate = parseDate(dataset[dataset.length - 1]?.date);
    const includeYear =
      !firstDate || !lastDate
        ? true
        : firstDate.getFullYear() !== lastDate.getFullYear();

    const options = includeYear
      ? { month: "short", day: "numeric", year: "numeric" }
      : { month: "short", day: "numeric" };

    return new Intl.DateTimeFormat("en-US", options).format(date);
  };

  const updateRangeButtons = (activeRange) => {
    rangeButtons.forEach((button) => {
      const isActive = button.dataset.chartRange === activeRange;
      button.setAttribute("aria-pressed", String(isActive));
      button.classList.toggle("is-active", isActive);
    });
  };

  let currentRange = "daily";
  let currentSeries = getSeries(focusSelect.value) || chartData.find((entry) => entry.is_available);
  let chartInstance = null;

  if (!currentSeries) {
    const firstOption = chartData[0];
    if (firstOption) {
      currentSeries = firstOption;
      focusSelect.value = firstOption.slug;
    }
  }

  const ensureChart = () => {
    if (chartInstance) {
      return chartInstance;
    }

    chartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false,
        },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                const series = getSeries(focusSelect.value);
                const formatted = formatValue(context.parsed.y, series?.format);
                return `${series?.name ?? "Value"}: ${formatted}`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: {
              display: false,
            },
            ticks: {
              autoSkip: true,
              maxTicksLimit: 6,
            },
          },
          y: {
            ticks: {
              callback: (value) => {
                const series = getSeries(focusSelect.value);
                return formatValue(value, series?.format);
              },
            },
            grid: {
              color: "rgba(148, 163, 184, 0.2)",
            },
          },
        },
      },
    });

    return chartInstance;
  };

  const applySeries = () => {
    const series = getSeries(currentSeries?.slug);
    if (!series) {
      return;
    }

    const dataset = series.data?.[currentRange] ?? [];

    if (descriptionDisplay) {
      descriptionDisplay.textContent = series.description ?? "";
    }

    if (!dataset.length) {
      if (emptyDisplay) {
        emptyDisplay.hidden = false;
      }
      canvas.hidden = true;
      if (valueDisplay) {
        valueDisplay.textContent = "—";
      }
      if (chartInstance) {
        chartInstance.data.labels = [];
        chartInstance.data.datasets = [];
        chartInstance.update();
      }
      return;
    }

    if (emptyDisplay) {
      emptyDisplay.hidden = true;
    }
    canvas.hidden = false;

    const labels = dataset.map((entry) =>
      formatLabel(entry.date, currentRange, dataset)
    );
    const values = dataset.map((entry) => entry.value ?? 0);

    const chart = ensureChart();
    chart.data.labels = labels;
    chart.data.datasets = [
      {
        label: series.name,
        data: values,
        borderColor: series.color,
        backgroundColor: toTransparent(series.color, 0.15),
        tension: 0.35,
        fill: true,
        pointRadius: 3,
        pointHoverRadius: 4,
      },
    ];
    chart.update();

    if (valueDisplay) {
      const lastValue = values[values.length - 1];
      valueDisplay.textContent = formatValue(lastValue, series.format);
    }
  };

  updateRangeButtons(currentRange);
  applySeries();

  focusSelect.addEventListener("change", (event) => {
    const target = event.target;
    if (!target) {
      return;
    }

    const nextSeries = getSeries(target.value);
    if (!nextSeries) {
      return;
    }

    currentSeries = nextSeries;
    applySeries();
  });

  rangeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const requestedRange = button.dataset.chartRange;
      if (!requestedRange || requestedRange === currentRange) {
        return;
      }
      currentRange = requestedRange;
      updateRangeButtons(currentRange);
      applySeries();
    });
  });
});

/* Interactions for the Lifesim home dashboard. */
document.addEventListener("DOMContentLoaded", () => {
  const metrics = document.querySelectorAll(".metric");
  const timelineItems = document.querySelectorAll(".timeline__list li");

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

/* Banking dashboard interactivity. */
document.addEventListener("DOMContentLoaded", () => {
  const goalToggle = document.querySelector(".goal-toggle");
  const goals = document.querySelectorAll(".goal");

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

  updateGoalProgress(false);
});

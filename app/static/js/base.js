/* Global interactions for Lifesim layout. */
document.addEventListener("DOMContentLoaded", () => {
  const navToggle = document.querySelector(".nav-toggle");
  const nav = document.getElementById("primary-nav");
  const logPanel = document.querySelector(".log-console");
  const logToggle = document.getElementById("log-toggle");

  if (navToggle && nav) {
    navToggle.addEventListener("click", () => {
      const isOpen = nav.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(isOpen));
    });
  }

  if (logToggle && logPanel) {
    logToggle.addEventListener("click", () => {
      const isClosed = logPanel.classList.toggle("closed");
      logToggle.textContent = isClosed ? "Show" : "Hide";
    });
    logPanel.classList.add("closed");
  }
});

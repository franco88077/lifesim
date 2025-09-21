/* Additional behaviour for the banking home view. */
document.addEventListener("DOMContentLoaded", () => {
  const viewMoreTriggers = document.querySelectorAll("[data-view-more]");

  viewMoreTriggers.forEach((trigger) => {
    const targetUrl = trigger.getAttribute("data-view-more");
    if (!targetUrl) {
      return;
    }

    const navigate = () => {
      window.location.href = targetUrl;
    };

    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      navigate();
    });

    trigger.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        navigate();
      }
    });
  });
});

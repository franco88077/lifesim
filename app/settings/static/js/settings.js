/* Enhance the system settings form with live timezone previews. */
document.addEventListener("DOMContentLoaded", () => {
  const select = document.querySelector("[data-timezone-select]");
  const previewContainer = document.querySelector("[data-timezone-preview]");
  const previewValue = document.querySelector("[data-timezone-preview-value]");
  const activeDisplay = document.querySelector("[data-active-timezone]");

  if (!select || !previewValue || !activeDisplay) {
    return;
  }

  const buildLabel = (option) => {
    if (!option) {
      return "";
    }
    const label = option.textContent?.trim() ?? option.value;
    return label;
  };

  const updatePreview = () => {
    const selectedOption = select.options[select.selectedIndex];
    if (!selectedOption) {
      return;
    }

    const label = buildLabel(selectedOption);

    if (previewContainer) {
      previewContainer.hidden = label === activeDisplay.textContent?.trim();
    }

    previewValue.textContent = label;
  };

  select.addEventListener("change", updatePreview);

  updatePreview();
});

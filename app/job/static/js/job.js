/* Job system interactions for managing listings and settings. */

const parseJSON = (element) => {
  if (!element) {
    return null;
  }

  try {
    return JSON.parse(element.textContent || element.value || "");
  } catch (error) {
    console.error("Failed to parse JSON payload", error);
    return null;
  }
};

const fetchJSON = async (url, options = {}) => {
  const config = { ...options };
  config.headers = config.headers ? { ...config.headers } : {};

  if (config.method && config.method !== "GET" && config.body && !config.headers["Content-Type"]) {
    config.headers["Content-Type"] = "application/json";
  }

  try {
    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
      return { success: false, message: data?.message || response.statusText };
    }

    return data;
  } catch (error) {
    return { success: false, message: error.message || "Network request failed." };
  }
};

document.addEventListener("DOMContentLoaded", () => {
  const jobDataElement = document.getElementById("job-initial-data");
  const settingsDataElement = document.getElementById("job-settings-data");

  const initialJobs = parseJSON(jobDataElement);
  const initialSettings = parseJSON(settingsDataElement);

  const state = {
    jobs: Array.isArray(initialJobs) ? initialJobs : [],
    settings: initialSettings,
  };

  const resetTextTargets = document.querySelectorAll("[data-reset-text]");

  const updateResetText = (label) => {
    if (!label) {
      return;
    }
    resetTextTargets.forEach((node) => {
      node.textContent = label;
    });
  };

  const applySettingsToForm = (
    settings,
    { rateInput, dailyLimitInput, minimumNote, companyInput } = {}
  ) => {
    if (!settings || typeof settings !== "object") {
      return;
    }

    state.settings = settings;

    if (rateInput) {
      if (settings.minimum_hourly_wage !== undefined) {
        rateInput.min = settings.minimum_hourly_wage;
      }
      if (!rateInput.value) {
        rateInput.value = settings.minimum_hourly_wage;
      }
    }

    if (dailyLimitInput) {
      dailyLimitInput.placeholder = settings.default_daily_limit ?? "";
    }

    if (minimumNote && settings.minimum_hourly_wage_display) {
      minimumNote.textContent = `This rate must meet the minimum wage of ${settings.minimum_hourly_wage_display}.`;
    }

    if (companyInput && settings.payroll_company_name !== undefined) {
      companyInput.value = settings.payroll_company_name;
    }

    updateResetText(settings.daily_reset_label);
  };

  const jobList = document.querySelector("[data-job-admin-list]");
  const jobForm = document.querySelector("[data-job-form]");
  const jobFormMessage = jobForm?.querySelector("[data-job-form-message]");
  const jobFormHeading = document.querySelector("[data-job-form-heading]");
  const jobSubmitButton = jobForm?.querySelector("[data-job-submit]");
  const jobCancelButton = jobForm?.querySelector("[data-job-cancel]");
  const rateInput = jobForm?.querySelector("[data-rate-input]");
  const minimumNote = jobForm?.querySelector("[data-minimum-note]");
  const rateLabel = jobForm?.querySelector("[data-rate-label]");
  const rateSuffix = jobForm?.querySelector("[data-rate-suffix]");
  const dailyLimitInput = jobForm?.querySelector("[data-daily-limit]");
  const payTypeInputs = jobForm ? Array.from(jobForm.querySelectorAll("input[name='pay_type']")) : [];

  let editingJobId = null;

  const showFormMessage = (text, tone = "info") => {
    if (!jobFormMessage) {
      return;
    }
    jobFormMessage.textContent = text;
    jobFormMessage.classList.toggle("is-error", tone === "error");
  };

  const createMetaItem = (label, value) => {
    const wrapper = document.createElement("div");
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value;
    wrapper.append(dt, dd);
    return wrapper;
  };

  const createJobCard = (job) => {
    const card = document.createElement("article");
    card.className = "job-admin-card";
    card.dataset.jobCard = "";
    card.dataset.jobId = job.id;

    const header = document.createElement("header");
    header.className = "job-admin-card__header";

    const headerInfo = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = job.title;
    const tag = document.createElement("span");
    tag.className = "job-tag";
    tag.textContent = job.pay_type_label;
    headerInfo.append(title, tag);

    const status = document.createElement("span");
    status.className = `job-admin-card__status job-admin-card__status--${job.status}`;
    status.textContent = job.status_label;

    header.append(headerInfo, status);
    card.append(header);

    const description = document.createElement("p");
    description.className = "job-admin-card__description";
    description.textContent = job.description;
    card.append(description);

    const meta = document.createElement("dl");
    meta.className = "job-admin-card__meta";
    meta.append(
      createMetaItem("Pay", job.rate_display),
      createMetaItem("Daily limit", job.daily_limit_display),
      createMetaItem("Remaining today", job.remaining_display)
    );
    card.append(meta);

    const actions = document.createElement("footer");
    actions.className = "job-admin-card__actions";

    const editButton = document.createElement("button");
    editButton.type = "button";
    editButton.dataset.jobEdit = "";
    editButton.textContent = "Edit";

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.dataset.jobDelete = "";
    deleteButton.className = "danger";
    deleteButton.textContent = "Remove";

    actions.append(editButton, deleteButton);
    card.append(actions);

    return card;
  };

  const renderJobs = () => {
    if (!jobList) {
      return;
    }

    jobList.innerHTML = "";

    if (!state.jobs || state.jobs.length === 0) {
      const emptyMessage = document.createElement("p");
      emptyMessage.className = "job-admin__empty";
      emptyMessage.dataset.jobEmpty = "";
      emptyMessage.textContent = "No jobs have been added yet.";
      jobList.append(emptyMessage);
      return;
    }

    state.jobs.forEach((job) => {
      jobList.append(createJobCard(job));
    });
  };

  const updateRateCopy = () => {
    if (!jobForm) {
      return;
    }

    const selectedType = jobForm.querySelector("input[name='pay_type']:checked")?.value || "time";

    if (selectedType === "task") {
      if (rateLabel) rateLabel.textContent = "Task payout";
      if (rateSuffix) rateSuffix.textContent = "per task";
      if (rateInput) {
        rateInput.min = "1";
        if (!rateInput.value) {
          rateInput.value = "25";
        }
      }
      if (minimumNote) {
        minimumNote.textContent = "Task-based work pays a fixed amount each completion.";
      }
    } else {
      if (rateLabel) rateLabel.textContent = "Hourly rate";
      if (rateSuffix) rateSuffix.textContent = "per hour";
      if (rateInput && state.settings?.minimum_hourly_wage !== undefined) {
        rateInput.min = state.settings.minimum_hourly_wage;
        if (!editingJobId && Number(rateInput.value || 0) < Number(rateInput.min)) {
          rateInput.value = state.settings.minimum_hourly_wage;
        }
      }
      if (minimumNote && state.settings?.minimum_hourly_wage_display) {
        minimumNote.textContent = `This rate must meet the minimum wage of ${state.settings.minimum_hourly_wage_display}.`;
      }
    }
  };

  const resetJobForm = (keepMessage = false) => {
    if (!jobForm) {
      return;
    }

    jobForm.reset();
    editingJobId = null;
    if (jobFormHeading) {
      jobFormHeading.textContent = "Create a job";
    }
    if (jobSubmitButton) {
      jobSubmitButton.textContent = "Create job";
    }
    if (jobCancelButton) {
      jobCancelButton.hidden = true;
    }
    if (dailyLimitInput) {
      dailyLimitInput.value = "";
    }
    if (!keepMessage) {
      showFormMessage("");
    }
    if (state.settings) {
      applySettingsToForm(state.settings, { rateInput, dailyLimitInput, minimumNote });
    }
    updateRateCopy();
  };

  const beginEdit = (job) => {
    if (!jobForm) {
      return;
    }

    editingJobId = job.id;
    if (jobFormHeading) {
      jobFormHeading.textContent = "Edit job";
    }
    if (jobSubmitButton) {
      jobSubmitButton.textContent = "Save changes";
    }
    if (jobCancelButton) {
      jobCancelButton.hidden = false;
    }

    jobForm.elements.title.value = job.title;
    jobForm.elements.description.value = job.description;
    payTypeInputs.forEach((input) => {
      input.checked = input.value === job.pay_type;
    });

    if (rateInput) {
      rateInput.value = Number(job.rate).toFixed(2);
    }

    if (dailyLimitInput) {
      dailyLimitInput.value = job.daily_limit ?? "";
    }

    updateRateCopy();
    jobForm.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const loadJobs = async () => {
    const response = await fetchJSON("/job/api/jobs");
    if (!response.success) {
      showFormMessage(response.message || "Unable to load jobs.", "error");
      return;
    }

    state.jobs = response.jobs || [];
    if (response.settings) {
      applySettingsToForm(response.settings, { rateInput, dailyLimitInput, minimumNote });
    } else if (state.settings) {
      applySettingsToForm(state.settings, { rateInput, dailyLimitInput, minimumNote });
    }
    renderJobs();
    updateRateCopy();
  };

  const handleJobSubmit = async (event) => {
    event.preventDefault();
    if (!jobForm) {
      return;
    }

    const formData = new FormData(jobForm);
    const payload = {
      title: (formData.get("title") || "").trim(),
      description: (formData.get("description") || "").trim(),
      pay_type: formData.get("pay_type") || "time",
      pay_rate: Number(formData.get("pay_rate")),
      daily_limit: formData.get("daily_limit"),
    };

    if (!payload.title) {
      showFormMessage("Enter a job title to continue.", "error");
      return;
    }

    if (!payload.description) {
      showFormMessage("Add a brief description for the job.", "error");
      return;
    }

    if (!Number.isFinite(payload.pay_rate) || payload.pay_rate <= 0) {
      showFormMessage("Enter a valid pay rate greater than zero.", "error");
      return;
    }

    if (payload.daily_limit !== null && payload.daily_limit !== "") {
      const parsedLimit = Number.parseInt(payload.daily_limit, 10);
      if (!Number.isFinite(parsedLimit) || parsedLimit <= 0) {
        showFormMessage("Daily limit must be a positive whole number or left blank.", "error");
        return;
      }
      payload.daily_limit = parsedLimit;
    } else {
      payload.daily_limit = null;
    }

    const endpoint = editingJobId ? `/job/api/jobs/${editingJobId}` : "/job/api/jobs";
    const method = editingJobId ? "PUT" : "POST";
    const response = await fetchJSON(endpoint, {
      method,
      body: JSON.stringify(payload),
    });

    if (!response.success) {
      showFormMessage(response.message || "Unable to save job.", "error");
      return;
    }

    await loadJobs();
    showFormMessage(response.message || "Job saved successfully.");
    resetJobForm(true);
  };

  const handleJobListClick = async (event) => {
    const editButton = event.target.closest("[data-job-edit]");
    if (editButton) {
      const card = editButton.closest("[data-job-card]");
      if (!card) {
        return;
      }
      const job = state.jobs.find((item) => item.id === card.dataset.jobId);
      if (job) {
        beginEdit(job);
      }
      return;
    }

    const deleteButton = event.target.closest("[data-job-delete]");
    if (deleteButton) {
      const card = deleteButton.closest("[data-job-card]");
      if (!card) {
        return;
      }
      const jobId = card.dataset.jobId;
      const job = state.jobs.find((item) => item.id === jobId);
      const confirmation = window.confirm(
        job ? `Remove the job “${job.title}”? This cannot be undone.` : "Remove this job?"
      );
      if (!confirmation) {
        return;
      }

      const response = await fetchJSON(`/job/api/jobs/${jobId}`, {
        method: "DELETE",
      });

      if (!response.success) {
        showFormMessage(response.message || "Unable to remove job.", "error");
        return;
      }

      if (editingJobId === jobId) {
        resetJobForm();
      }

      await loadJobs();
      showFormMessage(response.message || "Job removed.");
    }
  };

  if (jobForm && jobList) {
    applySettingsToForm(state.settings || {}, { rateInput, dailyLimitInput, minimumNote });
    updateRateCopy();
    renderJobs();
    loadJobs();

    jobForm.addEventListener("submit", handleJobSubmit);
    jobList.addEventListener("click", handleJobListClick);
    payTypeInputs.forEach((input) => {
      input.addEventListener("change", updateRateCopy);
    });
    if (jobCancelButton) {
      jobCancelButton.addEventListener("click", () => resetJobForm());
    }
  }

  const settingsForm = document.querySelector("[data-job-settings-form]");
  const settingsMessage = settingsForm?.querySelector("[data-job-settings-message]");
  const companyNameInput = settingsForm?.querySelector("[data-job-company-name]");

  const showSettingsMessage = (text, tone = "info") => {
    if (!settingsMessage) {
      return;
    }
    settingsMessage.textContent = text;
    settingsMessage.classList.toggle("is-error", tone === "error");
  };

  const handleSettingsSubmit = async (event) => {
    event.preventDefault();
    if (!settingsForm) {
      return;
    }

    const formData = new FormData(settingsForm);
    const companyName = String(formData.get("payroll_company_name") || "").trim();
    const minimumWage = Number(formData.get("minimum_hourly_wage"));
    const defaultLimitRaw = formData.get("default_daily_limit");
    const resetHour = Number.parseInt(formData.get("daily_reset_hour"), 10);

    if (!companyName) {
      showSettingsMessage("Enter a company name for job payments.", "error");
      return;
    }

    if (!Number.isFinite(minimumWage) || minimumWage <= 0) {
      showSettingsMessage("Minimum wage must be greater than zero.", "error");
      return;
    }

    const payload = {
      payroll_company_name: companyName,
      minimum_hourly_wage: minimumWage,
      default_daily_limit: null,
      daily_reset_hour: resetHour,
    };

    if (defaultLimitRaw !== null && defaultLimitRaw !== "") {
      const parsedLimit = Number.parseInt(defaultLimitRaw, 10);
      if (!Number.isFinite(parsedLimit) || parsedLimit < 0) {
        showSettingsMessage("Default daily limit must be zero or greater.", "error");
        return;
      }
      payload.default_daily_limit = parsedLimit;
    }

    const response = await fetchJSON("/job/api/settings", {
      method: "PATCH",
      body: JSON.stringify(payload),
    });

    if (!response.success) {
      showSettingsMessage(response.message || "Unable to update settings.", "error");
      return;
    }

    applySettingsToForm(response.settings, {
      rateInput,
      dailyLimitInput,
      minimumNote,
      companyInput: companyNameInput,
    });
    state.settings = response.settings;
    if (rateInput) {
      updateRateCopy();
    }
    showSettingsMessage(response.message || "Settings saved.");
  };

  if (settingsForm) {
    if (state.settings) {
      applySettingsToForm(state.settings, { companyInput: companyNameInput });
      updateResetText(state.settings.daily_reset_label);
    }
    settingsForm.addEventListener("submit", handleSettingsSubmit);
  }
});


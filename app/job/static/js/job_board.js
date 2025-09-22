/* Job board interactions for starting and completing work. */

const parseJSON = (element) => {
  if (!element) {
    return null;
  }
  try {
    return JSON.parse(element.textContent || element.value || "");
  } catch (error) {
    console.error("Failed to parse job board payload", error);
    return null;
  }
};

const fetchJSON = async (url, options = {}) => {
  const config = { ...options };
  config.headers = config.headers ? { ...config.headers } : {};
  if (
    config.method &&
    config.method !== "GET" &&
    config.body &&
    !config.headers["Content-Type"]
  ) {
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

const formatCurrency = (value) => {
  const amount = Number.isFinite(value) ? value : 0;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
};

document.addEventListener("DOMContentLoaded", () => {
  const boardDataElement = document.getElementById("job-board-data");
  const initialData = parseJSON(boardDataElement) || {};

  const state = {
    jobs: [],
    jobMap: new Map(),
    payoutOptions: Array.isArray(initialData.payout_options)
      ? initialData.payout_options.filter((option) => option && option.value)
      : [],
    settings: initialData.settings || {},
  };

  if (!state.payoutOptions.some((option) => option.value === "cash")) {
    state.payoutOptions.unshift({
      value: "cash",
      label: "Cash",
      description: "Receive the payment as cash on hand.",
      account_slug: "hand",
    });
  }

  const jobBoard = document.querySelector(".job-board");
  if (!jobBoard) {
    return;
  }

  const summaryTargets = document.querySelectorAll("[data-job-summary]");
  const timers = new Map();

  const normalizeJob = (job) => {
    const sessionStartRaw = job?.active_session_started_at;
    const sessionStart = sessionStartRaw ? new Date(sessionStartRaw) : null;
    const hasValidStart = sessionStart && !Number.isNaN(sessionStart.getTime());

    return {
      ...job,
      sessionBaseSeconds: Number(job?.active_session_seconds || 0),
      sessionStart: hasValidStart ? sessionStart : null,
    };
  };

  const getSessionSeconds = (job) => {
    const base = Number(job?.sessionBaseSeconds || 0);
    if (job?.sessionStart) {
      const elapsed = Math.max(
        0,
        Math.floor((Date.now() - job.sessionStart.getTime()) / 1000)
      );
      return base + elapsed;
    }
    return base;
  };

  const calculateRealtimeEarnings = (job, seconds) => {
    if (job?.pay_type !== "time") {
      return 0;
    }
    const rate = Number(job.rate || 0);
    if (!Number.isFinite(rate)) {
      return 0;
    }
    const raw = (seconds / 3600) * rate;
    return Math.ceil(raw * 100) / 100;
  };

  const formatDuration = (seconds) => {
    const total = Math.max(0, Number(seconds) || 0);
    const hrs = Math.floor(total / 3600)
      .toString()
      .padStart(2, "0");
    const mins = Math.floor((total % 3600) / 60)
      .toString()
      .padStart(2, "0");
    const secs = Math.floor(total % 60)
      .toString()
      .padStart(2, "0");
    return `${hrs}:${mins}:${secs}`;
  };

  const setJobMessage = (jobId, message, tone = "info") => {
    const card = document.querySelector(
      `[data-job-card][data-job-id="${jobId}"]`
    );
    if (!card) {
      return;
    }
    const messageElement = card.querySelector("[data-job-message]");
    if (!messageElement) {
      return;
    }
    messageElement.textContent = message || "";
    messageElement.classList.toggle("job-card__message--error", tone === "error");
    messageElement.classList.toggle("job-card__message--success", tone === "success");
  };

  const clearTimer = (jobId) => {
    const existing = timers.get(jobId);
    if (existing) {
      window.clearInterval(existing);
      timers.delete(jobId);
    }
  };

  const updateShift = (job) => {
    const card = document.querySelector(
      `[data-job-card][data-job-id="${job.id}"]`
    );
    if (!card) {
      return;
    }
    const shift = card.querySelector("[data-job-shift]");
    const timer = card.querySelector("[data-job-timer]");
    const earnings = card.querySelector("[data-job-earnings]");
    if (!shift || !timer || !earnings) {
      return;
    }
    const seconds = Math.max(0, Math.floor(getSessionSeconds(job)));
    if (seconds <= 0 && !job.sessionStart) {
      shift.hidden = true;
      timer.textContent = "00:00:00";
      earnings.textContent = formatCurrency(0);
      return;
    }
    shift.hidden = false;
    timer.textContent = formatDuration(seconds);
    earnings.textContent = formatCurrency(
      calculateRealtimeEarnings(job, seconds)
    );
  };

  const startTimer = (job) => {
    clearTimer(job.id);
    updateShift(job);
    const intervalId = window.setInterval(() => {
      const current = state.jobMap.get(job.id);
      if (!current || !current.sessionStart) {
        clearTimer(job.id);
        if (current) {
          updateShift(current);
        }
        return;
      }
      updateShift(current);
    }, 1000);
    timers.set(job.id, intervalId);
  };

  const updateSummary = () => {
    const totals = {
      available: 0,
      time: 0,
      task: 0,
    };
    state.jobs.forEach((job) => {
      if (job.is_available) {
        totals.available += 1;
      }
      if (job.pay_type === "time") {
        totals.time += 1;
      } else if (job.pay_type === "task") {
        totals.task += 1;
      }
    });
    summaryTargets.forEach((node) => {
      const key = node.dataset.jobSummary;
      if (key && key in totals) {
        node.textContent = totals[key];
      }
    });
  };

  const updateJobCard = (job) => {
    const card = document.querySelector(
      `[data-job-card][data-job-id="${job.id}"]`
    );
    if (!card) {
      return;
    }
    card.dataset.jobStatus = job.status;
    card.dataset.jobType = job.pay_type;

    const statusLabel = card.querySelector("[data-job-status-label]");
    if (statusLabel) {
      statusLabel.textContent = job.status_label;
      statusLabel.className = `job-card__status job-card__status--${job.status}`;
    }

    const remaining = card.querySelector("[data-job-remaining]");
    if (remaining) {
      remaining.textContent = job.remaining_display;
    }

    const note = card.querySelector("[data-job-note]");
    if (note) {
      note.textContent = job.note;
    }

    const startButton = card.querySelector("[data-job-start]");
    const pauseButton = card.querySelector("[data-job-pause]");
    const completeButton = card.querySelector("[data-job-complete]");
    const hasAvailability =
      job.remaining_today === null || job.remaining_today > 0;
    const totalSeconds = Math.max(0, Math.floor(getSessionSeconds(job)));

    if (startButton) {
      if (job.pay_type === "time") {
        if (job.sessionStart) {
          startButton.hidden = true;
        } else {
          startButton.hidden = false;
          startButton.disabled = !hasAvailability;
          startButton.textContent = totalSeconds > 0 ? "Resume Job" : "Start Job";
        }
      } else {
        startButton.hidden = true;
      }
    }

    if (pauseButton) {
      if (job.pay_type === "time") {
        pauseButton.hidden = !job.sessionStart;
        pauseButton.disabled = !job.sessionStart;
      } else {
        pauseButton.hidden = true;
      }
    }

    if (completeButton) {
      completeButton.hidden = false;
      if (job.pay_type === "time") {
        completeButton.disabled = totalSeconds <= 0;
      } else {
        completeButton.disabled = !hasAvailability;
      }
    }

    if (job.pay_type === "time") {
      if (job.sessionStart) {
        startTimer(job);
      } else {
        clearTimer(job.id);
        updateShift(job);
      }
    } else {
      clearTimer(job.id);
      updateShift(job);
    }
  };

  const setJobState = (job) => {
    const normalized = normalizeJob(job);
    state.jobMap.set(normalized.id, normalized);
    const index = state.jobs.findIndex((item) => item.id === normalized.id);
    if (index >= 0) {
      state.jobs[index] = normalized;
    } else {
      state.jobs.push(normalized);
    }
    updateJobCard(normalized);
    updateSummary();
    return normalized;
  };

  const modal = document.querySelector("[data-job-modal]");
  const modalTitle = modal?.querySelector("[data-job-modal-title]");
  const modalMessage = modal?.querySelector("[data-job-modal-message]");
  const modalOptions = modal?.querySelector("[data-job-modal-options]");
  const modalOptionsList = modal?.querySelector("[data-job-modal-options-list]");
  const modalError = modal?.querySelector("[data-job-modal-error]");
  const modalForm = modal?.querySelector("[data-job-modal-form]");
  const modalConfirm = modal?.querySelector("[data-job-modal-confirm]");
  const modalCancel = modal?.querySelector("[data-job-modal-cancel]");
  const modalClose = modal?.querySelector("[data-job-modal-close]");

  let modalState = null;

  const closeModal = () => {
    if (!modal) {
      return;
    }
    modal.hidden = true;
    document.body.classList.remove("job-modal-open");
    modalState = null;
  };

  const populatePayoutOptions = () => {
    if (!modalOptions || !modalOptionsList) {
      return;
    }
    modalOptionsList.innerHTML = "";
    const options = state.payoutOptions.length
      ? state.payoutOptions
      : [
          {
            value: "cash",
            label: "Cash",
            description: "Receive the payment as cash on hand.",
            account_slug: "hand",
          },
        ];
    options.forEach((option, index) => {
      const wrapper = document.createElement("label");
      wrapper.className = "job-modal__option";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "payout_method";
      input.value = option.value;
      if (index === 0) {
        input.checked = true;
      }
      const title = document.createElement("span");
      title.className = "job-modal__option-title";
      title.textContent = option.label || option.value;
      const description = document.createElement("span");
      description.className = "job-modal__option-description";
      description.textContent = option.description || "";
      wrapper.append(input, title, description);
      modalOptionsList.append(wrapper);
    });
    modalOptions.hidden = options.length === 0;
  };

  const openModal = (config) => {
    if (!modal || !modalTitle || !modalMessage || !modalConfirm || !modalError) {
      return;
    }
    modalState = config;
    modalTitle.textContent = config.title || "";
    modalMessage.textContent = config.message || "";
    modalConfirm.textContent = config.confirmLabel || "Confirm";
    modalConfirm.disabled = false;
    modalError.textContent = "";

    if (config.requirePayout) {
      populatePayoutOptions();
    }
    if (modalOptions) {
      modalOptions.hidden = !config.requirePayout;
    }

    modal.hidden = false;
    document.body.classList.add("job-modal-open");
    window.requestAnimationFrame(() => {
      modalConfirm.focus();
    });
  };

  const getSelectedPayout = () => {
    if (!modalForm) {
      return null;
    }
    const selected = modalForm.querySelector(
      'input[name="payout_method"]:checked'
    );
    return selected ? selected.value : null;
  };

  const startJobRequest = async (jobId) => {
    const response = await fetchJSON(`/job/api/jobs/${jobId}/start`, {
      method: "POST",
    });
    if (!response.success) {
      return response;
    }
    setJobState(response.job);
    return response;
  };

  const pauseJobRequest = async (jobId) => {
    const response = await fetchJSON(`/job/api/jobs/${jobId}/pause`, {
      method: "POST",
    });
    if (!response.success) {
      return response;
    }
    setJobState(response.job);
    return response;
  };

  const completeJobRequest = async (jobId, payoutMethod) => {
    const response = await fetchJSON(`/job/api/jobs/${jobId}/complete`, {
      method: "POST",
      body: JSON.stringify({ payout_method: payoutMethod }),
    });
    if (!response.success) {
      return response;
    }
    setJobState(response.job);
    return response;
  };

  if (modalForm) {
    modalForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!modalState) {
        return;
      }
      modalConfirm.disabled = true;
      modalError.textContent = "";
      if (modalState.mode === "start") {
        const result = await startJobRequest(modalState.jobId);
        if (!result.success) {
          modalError.textContent = result.message || "Unable to start this job.";
          setJobMessage(modalState.jobId, result.message || "Unable to start this job.", "error");
          modalConfirm.disabled = false;
          return;
        }
        setJobMessage(modalState.jobId, result.message || "Shift started.", "success");
        closeModal();
      } else if (modalState.mode === "complete") {
        const payoutMethod = getSelectedPayout();
        if (!payoutMethod) {
          modalError.textContent = "Select how you'd like to receive payment.";
          modalConfirm.disabled = false;
          return;
        }
        const result = await completeJobRequest(modalState.jobId, payoutMethod);
        if (!result.success) {
          modalError.textContent = result.message || "Unable to complete this job.";
          setJobMessage(modalState.jobId, result.message || "Unable to complete this job.", "error");
          modalConfirm.disabled = false;
          return;
        }
        setJobMessage(modalState.jobId, result.message || "Job completed.", "success");
        closeModal();
      }
    });
  }

  if (modalCancel) {
    modalCancel.addEventListener("click", () => closeModal());
  }
  if (modalClose) {
    modalClose.addEventListener("click", () => closeModal());
  }
  if (modal) {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        closeModal();
      }
    });
  }
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal && !modal.hidden) {
      closeModal();
    }
  });

  jobBoard.addEventListener("click", async (event) => {
    const startButton = event.target.closest("[data-job-start]");
    if (startButton) {
      const card = startButton.closest("[data-job-card]");
      if (!card || startButton.disabled) {
        return;
      }
      const job = state.jobMap.get(card.dataset.jobId);
      if (!job) {
        return;
      }
      const totalSeconds = Math.max(0, Math.floor(getSessionSeconds(job)));
      const isResuming = totalSeconds > 0;
      openModal({
        mode: "start",
        jobId: job.id,
        title: isResuming ? "Resume shift" : "Start job",
        message: isResuming
          ? `Resume tracking time for ${job.title}.`
          : `Start working on ${job.title}?`,
        confirmLabel: isResuming ? "Resume" : "Start",
        requirePayout: false,
      });
      return;
    }

    const pauseButton = event.target.closest("[data-job-pause]");
    if (pauseButton) {
      const card = pauseButton.closest("[data-job-card]");
      if (!card || pauseButton.disabled) {
        return;
      }
      pauseButton.disabled = true;
      const result = await pauseJobRequest(card.dataset.jobId);
      pauseButton.disabled = false;
      if (!result.success) {
        setJobMessage(card.dataset.jobId, result.message || "Unable to pause this job.", "error");
        return;
      }
      setJobMessage(card.dataset.jobId, result.message || "Shift paused.", "success");
      return;
    }

    const completeButton = event.target.closest("[data-job-complete]");
    if (completeButton) {
      const card = completeButton.closest("[data-job-card]");
      if (!card || completeButton.disabled) {
        return;
      }
      const job = state.jobMap.get(card.dataset.jobId);
      if (!job) {
        return;
      }
      let earningsPreview = 0;
      if (job.pay_type === "time") {
        earningsPreview = calculateRealtimeEarnings(job, getSessionSeconds(job));
      } else if (job.pay_type === "task") {
        earningsPreview = Number(job.rate || 0);
      }
      const previewCopy =
        earningsPreview > 0
          ? `You will earn approximately ${formatCurrency(earningsPreview)}.`
          : "Complete this job to record your earnings.";
      openModal({
        mode: "complete",
        jobId: job.id,
        title: "Complete job",
        message: `${job.title} — ${previewCopy}`,
        confirmLabel: "Complete",
        requirePayout: true,
      });
    }
  });

  const initialJobs = Array.isArray(initialData.jobs) ? initialData.jobs : [];
  initialJobs.forEach((job) => {
    const normalized = normalizeJob(job);
    state.jobs.push(normalized);
    state.jobMap.set(normalized.id, normalized);
    updateJobCard(normalized);
  });
  updateSummary();
  state.jobs.forEach((job) => {
    if (job.pay_type === "time") {
      if (job.sessionStart) {
        startTimer(job);
      } else {
        updateShift(job);
      }
    }
  });
});

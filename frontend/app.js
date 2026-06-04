const API_BASE = window.PIPELINEPULSE_CONFIG?.API_BASE || window.API_BASE || "/api";

const FALLBACK_OPTIONS = {
  providers: [
    {
      id: "aws",
      label: "Amazon Web Services",
      regions: [
        { id: "us-east-1", label: "US East (N. Virginia)" },
        { id: "us-west-2", label: "US West (Oregon)" },
        { id: "eu-west-1", label: "Europe (Ireland)" },
        { id: "ap-south-1", label: "Asia Pacific (Mumbai)" },
      ],
      instances: [
        { id: "t3.small", label: "t3.small", vcpu: 2, memory_gb: 2 },
        { id: "t3.medium", label: "t3.medium", vcpu: 2, memory_gb: 4 },
        { id: "m6i.large", label: "m6i.large", vcpu: 2, memory_gb: 8 },
        { id: "c6i.large", label: "c6i.large", vcpu: 2, memory_gb: 4 },
      ],
    },
  ],
};

const state = {
  providers: FALLBACK_OPTIONS.providers,
  reports: [],
  pricingMode: "approximate",
  liveApiKey: sessionStorage.getItem("pipelinepulse_live_api_key") || "",
};

const form = document.querySelector("#reportForm");
const providerSelect = document.querySelector("#providerSelect");
const regionSelect = document.querySelector("#regionSelect");
const instanceSelect = document.querySelector("#instanceSelect");
const formMessage = document.querySelector("#formMessage");
const reportCount = document.querySelector("#reportCount");
const historyList = document.querySelector("#historyList");
const approxModeButton = document.querySelector("#approxModeButton");
const accurateModeButton = document.querySelector("#accurateModeButton");
const pricingModeInput = document.querySelector("#pricingModeInput");
const liveApiKeyInput = document.querySelector("#liveApiKeyInput");
const modeHelp = document.querySelector("#modeHelp");
const approxWarning = document.querySelector("#approxWarning");
const apiKeyModal = document.querySelector("#apiKeyModal");
const apiKeyField = document.querySelector("#apiKeyField");
const closeApiKeyModal = document.querySelector("#closeApiKeyModal");
const saveApiKey = document.querySelector("#saveApiKey");
const downloadReportButton = document.querySelector("#downloadReportButton");

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: value < 1 ? 4 : 2,
  }).format(value);
}

function formatNumber(value, digits = 2) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(value);
}

async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error || "Request failed");
  }
  return body;
}

async function loadOptions() {
  try {
    const data = await apiFetch("/options");
    state.providers = data.providers;
  } catch (error) {
    state.providers = FALLBACK_OPTIONS.providers;
    formMessage.textContent = "Using local AWS options until the backend options endpoint is available.";
  }

  refreshProviderOptions();
}

async function loadReports() {
  try {
    const data = await apiFetch("/reports");
    state.reports = data.reports;
    renderHistory();
    if (state.reports[0]) {
      renderReport(state.reports[0]);
    }
  } catch (error) {
    renderHistory();
  }
}

function availableProviders() {
  if (state.pricingMode === "approximate") {
    return state.providers.filter((provider) => provider.id === "aws");
  }
  return state.providers;
}

function refreshProviderOptions() {
  const providers = availableProviders();
  const currentProvider = providerSelect.value;
  providerSelect.innerHTML = providers
    .map((provider) => `<option value="${provider.id}">${provider.label}</option>`)
    .join("");

  if (providers.some((provider) => provider.id === currentProvider)) {
    providerSelect.value = currentProvider;
  }

  refreshProviderFields();
}

function selectedProvider() {
  return availableProviders().find((provider) => provider.id === providerSelect.value);
}

function refreshProviderFields() {
  const provider = selectedProvider();
  if (!provider) {
    regionSelect.innerHTML = "";
    instanceSelect.innerHTML = "";
    return;
  }

  regionSelect.innerHTML = provider.regions
    .map((region) => `<option value="${region.id}">${region.label}</option>`)
    .join("");
  instanceSelect.innerHTML = provider.instances
    .map(
      (instance) =>
        `<option value="${instance.id}">${instance.label} - ${instance.vcpu} vCPU / ${instance.memory_gb} GB</option>`,
    )
    .join("");
}

function setPricingMode(mode) {
  state.pricingMode = mode;
  pricingModeInput.value = mode;
  liveApiKeyInput.value = state.liveApiKey;
  approxModeButton.classList.toggle("active", mode === "approximate");
  accurateModeButton.classList.toggle("active", mode === "accurate");
  approxModeButton.setAttribute("aria-pressed", String(mode === "approximate"));
  accurateModeButton.setAttribute("aria-pressed", String(mode === "accurate"));
  modeHelp.textContent =
    mode === "accurate"
      ? "Green selected: API key required for better accurate results."
      : "Use Blue for approx results and Green (API required) for better accurate results.";
  approxWarning.classList.toggle("hidden", mode === "accurate");
  refreshProviderOptions();
}

function openApiKeyModal() {
  apiKeyField.value = state.liveApiKey;
  apiKeyModal.classList.remove("hidden");
  apiKeyField.focus();
}

function closeModal() {
  apiKeyModal.classList.add("hidden");
}

function renderReport(report) {
  const billing = report.details.billing || fallbackBilling(report);
  const carbonProjection = report.details.carbon_projection || fallbackCarbonProjection(report);
  const equivalents = report.details.equivalents || {};
  const efficiency = report.details.efficiency || { score: 0, label: "Not available" };

  document.querySelector("#emptyState").classList.add("hidden");
  document.querySelector("#reportView").classList.remove("hidden");
  document.querySelector("#reportSummaryTitle").textContent = report.pipeline_name || "Current pipeline run";
  document.querySelector("#costMetric").textContent = formatCurrency(report.cost_usd);
  document.querySelector("#carbonMetric").textContent = `${formatNumber(report.emissions_gco2e)} g`;
  document.querySelector("#energyMetric").textContent = `${formatNumber(report.energy_kwh, 4)} kWh`;
  document.querySelector("#powerMetric").textContent = `${formatNumber(report.avg_watts)} W`;
  const modeSource = document.querySelector("#modeSource");
  const isLiveReport = report.details.pricing_mode === "accurate" && !report.details.pricing.is_estimate;
  modeSource.textContent =
    report.details.report_type || (isLiveReport ? "Accurate live pricing report" : "Approximate estimate report");
  modeSource.style.background = report.details.pricing_mode === "accurate" ? "#e7f8ef" : "#eaf1ff";
  modeSource.style.color = report.details.pricing_mode === "accurate" ? "#087948" : "#164dcc";
  document.querySelector("#costMetricLabel").textContent = isLiveReport
    ? "Live total run cost"
    : "Estimated total run cost";
  document.querySelector("#costMetricHelp").textContent = isLiveReport
    ? `Total for ${formatNumber(report.duration_minutes)} minutes using live pricing`
    : `Total for ${formatNumber(report.duration_minutes)} minutes using catalog pricing`;
  document.querySelector("#runDurationDetail").textContent = `${formatNumber(report.duration_minutes)} minutes`;
  document.querySelector("#hourlyPrice").textContent = `${formatCurrency(report.hourly_price_usd)} / hour`;
  document.querySelector("#expectedRunsDetail").textContent =
    `${formatNumber(billing.expected_runs_per_month, 0)} runs / month`;
  document.querySelector("#budgetStatusDetail").textContent =
    `${formatBudgetStatus(billing.budget_status)} (${formatCurrency(Math.abs(billing.budget_remaining_usd || 0))} ${billing.budget_remaining_usd >= 0 ? "remaining" : "over"})`;
  document.querySelector("#carbonIntensity").textContent =
    `${formatNumber(report.carbon_intensity_g_per_kwh, 0)} gCO2e/kWh`;
  document.querySelector("#pricingSource").textContent = report.details.pricing.source;
  document.querySelector("#carbonSource").textContent = report.details.carbon.source;
  document.querySelector("#recommendation").textContent = report.details.recommendation.message;
  document.querySelector("#monthlyCostMetric").textContent = formatCurrency(billing.projected_monthly_cost_usd);
  document.querySelector("#yearlyCostMetric").textContent = formatCurrency(billing.projected_yearly_cost_usd);
  document.querySelector("#monthlyCostHelp").textContent =
    `${formatNumber(billing.expected_runs_per_month, 0)} expected runs per month`;
  document.querySelector("#monthlyCarbonMetric").textContent =
    `${formatNumber(carbonProjection.projected_monthly_emissions_kgco2e, 3)} kg`;
  document.querySelector("#efficiencyMetric").textContent = `${formatNumber(efficiency.score, 0)}/100`;
  document.querySelector("#efficiencyLabel").textContent = efficiency.label;
  document.querySelector("#phoneChargeMetric").textContent =
    `${formatNumber(equivalents.smartphone_charges_per_run || 0, 1)} charges`;
  document.querySelector("#drivingMetric").textContent = `${formatNumber(equivalents.driving_km_per_run || 0, 3)} km`;
  document.querySelector("#regionSavingsMetric").textContent =
    `${formatNumber(carbonProjection.estimated_monthly_region_savings_kgco2e || 0, 3)} kg`;
  updateImpactNeedle(report);
  markActiveHistory(report.id);

  const reportWarning = document.querySelector("#reportWarning");
  if (report.details.warning) {
    reportWarning.textContent = report.details.warning;
    reportWarning.classList.remove("hidden");
  } else {
    reportWarning.classList.add("hidden");
  }
}

function fallbackBilling(report) {
  return {
    expected_runs_per_month: 1,
    projected_monthly_cost_usd: report.cost_usd,
    projected_yearly_cost_usd: report.cost_usd * 12,
    budget_remaining_usd: 0,
    budget_status: "within_budget",
  };
}

function fallbackCarbonProjection(report) {
  return {
    projected_monthly_emissions_kgco2e: report.emissions_gco2e / 1000,
    estimated_monthly_region_savings_kgco2e: 0,
  };
}

function formatBudgetStatus(status) {
  return status === "over_budget" ? "Over budget" : "Within budget";
}

function renderHistory() {
  reportCount.textContent = state.reports.length;
  if (!state.reports.length) {
    historyList.innerHTML = '<p class="message">No reports stored for this browser session yet.</p>';
    return;
  }

  historyList.innerHTML = state.reports
    .map(
      (report) => `
        <article class="history-item" data-report-id="${report.id}">
          <div>
            <h3>${escapeHtml(report.pipeline_name)}</h3>
            <p>${report.provider.toUpperCase()} - ${report.region} - ${report.instance_type} - ${formatNumber(report.duration_minutes)} min</p>
          </div>
          <span class="pill">${report.details.report_type || (report.details.pricing_mode === "accurate" ? "Live pricing" : "Approx estimate")}</span>
          <span class="pill">Total ${formatCurrency(report.cost_usd)}</span>
          <span class="pill">${formatNumber(report.emissions_gco2e)} gCO2e</span>
        </article>
      `,
    )
    .join("");

  document.querySelectorAll(".history-item").forEach((item) => {
    item.addEventListener("click", () => {
      const report = state.reports.find((row) => row.id === item.dataset.reportId);
      if (report) {
        renderReport(report);
      }
    });
  });
}

function updateImpactNeedle(report) {
  const needle = document.querySelector("#impactNeedle");
  if (!needle) {
    return;
  }

  const costScore = Math.min(report.cost_usd / 1.5, 1);
  const carbonScore = Math.min(report.emissions_gco2e / 500, 1);
  const score = Math.max(8, Math.min(92, (costScore * 0.45 + carbonScore * 0.55) * 100));
  needle.style.left = `${score}%`;
}

function markActiveHistory(reportId) {
  document.querySelectorAll(".history-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.reportId === reportId);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (state.pricingMode === "accurate" && !state.liveApiKey) {
    openApiKeyModal();
    formMessage.textContent = "Please enter Live API key for accurate pricing.";
    return;
  }

  const submitButton = form.querySelector(".submit-button");
  submitButton.disabled = true;
  formMessage.textContent = "Generating report...";

  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  payload.pricing_mode = state.pricingMode;
  payload.live_api_key = state.liveApiKey;

  try {
    const data = await apiFetch("/reports", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.reports = [data.report, ...state.reports.filter((report) => report.id !== data.report.id)];
    renderReport(data.report);
    renderHistory();
    formMessage.textContent = "Report generated and stored.";
  } catch (error) {
    formMessage.textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
});

approxModeButton.addEventListener("click", () => {
  setPricingMode("approximate");
});

accurateModeButton.addEventListener("click", () => {
  if (state.pricingMode === "accurate") {
    return;
  }
  setPricingMode("accurate");
  openApiKeyModal();
});

closeApiKeyModal.addEventListener("click", () => {
  setPricingMode("approximate");
  closeModal();
});

saveApiKey.addEventListener("click", () => {
  const key = apiKeyField.value.trim();
  if (!key) {
    formMessage.textContent = "Please enter Live API key for accurate pricing.";
    return;
  }
  state.liveApiKey = key;
  sessionStorage.setItem("pipelinepulse_live_api_key", key);
  liveApiKeyInput.value = key;
  setPricingMode("accurate");
  closeModal();
  formMessage.textContent = "Accurate mode enabled.";
});

downloadReportButton.addEventListener("click", () => {
  window.print();
});

apiKeyModal.addEventListener("click", (event) => {
  if (event.target === apiKeyModal) {
    setPricingMode("approximate");
    closeModal();
  }
});

providerSelect.addEventListener("change", refreshProviderFields);

setPricingMode("approximate");
loadOptions().then(loadReports);

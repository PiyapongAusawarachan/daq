/* eslint-disable */
// Dashboard logic — talks ONLY to /api/* (never to MySQL directly).

const REFRESH_MS = 10_000;

const els = {
  device: document.getElementById("deviceSelect"),
  hours: document.getElementById("hoursSelect"),
  lastUpdate: document.getElementById("lastUpdate"),
  connPill: document.getElementById("connPill"),

  banner: document.getElementById("banner"),
  bannerStatus: document.getElementById("bannerStatus"),
  bannerScore: document.getElementById("bannerScore"),
  bannerDecision: document.getElementById("bannerDecision"),
  bannerSub: document.getElementById("bannerSub"),
  bannerIcon: document.getElementById("bannerIcon"),
  scoreArc: document.getElementById("scoreArc"),

  footwearIllustration: document.getElementById("footwearIllustration"),
  recFootwear: document.getElementById("recFootwear"),
  recFootwearDesc: document.getElementById("recFootwearDesc"),
  recFootwearBadge: document.getElementById("recFootwearBadge"),
  recSoil: document.getElementById("recSoil"),
  recAir: document.getElementById("recAir"),
  recAirBadge: document.getElementById("recAirBadge"),
  recAirScore: document.getElementById("recAirScore"),
  recAirPm: document.getElementById("recAirPm"),
  recRain: document.getElementById("recRain"),
  recRainProb: document.getElementById("recRainProb"),
  recRainBadge: document.getElementById("recRainBadge"),

  scoreTemp: document.getElementById("scoreTemp"),
  scoreHum: document.getElementById("scoreHum"),
  scoreAir: document.getElementById("scoreAir"),
  scoreSoil: document.getElementById("scoreSoil"),
  barTemp: document.getElementById("barTemp"),
  barHum: document.getElementById("barHum"),
  barAir: document.getElementById("barAir"),
  barSoil: document.getElementById("barSoil"),

  sTemp: document.getElementById("sTemp"),
  sHum: document.getElementById("sHum"),
  sSoil: document.getElementById("sSoil"),
  sPm1: document.getElementById("sPm1"),
  sPm25: document.getElementById("sPm25"),
  sPm10: document.getElementById("sPm10"),

  analysisNote: document.getElementById("analysisNote"),
  statsGrid: document.getElementById("statsGrid"),
  summaryWindowChip: document.getElementById("summaryWindowChip"),
  distWindowChip: document.getElementById("distWindowChip"),
  distTotal: document.getElementById("distTotal"),
  distLegend: document.getElementById("distLegend"),
};

const SENSOR_TILE_BY_FIELD = {
  temperature: "sTemp",
  humidity: "sHum",
  soil_moisture: "sSoil",
  pm1_0: "sPm1",
  pm2_5: "sPm25",
  pm10: "sPm10",
};

const SCORE_ARC_LEN = 326.7; // 2 * PI * r=52
let trendChart = null;
let distChart = null;

// ---------------------------------------------------------------------------
// Footwear SVG icons (3 styles for FG / SG / TF)
// ---------------------------------------------------------------------------
const FOOTWEAR_SVG = {
  FG: `<svg viewBox="0 0 110 70" xmlns="http://www.w3.org/2000/svg">
    <defs><linearGradient id="fg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#34d399"/><stop offset="100%" stop-color="#0ea5e9"/></linearGradient></defs>
    <path d="M8 38 C 8 22, 26 14, 50 14 L 78 14 C 92 14, 100 22, 100 36 L 100 44 C 100 50, 96 54, 88 54 L 18 54 C 12 54, 8 50, 8 44 Z" fill="url(#fg)" opacity="0.95"/>
    <path d="M10 44 L 100 44" stroke="#0b1024" stroke-width="2" opacity="0.4"/>
    <circle cx="20" cy="60" r="3.5" fill="#0b1024"/><circle cx="34" cy="60" r="3.5" fill="#0b1024"/>
    <circle cx="48" cy="60" r="3.5" fill="#0b1024"/><circle cx="62" cy="60" r="3.5" fill="#0b1024"/>
    <circle cx="76" cy="60" r="3.5" fill="#0b1024"/><circle cx="90" cy="60" r="3.5" fill="#0b1024"/>
    <path d="M40 22 L 70 22 M40 28 L 70 28" stroke="white" stroke-width="1.4" opacity="0.7"/>
  </svg>`,
  SG: `<svg viewBox="0 0 110 70" xmlns="http://www.w3.org/2000/svg">
    <defs><linearGradient id="sg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#fbbf24"/><stop offset="100%" stop-color="#f97316"/></linearGradient></defs>
    <path d="M8 38 C 8 22, 26 14, 50 14 L 78 14 C 92 14, 100 22, 100 36 L 100 44 C 100 50, 96 54, 88 54 L 18 54 C 12 54, 8 50, 8 44 Z" fill="url(#sg)" opacity="0.95"/>
    <path d="M10 44 L 100 44" stroke="#0b1024" stroke-width="2" opacity="0.4"/>
    <rect x="18" y="56" width="6" height="10" rx="2" fill="#0b1024"/>
    <rect x="34" y="56" width="6" height="12" rx="2" fill="#0b1024"/>
    <rect x="50" y="56" width="6" height="10" rx="2" fill="#0b1024"/>
    <rect x="66" y="56" width="6" height="12" rx="2" fill="#0b1024"/>
    <rect x="82" y="56" width="6" height="10" rx="2" fill="#0b1024"/>
    <path d="M40 22 L 70 22 M40 28 L 70 28" stroke="white" stroke-width="1.4" opacity="0.7"/>
  </svg>`,
  TF: `<svg viewBox="0 0 110 70" xmlns="http://www.w3.org/2000/svg">
    <defs><linearGradient id="tf" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#a78bfa"/><stop offset="100%" stop-color="#38bdf8"/></linearGradient></defs>
    <path d="M8 38 C 8 22, 26 14, 50 14 L 78 14 C 92 14, 100 22, 100 36 L 100 44 C 100 50, 96 54, 88 54 L 18 54 C 12 54, 8 50, 8 44 Z" fill="url(#tf)" opacity="0.95"/>
    <rect x="10" y="46" width="92" height="10" rx="3" fill="#0b1024" opacity="0.55"/>
    <g fill="#0b1024" opacity="0.85">
      <circle cx="18" cy="58" r="1.6"/><circle cx="26" cy="58" r="1.6"/><circle cx="34" cy="58" r="1.6"/>
      <circle cx="42" cy="58" r="1.6"/><circle cx="50" cy="58" r="1.6"/><circle cx="58" cy="58" r="1.6"/>
      <circle cx="66" cy="58" r="1.6"/><circle cx="74" cy="58" r="1.6"/><circle cx="82" cy="58" r="1.6"/>
      <circle cx="90" cy="58" r="1.6"/>
    </g>
    <path d="M40 22 L 70 22 M40 28 L 70 28" stroke="white" stroke-width="1.4" opacity="0.7"/>
  </svg>`,
  UNKNOWN: `<svg viewBox="0 0 110 70" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="20" width="90" height="34" rx="14" fill="rgba(148,163,184,0.25)"/>
    <text x="55" y="44" text-anchor="middle" fill="#cbd5e1" font-family="Inter,sans-serif" font-size="14" font-weight="600">?</text>
  </svg>`,
};

const STATUS_ICONS = {
  Good:    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M5 12.5l4.2 4.2L19 7" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  Caution: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 3l10 18H2L12 3z" stroke-linejoin="round"/><path d="M12 10v5M12 18v.5" stroke-linecap="round"/></svg>`,
  "Not Recommended": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="9"/><path d="M6 6l12 12" stroke-linecap="round"/></svg>`,
  Unknown: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="9"/><path d="M9 9.5a3 3 0 1 1 4.4 2.6c-.9.5-1.4 1-1.4 1.9M12 17v.5" stroke-linecap="round"/></svg>`,
};

function statusKey(status) {
  if (status === "Good") return "good";
  if (status === "Caution") return "caution";
  if (status === "Not Recommended") return "bad";
  return "unknown";
}
function bannerClass(status) { return `status-banner status-${statusKey(status)}`; }
function badgeClass(level) {
  if (level === "good") return "badge good";
  if (level === "caution") return "badge caution";
  if (level === "bad") return "badge bad";
  return "badge";
}

function fmt(value, digits = 1) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return value.toFixed(digits);
  return value;
}
function setText(el, value) { if (el) el.textContent = value; }

function relativeTime(iso) {
  if (!iso) return "—";
  const t = new Date(iso.replace(" ", "T"));
  if (isNaN(t)) return iso;
  const diff = Math.floor((Date.now() - t.getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function setRing(score) {
  if (els.scoreArc == null) return;
  const pct = Math.max(0, Math.min(100, Number(score) || 0));
  const offset = SCORE_ARC_LEN * (1 - pct / 100);
  els.scoreArc.style.transition = "stroke-dashoffset .6s cubic-bezier(.2,.8,.2,1)";
  els.scoreArc.setAttribute("stroke-dashoffset", offset.toFixed(1));
}

function setBar(el, pct) {
  if (!el) return;
  const v = Math.max(0, Math.min(100, Number(pct) || 0));
  el.style.width = `${v}%`;
}

function pickFootwearIcon(rec) {
  if (!rec) return FOOTWEAR_SVG.UNKNOWN;
  const r = rec.toString().toUpperCase();
  if (r.includes("SG") || r.includes("SOFT")) return FOOTWEAR_SVG.SG;
  if (r.includes("TF") || r.includes("TURF")) return FOOTWEAR_SVG.TF;
  if (r.includes("FG") || r.includes("FIRM")) return FOOTWEAR_SVG.FG;
  return FOOTWEAR_SVG.UNKNOWN;
}

function airBadge(status) {
  if (status === "Good") return "good";
  if (status === "Moderate") return "caution";
  if (status === "Unhealthy") return "bad";
  return "";
}
function rainBadge(prob) {
  if (prob == null) return "";
  if (prob >= 70) return "bad";
  if (prob >= 40) return "caution";
  return "good";
}

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

function getQuery() {
  const device = els.device.value || "";
  const hours = parseInt(els.hours.value || "24", 10);
  return { device, hours };
}

function setConn(state, label) {
  els.connPill.classList.remove("stale", "error");
  if (state === "stale") els.connPill.classList.add("stale");
  if (state === "error") els.connPill.classList.add("error");
  setText(els.lastUpdate, label);
}

async function loadDevices() {
  try {
    const devices = await fetchJSON("/api/devices");
    const current = els.device.value;
    els.device.innerHTML = '<option value="">All</option>' +
      devices.map(d => `<option value="${d.device_id}">${d.device_id}</option>`).join("");
    if (current) els.device.value = current;
  } catch (e) { console.warn(e); }
}

async function loadLatest({ device }) {
  const url = device ? `/api/latest?device_id=${encodeURIComponent(device)}` : "/api/latest";
  const data = await fetchJSON(url);

  // Banner
  const status = data.field_status || "Unknown";
  setText(els.bannerStatus, status);
  setText(els.bannerScore, fmt(data.field_score, 0));
  els.banner.className = bannerClass(status);
  els.bannerIcon.innerHTML = STATUS_ICONS[status] || STATUS_ICONS.Unknown;
  setRing(data.field_score || 0);

  setText(els.bannerSub,
    data.field_score == null
      ? "Awaiting first analysis (runs after configured delay)"
      : `Updated ${relativeTime(data.analysis_created_at || data.raw_created_at)}`
  );

  // Score cards + bars
  setText(els.scoreTemp, fmt(data.temp_score, 0));
  setText(els.scoreHum, fmt(data.humidity_score, 0));
  setText(els.scoreAir, fmt(data.air_quality_score, 0));
  setText(els.scoreSoil, fmt(data.soil_score, 0));
  setBar(els.barTemp, data.temp_score);
  setBar(els.barHum, data.humidity_score);
  setBar(els.barAir, data.air_quality_score);
  setBar(els.barSoil, data.soil_score);

  // Sensor tiles
  setText(els.sTemp, fmt(data.temperature, 1));
  setText(els.sHum, fmt(data.humidity, 1));
  setText(els.sSoil, fmt(data.soil_moisture, 0));
  setText(els.sPm1, fmt(data.pm1_0, 0));
  setText(els.sPm25, fmt(data.pm2_5, 0));
  setText(els.sPm10, fmt(data.pm10, 0));

  // Mark sensor tiles whose value is a fallback (sensor errored on the latest row)
  const stale = new Set(data.stale_fields || []);
  Object.entries(SENSOR_TILE_BY_FIELD).forEach(([field, elId]) => {
    const tile = document.getElementById(elId)?.closest(".sensor-tile");
    if (!tile) return;
    tile.classList.toggle("stale", stale.has(field));
  });

  // PM detail line
  setText(els.recAirPm,
    `PM2.5 ${fmt(data.pm2_5, 0)} \u00B5g/m\u00B3 \u00B7 PM10 ${fmt(data.pm10, 0)} \u00B5g/m\u00B3`);

  // Analysis-source note
  if (data.analysis_from_raw_id == null) {
    setText(els.analysisNote, "Analysis source: not yet available for any reading.");
  } else if (data.analysis_is_latest) {
    setText(els.analysisNote, `Analysis source: latest reading (raw_id ${data.analysis_from_raw_id}).`);
  } else {
    setText(els.analysisNote,
      `Analysis source: previous reading (raw_id ${data.analysis_from_raw_id}). The most recent sample is awaiting processing.`);
  }

  setConn("ok", `Updated ${relativeTime(data.raw_created_at)}`);
}

async function loadRecommendation({ device }) {
  const url = device ? `/api/recommendation?device_id=${encodeURIComponent(device)}` : "/api/recommendation";
  const data = await fetchJSON(url);

  setText(els.bannerDecision, data.play_decision || "Unknown");

  // Footwear card
  const footwear = data.footwear_recommendation || "—";
  setText(els.recFootwear, footwear);
  els.footwearIllustration.innerHTML = pickFootwearIcon(data.footwear_recommendation);
  setText(els.recSoil, `Soil: ${data.soil_condition || "—"}`);

  const fwLevel = data.field_status === "Good" ? "good"
                : data.field_status === "Caution" ? "caution"
                : data.field_status === "Not Recommended" ? "bad" : "";
  els.recFootwearBadge.className = badgeClass(fwLevel);
  els.recFootwearBadge.textContent = data.field_status || "—";

  let fwDesc = "Pick depends on soil condition";
  const r = (data.footwear_recommendation || "").toUpperCase();
  if (r.includes("FG")) fwDesc = "Firm ground cleats — best on dry, hard turf";
  else if (r.includes("SG")) fwDesc = "Soft ground cleats — long studs for wet grass";
  else if (r.includes("TF")) fwDesc = "Turf shoes — flat sole for hard surfaces";
  setText(els.recFootwearDesc, fwDesc);

  // Air card
  setText(els.recAir, data.air_quality_status || "—");
  setText(els.recAirScore, `Field score: ${fmt(data.field_score, 1)}`);
  els.recAirBadge.className = badgeClass(airBadge(data.air_quality_status));
  els.recAirBadge.textContent = data.air_quality_status || "—";

  // Rain card
  setText(els.recRain, data.rain_forecast_status || "—");
  setText(els.recRainProb, `Probability: ${fmt(data.rain_probability_pct, 0)}%`);
  els.recRainBadge.className = badgeClass(rainBadge(data.rain_probability_pct));
  els.recRainBadge.textContent = data.rain_probability_pct != null
    ? `${Math.round(data.rain_probability_pct)}%`
    : "—";
}

async function loadHistory({ device, hours }) {
  const q = new URLSearchParams({ hours: hours, limit: 300 });
  if (device) q.set("device_id", device);
  const rows = await fetchJSON(`/api/history?${q.toString()}`);

  const labels = rows.map(r => (r.created_at || "").slice(5, 16));
  const tempData = rows.map(r => r.temperature);
  const humData = rows.map(r => r.humidity);
  const scoreData = rows.map(r => r.field_score);

  const datasets = [
    { label: "Temperature (\u00B0C)", data: tempData, borderColor: "#f87171", backgroundColor: "rgba(248,113,113,0.12)", yAxisID: "y", tension: 0.35, fill: true, pointRadius: 0, borderWidth: 2 },
    { label: "Humidity (%)",          data: humData,  borderColor: "#38bdf8", backgroundColor: "rgba(56,189,248,0.12)",  yAxisID: "y", tension: 0.35, fill: true, pointRadius: 0, borderWidth: 2 },
    { label: "Field Score",           data: scoreData, borderColor: "#a78bfa", backgroundColor: "rgba(167,139,250,0.16)", yAxisID: "y1", tension: 0.35, fill: true, pointRadius: 0, borderWidth: 2 },
  ];

  if (trendChart) trendChart.destroy();
  trendChart = new Chart(document.getElementById("trendChart"), {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { color: "#cbd5e1", boxWidth: 12, usePointStyle: true } },
        tooltip: { backgroundColor: "rgba(13,18,36,0.95)", borderColor: "rgba(148,163,184,0.25)", borderWidth: 1 },
      },
      scales: {
        x: { ticks: { color: "#8b94a7", maxTicksLimit: 8 }, grid: { color: "rgba(148,163,184,0.08)" } },
        y: { position: "left",  ticks: { color: "#8b94a7" }, grid: { color: "rgba(148,163,184,0.08)" } },
        y1: { position: "right", ticks: { color: "#8b94a7" }, grid: { drawOnChartArea: false }, suggestedMin: 0, suggestedMax: 100 },
      },
    },
  });
}

function statTile(label, value, unit, range) {
  return `
    <div class="stat-tile">
      <span class="stat-label">${label}</span>
      <span class="stat-value">${value}${unit ? `<small>${unit}</small>` : ""}</span>
      ${range ? `<span class="stat-range">${range}</span>` : ""}
    </div>`;
}

function rangeText(min, max, digits) {
  const lo = fmt(min, digits);
  const hi = fmt(max, digits);
  return `<span>min <b>${lo}</b></span><span>max <b>${hi}</b></span>`;
}

function windowLabel(hours) {
  if (hours < 24) return `last ${hours}h`;
  const d = Math.round(hours / 24);
  return d === 1 ? "last 1d" : `last ${d}d`;
}

async function loadSummary({ device, hours }) {
  const q = new URLSearchParams({ hours: hours });
  if (device) q.set("device_id", device);
  const data = await fetchJSON(`/api/summary?${q.toString()}`);
  const a = data.aggregates || {};

  els.summaryWindowChip.textContent = windowLabel(hours);
  els.distWindowChip.textContent = windowLabel(hours);

  els.statsGrid.innerHTML = [
    statTile("Readings",          a.row_count ?? 0,                 "rows", ""),
    statTile("Avg Field Score",   fmt(a.avg_field_score, 1),        "/100", ""),
    statTile("Temperature",       fmt(a.avg_temp, 1),               "\u00B0C avg",  rangeText(a.min_temp, a.max_temp, 1)),
    statTile("Humidity",          fmt(a.avg_humidity, 1),           "% avg",        rangeText(a.min_humidity, a.max_humidity, 1)),
    statTile("PM2.5",             fmt(a.avg_pm25, 1),               "\u00B5g/m\u00B3 avg", rangeText(a.min_pm25, a.max_pm25, 0)),
    statTile("PM10",              fmt(a.avg_pm10, 1),               "\u00B5g/m\u00B3 avg", rangeText(a.min_pm10, a.max_pm10, 0)),
    statTile("Soil Moisture",     fmt(a.avg_soil, 0),               "ADC avg",      rangeText(a.min_soil, a.max_soil, 0)),
    statTile("Rain Probability",  fmt(a.avg_rain_prob, 0),          "% avg",        ""),
  ].join("");

  // ----- Distribution donut -----
  const distRaw = data.status_distribution || {};
  const order = ["Good", "Caution", "Not Recommended", "Unknown"];
  const labels = order.filter(k => distRaw[k] != null);
  const values = labels.map(k => distRaw[k]);
  const colorMap = {
    "Good": "#22c55e",
    "Caution": "#f59e0b",
    "Not Recommended": "#ef4444",
    "Unknown": "#64748b",
  };
  const colors = labels.map(k => colorMap[k] || "#64748b");
  const total = values.reduce((s, v) => s + v, 0);

  setText(els.distTotal, total);

  if (total === 0) {
    els.distLegend.innerHTML = `<div class="dist-empty">No analyzed readings in this window yet.</div>`;
  } else {
    els.distLegend.innerHTML = labels.map((k, i) => {
      const v = values[i];
      const pct = ((v / total) * 100).toFixed(1);
      return `
        <div class="dist-row">
          <span class="dist-swatch" style="background:${colors[i]}"></span>
          <span class="dist-name">${k}</span>
          <span class="dist-count">${v}</span>
          <span class="dist-pct">${pct}%</span>
        </div>`;
    }).join("");
  }

  if (distChart) distChart.destroy();
  distChart = new Chart(document.getElementById("distChart"), {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderColor: "rgba(13,18,36,0.9)",
        borderWidth: 3,
        hoverOffset: 10,
        hoverBorderColor: "rgba(255,255,255,0.18)",
        spacing: 2,
      }],
    },
    options: {
      cutout: "72%",
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(13,18,36,0.95)",
          borderColor: "rgba(148,163,184,0.25)",
          borderWidth: 1,
          callbacks: {
            label: (ctx) => {
              const v = ctx.parsed;
              const pct = total ? ((v / total) * 100).toFixed(1) : "0";
              return ` ${ctx.label}: ${v} (${pct}%)`;
            },
          },
        },
      },
      animation: { animateRotate: true, animateScale: true },
    },
  });
}

async function refreshAll() {
  const ctx = getQuery();
  try {
    await Promise.all([
      loadLatest(ctx),
      loadRecommendation(ctx),
      loadHistory(ctx),
      loadSummary(ctx),
    ]);
  } catch (err) {
    console.error(err);
    setConn("error", "Update failed, retrying...");
  }
}

async function init() {
  await loadDevices();
  await refreshAll();
  els.device.addEventListener("change", refreshAll);
  els.hours.addEventListener("change", refreshAll);
  setInterval(refreshAll, REFRESH_MS);
}

init();

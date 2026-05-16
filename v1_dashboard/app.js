const DATA_URL = "../data/derived_only/dashboard/dashboard_data.json";
const HISTORY_URLS = {
  summary: "../data/derived_only/history/trend_daily_summary.csv",
  city: "../data/derived_only/history/trend_city.csv",
  role: "../data/derived_only/history/trend_role.csv",
  skill: "../data/derived_only/history/trend_skill.csv",
  source: "../data/derived_only/history/trend_source.csv"
};

const fmt = new Intl.NumberFormat("en-US");
let dashboardData = null;
let historyData = null;
let selectedCountry = "All countries";

function byId(id) {
  return document.getElementById(id);
}

function text(id, value) {
  const node = byId(id);
  if (node) node.textContent = value;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function toneClass(index) {
  return ["fill-blue", "fill-green", "fill-pink", "fill-cream", "fill-orange"][index % 5];
}

function clampPercent(value, floor = 3) {
  const numeric = Number(value || 0);
  return Math.max(floor, Math.min(100, numeric));
}

function parseCsv(textValue) {
  const text = String(textValue || "").replace(/^\uFEFF/, "");
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (char === '"') {
      if (quoted && next === '"') {
        field += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
      continue;
    }

    if (char === "," && !quoted) {
      row.push(field);
      field = "";
      continue;
    }

    if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") index += 1;
      row.push(field);
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      field = "";
      continue;
    }

    field += char;
  }

  if (field || row.length) {
    row.push(field);
    if (row.some((value) => value !== "")) rows.push(row);
  }

  if (!rows.length) return [];
  const [headers, ...body] = rows;
  return body.map((values) =>
    headers.reduce((record, header, index) => {
      record[header] = values[index] ?? "";
      return record;
    }, {})
  );
}

async function fetchCsv(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return parseCsv(await response.text());
}

async function loadHistoryData() {
  const entries = await Promise.all(
    Object.entries(HISTORY_URLS).map(async ([key, url]) => {
      try {
        return [key, await fetchCsv(url)];
      } catch {
        return [key, []];
      }
    })
  );
  return Object.fromEntries(entries);
}

function latestRow(rows) {
  if (!Array.isArray(rows) || !rows.length) return {};
  return rows.slice().sort((a, b) => String(b.snapshot_date || "").localeCompare(String(a.snapshot_date || "")))[0];
}

function sortedSnapshotRows(rows) {
  if (!Array.isArray(rows)) return [];
  return rows.slice().sort((a, b) => String(b.snapshot_date || "").localeCompare(String(a.snapshot_date || "")));
}

function rowsForSnapshot(rows, snapshotDate) {
  if (!Array.isArray(rows)) return [];
  return rows.filter((row) => row.snapshot_date === snapshotDate);
}

function formatLongDate(value) {
  const textValue = String(value || "");
  const parts = textValue.split("-").map((part) => Number(part));
  if (parts.length !== 3 || parts.some((part) => Number.isNaN(part))) return textValue;
  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric"
  }).format(new Date(Date.UTC(parts[0], parts[1] - 1, parts[2])));
}

function rowsForCountry(rows, country) {
  if (!Array.isArray(rows)) return [];
  if (!country || country === "All countries") return rows;
  return rows.filter((row) => row.country === country);
}

function sumRows(rows, field = "count") {
  return rows.reduce((sum, row) => sum + Number(row[field] || 0), 0);
}

function renderMiniBars(id, rows, labelField, valueField = "count", limit = 4) {
  const node = byId(id);
  if (!node) return;
  const data = rows.slice(0, limit);
  if (!data.length) {
    node.innerHTML = `<p class="empty">No aggregate rows available.</p>`;
    return;
  }
  const max = Math.max(...data.map((row) => Number(row[valueField] || 0)), 1);
  node.innerHTML = data
    .map((row, index) => {
      const value = Number(row[valueField] || 0);
      const width = clampPercent((value / max) * 100);
      return `
        <div class="mini-row">
          <span>${escapeHtml(labelField(row))}</span>
          <div class="mini-track" aria-hidden="true">
            <span class="mini-fill ${toneClass(index)}" style="--target-width: ${width}%"></span>
          </div>
          <span class="mini-value">${fmt.format(value)}</span>
        </div>
      `;
    })
    .join("");
}

function renderBars(id, rows, labelField, valueField = "count", limit = 10) {
  const node = byId(id);
  if (!node) return;
  const data = rows.slice(0, limit);
  if (!data.length) {
    node.innerHTML = `<p class="empty">No aggregate rows available.</p>`;
    return;
  }
  const max = Math.max(...data.map((row) => Number(row[valueField] || 0)), 1);
  node.innerHTML = data
    .map((row, index) => {
      const value = Number(row[valueField] || 0);
      const width = clampPercent((value / max) * 100);
      return `
        <div class="bar-row">
          <span class="bar-label">${escapeHtml(labelField(row))}</span>
          <div class="bar-track" aria-hidden="true">
            <span class="bar-fill ${toneClass(index)}" style="--target-width: ${width}%"></span>
          </div>
          <span class="bar-value">${fmt.format(value)}</span>
        </div>
      `;
    })
    .join("");
}

function renderHero(data) {
  const kpis = data.kpis || {};
  const node = byId("hero-kpis");
  if (node) {
    const cards = [
      ["Included postings", fmt.format(kpis.included_rows || 0)],
      ["Countries covered", fmt.format(kpis.countries || 0)],
      ["Cities covered", fmt.format(kpis.cities || 0)],
      ["Skills tracked", fmt.format((data.skill_counts || []).length)]
    ];
    node.innerHTML = cards
      .map(
        ([label, value]) => `
          <article class="hero-stat">
            <strong>${escapeHtml(value)}</strong>
            <span>${escapeHtml(label)}</span>
          </article>
        `
      )
      .join("");
  }

  const cityRows = data.postings_by_city || [];
  text("hero-city-total", `${fmt.format(sumRows(cityRows))} postings`);
  renderMiniBars("hero-city-bars", cityRows, (row) => row.city, "count", 4);
}

function renderCountryOptions(data) {
  const select = byId("country-select");
  if (!select) return;

  const countries = (data.countries || [])
    .map((row) => row.country)
    .filter(Boolean);

  const options = ["All countries", ...countries];
  select.innerHTML = options
    .map((country) => `<option value="${escapeHtml(country)}">${escapeHtml(country)}</option>`)
    .join("");
  select.value = selectedCountry;
  select.addEventListener("change", () => {
    selectedCountry = select.value;
    renderExplorer();
  });
}

function renderTopSkills(rows) {
  const node = byId("top-skills-list");
  if (!node) return;
  const data = rows.slice(0, 10);
  if (!data.length) {
    node.innerHTML = `<p class="empty">No skill rows available.</p>`;
    return;
  }
  node.innerHTML = data
    .map(
      (row, index) => `
        <div class="top-skill-row">
          <span class="top-rank">${index + 1}</span>
          <span class="top-name">${escapeHtml(row.skill)}</span>
          <span class="top-count">${fmt.format(row.count)}</span>
        </div>
      `
    )
    .join("");
}

function renderRoleBars(rows) {
  const node = byId("role-chart");
  if (!node) return;
  const data = rows.slice(0, 8);
  if (!data.length) {
    node.innerHTML = `<p class="empty">No role rows available.</p>`;
    return;
  }
  const max = Math.max(...data.map((row) => Number(row.count || 0)), 1);
  node.innerHTML = data
    .map((row, index) => {
      const width = clampPercent((Number(row.count || 0) / max) * 100);
      return `
        <div class="role-row">
          <span class="role-label">${escapeHtml(row.role_category)}</span>
          <div class="role-track" aria-hidden="true">
            <span class="role-fill ${toneClass(index)}" style="--target-width: ${width}%"></span>
          </div>
          <span class="role-value">${fmt.format(row.count)}</span>
        </div>
      `;
    })
    .join("");
}

function renderMetricCards(id, cards) {
  const node = byId(id);
  if (!node) return;
  node.innerHTML = cards
    .map(
      ([label, value, helper]) => `
        <article class="signal-metric">
          <strong>${escapeHtml(value)}</strong>
          <span>${escapeHtml(label)}</span>
          ${helper ? `<small>${escapeHtml(helper)}</small>` : ""}
        </article>
      `
    )
    .join("");
}

function renderSourceList(rows) {
  const node = byId("v2-source-list");
  if (!node) return;
  if (!rows?.length) {
    node.innerHTML = `<p class="empty">No source history available.</p>`;
    return;
  }
  node.innerHTML = rows
    .map(
      (row) => `
        <div class="source-row">
          <span>${escapeHtml(row.source_name)}</span>
          <strong>${fmt.format(Number(row.unique_job_count || 0))}</strong>
          <small>${fmt.format(Number(row.observation_count || 0))} observations</small>
        </div>
      `
    )
    .join("");
}

function skillGroupRows(rows) {
  const groups = new Map();
  rows.forEach((row) => {
    const group = row.skill_group || "Other";
    const current = groups.get(group) || { skill_group: group, count: 0, fresh_jobs: 0 };
    current.count += Number(row.count || 0);
    current.fresh_jobs += Number(row.fresh_jobs || 0);
    groups.set(group, current);
  });
  return Array.from(groups.values()).sort((a, b) => b.count - a.count || a.skill_group.localeCompare(b.skill_group));
}

function renderV2Signals(history) {
  if (!history) return;
  const summaries = sortedSnapshotRows(history.summary);
  const summary = summaries[0] || {};
  const previousSummary = summaries.find((row) => row.snapshot_date !== summary.snapshot_date) || {};
  if (!Object.keys(summary).length) {
    text("signals-summary", "Current market read is unavailable until the tracker history files are generated.");
    return;
  }

  const snapshotDate = formatLongDate(summary.snapshot_date);
  const totalJobs = Number(summary.total_unique_jobs || 0);
  const previousTotal = Number(previousSummary.total_unique_jobs || 0);
  const movementText = previousSummary.snapshot_date
    ? `${totalJobs - previousTotal >= 0 ? "+" : ""}${fmt.format(totalJobs - previousTotal)} observed since ${formatLongDate(previousSummary.snapshot_date)}`
    : "Trend movement appears after another update.";
  const latestCityRows = rowsForSnapshot(history.city, summary.snapshot_date);
  const latestRoleRows = rowsForSnapshot(history.role, summary.snapshot_date);
  const latestSkillRows = rowsForSnapshot(history.skill, summary.snapshot_date);
  const latestSourceRows = rowsForSnapshot(history.source, summary.snapshot_date);

  text(
    "signals-summary",
    `Current market read: ${snapshotDate} \u00b7 ${fmt.format(totalJobs)} reviewed roles \u00b7 ${movementText}.`
  );

  renderMetricCards("v2-metrics", [
    ["Reviewed roles", fmt.format(totalJobs), movementText],
    ["Fresh jobs", fmt.format(Number(summary.fresh_jobs || 0)), "0-30 day posting window"],
    ["Avg confidence", `${Number(summary.avg_confidence_score || 0).toFixed(1)}`, "Completeness and validation score"],
    ["Skill signals", fmt.format(Number(summary.skill_count || 0)), "Mapped into taxonomy groups"]
  ]);
  renderSourceList(latestSourceRows);
  renderBars("v2-city-chart", latestCityRows, (row) => `${row.city}, ${row.country}`, "count", 5);
  renderBars("v2-role-chart", latestRoleRows, (row) => row.role_category, "count", 8);
  renderBars("v2-skill-group-chart", skillGroupRows(latestSkillRows), (row) => row.skill_group, "count", 8);
}

function renderExplorer() {
  if (!dashboardData) return;

  const skillRows =
    selectedCountry === "All countries"
      ? dashboardData.skill_counts || []
      : rowsForCountry(dashboardData.skill_counts_by_country || [], selectedCountry);
  const roleRows =
    selectedCountry === "All countries"
      ? dashboardData.role_mix || []
      : rowsForCountry(dashboardData.role_mix_by_country || [], selectedCountry);
  const cityRows = rowsForCountry(dashboardData.postings_by_city || [], selectedCountry);
  const countryRows = dashboardData.countries || [];
  const postingCount = selectedCountry === "All countries" ? sumRows(countryRows) : sumRows(cityRows);
  const countryLabel = selectedCountry === "All countries" ? "the GCC sample" : selectedCountry;

  text(
    "explore-summary",
    `For ${countryLabel}, this prototype includes ${fmt.format(postingCount)} reviewed-and-included postings.`
  );
  text("skill-chart-title", `Skills in demand in ${countryLabel}`);
  text("top-skills-title", `Top skills in ${countryLabel}`);
  text("role-chart-title", `Analyst categories in ${countryLabel}`);

  renderBars("skills-chart", skillRows, (row) => row.skill, "count", 10);
  renderTopSkills(skillRows);
  renderRoleBars(roleRows);
  renderBars("city-chart", cityRows, (row) => `${row.city}, ${row.country}`, "count", 8);
  renderBars("country-chart", countryRows, (row) => row.country, "count", 4);

  requestAnimationFrame(() => {
    document.querySelectorAll(".explore-section .bar-row, .explore-section .role-row").forEach((node) => {
      node.classList.add("is-visible");
    });
  });
}

function renderMethodology(data) {
  const list = byId("data-handling-list");
  if (list) {
    list.innerHTML = (data.data_handling || [])
      .map((item) => `<article class="methodology-item">${escapeHtml(item)}</article>`)
      .join("");
  }

  text(
    "footer-status",
    `${data.metadata?.title || "Dashboard"} | ${data.metadata?.status || "Prototype"}`
  );
}

function setupInteractions() {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.documentElement.classList.toggle("motion-ready", !reduced);

  const revealTargets = document.querySelectorAll(".reveal, .observe-section");
  if (reduced || !("IntersectionObserver" in window)) {
    revealTargets.forEach((node) => node.classList.add("is-visible"));
  } else {
    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            revealObserver.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.14 }
    );
    revealTargets.forEach((node) => revealObserver.observe(node));
  }

  const navLinks = Array.from(document.querySelectorAll(".site-nav a"));
  const sections = navLinks
    .map((link) => {
      const id = link.getAttribute("href")?.replace("#", "");
      const section = id ? byId(id) : null;
      return section ? [link, section] : null;
    })
    .filter(Boolean);

  if (!sections.length) return;

  const setActiveLink = (activeLink) => {
    navLinks.forEach((link) => {
      const isActive = link === activeLink;
      link.classList.toggle("is-active", isActive);
      if (isActive) {
        link.setAttribute("aria-current", "true");
      } else {
        link.removeAttribute("aria-current");
      }
    });
  };

  const updateActiveSection = () => {
    const headerHeight = document.querySelector(".site-header")?.offsetHeight || 0;
    const navLine = Math.max(headerHeight + 24, window.innerHeight * 0.38);
    const active = sections.find(([, section]) => {
      const rect = section.getBoundingClientRect();
      return rect.top <= navLine && rect.bottom > navLine;
    })?.[0] || null;

    setActiveLink(active);
  };

  let navTicking = false;
  const requestNavUpdate = () => {
    if (navTicking) return;
    navTicking = true;
    requestAnimationFrame(() => {
      updateActiveSection();
      navTicking = false;
    });
  };

  updateActiveSection();
  window.addEventListener("scroll", requestNavUpdate, { passive: true });
  window.addEventListener("resize", requestNavUpdate);
}

function render(data) {
  dashboardData = data;
  renderHero(data);
  renderV2Signals(historyData);
  renderCountryOptions(data);
  renderExplorer();
  renderMethodology(data);
  setupInteractions();
}

async function load() {
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const [data, history] = await Promise.all([response.json(), loadHistoryData()]);
    historyData = history;
    render(data);
  } catch (error) {
    text(
      "footer-status",
      `Could not load aggregate dashboard data. Run: python scripts\\build_dashboard_aggregates.py, then serve the repo root locally. (${error.message})`
    );
  }
}

load();

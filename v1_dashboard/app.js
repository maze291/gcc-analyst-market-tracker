const DATA_URL = "../data/derived_only/dashboard/dashboard_data.json";

const fmt = new Intl.NumberFormat("en-US");

function text(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

function percent(value) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function colorClass(index) {
  return ["", "teal", "amber", "red"][index % 4];
}

function renderBars(id, rows, labelField, valueField = "count", limit = 10) {
  const node = document.getElementById(id);
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
      const width = Math.max(4, (value / max) * 100);
      const label = labelField(row);
      return `
        <div class="bar-row">
          <span class="bar-label">${escapeHtml(label)}</span>
          <div class="bar-track">
            <span class="bar-fill ${colorClass(index)}" style="width: ${width}%"></span>
          </div>
          <span class="bar-value">${fmt.format(value)}</span>
        </div>
      `;
    })
    .join("");
}

function renderSourceQuality(rows) {
  const node = document.getElementById("source-quality");
  if (!node) return;
  node.innerHTML = rows
    .map(
      (row) => `
      <article class="source-card">
        <header>
          <h3>${escapeHtml(row.source_name)}</h3>
          <span class="score">${fmt.format(row.reviewed_rows)} reviewed</span>
        </header>
        <div class="quality-grid">
          <div class="quality-metric">
            <strong>${fmt.format(row.included_rows)}</strong>
            <span>Included</span>
          </div>
          <div class="quality-metric">
            <strong>${percent(row.title_relevance_rate)}</strong>
            <span>Title relevance</span>
          </div>
          <div class="quality-metric">
            <strong>${percent(row.company_presence_rate)}</strong>
            <span>Company present</span>
          </div>
          <div class="quality-metric">
            <strong>${percent(row.skills_extractable_rate)}</strong>
            <span>Skills extractable</span>
          </div>
        </div>
        <div class="risk-strip">
          <div><strong>${percent(row.restricted_source_rate)}</strong>Restricted source</div>
          <div><strong>${percent(row.possible_pii_raw_pattern_rate)}</strong>Raw contact pattern</div>
          <div><strong>${percent(row.salary_coverage_rate)}</strong>Salary coverage</div>
        </div>
      </article>
    `
    )
    .join("");
}

function renderSalary(rows) {
  const node = document.getElementById("salary-chart");
  if (!node) return;
  if (!rows.length) {
    node.innerHTML = `<p class="empty">No salary coverage rows available.</p>`;
    return;
  }
  node.innerHTML = rows
    .map((row) => {
      const rate = Number(row.salary_coverage_rate || 0);
      return `
        <div class="stack-row">
          <header>
            <span>${escapeHtml(row.source_name)} / ${escapeHtml(row.country)}</span>
            <span>${percent(rate)} (${fmt.format(row.salary_present_rows)} of ${fmt.format(row.included_rows)})</span>
          </header>
          <div class="stack-track">
            <span class="stack-fill" style="width: ${Math.max(2, rate)}%"></span>
          </div>
        </div>
      `;
    })
    .join("");
}

function render(data) {
  const kpis = data.kpis || {};
  text("kpi-included", fmt.format(kpis.included_rows || 0));
  text("kpi-deduped", `${fmt.format(kpis.deduped_included_estimate || 0)} deduped estimate`);
  text("kpi-reviewed", fmt.format(kpis.reviewed_rows || 0));
  text("kpi-review-later", `${fmt.format(kpis.review_later_rows || 0)} review later`);
  text("kpi-markets", fmt.format(kpis.countries || 0));
  text("kpi-cities", `${fmt.format(kpis.cities || 0)} cities`);
  text("kpi-salary", percent(kpis.salary_coverage_rate));
  text("kpi-restricted", percent(kpis.restricted_source_rate_all_reviewed));
  text("kpi-pii", percent(kpis.possible_pii_raw_pattern_rate_all_reviewed));
  text("retained-pii", fmt.format(data.metadata?.retained_pii_contact_fields ?? 0));
  text("review-status", fmt.format(kpis.review_later_rows || 0));

  renderSourceQuality(data.source_quality || []);
  renderBars("city-chart", data.postings_by_city || [], (row) => `${row.city}, ${row.country}`, "count", 8);
  renderBars("role-chart", data.role_mix || [], (row) => row.role_category, "count", 10);
  renderBars("skills-chart", data.skill_counts || [], (row) => row.skill, "count", 10);
  renderSalary(data.salary_coverage || []);

  text(
    "footer-status",
    `${data.metadata?.title || "Dashboard"} | ${data.metadata?.status || "Prototype"} | ${data.metadata?.public_release_status || "Public release not cleared"}`
  );
}

async function load() {
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    render(data);
  } catch (error) {
    text(
      "footer-status",
      `Could not load aggregate dashboard data. Run: python scripts\\build_dashboard_aggregates.py, then serve the repo root locally. (${error.message})`
    );
  }
}

load();

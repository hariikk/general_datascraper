"use strict";

let pollTimer = null;

/* ---------- small helpers ---------- */

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || "Request failed");
  return r.json();
}

async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || "Request failed");
  return data;
}

function setBanner(msg, type) {
  const b = document.getElementById("banner");
  if (!msg) { b.classList.add("hidden"); b.textContent = ""; return; }
  b.textContent = msg;
  b.className = "banner " + (type || "info");
}

function setBusy(running) {
  document.getElementById("search-btn").disabled = running;
  document.getElementById("extract-btn").disabled = running;
}

/* ---------- Ollama status ---------- */

async function checkStatus() {
  const pill = document.getElementById("ollama-pill");
  pill.className = "pill pill-unknown";
  pill.textContent = "Checking Ollama…";
  try {
    const s = await getJSON("/api/status");
    const ok = s.ollama && s.ollama.ok;
    pill.textContent = ok ? "Ollama ready" : "Ollama not available";
    pill.className = "pill " + (ok ? "pill-ok" : "pill-bad");
    pill.title = (s.ollama && s.ollama.message) || "";
    if (!ok) setBanner(s.ollama.message, "error");
    if (s.job) {
      setBusy(true);
      showProgress(true);
      pollJob(s.job.id);
    }
  } catch (e) {
    pill.className = "pill pill-bad";
    pill.textContent = "Cannot reach the server";
  }
}

/* ---------- sources ---------- */

async function loadSources() {
  const list = document.getElementById("source-list");
  list.innerHTML = "";
  const sources = await getJSON("/api/sources");
  sources.forEach(s => {
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.value = s.name;
    cb.checked = true;
    label.appendChild(cb);
    label.appendChild(document.createTextNode(s.label));
    list.appendChild(label);
  });
}

/* ---------- settings ---------- */

async function loadSettings() {
  const s = await getJSON("/api/settings");
  document.getElementById("set-email").value = s.email || "";
  document.getElementById("set-model").value = s.model || "";
  document.getElementById("set-max").value = s.max_results || 50;
  document.getElementById("max-results").value = s.max_results || 50;
}

async function saveSettings() {
  try {
    const body = {
      email: document.getElementById("set-email").value.trim(),
      model: document.getElementById("set-model").value.trim(),
      max_results: parseInt(document.getElementById("set-max").value, 10) || 50,
    };
    await postJSON("/api/settings", body);
    document.getElementById("max-results").value = body.max_results;
    setBanner("Settings saved.", "ok");
    setTimeout(() => setBanner(""), 2000);
    checkStatus();
  } catch (e) {
    setBanner(e.message, "error");
  }
}

/* ---------- query builder ---------- */

function addTerm(value) {
  const list = document.getElementById("term-list");
  const rows = list.querySelectorAll(".term-row");
  const row = document.createElement("div");
  row.className = "term-row";

  if (rows.length > 0) {
    const op = document.createElement("select");
    op.className = "term-op";
    ["AND", "OR", "NOT"].forEach(o => {
      const opt = document.createElement("option");
      opt.value = o; opt.textContent = o;
      op.appendChild(opt);
    });
    row.appendChild(op);
  }

  const input = document.createElement("input");
  input.type = "text";
  input.className = "term-input";
  input.placeholder = rows.length === 0 ? "e.g. nicotinic acetylcholine receptor" : "e.g. mutation";
  if (value) input.value = value;
  row.appendChild(input);

  if (rows.length > 0) {
    const rm = document.createElement("button");
    rm.type = "button";
    rm.className = "remove-term";
    rm.textContent = "×";
    rm.title = "Remove";
    rm.onclick = () => row.remove();
    row.appendChild(rm);
  }

  list.appendChild(row);
}

function buildQuery() {
  const rows = [...document.querySelectorAll("#term-list .term-row")];
  const terms = [];
  rows.forEach((row, idx) => {
    const t = row.querySelector(".term-input").value.trim();
    if (!t) return;
    const op = idx === 0 ? null : row.querySelector(".term-op").value;
    terms.push({ op, term: t });
  });
  if (!terms.length) return "";
  let q = terms[0].term;
  for (let i = 1; i < terms.length; i++) q += " " + terms[i].op + " " + terms[i].term;
  return q;
}

/* ---------- search & extract ---------- */

async function doSearch() {
  setBanner("");
  const query = buildQuery();
  const sources = [...document.querySelectorAll("#source-list input:checked")].map(c => c.value);
  const maxResults = parseInt(document.getElementById("max-results").value, 10) || 50;
  if (!query) { setBanner("Enter at least one search term.", "error"); return; }
  if (!sources.length) { setBanner("Choose at least one website.", "error"); return; }

  try {
    const { job_id } = await postJSON("/api/search", { query, sources, max_results: maxResults });
    setBusy(true);
    showProgress(true);
    pollJob(job_id);
  } catch (e) {
    setBanner(e.message, "error");
  }
}

async function doExtract() {
  setBanner("");
  const goal = document.getElementById("goal").value.trim();
  const columns = document.getElementById("columns").value
    .split(",").map(s => s.trim()).filter(Boolean);
  if (!goal) { setBanner("Describe what data you want to extract.", "error"); return; }

  try {
    const { job_id } = await postJSON("/api/extract", { goal, columns });
    setBusy(true);
    showProgress(true);
    pollJob(job_id);
  } catch (e) {
    setBanner(e.message, "error");
  }
}

/* ---------- polling ---------- */

function showProgress(show) {
  document.getElementById("progress-card").classList.toggle("hidden", !show);
}

function pollJob(jobId) {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const job = await getJSON("/api/job/" + jobId);
      renderProgress(job);
      if (job.status === "done") {
        clearInterval(pollTimer);
        pollTimer = null;
        setBusy(false);
        showProgress(false);
        await loadResults();
        if (job.result && job.result.added !== undefined) {
          setBanner(`Search finished: ${job.result.total} papers.`, "ok");
        } else if (job.result && job.result.extracted !== undefined) {
          setBanner(`Extraction finished: ${job.result.extracted} row(s) extracted, ${job.result.closed} paper(s) closed.`, "ok");
        }
      } else if (job.status === "error") {
        clearInterval(pollTimer);
        pollTimer = null;
        setBusy(false);
        showProgress(false);
        setBanner("Error: " + (job.error || "something went wrong"), "error");
      }
    } catch (e) {
      clearInterval(pollTimer);
      pollTimer = null;
      setBusy(false);
      setBanner(e.message, "error");
    }
  }, 1200);
}

function renderProgress(job) {
  const p = job.progress || { done: 0, total: 0, current: "" };
  const bar = document.getElementById("progress-bar");
  if (p.total > 0) {
    bar.classList.remove("indeterminate");
    bar.style.width = Math.round((p.done / p.total) * 100) + "%";
  } else {
    bar.classList.add("indeterminate");
    bar.style.width = "40%";
  }
  const status = document.getElementById("progress-status");
  if (p.total > 0) status.textContent = `${p.done} / ${p.total} — ${p.current || ""}`;
  else status.textContent = p.current || "Working…";
  const log = document.getElementById("log");
  log.textContent = (job.log || []).join("\n");
  log.scrollTop = log.scrollHeight;
}

/* ---------- results ---------- */

async function loadResults() {
  let data;
  try {
    data = await getJSON("/api/results");
  } catch (e) {
    return;
  }
  const card = document.getElementById("results-card");
  const hasAny = data.search || data.extracted || data.closed;
  card.classList.toggle("hidden", !hasAny);

  if (data.search) {
    document.getElementById("search-count").textContent = `(${data.search.rows.length})`;
    renderTable("search-table", data.search.header, data.search.rows);
  }
  if (data.extracted) {
    document.getElementById("extracted-count").textContent = `(${data.extracted.rows.length})`;
    renderTable("extracted-table", data.extracted.header, data.extracted.rows);
  }
}

function renderTable(containerId, header, rows) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  const table = document.createElement("table");

  const thead = document.createElement("thead");
  const hr = document.createElement("tr");
  header.forEach(h => {
    const th = document.createElement("th");
    th.textContent = h;
    hr.appendChild(th);
  });
  thead.appendChild(hr);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  const cap = 300;
  rows.slice(0, cap).forEach(r => {
    const tr = document.createElement("tr");
    header.forEach((h, i) => {
      const td = document.createElement("td");
      let v = r[i];
      if (v === null || v === undefined) v = "";
      v = String(v);
      if (h === "is_open_access") {
        td.className = v === "yes" ? "oa-yes" : "oa-no";
        v = v === "yes" ? "open" : (v === "no" ? "closed" : "");
      }
      td.textContent = v;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  container.appendChild(table);

  if (rows.length > cap) {
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = `Showing first ${cap} of ${rows.length} rows — download the Excel for everything.`;
    container.appendChild(note);
  }
}

function downloadFile(name) {
  window.location.href = "/download/" + name;
}

async function openOutputFolder() {
  try {
    await postJSON("/open-output", {});
  } catch (e) {
    setBanner(e.message, "error");
  }
}

/* ---------- numeric-only inputs ---------- */
function bindNumericInputs() {
  document.querySelectorAll("input[data-numeric]").forEach(el => {
    el.addEventListener("input", () => {
      const digits = el.value.replace(/\D/g, "");
      if (el.value !== digits) el.value = digits;
    });
    el.addEventListener("keydown", (e) => {
      if (e.key.length === 1 && !/[0-9]/.test(e.key) && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
      }
    });
  });
}

/* ---------- init ---------- */

document.getElementById("add-term").onclick = () => addTerm();

window.addEventListener("DOMContentLoaded", async () => {
  bindNumericInputs();
  addTerm();
  addTerm();
  try {
    await Promise.all([loadSources(), loadSettings()]);
  } catch (e) { /* non-fatal */ }
  await loadResults();
  await checkStatus();
});

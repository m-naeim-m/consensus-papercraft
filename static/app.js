// Consensus PaperCraft Studio Application Logic

let currentScope = "full_paper";
let selectedPaperIds = new Set();
let libraryPapers = [];
let allKeys = [];
let isDemoMode = false;

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  fetchKeys();
  loadLibrary();
  refreshLogs();

  // Auto refresh logs every 3 seconds
  setInterval(() => {
    const chk = document.getElementById("auto-refresh-logs");
    if (chk && chk.checked) {
      refreshLogs(false);
    }
  }, 3000);

  // Live markdown render in editor
  const editor = document.getElementById("paper-editor");
  if (editor) {
    editor.addEventListener("input", () => {
      renderMarkdownPreview(editor.value);
      updateEditorWordCount(editor.value);
    });
  }
});

// Toast notification
function showToast(msg, isError = false) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.style.background = isError ? "var(--danger)" : "var(--secondary)";
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 3500);
}

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

  const targetTab = document.getElementById(`tab-${tabId}`);
  if (targetTab) {
    targetTab.classList.add("active");
  }

  // Find matching nav button
  const btns = Array.from(document.querySelectorAll(".tab-btn"));
  const match = btns.find(b => b.getAttribute("onclick").includes(tabId));
  if (match) match.classList.add("active");

  if (tabId === "keys") fetchKeys();
  if (tabId === "library") loadLibrary();
  if (tabId === "logs") refreshLogs(true);
}

// Theme Toggle
function toggleTheme() {
  const html = document.documentElement;
  if (html.getAttribute("data-theme") === "dark") {
    html.removeAttribute("data-theme");
  } else {
    html.setAttribute("data-theme", "dark");
  }
}

// Demo Mode Toggle
async function toggleDemoMode() {
  try {
    const res = await fetch("/api/settings/demo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ demo_mode: !isDemoMode })
    });
    const data = await res.json();
    isDemoMode = data.demo_mode;
    updateDemoModeUI();
    showToast(isDemoMode ? "حالت آزمایشی فعال شد." : "حالت اتصال زنده فعال شد.");
    fetchKeys();
  } catch (err) {
    showToast("خطا در تغییر حالت آزمایشی", true);
  }
}

function updateDemoModeUI() {
  const lbl = document.getElementById("demo-mode-status");
  const btn = document.getElementById("toggle-demo-btn");
  if (lbl) lbl.textContent = isDemoMode ? "فعال (شبیه‌ساز)" : "غیرفعال (زنده)";
  if (btn) {
    btn.style.background = isDemoMode ? "var(--warning-light)" : "";
    btn.style.borderColor = isDemoMode ? "var(--warning)" : "";
  }
}

// --- Keys Management ---

async function fetchKeys() {
  try {
    const res = await fetch("/api/keys");
    const data = await res.json();
    allKeys = data.keys || [];
    isDemoMode = data.demo_mode;
    updateDemoModeUI();

    // Update Nav Count
    const navCount = document.getElementById("nav-keys-count");
    if (navCount) navCount.textContent = allKeys.length;

    // Update Header Badge
    const badge = document.getElementById("pool-status-badge");
    if (badge) {
      if (allKeys.length === 0 || data.active_keys === 0) {
        badge.className = "badge badge-warning";
        badge.innerHTML = `⚠️ بدون کلید فعال (${data.total_keys} ثبت‌شده)`;
      } else {
        badge.className = "badge badge-success";
        badge.innerHTML = `🟢 ${data.active_keys} کلید فعال | بالانسر راند رابین (${data.total_requests_served} درخواست)`;
      }
    }

    renderKeysTable(allKeys);
  } catch (err) {
    console.error("Error fetching keys:", err);
  }
}

function renderKeysTable(keys) {
  const tbody = document.getElementById("keys-table-body");
  if (!tbody) return;

  if (keys.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:24px;">هیچ کلیدی ثبت نشده است. از فرم‌های بالا برای افزودن کلیدهای Consensus استفاده کنید.</td></tr>`;
    return;
  }

  tbody.innerHTML = keys.map((k, idx) => {
    let statusBadge = "";
    if (k.status === "active") {
      statusBadge = `<span class="badge badge-success">فعال</span>`;
    } else if (k.status === "rate_limited") {
      statusBadge = `<span class="badge badge-warning">ریت لیمیت (درنگ ۶۰ ثانیه)</span>`;
    } else if (k.status === "quota_exhausted") {
      statusBadge = `<span class="badge badge-danger">سهمیه پایان‌یافته (۴۰۳)</span>`;
    } else if (k.status === "invalid") {
      statusBadge = `<span class="badge badge-danger">کلید نامعتبر (۴۰۱)</span>`;
    } else {
      statusBadge = `<span class="badge badge-secondary">غیرفعال</span>`;
    }

    const lastUsed = k.last_used || "هنوز استفاده نشده";
    const lastError = k.last_error ? `<span style="color:var(--danger); font-size:11.5px;">${k.last_error}</span>` : `<span style="color:var(--accent); font-size:11.5px;">بدون خطا</span>`;

    return `
      <tr>
        <td><strong>${k.name}</strong></td>
        <td><code>${k.masked_key || "(خالی)"}</code></td>
        <td>${statusBadge}</td>
        <td><strong>${k.requests_count}</strong> بار</td>
        <td style="font-size:12px; color:var(--text-muted);">${lastUsed}</td>
        <td>${lastError}</td>
        <td>
          <div style="display:flex; gap:6px;">
            <button class="btn btn-secondary btn-sm" onclick="toggleKeyStatus('${k.id}', '${k.status}')" title="فعال/غیرفعال">
              ${k.status === "active" ? "⏸️" : "▶️"}
            </button>
            <button class="btn btn-secondary btn-sm" onclick="testExistingKey('${k.id}')" title="تست اتصال">
              🩺
            </button>
            <button class="btn btn-danger btn-sm" onclick="deleteKey('${k.id}')" title="حذف">
              🗑️
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

async function submitSingleKey() {
  const nameInput = document.getElementById("new-key-name");
  const keyInput = document.getElementById("new-key-token");
  const name = nameInput.value.trim();
  const key = keyInput.value.trim();

  if (!key) {
    showToast("لطفاً کلید API را وارد کنید.", true);
    return;
  }

  try {
    const res = await fetch("/api/keys", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name || undefined, key })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(`کلید با موفقیت افزوده شد.`);
      nameInput.value = "";
      keyInput.value = "";
      document.getElementById("key-test-feedback").innerHTML = "";
      fetchKeys();
    } else {
      showToast(data.detail || "خطا در افزودن کلید", true);
    }
  } catch (err) {
    showToast("خطای سرور", true);
  }
}

async function submitBulkKeys() {
  const textarea = document.getElementById("bulk-keys-input");
  const text = textarea.value.trim();
  if (!text) {
    showToast("متن کلیدها خالی است.", true);
    return;
  }

  try {
    const res = await fetch("/api/keys/bulk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keys_text: text })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(`${data.added_count} کلید جدید با موفقیت اضافه شد.`);
      textarea.value = "";
      fetchKeys();
    } else {
      showToast("خطا در افزودن دسته‌ای کلیدها", true);
    }
  } catch (err) {
    showToast("خطای سرور", true);
  }
}

async function testSingleKeyInput() {
  const keyInput = document.getElementById("new-key-token");
  const key = keyInput.value.trim();
  const fb = document.getElementById("key-test-feedback");

  if (!key) {
    fb.innerHTML = `<span style="color:var(--danger)">لطفاً ابتدا کلید را در کادر وارد نمایید.</span>`;
    return;
  }

  fb.innerHTML = `<span style="color:var(--text-muted)">در حال برقراری ارتباط با Consensus API...</span>`;

  try {
    const res = await fetch("/api/keys/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key })
    });
    const data = await res.json();
    if (data.valid) {
      fb.innerHTML = `<span style="color:var(--accent); font-weight:bold;">✅ ${data.message}</span>`;
    } else {
      fb.innerHTML = `<span style="color:var(--danger); font-weight:bold;">❌ ${data.message}</span>`;
    }
  } catch (err) {
    fb.innerHTML = `<span style="color:var(--danger)">خطای اتصال به شبکه یا فیلترینگ</span>`;
  }
}

async function testExistingKey(keyId) {
  const k = allKeys.find(item => item.id === keyId);
  if (!k || !k.key) {
    showToast("کلید موجود نیست یا مقدار آن خالی است.", true);
    return;
  }
  showToast(`در حال تست سلامت کلید [${k.name}]...`);
  try {
    const res = await fetch("/api/keys/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: k.key })
    });
    const data = await res.json();
    if (data.valid) {
      showToast(`✅ [${k.name}]: اتصال موفق`);
    } else {
      showToast(`❌ [${k.name}]: ${data.message}`, true);
    }
    fetchKeys();
  } catch (err) {
    showToast("خطای اتصال", true);
  }
}

async function toggleKeyStatus(keyId, currentStatus) {
  const newStatus = currentStatus === "active" ? "disabled" : "active";
  try {
    await fetch(`/api/keys/${keyId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    fetchKeys();
  } catch (err) {
    showToast("خطا در تغییر وضعیت", true);
  }
}

async function deleteKey(keyId) {
  if (!confirm("آیا از حذف این کلید مطمئن هستید؟")) return;
  try {
    await fetch(`/api/keys/${keyId}`, { method: "DELETE" });
    showToast("کلید حذف شد.");
    fetchKeys();
  } catch (err) {
    showToast("خطا در حذف کلید", true);
  }
}

async function resetAllKeys() {
  try {
    await fetch("/api/keys/reset", { method: "POST" });
    showToast("تمام کلیدها به حالت فعال بازنشانی شدند.");
    fetchKeys();
  } catch (err) {
    showToast("خطا در ریست", true);
  }
}

// --- Consensus Literature Search ---

function quickSearch(query) {
  const input = document.getElementById("search-query-input");
  input.value = query;
  executeSearch();
}

async function executeSearch() {
  const queryInput = document.getElementById("search-query-input");
  const query = queryInput.value.trim();
  if (!query) {
    showToast("لطفاً عبارت جستجو را وارد کنید.", true);
    return;
  }

  const yearMin = document.getElementById("filter-year-min").value;
  const yearMax = document.getElementById("filter-year-max").value;
  const pageSize = document.getElementById("filter-page-size").value;

  const btn = document.getElementById("search-btn");
  const badge = document.getElementById("search-dispatch-badge");
  const container = document.getElementById("search-results-container");

  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span> در حال کاوش...`;
  badge.className = "badge badge-primary";
  badge.textContent = "در حال ارسال درخواست به بالانسر...";
  container.innerHTML = `<div style="text-align:center; padding:50px; color:var(--text-muted);"><span class="spinner" style="border-top-color:var(--primary); width:32px; height:32px;"></span><p style="margin-top:12px;">در حال جستجو در Consensus و توزیع بار بین کلیدها...</p></div>`;

  try {
    const payload = {
      query,
      year_min: yearMin ? parseInt(yearMin) : undefined,
      year_max: yearMax ? parseInt(yearMax) : undefined,
      page_size: pageSize ? parseInt(pageSize) : 10
    };

    const res = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "خطا در دریافت نتایج");
    }

    // Success
    badge.className = "badge badge-success";
    badge.innerHTML = `✅ انجام شد توسط: <strong>${data.key_used}</strong> (${data.execution_time_ms} ms) ${data.failovers_count > 0 ? `| ${data.failovers_count} سوییچ خودکار` : ''}`;

    renderSearchResults(data.results);
    fetchKeys(); // update counts
  } catch (err) {
    badge.className = "badge badge-danger";
    badge.textContent = `خطا: ${err.message}`;
    container.innerHTML = `
      <div class="card" style="border-color:var(--danger); text-align:center; padding:30px;">
        <div style="font-size:32px; margin-bottom:10px;">⚠️</div>
        <h3 style="color:var(--danger); margin-bottom:10px;">خطا در دریافت مقالات</h3>
        <p style="color:var(--text-muted); font-size:14px; max-width:600px; margin:0 auto 16px auto;">${err.message}</p>
        <p style="font-size:13px; color:var(--text-muted);">
          می‌توانید کلیدهای API خود را در تب «مدیریت استخر کلیدها» بررسی کنید، یا دکمه <strong>«حالت آزمایشی»</strong> در بالای صفحه را فعال نمایید تا بدون نیاز به کلید، جریان کار و نگارش مقاله را بررسی نمایید.
        </p>
      </div>
    `;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `جستجو در مقالات`;
  }
}

function renderSearchResults(results) {
  const container = document.getElementById("search-results-container");
  if (!results || results.length === 0) {
    container.innerHTML = `<div class="card" style="text-align:center; padding:40px; color:var(--text-muted);">مقاله‌ای مطابق با جستجوی شما یافت نشد. عبارت دیگری را امتحان کنید.</div>`;
    return;
  }

  container.innerHTML = results.map((p, idx) => {
    const isSaved = libraryPapers.some(lp => lp.doi === p.doi || lp.title === p.title);
    const authorsStr = (p.authors && p.authors.length) ? p.authors.slice(0, 3).join(", ") + (p.authors.length > 3 ? " et al." : "") : "نویسندگان نامشخص";
    const yearStr = p.publish_year || "n.d.";
    const journalStr = p.journal_name || "نشریه علمی معتبر";
    const studyTypeBadge = p.study_type ? `<span class="badge badge-primary">${p.study_type}</span>` : "";
    const sjrBadge = p.sjr_best_quartile ? `<span class="badge badge-success">Q${p.sjr_best_quartile}</span>` : "";
    const sampleBadge = p.sample_size ? `<span class="badge badge-secondary">نمونه N=${p.sample_size}</span>` : "";

    const takeawayHtml = p.takeaway ? `
      <div class="takeaway-box">
        <strong>💡 خلاصه هوش مصنوعی Consensus:</strong> ${p.takeaway}
      </div>
    ` : "";

    const jsonStr = encodeURIComponent(JSON.stringify(p));

    return `
      <div class="paper-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
          <h3 class="paper-title">${p.title}</h3>
          <div style="display:flex; gap:6px; flex-shrink:0;">
            ${sjrBadge}
            ${studyTypeBadge}
            ${sampleBadge}
          </div>
        </div>

        <div class="paper-meta">
          <span>👥 ${authorsStr}</span>
          <span>📅 ${yearStr}</span>
          <span>📖 ${journalStr}</span>
          <span>⭐ ${p.citation_count || 0} استناد</span>
          ${p.doi ? `<span>🔗 DOI: ${p.doi}</span>` : ""}
        </div>

        ${takeawayHtml}

        <p class="paper-abstract">
          ${p.abstract ? p.abstract.slice(0, 320) + (p.abstract.length > 320 ? "..." : "") : "چکیده‌ای برای این مقاله در دسترس نیست."}
        </p>

        <div class="paper-actions">
          <div>
            ${p.url ? `<a href="${p.url}" target="_blank" class="btn btn-secondary btn-sm">مشاهده در Consensus ↗</a>` : ""}
            ${p.doi ? `<a href="https://doi.org/${p.doi}" target="_blank" class="btn btn-secondary btn-sm">لینک DOI ↗</a>` : ""}
          </div>

          <button id="save-btn-${idx}" class="btn ${isSaved ? 'btn-secondary' : 'btn-primary'} btn-sm" onclick="savePaperFromSearch('${jsonStr}', ${idx})">
            ${isSaved ? '✅ در کتابخانه موجود است' : '📌 افزودن به کتابخانه و ماتریس'}
          </button>
        </div>
      </div>
    `;
  }).join("");
}

async function savePaperFromSearch(encodedJson, btnIdx) {
  try {
    const paper = JSON.parse(decodeURIComponent(encodedJson));
    const res = await fetch("/api/library", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(paper)
    });
    if (res.ok) {
      showToast(`مقاله «${paper.title.slice(0, 35)}...» به کتابخانه اضافه شد.`);
      const btn = document.getElementById(`save-btn-${btnIdx}`);
      if (btn) {
        btn.className = "btn btn-secondary btn-sm";
        btn.textContent = "✅ در کتابخانه موجود است";
      }
      loadLibrary();
    }
  } catch (err) {
    showToast("خطا در ذخیره مقاله", true);
  }
}

// --- Library & Literature Matrix ---

async function loadLibrary() {
  try {
    const res = await fetch("/api/library");
    const data = await res.json();
    libraryPapers = data.papers || [];

    // Update Counts
    const navCount = document.getElementById("nav-library-count");
    if (navCount) navCount.textContent = libraryPapers.length;

    const statCount = document.getElementById("stat-saved-papers");
    if (statCount) statCount.textContent = libraryPapers.length;

    renderMatrixTable(libraryPapers);
    renderWriterPapersList(libraryPapers);
  } catch (err) {
    console.error("Error loading library:", err);
  }
}

function renderMatrixTable(papers) {
  const tbody = document.getElementById("matrix-table-body");
  if (!tbody) return;

  if (papers.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:var(--text-muted); padding:30px;">کتابخانه خالی است. از تب «کاوش مقالات کانسنسوس» مقالات دلخواه را جستجو و اضافه کنید.</td></tr>`;
    return;
  }

  tbody.innerHTML = papers.map((p, idx) => {
    const auth = (p.authors && p.authors[0]) ? p.authors[0].split(",")[0] + (p.authors.length > 1 ? " et al." : "") : "-";
    const takeaway = p.takeaway || (p.abstract ? p.abstract.slice(0, 100) + "..." : "-");

    return `
      <tr>
        <td><strong>${idx + 1}</strong></td>
        <td>${auth}</td>
        <td>${p.publish_year || "-"}</td>
        <td><strong>${p.title}</strong></td>
        <td>${p.journal_name || "-"}</td>
        <td>${p.study_type || "تجربی"}</td>
        <td>${p.sample_size || "-"}</td>
        <td style="font-size:12.5px; color:#166534;">${takeaway}</td>
        <td>${p.citation_count || 0}</td>
        <td>
          <button class="btn btn-danger btn-sm" onclick="removePaperFromLibrary('${p.id || p.doi}')" title="حذف">🗑️</button>
        </td>
      </tr>
    `;
  }).join("");
}

function renderWriterPapersList(papers) {
  const list = document.getElementById("writer-selected-papers-list");
  if (!list) return;

  if (papers.length === 0) {
    list.innerHTML = `
      <p style="color:var(--text-muted); font-size:13px; text-align:center; padding:30px;">
        هنوز مقاله‌ای در کتابخانه وجود ندارد. از تب «کاوش مقالات کانسنسوس» مقالات مورد نظر را جستجو و سنجاق کنید تا در نگارش متن به آن‌ها استناد شود.
      </p>
    `;
    return;
  }

  // Auto-select all by default if not set
  if (selectedPaperIds.size === 0) {
    papers.forEach(p => selectedPaperIds.add(p.id || p.doi));
  }

  list.innerHTML = papers.map((p, idx) => {
    const pid = p.id || p.doi;
    const isChecked = selectedPaperIds.has(pid);
    const auth = (p.authors && p.authors[0]) ? p.authors[0].split(",")[0] : "Author";
    const year = p.publish_year || "n.d.";

    return `
      <div style="display:flex; align-items:center; gap:10px; padding:8px 10px; border-bottom:1px solid var(--border); font-size:13px;">
        <input type="checkbox" id="chk-${pid}" ${isChecked ? 'checked' : ''} onchange="toggleWriterPaperSelection('${pid}', this.checked)">
        <label for="chk-${pid}" style="flex:1; cursor:pointer;">
          <strong>[${idx + 1}] (${auth}, ${year})</strong>: ${p.title}
        </label>
      </div>
    `;
  }).join("");
}

function toggleWriterPaperSelection(pid, checked) {
  if (checked) {
    selectedPaperIds.add(pid);
  } else {
    selectedPaperIds.delete(pid);
  }
}

async function removePaperFromLibrary(pid) {
  try {
    await fetch(`/api/library/${pid}`, { method: "DELETE" });
    showToast("مقاله از کتابخانه حذف شد.");
    selectedPaperIds.delete(pid);
    loadLibrary();
  } catch (err) {
    showToast("خطا در حذف", true);
  }
}

async function clearLibrary() {
  if (!confirm("آیا از پاکسازی تمام مقالات کتابخانه اطمینان دارید؟")) return;
  for (const p of libraryPapers) {
    await fetch(`/api/library/${p.id || p.doi}`, { method: "DELETE" });
  }
  selectedPaperIds.clear();
  loadLibrary();
  showToast("کتابخانه پاکسازی شد.");
}

// EndNote Exports
async function exportEndNoteEnw() {
  if (libraryPapers.length === 0) {
    showToast("کتابخانه خالی است.", true);
    return;
  }
  window.open("/api/export/enw", "_blank");
}

async function exportEndNoteRis() {
  if (libraryPapers.length === 0) {
    showToast("کتابخانه خالی است.", true);
    return;
  }
  window.open("/api/export/ris", "_blank");
}

// --- Paper Writer Studio ---

function selectScope(btn) {
  document.querySelectorAll(".scope-btn").forEach(b => b.classList.remove("active", "btn-primary"));
  document.querySelectorAll(".scope-btn").forEach(b => b.classList.add("btn-secondary"));
  btn.classList.remove("btn-secondary");
  btn.classList.add("active", "btn-primary");
  currentScope = btn.getAttribute("data-scope");
}

function loadSampleTopic() {
  document.getElementById("paper-topic").value = "ارزیابی و اولویت‌بندی عملکرد نظام‌های ثبت بالینی با تصمیم‌گیری چندمعیاره";
  showToast("موضوع نمونه بارگذاری شد.");
}

async function generatePaperSection() {
  const topicInput = document.getElementById("paper-topic");
  const topic = topicInput.value.trim();
  if (!topic) {
    showToast("لطفاً موضوع یا عنوان مقاله را وارد کنید.", true);
    topicInput.focus();
    return;
  }

  const lang = document.getElementById("paper-language").value;
  const citationStyle = document.getElementById("paper-citation-style").value;
  const btn = document.getElementById("generate-paper-btn");
  const editor = document.getElementById("paper-editor");

  // Pick selected papers from library
  const chosenPapers = libraryPapers.filter(p => selectedPaperIds.has(p.id || p.doi));

  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span> در حال سنتز شواهد و نگارش بخش...`;

  try {
    const payload = {
      topic,
      section_type: currentScope,
      language: lang,
      citation_style: citationStyle,
      paper_ids: Array.from(selectedPaperIds),
      custom_papers: chosenPapers
    };

    const res = await fetch("/api/generate-section", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "خطا در نگارش بخش");

    editor.value = data.content;
    renderMarkdownPreview(data.content);
    updateEditorWordCount(data.content);
    showToast(`بخش با استناد به ${data.papers_used_count} مقاله با موفقیت نگارش شد.`);

    // update section count stat
    const secCount = document.getElementById("stat-sections-count");
    if (secCount) secCount.textContent = parseInt(secCount.textContent || "0") + 1;
  } catch (err) {
    showToast(`خطا: ${err.message}`, true);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>🚀</span> تولید و سنتز بخش مقاله با استناد به شواهد`;
  }
}

function updateEditorWordCount(text) {
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const statWords = document.getElementById("stat-words-count");
  if (statWords) statWords.textContent = words.toLocaleString();
}

// Basic client-side Markdown preview renderer
function renderMarkdownPreview(markdown) {
  const preview = document.getElementById("paper-preview");
  if (!preview) return;

  if (!markdown.trim()) {
    preview.innerHTML = `<p style="color:var(--text-muted); text-align:center; margin-top:100px;">متنی برای نمایش وجود ندارد.</p>`;
    return;
  }

  let html = markdown
    // Escape HTML
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    // Headers
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    // Bold & Italic
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    // Blockquote
    .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
    // Horizontal rule
    .replace(/^---$/gim, '<hr style="border:none; border-top:1px solid var(--border); margin:20px 0;">')
    // Paragraphs
    .replace(/\n\n+/g, '</p><p>');

  preview.innerHTML = `<p>${html}</p>`;
}

async function exportWordDocx() {
  const editor = document.getElementById("paper-editor");
  const topic = document.getElementById("paper-topic").value.trim() || "مقاله علمی";
  const lang = document.getElementById("paper-language").value;
  const content = editor.value.trim();

  if (!content) {
    showToast("متن مقاله خالی است. لطفاً ابتدا بخشی را نگارش کنید.", true);
    return;
  }

  showToast("در حال تولید فایل Word استاندارد (.docx)...");

  try {
    const res = await fetch("/api/export/docx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: topic,
        content: content,
        language: lang
      })
    });

    if (!res.ok) throw new Error("خطا در ایجاد فایل Word");

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${topic.slice(0, 30).replace(/\s+/g, '_')}.docx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    showToast("دانلود فایل Word آغاز شد.");
  } catch (err) {
    showToast(err.message, true);
  }
}

function exportMarkdownFile() {
  const editor = document.getElementById("paper-editor");
  const topic = document.getElementById("paper-topic").value.trim() || "paper";
  const content = editor.value.trim();

  if (!content) {
    showToast("متن مقاله خالی است.", true);
    return;
  }

  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${topic.slice(0, 30).replace(/\s+/g, '_')}.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  showToast("فایل Markdown دانلود شد.");
}

function copyEditorContent() {
  const editor = document.getElementById("paper-editor");
  if (!editor.value.trim()) {
    showToast("متنی برای کپی وجود ندارد.", true);
    return;
  }
  navigator.clipboard.writeText(editor.value).then(() => {
    showToast("متن در کلیپ‌بورد کپی شد.");
  });
}

// --- Logs & Failover Monitoring ---

async function refreshLogs(notify = false) {
  try {
    const res = await fetch("/api/logs");
    const data = await res.json();
    renderLogs(data.logs || []);
    if (notify) showToast("لاگ‌ها به‌روزرسانی شدند.");
  } catch (err) {
    console.error("Error fetching logs:", err);
  }
}

function renderLogs(logs) {
  const container = document.getElementById("logs-container");
  if (!container) return;

  if (logs.length === 0) {
    container.innerHTML = `<div style="text-align:center; padding:24px; color:var(--text-muted); font-size:13px;">هنوز رویدادی ثبت نشده است.</div>`;
    return;
  }

  container.innerHTML = logs.map(l => {
    let icon = "ℹ️";
    let color = "var(--text-main)";

    if (l.event_type === "success") {
      icon = "🟢";
      color = "#166534";
    } else if (l.event_type === "failover") {
      icon = "⚠️";
      color = "var(--warning)";
    } else if (l.event_type === "error") {
      icon = "❌";
      color = "var(--danger)";
    } else if (l.event_type === "warning") {
      icon = "🟡";
      color = "var(--warning)";
    }

    return `
      <div class="log-item">
        <span class="log-time">${l.timestamp}</span>
        <span>${icon}</span>
        <span class="log-msg" style="color:${color};">
          ${l.message}
        </span>
        <span class="badge badge-secondary" style="font-size:11px;">${l.key_name}</span>
      </div>
    `;
  }).join("");
}

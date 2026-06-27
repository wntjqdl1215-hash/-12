const $ = (sel) => document.querySelector(sel);
const results = $("#results");
const input = $("#symbols");
const briefingEl = $("#briefing");
const updatedEl = $("#updated");

const STORAGE_KEY = "watchlist";
const DEFAULT_LIST = "삼성전자, SK하이닉스";
let timer = null;

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ----- 관심 종목 저장/복원 -----
function saveWatchlist(v) {
  try { localStorage.setItem(STORAGE_KEY, v); } catch (_) {}
}
function loadWatchlist() {
  try { return localStorage.getItem(STORAGE_KEY) || DEFAULT_LIST; } catch (_) { return DEFAULT_LIST; }
}

async function load() {
  const symbols = input.value.trim();
  if (!symbols) return;
  saveWatchlist(symbols);
  results.innerHTML = `<div class="loading">뉴스를 모으는 중… ⏳</div>`;
  briefingEl.hidden = true;

  try {
    const res = await fetch(`/api/news?symbols=${encodeURIComponent(symbols)}&limit=5`);
    const data = await res.json();
    renderBriefing(data);
    render(data);
    stamp(data.generated_at);
  } catch (e) {
    results.innerHTML = `<div class="error">불러오기 실패: ${esc(e.message)}</div>`;
  }
}

function stamp(ts) {
  const d = ts ? new Date(ts * 1000) : new Date();
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  updatedEl.textContent = `업데이트 ${hh}:${mm}`;
}

// ----- 아침 브리핑: 종목별 가장 최근 핵심 한 줄 -----
function renderBriefing(data) {
  const stocks = (data.stocks || []).filter((s) => !s.error && (s.items || []).length);
  if (!stocks.length) { briefingEl.hidden = true; return; }

  const rows = stocks.map((s) => {
    const top = s.items[0];
    return `<li class="brief-row" data-target="stock-${esc(s.code)}">
      <span class="brief-name">${esc(s.name)}</span>
      <span class="brief-headline">${esc(top.title)}</span>
    </li>`;
  }).join("");

  briefingEl.innerHTML = `
    <h2>☀️ 오늘의 브리핑 <span class="brief-sub">내 종목 핵심만</span></h2>
    <ul class="brief-list">${rows}</ul>`;
  briefingEl.hidden = false;

  briefingEl.querySelectorAll(".brief-row").forEach((el) => {
    el.addEventListener("click", () => {
      const t = document.getElementById(el.dataset.target);
      if (t) t.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function render(data) {
  const stocks = data.stocks || [];
  if (!stocks.length) {
    results.innerHTML = `<div class="empty">결과가 없습니다.</div>`;
    return;
  }

  results.innerHTML = stocks.map((s) => {
    if (s.error) {
      return `<section class="stock-block">
        <div class="stock-head"><span class="name">${esc(s.input)}</span></div>
        <div class="error">${esc(s.error)}</div>
      </section>`;
    }
    const cards = (s.items || []).map(cardHTML).join("") ||
      `<div class="empty">관련 뉴스가 없습니다.</div>`;
    return `<section class="stock-block" id="stock-${esc(s.code)}">
      <div class="stock-head">
        <span class="name">${esc(s.name)}</span>
        <span class="code">${esc(s.code || "")}</span>
      </div>
      <div class="grid">${cards}</div>
    </section>`;
  }).join("");

  results.querySelectorAll(".term").forEach((el) => {
    el.addEventListener("click", () => el.classList.toggle("open"));
  });
}

function cardHTML(it) {
  const terms = (it.terms || []).map((t) =>
    `<span class="term">${esc(t.term)}<span class="tip">${esc(t.explain)}</span></span>`
  ).join("");

  const engineBadge = it.engine === "claude" ? "AI 쉬운 요약" : "쉬운 요약";

  return `<article class="card">
    <div class="meta"><span>${esc(it.source)}</span><span>${esc(it.date)}</span></div>
    <h3 class="title">${esc(it.title)}</h3>
    <div class="summary"><span class="badge">${engineBadge}</span>${esc(it.summary)}</div>
    ${terms ? `<div class="terms">${terms}</div>` : ""}
    <div class="actions">
      <a class="btn-open" href="${esc(it.url)}" target="_blank" rel="noopener">본문 보기</a>
    </div>
  </article>`;
}

// ----- 자동 새로고침 -----
function setupAutoRefresh() {
  const box = $("#autoRefresh");
  const apply = () => {
    if (timer) { clearInterval(timer); timer = null; }
    if (box.checked) timer = setInterval(load, 5 * 60 * 1000);
  };
  box.addEventListener("change", apply);
  apply();
}

// ----- 이벤트 -----
$("#loadBtn").addEventListener("click", load);
input.addEventListener("keydown", (e) => { if (e.key === "Enter") load(); });
document.querySelectorAll(".quick").forEach((el) => {
  el.addEventListener("click", () => {
    const v = el.dataset.v;
    const cur = input.value.split(",").map((x) => x.trim()).filter(Boolean);
    if (!cur.includes(v)) cur.push(v);
    input.value = cur.join(", ");
    load();
  });
});

// 첫 진입: 저장된 관심 종목 복원 후 로드
input.value = loadWatchlist();
setupAutoRefresh();
load();

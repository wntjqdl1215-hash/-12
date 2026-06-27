const $ = (sel) => document.querySelector(sel);
const results = $("#results");
const input = $("#symbols");
const briefingEl = $("#briefing");
const updatedEl = $("#updated");
const watchlistEl = $("#watchlist");

const STORAGE_KEY = "watchlist";
const DEFAULT_LIST = ["삼성전자", "SK하이닉스"];
let watchlist = [];
let timer = null;

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ----- 관심 종목 저장/복원 (배열) -----
function saveWatchlist() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(watchlist)); } catch (_) {}
}
function loadWatchlist() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [...DEFAULT_LIST];
    if (raw.startsWith("[")) return JSON.parse(raw);
    return raw.split(",").map((x) => x.trim()).filter(Boolean); // 구버전 호환
  } catch (_) { return [...DEFAULT_LIST]; }
}

function addSymbols(text) {
  text.split(",").map((x) => x.trim()).filter(Boolean).forEach((v) => {
    if (!watchlist.includes(v)) watchlist.push(v);
  });
  saveWatchlist();
  renderChips();
}
function removeSymbol(v) {
  watchlist = watchlist.filter((x) => x !== v);
  saveWatchlist();
  renderChips();
  load();
}

// 관심 종목 칩 (삭제 가능)
function renderChips() {
  watchlistEl.innerHTML = watchlist.map((v) =>
    `<span class="wchip">${esc(v)}<button class="x" data-v="${esc(v)}">×</button></span>`
  ).join("") || `<span class="label">관심 종목을 추가하세요</span>`;
  watchlistEl.querySelectorAll(".x").forEach((b) =>
    b.addEventListener("click", () => removeSymbol(b.dataset.v)));
}

async function load() {
  if (!watchlist.length) { results.innerHTML = `<div class="empty">관심 종목을 추가하세요.</div>`; briefingEl.hidden = true; return; }
  const symbols = watchlist.join(",");
  results.innerHTML = `<div class="loading">뉴스를 모으는 중… ⏳</div>`;
  briefingEl.hidden = true;

  try {
    const res = await fetch(`/api/news?symbols=${encodeURIComponent(symbols)}&limit=5`);
    const data = await res.json();
    renderBriefing(data);
    render(data);
    stamp(data.generated_at);
    notifyNew(data);
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

const TONE_LABEL = { positive: "🟢 긍정", negative: "🔴 부정", neutral: "⚪ 중립" };

// ----- 아침 브리핑 -----
function renderBriefing(data) {
  const stocks = (data.stocks || []).filter((s) => !s.error && (s.items || []).length);
  if (!stocks.length) { briefingEl.hidden = true; return; }

  const rows = stocks.map((s) => {
    const top = s.items[0];
    const tone = (top.tone && TONE_LABEL[top.tone.tone]) || "";
    const newCnt = s.items.filter((i) => i.is_new).length;
    return `<li class="brief-row" data-target="stock-${esc(s.code)}">
      <span class="brief-name">${esc(s.name)}</span>
      <span class="brief-headline">${esc(top.title)}</span>
      <span class="brief-meta">${tone}${newCnt ? ` · NEW ${newCnt}` : ""}</span>
    </li>`;
  }).join("");

  briefingEl.innerHTML = `
    <h2>☀️ 오늘의 브리핑 <span class="brief-sub">내 종목 핵심만 · 톤은 참고용</span></h2>
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
  if (!stocks.length) { results.innerHTML = `<div class="empty">결과가 없습니다.</div>`; return; }

  results.innerHTML = stocks.map((s) => {
    if (s.error) {
      return `<section class="stock-block">
        <div class="stock-head"><span class="name">${esc(s.input)}</span></div>
        <div class="error">${esc(s.error)}</div></section>`;
    }
    const cards = (s.items || []).map(cardHTML).join("") ||
      `<div class="empty">관련 뉴스가 없습니다.</div>`;
    return `<section class="stock-block" id="stock-${esc(s.code)}">
      <div class="stock-head">
        <span class="name">${esc(s.name)}</span>
        <span class="code">${esc(s.code || "")}</span>
      </div>
      <div class="grid">${cards}</div></section>`;
  }).join("");

  results.querySelectorAll(".term").forEach((el) =>
    el.addEventListener("click", () => el.classList.toggle("open")));
}

function cardHTML(it) {
  const terms = (it.terms || []).map((t) =>
    `<span class="term">${esc(t.term)}<span class="tip">${esc(t.explain)}</span></span>`
  ).join("");

  const engineBadge = it.engine === "claude" ? "AI 쉬운 요약" : "쉬운 요약";
  const tone = it.tone ? it.tone.tone : "neutral";
  const toneBadge = `<span class="tone ${tone}">${TONE_LABEL[tone] || ""}</span>`;
  const srcType = it.source_type ? `<span class="srctype st-${esc(it.source_type)}">${esc(it.source_type)}</span>` : "";
  const newBadge = it.is_new ? `<span class="new">NEW</span>` : "";

  return `<article class="card">
    <div class="meta">
      ${srcType}<span>${esc(it.source)}</span><span>${esc(it.date)}</span>${newBadge}
    </div>
    <h3 class="title">${esc(it.title)}</h3>
    <div class="summary"><span class="badge">${engineBadge}</span>${esc(it.summary)}</div>
    <div class="cardtags">${toneBadge}${terms}</div>
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
$("#loadBtn").addEventListener("click", () => { addSymbols(input.value); input.value = ""; load(); });
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { addSymbols(input.value); input.value = ""; load(); }
});
document.querySelectorAll(".quick").forEach((el) =>
  el.addEventListener("click", () => { addSymbols(el.dataset.v); load(); }));

// ----- 알림 (NEW 뉴스) -----
const notifyBtn = $("#notifyBtn");
function setupNotifications() {
  if (!("Notification" in window)) return;
  const refresh = () => {
    if (Notification.permission === "default") {
      notifyBtn.hidden = false;
      notifyBtn.textContent = "🔔 알림 켜기";
    } else if (Notification.permission === "granted") {
      notifyBtn.hidden = false;
      notifyBtn.textContent = "🔔 알림 켜짐";
      notifyBtn.disabled = true;
    } else {
      notifyBtn.hidden = true; // 거부됨
    }
  };
  notifyBtn.addEventListener("click", async () => {
    await Notification.requestPermission();
    refresh();
  });
  refresh();
}

function notifyNew(data) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  const news = [];
  (data.stocks || []).forEach((s) => {
    (s.items || []).forEach((i) => { if (i.is_new) news.push(`${s.name}: ${i.title}`); });
  });
  if (!news.length) return;
  const body = news.slice(0, 3).join("\n") + (news.length > 3 ? `\n외 ${news.length - 3}건` : "");
  try {
    new Notification(`📈 새 뉴스 ${news.length}건`, { body, icon: "/icons/icon-192.png", tag: "stock-news" });
  } catch (_) {}
}

// ----- 서비스워커 등록 (PWA) -----
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}

// 첫 진입
watchlist = loadWatchlist();
renderChips();
setupAutoRefresh();
setupNotifications();
load();

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
    `<span class="wchip">${esc(v)}<button class="x" data-v="${esc(v)}" aria-label="${esc(v)} 삭제" title="삭제">×</button></span>`
  ).join("") || `<span class="label">관심 종목을 추가하세요</span>`;
  watchlistEl.querySelectorAll(".x").forEach((b) =>
    b.addEventListener("click", () => removeSymbol(b.dataset.v)));
}

async function load(preserveScroll = false) {
  if (!watchlist.length) { results.innerHTML = `<div class="empty">관심 종목을 추가하세요.</div>`; briefingEl.hidden = true; return; }
  const symbols = watchlist.join(",");
  const y = window.scrollY;
  if (!preserveScroll) {  // 자동 새로고침일 땐 깜빡임/스크롤 튕김 없이 조용히 교체
    results.innerHTML = `<div class="loading">뉴스를 모으는 중… ⏳</div>`;
    briefingEl.hidden = true;
  }

  try {
    const res = await fetch(`/api/news?symbols=${encodeURIComponent(symbols)}&limit=5`);
    const data = await res.json();
    renderBriefing(data);
    render(data);
    stamp(data.generated_at);
    notifyNew(data);
    if (preserveScroll) window.scrollTo(0, y);  // 읽던 위치 유지
  } catch (e) {
    if (!preserveScroll) results.innerHTML = `<div class="error">불러오기 실패: ${esc(e.message)}</div>`;
  }
}

function stamp(ts) {
  const d = ts ? new Date(ts * 1000) : new Date();
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  updatedEl.textContent = `업데이트 ${hh}:${mm}`;
}

const TONE_LABEL = { positive: "🟢 긍정", negative: "🔴 부정", neutral: "⚪ 중립" };

// 'YYYY.MM.DD HH:MM' 또는 'YYYY.MM.DD' -> '3시간 전' 같은 상대시간
function relativeTime(dateStr) {
  if (!dateStr) return "";
  const m = dateStr.match(/(\d{4})\.(\d{2})\.(\d{2})(?:\s+(\d{2}):(\d{2}))?/);
  if (!m) return dateStr;
  const d = new Date(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0));
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 0) return dateStr;
  if (diff < 60) return "방금 전";
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}일 전`;
  return dateStr.slice(0, 10);
}

function tallyHTML(t) {
  if (!t) return "";
  const parts = [];
  if (t.positive) parts.push(`🟢${t.positive}`);
  if (t.negative) parts.push(`🔴${t.negative}`);
  if (t.neutral) parts.push(`⚪${t.neutral}`);
  return parts.join(" ");
}

// ----- 아침 브리핑 -----
function renderBriefing(data) {
  const stocks = (data.stocks || []).filter((s) => !s.error && (s.items || []).length);
  if (!stocks.length) { briefingEl.hidden = true; return; }

  const rows = stocks.map((s) => {
    const top = s.items[0];
    const tally = tallyHTML(s.tone_tally);
    const discCnt = (s.disclosures || []).length;
    const headline = discCnt ? `📢 ${esc(s.disclosures[0].report_name)}` : esc(top.title);
    return `<li class="brief-row" data-target="stock-${esc(s.code)}">
      <span class="brief-name">${esc(s.name)}</span>
      <span class="brief-headline">${headline}</span>
      <span class="brief-meta">${discCnt ? `공시 ${discCnt} · ` : ""}${tally}</span>
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
        ${priceHTML(s.price)}
      </div>
      ${s.insight ? `<div class="insight">${esc(s.insight)}</div>` : ""}
      ${disclosuresHTML(s.disclosures)}
      <div class="news-label">📰 뉴스</div>
      <div class="grid">${cards}</div></section>`;
  }).join("");

  // 용어 클릭/키보드 -> 카드 하단에 설명 표시(화면 밖으로 안 잘림, 카드당 한 줄)
  const toggleTerm = (el) => {
    const card = el.closest(".card");
    const box = card.querySelector(".term-explain");
    const name = el.textContent;
    if (!box.hidden && box.dataset.term === name) {       // 같은 칩 다시 누르면 닫기
      box.hidden = true; box.dataset.term = "";
      el.classList.remove("active");
      return;
    }
    card.querySelectorAll(".term").forEach((t) => t.classList.remove("active"));
    el.classList.add("active");
    box.textContent = `${name} — ${el.dataset.explain}`;
    box.dataset.term = name;
    box.hidden = false;
  };
  results.querySelectorAll(".term").forEach((el) => {
    el.addEventListener("click", () => toggleTerm(el));
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleTerm(el); }
    });
  });
}

// 📢 공시 섹션 (이 앱의 차별화 핵심)
function disclosuresHTML(discs) {
  if (!discs || !discs.length) return "";
  const rows = discs.map((d) => {
    const tagClass = d.tag || "neutral";
    const isNew = d.is_new ? `<span class="new">NEW</span>` : "";
    return `<div class="disc-row">
      <div class="disc-top">
        <span class="disc-tag ${tagClass}">${esc(d.label)}</span>
        <span class="disc-name">${esc(d.report_name)}</span>
        ${isNew}
      </div>
      <div class="disc-explain">💬 ${esc(d.explain)}</div>
      <div class="disc-foot">
        <span>${esc(d.date)} · ${esc(d.flr_nm)}</span>
        <a href="${esc(d.url)}" target="_blank" rel="noopener">DART 원문 ↗</a>
      </div>
    </div>`;
  }).join("");
  return `<div class="disc-box">
    <div class="disc-head">📢 공시 <span class="disc-sub">어려운 공시를 쉽게 풀어드려요 · 출처 DART</span></div>
    ${rows}
  </div>`;
}

function priceHTML(p) {
  if (!p) return "";
  const arrow = p.direction === "up" ? "▲" : p.direction === "down" ? "▼" : "−";
  const sign = p.change > 0 ? "+" : "";
  return `<span class="price ${p.direction}">
    <b>${Number(p.price).toLocaleString()}</b>
    <span class="chg">${arrow} ${sign}${Number(p.change).toLocaleString()} (${sign}${p.rate}%)</span>
  </span>`;
}

function cardHTML(it) {
  const terms = (it.terms || []).map((t) =>
    `<span class="term" role="button" tabindex="0" aria-label="${esc(t.term)} 뜻 보기" data-explain="${esc(t.explain)}">${esc(t.term)}</span>`
  ).join("");

  // 진짜 '쉬운' 부분은 💡한줄정리. 아래는 본문 핵심이므로 라벨을 구분한다.
  const engineBadge = it.engine === "claude" ? "AI 요약"
    : it.engine === "rule-en" ? "해외 요지" : "본문 요약";
  const tone = it.tone ? it.tone.tone : "neutral";
  const toneBadge = `<span class="tone ${tone}">${TONE_LABEL[tone] || ""}</span>`;
  const srcType = it.source_type ? `<span class="srctype st-${esc(it.source_type)}">${esc(it.source_type)}</span>` : "";
  const newBadge = it.is_new ? `<span class="new">NEW</span>` : "";

  return `<article class="card">
    <div class="meta">
      ${srcType}<span>${esc(it.source)}</span><span title="${esc(it.date)}">${esc(relativeTime(it.date))}</span>${newBadge}
    </div>
    <h3 class="title">${esc(it.title)}</h3>
    ${it.takeaway ? `<div class="takeaway">💡 ${esc(it.takeaway)}</div>` : ""}
    <div class="summary"><span class="badge">${engineBadge}</span>${esc(it.summary)}</div>
    <div class="cardtags">${toneBadge}${terms}</div>
    <div class="term-explain" hidden></div>
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
  const disc = [];
  const news = [];
  (data.stocks || []).forEach((s) => {
    (s.disclosures || []).forEach((d) => { if (d.is_new) disc.push(`${s.name} 공시: ${d.report_name}`); });
    (s.items || []).forEach((i) => { if (i.is_new) news.push(`${s.name}: ${i.title}`); });
  });
  // 공시 알림을 우선(차별화 핵심), 없으면 뉴스 알림
  const list = disc.length ? disc : news;
  if (!list.length) return;
  const title = disc.length ? `📢 새 공시 ${disc.length}건` : `📈 새 뉴스 ${news.length}건`;
  const body = list.slice(0, 3).join("\n") + (list.length > 3 ? `\n외 ${list.length - 3}건` : "");
  try {
    new Notification(title, { body, icon: "/icons/icon-192.png", tag: "stock-news" });
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

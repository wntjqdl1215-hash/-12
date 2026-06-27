const $ = (sel) => document.querySelector(sel);
const results = $("#results");
const input = $("#symbols");

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function load() {
  const symbols = input.value.trim();
  if (!symbols) return;
  results.innerHTML = `<div class="loading">뉴스를 모으는 중… ⏳</div>`;

  try {
    const res = await fetch(`/api/news?symbols=${encodeURIComponent(symbols)}&limit=5`);
    const data = await res.json();
    render(data);
  } catch (e) {
    results.innerHTML = `<div class="error">불러오기 실패: ${esc(e.message)}</div>`;
  }
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
    return `<section class="stock-block">
      <div class="stock-head">
        <span class="name">${esc(s.name)}</span>
        <span class="code">${esc(s.code || "")}</span>
      </div>
      <div class="grid">${cards}</div>
    </section>`;
  }).join("");

  // 용어 칩 탭/클릭 시 설명 토글 (모바일 대응)
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

// 첫 진입 시 자동 로드
load();

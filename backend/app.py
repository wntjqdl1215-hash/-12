"""주식 뉴스 한눈에 - 백엔드.

API:
  GET /api/news?symbols=삼성전자,000660   -> 관심 종목 뉴스 + 요약 + 톤 + NEW 표시
정적 프론트엔드(frontend/)도 같은 서버에서 서빙한다.

기능:
 - 다중 소스 수집(sources.py) + 초보자 요약/용어/톤(summarizer.py)
 - 결과 TTL 캐시(기본 5분)
 - 새 기사 NEW 표시(서버가 종목별로 이미 본 URL을 기억)
 - 서버사이드 자동 수집 스케줄러(요청된 종목을 주기적으로 미리 갱신)
"""
from __future__ import annotations

import os
import threading
import time

from flask import Flask, jsonify, request, send_from_directory

from crawler import fetch_news
from disclosures import fetch_disclosures
from prices import fetch_price
from stocks import normalize
from summarizer import summarize

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))           # 캐시 유효시간(초)
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", "300"))  # 자동 수집 주기(초)
MAX_SEEN = 500       # 종목별 기억하는 URL 최대 개수(메모리 상한)
MAX_TRACKED = 200    # 자동 수집 대상 최대 개수

app = Flask(__name__, static_folder=None)

_cache: dict[str, tuple[float, dict]] = {}     # key -> (ts, result)
_seen_urls: dict[str, dict] = {}               # code -> 이미 본 기사 URL(삽입순서 dict)
_seen_disc: dict[str, dict] = {}               # code -> 이미 본 공시 식별자
_tracked: set[str] = set()                     # 자동 수집 대상(요청된 symbol:limit 키)
_lock = threading.Lock()


def _build_symbol_news(symbol: str, limit: int) -> dict:
    code, name = normalize(symbol)
    result = {"input": symbol, "code": code, "name": name, "price": None,
              "items": [], "error": None}
    if not code:
        result["error"] = "종목코드를 찾지 못했습니다. 이름 또는 6자리 코드를 확인하세요."
        return result

    result["price"] = fetch_price(code)

    # 📢 공시(차별화 핵심): 저작권 안전한 DART 공공데이터 + 초보자 통역
    discs = fetch_disclosures(code, name, limit=5)
    with _lock:
        first_d = code not in _seen_disc
        dseen = _seen_disc.setdefault(code, {})
        d_new = {f"{d.url}|{d.report_name}" for d in discs
                 if f"{d.url}|{d.report_name}" not in dseen}
        for d in discs:
            dseen[f"{d.url}|{d.report_name}"] = None
        if len(dseen) > MAX_SEEN:
            _seen_disc[code] = dict(list(dseen.items())[-MAX_SEEN:])
    result["disclosures"] = [
        {**d.to_dict(), "is_new": (not first_d) and (f"{d.url}|{d.report_name}" in d_new)}
        for d in discs
    ]

    # 저작권 안전: 기사 본문을 긁지 않는다(제목+링크만). 분석은 제목 기반.
    news = fetch_news(code, name, limit=limit, with_body=False)

    # NEW 판정 + seen 갱신은 락 안에서 (요청 스레드 + 스케줄러 스레드 경합 방지)
    # seen은 삽입순서를 보존하는 dict -> 메모리 상한 시 오래된 것부터 정확히 제거(FIFO)
    with _lock:
        first_time = code not in _seen_urls
        seen = _seen_urls.setdefault(code, {})
        new_urls = {n.url for n in news if n.url not in seen}
        for n in news:
            seen[n.url] = None
        if len(seen) > MAX_SEEN:
            _seen_urls[code] = dict(list(seen.items())[-MAX_SEEN:])

    for n in news:
        s = summarize(n.title)   # 제목만으로 분석(본문 재표시 안 함)
        result["items"].append({
            "title": n.title,
            "source": n.source,
            "source_type": n.source_type,
            "date": n.date,
            "url": n.url,
            "summary": s["summary"],
            "takeaway": s.get("takeaway"),
            "terms": s["terms"],
            "tone": s["tone"],
            "engine": s["engine"],
            "is_new": (not first_time) and (n.url in new_urls),
        })

    result["tone_tally"] = _tone_tally(result["items"])
    result["insight"] = _insight(result["price"], result["tone_tally"])
    return result


def _tone_tally(items: list[dict]) -> dict:
    tally = {"positive": 0, "negative": 0, "neutral": 0}
    for it in items:
        tally[it["tone"]["tone"]] += 1
    return tally


def _insight(price: dict | None, tally: dict) -> str | None:
    """시세 방향 + 뉴스 톤 우세를 묶어 '왜 움직였나' 한 줄(정보 제공)."""
    if tally["positive"] == 0 and tally["negative"] == 0:
        news = "neutral"
    elif tally["positive"] > tally["negative"]:
        news = "positive"
    elif tally["negative"] > tally["positive"]:
        news = "negative"
    else:
        news = "mixed"

    d = price["direction"] if price else None
    if d == "up" and news == "positive":
        return "📈 주가도 오르고 뉴스 분위기도 긍정적이에요."
    if d == "up" and news == "negative":
        return "📈 주가는 올랐지만 뉴스 분위기는 부정적이에요. 배경을 살펴보세요."
    if d == "down" and news == "negative":
        return "📉 주가도 내리고 뉴스 분위기도 부정적이에요."
    if d == "down" and news == "positive":
        return "📉 뉴스는 긍정적인데 주가는 내렸어요. 단기 수급일 수 있어요."
    if news == "positive":
        return "🟢 최근 뉴스 분위기는 대체로 긍정적이에요."
    if news == "negative":
        return "🔴 최근 뉴스 분위기는 대체로 부정적이에요."
    return "⚪ 뚜렷한 방향성은 약해요. 정보만 참고하세요."


def _get_symbol_news(symbol: str, limit: int) -> dict:
    now = time.time()
    key = f"{symbol}:{limit}"
    with _lock:
        if len(_tracked) < MAX_TRACKED:
            _tracked.add(key)
        cached = _cache.get(key)
        if cached and now - cached[0] < CACHE_TTL:
            return cached[1]

    result = _build_symbol_news(symbol, limit)
    with _lock:
        _cache[key] = (time.time(), result)
    return result


def _scheduler_loop():
    """백그라운드: 요청된 종목들을 주기적으로 미리 수집해 캐시를 따뜻하게 유지."""
    while True:
        time.sleep(REFRESH_INTERVAL)
        with _lock:
            keys = list(_tracked)
        for key in keys:
            try:
                symbol, limit = key.rsplit(":", 1)
                res = _build_symbol_news(symbol, int(limit))
                with _lock:
                    _cache[key] = (time.time(), res)
            except Exception:
                continue


@app.get("/api/news")
def api_news():
    symbols = request.args.get("symbols", "").strip()
    limit = min(int(request.args.get("limit", "5")), 10)
    if not symbols:
        return jsonify({"error": "symbols 파라미터가 필요합니다.", "stocks": []}), 400

    stocks = [_get_symbol_news(s, limit) for s in (x for x in symbols.split(",") if x.strip())]
    return jsonify({"stocks": stocks, "generated_at": int(time.time())})


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "tracked": len(_tracked)})


# ----- 정적 프론트엔드 -----
@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:path>")
def static_files(path: str):
    return send_from_directory(FRONTEND_DIR, path)


def _start_scheduler():
    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()


# gunicorn 등으로 임포트될 때도 스케줄러 시작
_start_scheduler()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"▶ 주식 뉴스 한눈에 실행: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)

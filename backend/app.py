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
_seen_urls: dict[str, set] = {}                # code -> 이미 본 기사 URL 집합
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
    news = fetch_news(code, name, limit=limit)

    # NEW 판정 + seen 갱신은 락 안에서 (요청 스레드 + 스케줄러 스레드 경합 방지)
    with _lock:
        first_time = code not in _seen_urls
        seen = _seen_urls.setdefault(code, set())
        new_urls = {n.url for n in news if n.url not in seen}
        seen.update(n.url for n in news)
        if len(seen) > MAX_SEEN:               # 오래된 것부터 잘라 메모리 상한 유지
            _seen_urls[code] = set(list(seen)[-MAX_SEEN:])

    for n in news:
        s = summarize(n.title, n.body)
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
    return result


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

"""주식 뉴스 한눈에 - MVP 백엔드.

API:
  GET /api/news?symbols=삼성전자,000660   -> 관심 종목들의 뉴스 + 초보자 요약
정적 프론트엔드(frontend/)도 같은 서버에서 서빙한다.

간단한 자동화: 결과를 메모리에 TTL 캐시(기본 5분)해서 새로고침 시 빠르게 응답.
"""
from __future__ import annotations

import os
import time

from flask import Flask, jsonify, request, send_from_directory

from crawler import fetch_news
from stocks import normalize
from summarizer import summarize

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 초

app = Flask(__name__, static_folder=None)
_cache: dict[str, tuple[float, dict]] = {}


def _get_symbol_news(symbol: str, limit: int) -> dict:
    now = time.time()
    key = f"{symbol}:{limit}"
    cached = _cache.get(key)
    if cached and now - cached[0] < CACHE_TTL:
        return cached[1]

    code, name = normalize(symbol)
    result = {"input": symbol, "code": code, "name": name, "items": [], "error": None}
    if not code:
        result["error"] = "종목코드를 찾지 못했습니다. 이름 또는 6자리 코드를 확인하세요."
        return result

    news = fetch_news(code, name, limit=limit)
    for n in news:
        s = summarize(n.title, n.body)
        result["items"].append(
            {
                "title": n.title,
                "source": n.source,
                "date": n.date,
                "url": n.url,            # '본문 보기'에서 새 탭으로 열림
                "summary": s["summary"],
                "terms": s["terms"],     # 초보자용 용어 설명
                "engine": s["engine"],
            }
        )
    _cache[key] = (now, result)
    return result


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
    return jsonify({"ok": True})


# ----- 정적 프론트엔드 -----
@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:path>")
def static_files(path: str):
    return send_from_directory(FRONTEND_DIR, path)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"▶ 주식 뉴스 한눈에 실행: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)

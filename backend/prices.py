"""종목 시세 한 줄(현재가·등락률) 수집.

네이버 polling API(키 불필요)를 사용한다. 차단/실패 시 샘플 시세로 폴백한다.
'주식앱'다운 최소한의 시세 정보를 카드 상단에 보여주기 위함.
"""
from __future__ import annotations

import requests

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"}

# 오프라인/차단 환경 샘플 시세 (데모용)
_SAMPLE = {
    "005930": {"price": 81500, "change": 1200, "rate": 1.49},
    "000660": {"price": 234000, "change": -3500, "rate": -1.47},
    "035720": {"price": 41250, "change": 350, "rate": 0.86},
    "035420": {"price": 187600, "change": -900, "rate": -0.48},
    "247540": {"price": 96400, "change": 2100, "rate": 2.23},
}


def fetch_price(code: str) -> dict | None:
    """{price, change, rate, direction} 반환. 실패 시 샘플 -> 그래도 없으면 None."""
    data = _fetch_online(code) or _SAMPLE.get(code)
    if not data:
        return None
    change = data["change"]
    direction = "up" if change > 0 else "down" if change < 0 else "flat"
    return {
        "price": data["price"],
        "change": change,
        "rate": data["rate"],
        "direction": direction,
    }


def _fetch_online(code: str) -> dict | None:
    try:
        url = f"https://polling.finance.naver.com/api/realtime/domestic/stock/{code}"
        r = requests.get(url, headers=HEADERS, timeout=5)
        j = r.json()
        d = j["datas"][0]
        price = int(str(d["closePrice"]).replace(",", ""))
        change = int(str(d["compareToPreviousClosePrice"]).replace(",", ""))
        rate = float(str(d["fluctuationsRatio"]).replace(",", ""))
        return {"price": price, "change": change, "rate": rate}
    except Exception:
        return None

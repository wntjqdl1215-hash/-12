"""한국 주식 종목코드 <-> 이름 매핑.

초보자는 '삼성전자'처럼 이름으로 검색하고 싶어하지만 네이버 금융은 종목코드(005930)를
사용한다. 자주 쓰는 종목은 내장 사전으로 처리하고, 그 외에는 네이버 자동완성 API로
코드를 찾는다(네트워크가 열린 환경에서만 동작).
"""
from __future__ import annotations

import json
import urllib.parse

import requests

# 초보자가 가장 많이 보는 종목 위주의 작은 내장 사전 (오프라인에서도 동작)
BUILTIN: dict[str, str] = {
    "삼성전자": "005930",
    "SK하이닉스": "000660",
    "LG에너지솔루션": "373220",
    "삼성바이오로직스": "207940",
    "현대차": "005380",
    "기아": "000270",
    "셀트리온": "068270",
    "NAVER": "035420",
    "네이버": "035420",
    "카카오": "035720",
    "POSCO홀딩스": "005490",
    "포스코홀딩스": "005490",
    "에코프로비엠": "247540",
    "에코프로": "086520",
    "LG화학": "051910",
    "삼성SDI": "006400",
    "현대모비스": "012330",
    "KB금융": "105560",
    "신한지주": "055550",
    "한미반도체": "042700",
    "두산에너빌리티": "034020",
}

# 코드 -> 이름 역방향
_CODE_TO_NAME = {v: k for k, v in BUILTIN.items()}


def normalize(query: str) -> tuple[str | None, str]:
    """입력(이름 또는 6자리 코드)을 (종목코드, 표시이름)으로 정규화.

    코드를 못 찾으면 (None, 원본)을 반환한다.
    """
    q = query.strip()
    if not q:
        return None, query

    # 이미 6자리 코드면 그대로
    if q.isdigit() and len(q) == 6:
        return q, _CODE_TO_NAME.get(q, q)

    # 내장 사전
    if q in BUILTIN:
        return BUILTIN[q], q

    # 네이버 자동완성으로 검색 (온라인일 때만)
    code = _lookup_naver(q)
    if code:
        return code, q
    return None, q


def _lookup_naver(name: str) -> str | None:
    """네이버 금융 자동완성 API로 종목코드 조회."""
    try:
        url = "https://ac.finance.naver.com/ac"
        params = {
            "q": name,
            "q_enc": "euc-kr",
            "st": "111",
            "frm": "stock",
            "r_format": "json",
            "r_enc": "euc-kr",
            "r_lt": "111",
            "t_koreng": "1",
            "h_lan": "ko",
        }
        r = requests.get(
            url,
            params=params,
            timeout=5,
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.naver.com/"},
        )
        r.encoding = "euc-kr"
        data = json.loads(r.text)
        items = data.get("items", [])
        if items and items[0]:
            # items[0] = [[code], [name], ...]
            return items[0][0][0]
    except Exception:
        return None
    return None

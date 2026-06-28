"""DART 전자공시 수집 (저작권 안전: 금융감독원 공공데이터 OpenAPI).

- DART_API_KEY 환경변수가 있으면 실제 공시를 가져온다(무료 발급: opendart.fss.or.kr).
- 6자리 종목코드 -> DART 8자리 corp_code 변환은 공식 corpCode.xml로 자동 해석(캐시).
- 키/네트워크가 없으면 샘플 공시로 폴백(데모).

각 공시는 disclosure_translator로 초보자 해설 + 호재/악재 태그를 붙인다.
원문은 DART 뷰어 링크로 연결한다(본문을 긁어 재배포하지 않음 → 안전).
"""
from __future__ import annotations

import io
import os
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass

import requests

from disclosure_translator import translate

_CORP_CACHE: dict[str, str] = {}   # 종목코드(6) -> corp_code(8)
_CORP_LOADED = False


@dataclass
class Disclosure:
    report_name: str   # 보고서명 (예: 단일판매ㆍ공급계약체결)
    date: str          # 접수일자 YYYY.MM.DD
    flr_nm: str        # 공시 제출인(보통 회사명)
    url: str           # DART 원문 뷰어 링크
    tag: str           # positive/negative/caution/neutral
    label: str         # 🟢 호재 등
    explain: str       # 초보자 해설

    def to_dict(self) -> dict:
        return asdict(self)


def fetch_disclosures(code: str, name: str, limit: int = 5) -> list[Disclosure]:
    try:
        items = _fetch_online(code, name, limit)
        if items:
            return items
    except Exception:
        pass
    return _sample(code, name, limit)


def _fetch_online(code: str, name: str, limit: int) -> list[Disclosure]:
    key = os.getenv("DART_API_KEY")
    if not key:
        return []
    corp = _corp_code(code, key)
    if not corp:
        return []
    r = requests.get(
        "https://opendart.fss.or.kr/api/list.json",
        params={"crtfc_key": key, "corp_code": corp, "page_count": limit, "last_reprt_at": "Y"},
        timeout=8,
    )
    data = r.json()
    out: list[Disclosure] = []
    for it in data.get("list", [])[:limit]:
        rcept = it.get("rcept_no", "")
        rn = it.get("report_nm", "")
        t = translate(rn)
        out.append(Disclosure(
            report_name=rn,
            date=_fmt(it.get("rcept_dt", "")),
            flr_nm=it.get("flr_nm", name),
            url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept}",
            tag=t["tag"], label=t["label"], explain=t["explain"],
        ))
    return out


def _corp_code(stock_code: str, key: str) -> str | None:
    global _CORP_LOADED
    if stock_code in _CORP_CACHE:
        return _CORP_CACHE[stock_code]
    if _CORP_LOADED:
        return None
    # 공식 corpCode.xml(zip) 1회 다운로드 → 종목코드:corp_code 캐시 구축
    try:
        r = requests.get(
            "https://opendart.fss.or.kr/api/corpCode.xml",
            params={"crtfc_key": key}, timeout=20,
        )
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        xml = zf.read(zf.namelist()[0])
        root = ET.fromstring(xml)
        for el in root.iter("list"):
            sc = (el.findtext("stock_code") or "").strip()
            cc = (el.findtext("corp_code") or "").strip()
            if sc and cc:
                _CORP_CACHE[sc] = cc
    except Exception:
        pass
    finally:
        _CORP_LOADED = True
    return _CORP_CACHE.get(stock_code)


def _fmt(s: str) -> str:
    s = (s or "").strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}.{s[4:6]}.{s[6:]}"
    return s


# ----------------------------------------------------------------- 샘플(데모)
_SAMPLES: dict[str, list[tuple[str, str]]] = {
    "005930": [
        ("단일판매ㆍ공급계약체결", "2026.06.27"),
        ("주요사항보고서(자기주식취득결정)", "2026.06.26"),
        ("현금ㆍ현물배당결정", "2026.06.25"),
    ],
    "000660": [
        ("신규시설투자등", "2026.06.27"),
        ("영업(잠정)실적(공정공시)", "2026.06.26"),
    ],
    "035720": [
        ("전환사채권발행결정", "2026.06.27"),
        ("최대주주변경", "2026.06.24"),
    ],
}
_GENERIC = [("주요사항보고서", "2026.06.27"), ("분기보고서", "2026.06.25")]


def _sample(code: str, name: str, limit: int) -> list[Disclosure]:
    raw = _SAMPLES.get(code, _GENERIC)
    out = []
    for rn, dt in raw[:limit]:
        t = translate(rn)
        out.append(Disclosure(
            report_name=rn, date=dt, flr_nm=name,
            url="https://dart.fss.or.kr/",
            tag=t["tag"], label=t["label"], explain=t["explain"],
        ))
    return out

"""여러 소스를 합쳐 종목 뉴스를 수집하는 진입점.

흐름: 모든 소스에서 수집 → 제목 기준 중복 제거 → 최신순 정렬 → 상위 N개 본문 수집.
어떤 소스가 실패하거나 네트워크가 막히면 자동으로 샘플 데이터로 폴백한다.
"""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from sample_data import sample_news
from sources import ALL_SOURCES, HEADERS, NewsItem


def fetch_news(code: str, stock_name: str, limit: int = 6, with_body: bool = True) -> list[NewsItem]:
    collected: list[NewsItem] = []
    per_source = max(3, limit)  # 중복 제거 후 limit를 채우기 위해 소스별로 넉넉히

    for source_fn in ALL_SOURCES:
        try:
            collected.extend(source_fn(code, stock_name, per_source))
        except Exception:
            continue  # 소스 하나 실패는 무시

    items = _dedupe(collected)
    items = _diversify(_sort_recent(items), limit)

    if not items:
        return sample_news(code, stock_name, limit)  # 전부 실패 → 샘플 폴백

    if with_body:
        for it in items:
            # 본문이 이미 있거나(블로그/구글RSS), 구글 리다이렉트 링크면 재수집 생략
            if it.body or "news.google.com" in it.url:
                continue
            it.body = _fetch_body(it.url)
    return items


def _norm_title(title: str) -> str:
    """교차 출처 중복 판정용 제목 정규화.

    구글뉴스 제목의 ' - 매체명' 접미사, 앞쪽 '[블로그]/[속보]' 대괄호,
    공백/문장부호를 제거해 같은 기사를 같은 키로 만든다.
    """
    t = title or ""
    t = re.sub(r"\s*[-–|]\s*[^\-–|]{1,20}$", "", t)   # 끝의 ' - 한국경제' 류 제거
    t = re.sub(r"^\s*\[[^\]]{1,10}\]\s*", "", t)       # 앞의 '[블로그]' 류 제거
    t = re.sub(r"[\s\.,'\"·…]+", "", t)                 # 공백·문장부호 제거
    return t[:30].lower()


def _dedupe(items: list[NewsItem]) -> list[NewsItem]:
    seen = set()
    out = []
    for it in items:
        key = _norm_title(it.title)
        if key and key not in seen:
            seen.add(key)
            out.append(it)
    return out


def _diversify(sorted_items: list[NewsItem], limit: int) -> list[NewsItem]:
    """소스 편중 방지: 출처별로 라운드로빈 선택해 다양성을 보장.

    각 출처 안에서는 최신순을 유지한다(입력이 이미 최신순 정렬).
    """
    buckets: dict[str, list[NewsItem]] = {}
    for it in sorted_items:
        buckets.setdefault(it.source_type, []).append(it)

    out: list[NewsItem] = []
    while len(out) < limit and any(buckets.values()):
        for st in list(buckets.keys()):
            if buckets[st]:
                out.append(buckets[st].pop(0))
                if len(out) >= limit:
                    break
    return out


def _sort_recent(items: list[NewsItem]) -> list[NewsItem]:
    # 'YYYY.MM.DD HH:MM' 또는 'YYYY.MM.DD' 형태를 비교용 숫자로
    def key(it: NewsItem):
        nums = re.findall(r"\d+", it.date or "")
        return tuple(int(n) for n in nums) if nums else (0,)
    return sorted(items, key=key, reverse=True)


def _fetch_body(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        r.encoding = r.apparent_encoding or "euc-kr"
        soup = BeautifulSoup(r.text, "lxml")
        node = (
            soup.select_one("#news_read")
            or soup.select_one("#dic_area")
            or soup.select_one(".articleCont")
            or soup.select_one("#newsct_article")
            or soup.select_one("article")
        )
        text = node.get_text(" ", strip=True) if node else soup.get_text(" ", strip=True)
        return re.sub(r"\s+", " ", text)[:2000]
    except Exception:
        return ""

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
    items = _sort_recent(items)[:limit]

    if not items:
        return sample_news(code, stock_name, limit)  # 전부 실패 → 샘플 폴백

    if with_body:
        for it in items:
            # 본문이 이미 있거나(블로그/구글RSS), 구글 리다이렉트 링크면 재수집 생략
            if it.body or "news.google.com" in it.url:
                continue
            it.body = _fetch_body(it.url)
    return items


def _dedupe(items: list[NewsItem]) -> list[NewsItem]:
    seen = set()
    out = []
    for it in items:
        key = re.sub(r"\s+", "", it.title)[:40]
        if key and key not in seen:
            seen.add(key)
            out.append(it)
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

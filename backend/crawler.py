"""네이버 금융에서 종목별 뉴스를 긁어오는 크롤러.

- 종목별 뉴스 목록: https://finance.naver.com/item/news_news.naver?code=005930
- 각 뉴스의 본문은 원문 링크로 연결(앱에서는 '본문 보기' 버튼)

네트워크가 차단된 환경(예: 일부 클라우드 샌드박스)에서는 자동으로 샘플 데이터로
폴백한다. 사용자 PC 등 인터넷이 열린 곳에서 돌리면 실제 뉴스가 나온다.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import asdict, dataclass

import requests
from bs4 import BeautifulSoup

from sample_data import sample_news

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://finance.naver.com/",
}


@dataclass
class NewsItem:
    title: str
    source: str          # 언론사
    date: str            # YYYY.MM.DD HH:MM
    url: str             # 원문(본문) 링크
    code: str            # 종목코드
    stock_name: str      # 종목 이름
    body: str = ""       # 본문(요약용, 수집 시 best-effort)

    def to_dict(self) -> dict:
        return asdict(self)


def fetch_news(code: str, stock_name: str, limit: int = 6, with_body: bool = True) -> list[NewsItem]:
    """종목코드로 뉴스 목록을 가져온다. 실패 시 샘플 데이터로 폴백."""
    try:
        items = _fetch_news_online(code, stock_name, limit)
        if not items:
            raise RuntimeError("no items parsed")
        if with_body:
            for it in items:
                it.body = _fetch_body(it.url)
        return items
    except Exception:
        # 오프라인/차단 환경 폴백
        return sample_news(code, stock_name, limit)


def _fetch_news_online(code: str, stock_name: str, limit: int) -> list[NewsItem]:
    url = "https://finance.naver.com/item/news_news.naver"
    params = {"code": code, "page": 1, "sm": "title_entity_id.basic", "clusterId": ""}
    r = requests.get(url, params=params, headers=HEADERS, timeout=8)
    r.encoding = "euc-kr"
    soup = BeautifulSoup(r.text, "lxml")

    items: list[NewsItem] = []
    for row in soup.select("table.type5 tr"):
        title_tag = row.select_one("td.title a")
        if not title_tag:
            continue
        info = row.select_one("td.info")
        date_tag = row.select_one("td.date")
        href = title_tag.get("href", "")
        full_url = href if href.startswith("http") else "https://finance.naver.com" + href
        items.append(
            NewsItem(
                title=title_tag.get_text(strip=True),
                source=info.get_text(strip=True) if info else "",
                date=date_tag.get_text(strip=True) if date_tag else "",
                url=full_url,
                code=code,
                stock_name=stock_name,
            )
        )
        if len(items) >= limit:
            break
    return items


def _fetch_body(url: str) -> str:
    """기사 본문 텍스트를 best-effort로 추출(요약 입력용)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        r.encoding = r.apparent_encoding or "euc-kr"
        soup = BeautifulSoup(r.text, "lxml")
        node = (
            soup.select_one("#news_read")
            or soup.select_one("#dic_area")
            or soup.select_one(".articleCont")
            or soup.select_one("#newsct_article")
        )
        text = node.get_text(" ", strip=True) if node else soup.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text[:2000]
    except Exception:
        return ""

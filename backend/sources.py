"""여러 출처에서 종목 뉴스를 수집하는 모듈.

차별화 포인트: 네이버 금융 하나만 보지 않고 여러 소스를 한 번에 모은다.
 - 네이버금융  : 종목별 증권 뉴스 (한국)
 - 구글뉴스    : RSS 기반, 국내+해외 기사 폭넓게 (키 불필요)
 - 블로그      : 네이버 검색 오픈API (키 있을 때만, 없으면 자동 생략)

각 소스는 실패해도 전체가 죽지 않도록 try/except로 격리한다.
네트워크가 막힌 환경에서는 호출부(crawler)가 샘플 데이터로 폴백한다.
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass

import requests
from bs4 import BeautifulSoup

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
    source: str          # 언론사/블로그명
    source_type: str     # 출처 종류: 네이버뉴스 / 구글뉴스 / 블로그
    date: str
    url: str             # 원문(본문) 링크
    code: str
    stock_name: str
    body: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- 네이버 금융 뉴스
def from_naver_finance(code: str, name: str, limit: int) -> list[NewsItem]:
    url = "https://finance.naver.com/item/news_news.naver"
    params = {"code": code, "page": 1, "sm": "title_entity_id.basic"}
    r = requests.get(url, params=params, headers=HEADERS, timeout=8)
    r.encoding = "euc-kr"
    soup = BeautifulSoup(r.text, "lxml")

    items: list[NewsItem] = []
    for row in soup.select("table.type5 tr"):
        a = row.select_one("td.title a")
        if not a:
            continue
        # '관련뉴스' 묶음(relation_lst) 안의 중복 행은 건너뛴다
        if row.find_parent(class_="relation_lst") or "relation_lst" in (row.get("class") or []):
            continue
        info = row.select_one("td.info")
        date = row.select_one("td.date")
        href = a.get("href", "")
        full = href if href.startswith("http") else "https://finance.naver.com" + href
        items.append(NewsItem(
            title=a.get_text(strip=True),
            source=info.get_text(strip=True) if info else "네이버",
            source_type="네이버뉴스",
            date=date.get_text(strip=True) if date else "",
            url=full, code=code, stock_name=name,
        ))
        if len(items) >= limit:
            break
    return items


# ---------------------------------------------------------------- 구글 뉴스 RSS
def from_google_news(code: str, name: str, limit: int) -> list[NewsItem]:
    # 키 없이 동작하는 RSS. 국내+해외 기사를 폭넓게 잡는다.
    q = requests.utils.quote(f"{name} 주가")
    url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
    r = requests.get(url, headers=HEADERS, timeout=8)
    root = ET.fromstring(r.content)

    items: list[NewsItem] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        src_el = item.find("source")
        src = src_el.text.strip() if src_el is not None and src_el.text else "구글뉴스"
        # 구글뉴스 링크는 리다이렉트라 본문 재수집이 어렵다 -> RSS description을 본문으로 사용
        desc = _strip_tags(item.findtext("description") or "")
        # description엔 같은 매체명/링크 텍스트가 섞이므로 제목을 보강 텍스트로
        body = desc if len(desc) > len(title) else title
        items.append(NewsItem(
            title=title, source=src, source_type="구글뉴스",
            date=_fmt_rss_date(pub), url=link, code=code, stock_name=name, body=body,
        ))
        if len(items) >= limit:
            break
    return items


# ---------------------------------------------------------------- 네이버 블로그 (오픈API, 키 있을 때만)
def from_naver_blog(code: str, name: str, limit: int) -> list[NewsItem]:
    cid = os.getenv("NAVER_CLIENT_ID")
    secret = os.getenv("NAVER_CLIENT_SECRET")
    if not (cid and secret):
        return []  # 키 없으면 조용히 생략
    url = "https://openapi.naver.com/v1/search/blog.json"
    r = requests.get(
        url,
        params={"query": f"{name} 주식", "display": limit, "sort": "date"},
        headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": secret},
        timeout=8,
    )
    data = r.json()
    items: list[NewsItem] = []
    for it in data.get("items", []):
        items.append(NewsItem(
            title=_strip_tags(it.get("title", "")),
            source=it.get("bloggername", "블로그"),
            source_type="블로그",
            date=_fmt_yyyymmdd(it.get("postdate", "")),
            url=it.get("link", ""),
            code=code, stock_name=name,
            body=_strip_tags(it.get("description", "")),
        ))
    return items


# 활성화된 소스 목록 (위→아래 순서로 수집)
ALL_SOURCES = [from_naver_finance, from_google_news, from_naver_blog]


def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").replace("&quot;", '"').replace("&amp;", "&").strip()


def _fmt_yyyymmdd(s: str) -> str:
    # '20260627' -> '2026.06.27'
    s = (s or "").strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}.{s[4:6]}.{s[6:]}"
    return s


def _fmt_rss_date(s: str) -> str:
    # 'Fri, 27 Jun 2026 08:00:00 GMT' -> 'YYYY.MM.DD'
    m = re.search(r"(\d{1,2})\s+(\w{3})\s+(\d{4})", s or "")
    months = {m: i for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
    if m:
        d, mon, y = m.group(1), months.get(m.group(2), 1), m.group(3)
        return f"{y}.{mon:02d}.{int(d):02d}"
    return s or ""

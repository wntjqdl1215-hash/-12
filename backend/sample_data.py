"""오프라인/차단 환경용 샘플 뉴스(다중 소스 시연 포함).

실제 크롤링이 안 되는 환경에서도 화면·요약·소스 라벨을 그대로 보여주기 위한 데이터.
인터넷이 열린 환경에서는 sources의 실제 수집기가 동작하므로 이 파일은 쓰이지 않는다.
"""
from __future__ import annotations

_SAMPLES: dict[str, list[dict]] = {
    "005930": [
        {
            "title": "삼성전자, 3분기 영업이익 시장 전망치 상회…반도체가 견인",
            "source": "한국경제", "source_type": "네이버뉴스",
            "date": "2026.06.27 08:12",
            "url": "https://finance.naver.com/item/news.naver?code=005930",
            "body": ("삼성전자가 3분기 잠정 실적을 발표했다. 영업이익은 시장 컨센서스를 웃돌며 "
                     "어닝 서프라이즈를 기록했다. 메모리 반도체 업황 회복과 HBM 수요 증가가 실적을 "
                     "견인했다. 외국인은 이날 순매수로 돌아섰다."),
        },
        {
            "title": "Samsung Electronics shares jump on strong memory demand",
            "source": "Reuters", "source_type": "구글뉴스",
            "date": "2026.06.27 07:40",
            "url": "https://news.google.com/",
            "body": ("Samsung Electronics shares rose as memory chip prices rebounded on AI "
                     "server demand. Analysts raised their target prices."),
        },
        {
            "title": "[블로그] 삼성전자 지금 들어가도 될까? 실적 발표 정리",
            "source": "투자하는직장인", "source_type": "블로그",
            "date": "2026.06.26 22:10",
            "url": "https://blog.naver.com/",
            "body": ("이번 실적은 컨센서스를 웃돌았다. 다만 단기 주가는 변동성이 큰 구간이라 "
                     "분할 접근이 안전하다는 의견. 목표주가 상향 리포트가 이어졌다."),
        },
    ],
    "000660": [
        {
            "title": "SK하이닉스, HBM 공급 확대로 분기 최대 매출 경신",
            "source": "연합뉴스", "source_type": "네이버뉴스",
            "date": "2026.06.27 08:40",
            "url": "https://finance.naver.com/item/news.naver?code=000660",
            "body": ("SK하이닉스가 분기 기준 사상 최대 매출을 기록했다. AI 서버용 HBM 수요가 "
                     "폭발적으로 늘면서 메모리 가격이 반등했다. 영업이익률도 크게 개선됐다."),
        },
        {
            "title": "SK Hynix lifts AI memory outlook as HBM orders surge",
            "source": "Bloomberg", "source_type": "구글뉴스",
            "date": "2026.06.26 18:05",
            "url": "https://news.google.com/",
            "body": ("SK Hynix raised its outlook on strong HBM orders. The stock hit a record high."),
        },
    ],
}

_GENERIC = [
    {
        "title": "{name}, 거래량 늘며 변동성 확대", "source": "샘플뉴스", "source_type": "네이버뉴스",
        "date": "2026.06.27 09:00", "url": "https://finance.naver.com/",
        "body": ("{name} 주가가 늘어난 거래량 속에 변동성을 키우고 있다. 증권가는 실적과 "
                 "수급을 함께 볼 것을 권했다."),
    },
    {
        "title": "{name} 관련 해외 매체 보도 잇따라", "source": "구글뉴스", "source_type": "구글뉴스",
        "date": "2026.06.26 20:00", "url": "https://news.google.com/",
        "body": "{name}에 대한 해외 매체의 관심이 이어지고 있다.",
    },
]


def sample_news(code: str, stock_name: str, limit: int):
    from sources import NewsItem

    raw = _SAMPLES.get(code)
    if not raw:
        raw = [
            {**g,
             "title": g["title"].format(name=stock_name),
             "body": g["body"].format(name=stock_name)}
            for g in _GENERIC
        ]
    items = []
    for r in raw[:limit]:
        items.append(NewsItem(
            title=r["title"], source=r["source"], source_type=r["source_type"],
            date=r["date"], url=r["url"], code=code, stock_name=stock_name, body=r["body"],
        ))
    return items

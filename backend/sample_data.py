"""오프라인/차단 환경용 샘플 뉴스.

실제 크롤링이 안 되는 환경에서도 앱 화면과 요약 기능을 그대로 시연하기 위한 데이터.
인터넷이 열린 환경에서는 crawler가 진짜 뉴스를 가져오므로 이 파일은 쓰이지 않는다.
"""
from __future__ import annotations

# 종목코드 -> 샘플 기사 목록
_SAMPLES: dict[str, list[dict]] = {
    "005930": [
        {
            "title": "삼성전자, 3분기 영업이익 시장 전망치 상회…반도체가 견인",
            "source": "한국경제",
            "date": "2026.06.27 08:12",
            "url": "https://finance.naver.com/item/news.naver?code=005930",
            "body": (
                "삼성전자가 3분기 잠정 실적을 발표했다. 영업이익은 시장 컨센서스를 웃돌며 "
                "어닝 서프라이즈를 기록했다. 메모리 반도체 업황 회복과 HBM(고대역폭메모리) "
                "수요 증가가 실적을 견인했다. 증권가에서는 4분기에도 반도체 부문의 이익 개선이 "
                "이어질 것으로 전망했다. 외국인은 이날 순매수로 돌아섰다."
            ),
        },
        {
            "title": "외국인·기관 동반 순매수에 삼성전자 강세",
            "source": "매일경제",
            "date": "2026.06.27 09:31",
            "url": "https://finance.naver.com/item/news.naver?code=005930",
            "body": (
                "삼성전자 주가가 외국인과 기관의 동반 순매수에 힘입어 상승세를 보이고 있다. "
                "공매도 잔고는 줄어드는 추세다. 증권가는 목표주가를 상향 조정했다."
            ),
        },
        {
            "title": "증권가 '삼성전자 목표주가 상향'…HBM 기대감 반영",
            "source": "서울경제",
            "date": "2026.06.26 17:05",
            "url": "https://finance.naver.com/item/news.naver?code=005930",
            "body": (
                "주요 증권사들이 삼성전자의 목표주가를 일제히 올렸다. HBM 공급 확대와 "
                "파운드리 가동률 상승이 근거다. 다만 일부는 단기 주가 변동성에 유의하라고 조언했다."
            ),
        },
    ],
    "000660": [
        {
            "title": "SK하이닉스, HBM 공급 확대로 분기 최대 매출 경신",
            "source": "연합뉴스",
            "date": "2026.06.27 08:40",
            "url": "https://finance.naver.com/item/news.naver?code=000660",
            "body": (
                "SK하이닉스가 분기 기준 사상 최대 매출을 기록했다. AI 서버용 HBM 수요가 "
                "폭발적으로 늘면서 메모리 가격이 반등했다. 영업이익률도 크게 개선됐다."
            ),
        },
        {
            "title": "AI 반도체 수요 지속…SK하이닉스 목표주가 줄상향",
            "source": "이데일리",
            "date": "2026.06.26 16:22",
            "url": "https://finance.naver.com/item/news.naver?code=000660",
            "body": (
                "AI 투자 확대가 이어지며 SK하이닉스에 대한 증권가의 눈높이가 높아지고 있다. "
                "PER(주가수익비율) 부담에도 실적 성장세가 이를 상쇄한다는 분석이다."
            ),
        },
    ],
}

_GENERIC = [
    {
        "title": "{name}, 거래량 늘며 변동성 확대",
        "source": "샘플뉴스",
        "date": "2026.06.27 09:00",
        "url": "https://finance.naver.com/",
        "body": (
            "{name} 주가가 늘어난 거래량 속에 변동성을 키우고 있다. 단기 투자자들의 "
            "관심이 집중되는 가운데 증권가는 실적과 수급을 함께 볼 것을 권했다."
        ),
    },
]


def sample_news(code: str, stock_name: str, limit: int):
    from crawler import NewsItem  # 지연 임포트로 순환 참조 방지

    raw = _SAMPLES.get(code)
    if not raw:
        raw = [
            {**g, "title": g["title"].format(name=stock_name), "body": g["body"].format(name=stock_name)}
            for g in _GENERIC
        ]
    items = []
    for r in raw[:limit]:
        items.append(
            NewsItem(
                title=r["title"],
                source=r["source"],
                date=r["date"],
                url=r["url"],
                code=code,
                stock_name=stock_name,
                body=r["body"],
            )
        )
    return items

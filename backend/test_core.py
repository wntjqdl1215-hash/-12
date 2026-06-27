"""핵심 로직 회귀 방지 테스트.

실행: cd backend && python -m pytest -q
네트워크 불필요(순수 로직만 검증).
"""
from crawler import _dedupe, _diversify, _norm_title, _sort_recent
from sources import NewsItem, _fmt_yyyymmdd
from stocks import normalize
from summarizer import classify_tone, summarize


def _item(title, st="네이버뉴스", date="2026.06.27 09:00", url=None):
    return NewsItem(title, "src", st, date, url or title, "005930", "삼성전자")


# ---------------------------------------------------------------- 톤
def test_tone_special_cases():
    assert classify_tone("공매도 잔고 감소에 주가 안정")["tone"] == "positive"
    assert classify_tone("영업이익 최대 낙폭 기록")["tone"] == "negative"
    assert classify_tone("어닝 서프라이즈에 강세")["tone"] == "positive"
    assert classify_tone("상장폐지 우려")["tone"] == "negative"
    assert classify_tone("특별한 이슈 없이 보합")["tone"] == "neutral"


def test_tone_mixed_is_neutral():
    # 호재/악재가 팽팽하면 중립 (이중집계 버그 회귀 방지)
    assert classify_tone("목표주가 하향에도 외국인 순매수")["tone"] == "neutral"


def test_tone_english_word_boundary():
    # 'gain'이 'bargain'에, 'miss'가 'dismissed'에 오탐되면 안 됨
    assert classify_tone("Hard bargain over chip prices")["tone"] == "neutral"
    assert classify_tone("Samsung shares jump to record high")["tone"] == "positive"
    assert classify_tone("Chip stocks tumble on weak demand")["tone"] == "negative"


# ---------------------------------------------------------------- 중복 제거
def test_norm_title_strips_suffix_and_prefix():
    a = _norm_title("삼성전자 영업이익 상회 - 한국경제")
    b = _norm_title("삼성전자 영업이익 상회")
    c = _norm_title("[블로그] 삼성전자 영업이익 상회")
    assert a == b == c


def test_dedupe_cross_source():
    items = [
        _item("삼성전자 영업이익 상회", "네이버뉴스", url="n1"),
        _item("삼성전자 영업이익 상회 - 한국경제", "구글뉴스", url="g1"),
    ]
    assert len(_dedupe(items)) == 1


# ---------------------------------------------------------------- 다양성
def test_diversify_mixes_sources():
    items = [
        _item("a", "네이버뉴스", url="n1"), _item("b", "네이버뉴스", url="n2"),
        _item("c", "네이버뉴스", url="n3"),
        _item("d", "구글뉴스", url="g1"), _item("e", "블로그", url="b1"),
    ]
    picked = _diversify(_sort_recent(items), 3)
    kinds = {it.source_type for it in picked}
    assert len(picked) == 3
    assert len(kinds) >= 2  # 한 소스가 독식하지 않음


# ---------------------------------------------------------------- 종목/날짜
def test_normalize_builtin():
    assert normalize("삼성전자")[0] == "005930"
    assert normalize("005930")[0] == "005930"
    assert normalize("없는회사임")[0] is None


def test_fmt_yyyymmdd():
    assert _fmt_yyyymmdd("20260627") == "2026.06.27"
    assert _fmt_yyyymmdd("2026.06.27") == "2026.06.27"


# ---------------------------------------------------------------- 요약
def test_summarize_has_fields():
    s = summarize("삼성전자 영업이익 컨센서스 상회", "영업이익이 컨센서스를 웃돌며 어닝 서프라이즈")
    assert s["tone"]["tone"] == "positive"
    assert s["takeaway"]
    assert any(t["term"] == "영업이익" for t in s["terms"])


def test_summarize_english_gives_korean_gist():
    s = summarize("Samsung jumps on memory demand",
                  "Samsung Electronics shares rose as memory chip prices rebounded.")
    assert s["engine"] == "rule-en"
    assert "해외 매체" in s["summary"]

"""초보자용 뉴스 요약기.

컨셉: "예측해서 사라고 하지 않는다. 어려운 뉴스를 쉽게 풀어줄 뿐."
 - '쉽게 말하면' 한 줄 정리(신호 기반) + 본문 핵심
 - 어려운 용어 풀이
 - 기사 톤(긍정/부정/중립) — 구문/특수표현/부정어까지 고려해 오분류 최소화
 - 영어 기사도 한국어 요지로 변환

요약 엔진:
 1) ANTHROPIC_API_KEY 있으면 Claude로 자연스러운 초보자 요약(+영어 번역)
 2) 없으면 규칙 기반으로도 '한 줄 정리'를 만들어 동작 (키 없이도 쓸만하게)
"""
from __future__ import annotations

import os
import re

# ----------------------------------------------------------------- 용어 사전
GLOSSARY: dict[str, str] = {
    "영업이익": "회사가 본업으로 벌어들인 이익. 클수록 장사를 잘했다는 뜻.",
    "어닝 서프라이즈": "실적이 시장 예상보다 훨씬 잘 나온 것. 보통 주가에 호재.",
    "어닝쇼크": "실적이 예상보다 크게 나쁘게 나온 것. 보통 주가에 악재.",
    "컨센서스": "증권가 전문가들의 평균 예상치.",
    "HBM": "AI 반도체에 쓰이는 고성능 메모리. 요즘 수요가 매우 큼.",
    "공매도": "주가가 떨어질 것에 베팅하는 거래. 잔고가 줄면 보통 긍정 신호로 해석.",
    "순매수": "사는 양이 파는 양보다 많은 것. 외국인·기관 순매수는 보통 긍정적.",
    "순매도": "파는 양이 사는 양보다 많은 것. 보통 부정적 신호.",
    "목표주가": "증권사가 제시하는 '이 정도까지 오를 것'이라는 예상 가격.",
    "상향": "전망이나 목표치를 더 높게 조정한 것. 긍정적.",
    "하향": "전망이나 목표치를 더 낮게 조정한 것. 부정적.",
    "PER": "주가가 이익의 몇 배인지 나타내는 지표. 높으면 비싸게 거래된다는 뜻.",
    "PBR": "주가가 회사 순자산의 몇 배인지 나타내는 지표.",
    "컨센": "컨센서스(전문가 평균 예상치)의 줄임말.",
    "파운드리": "다른 회사의 반도체를 대신 만들어주는 위탁생산 사업.",
    "수급": "사고파는 돈의 흐름(누가 얼마나 사고파는지).",
    "변동성": "주가가 위아래로 출렁이는 정도. 클수록 위험·기회 모두 큼.",
    "잠정 실적": "정식 발표 전 회사가 먼저 알려주는 대략적인 실적.",
}


def find_terms(text: str) -> list[dict]:
    found, seen = [], set()
    for term, explain in GLOSSARY.items():
        if term in text and term not in seen:
            found.append({"term": term, "explain": explain})
            seen.add(term)
    return found


# ----------------------------------------------------------------- 톤 분류
# 특수 표현(겉모습과 반대인 것들)이 최우선
_POS_SPECIAL = ["공매도 잔고 감소", "공매도 감소", "공매도 잔고 축소", "낙폭 축소", "낙폭 줄",
                "낙폭 만회", "우려 완화", "불확실성 해소", "적자 축소", "적자폭 축소", "감산 효과"]
_NEG_SPECIAL = ["최대 낙폭", "사상 최대 손실", "최대 하락", "급등 후 급락", "기대 이하"]

# 강한 구문 (±2). 단일어와 중복 차감되지 않도록 '상향/하향'은 여기에만 둔다.
_POS_PHRASE = ["어닝 서프라이즈", "어닝서프라이즈", "목표주가 상향", "목표가 상향", "사상 최대",
               "최대 실적", "최대 매출", "흑자 전환", "흑자전환", "신고가", "최고가", "순매수",
               "수주", "반등", "강세", "급등", "호재", "상향 조정", "자사주 매입", "배당 확대"]
_NEG_PHRASE = ["어닝 쇼크", "어닝쇼크", "목표주가 하향", "목표가 하향", "신저가", "적자 전환",
               "적자전환", "급락", "약세", "순매도", "악재", "부진", "철회", "하향 조정",
               "리콜", "감산", "손실 확대",
               # 강한 악재(법적/자본): 누락돼 중립으로 잡히던 것들
               "유상증자", "횡령", "배임", "분식", "분식회계", "상장폐지", "상폐", "거래정지",
               "감자", "압수수색", "검찰 수사", "소송", "리스크 확대", "감리"]

# 약한 단일어 (±1). 한국어는 부분일치, 영어는 단어경계로(부분일치 오탐 방지).
_POS_WORD = ["상승", "개선", "확대", "성장", "기대", "수혜", "최대"]
_NEG_WORD = ["하락", "감소", "축소", "우려", "리스크", "부담", "둔화", "낙폭"]
_POS_EN = ["jump", "rise", "surge", "gain", "beat", "rally", "soar", "record high"]
_NEG_EN = ["drop", "fall", "plunge", "loss", "miss", "decline", "cut", "slump", "tumble"]


def classify_tone(text: str) -> dict:
    t = text or ""
    low = t.lower()
    score = 0
    for p in _POS_SPECIAL:
        if p in t:
            score += 3
    for p in _NEG_SPECIAL:
        if p in t:
            score -= 3
    for p in _POS_PHRASE:
        if p in t:
            score += 2
    for p in _NEG_PHRASE:
        if p in t:
            score -= 2
    for w in _POS_WORD:
        if w in t:
            score += 1
    for w in _NEG_WORD:
        if w in t:
            score -= 1
    # 영어는 단어경계 매칭 (예: 'gain'이 'bargain'에 잘못 걸리지 않게)
    for w in _POS_EN:
        if re.search(rf"\b{re.escape(w)}\b", low):
            score += 1
    for w in _NEG_EN:
        if re.search(rf"\b{re.escape(w)}\b", low):
            score -= 1
    # 부정어 뒤집기: '상승 아니다/안 오르' 같은 패턴 약하게 보정
    if re.search(r"(상승|개선|호재).{0,4}(아니|없|못|아님)", t):
        score -= 2
    if score > 0:
        return {"tone": "positive", "label": "긍정", "score": score}
    if score < 0:
        return {"tone": "negative", "label": "부정", "score": score}
    return {"tone": "neutral", "label": "중립", "score": 0}


# ----------------------------------------------------------------- '쉽게 말하면' 한 줄
_TAKE_RULES = [
    (["어닝 서프라이즈", "전망치 상회", "컨센서스를 웃", "예상치 상회", "최대 실적", "최대 매출", "beat"],
     "실적이 시장 예상보다 잘 나왔다는 뉴스예요. 보통 좋은 신호로 봐요."),
    (["어닝쇼크", "어닝 쇼크", "전망치 하회", "예상치 하회", "실적 부진", "miss"],
     "실적이 예상보다 나빴다는 뉴스예요. 보통 안 좋은 신호로 봐요."),
    (["목표주가 상향", "목표가 상향", "목표주가를 올", "상향 조정"],
     "증권사가 '더 오를 수 있다'고 기대치를 올렸다는 뉴스예요."),
    (["목표주가 하향", "목표가 하향", "목표주가를 낮", "하향 조정"],
     "증권사가 기대치를 낮췄다는 뉴스예요."),
    (["순매수", "외국인.{0,6}매수", "기관.{0,6}매수"],
     "외국인·기관이 이 종목을 사들이고 있다는 뉴스예요."),
    (["공매도 잔고 감소", "공매도 감소"],
     "하락에 베팅하던 물량이 줄었다는 뜻이라, 보통 긍정적으로 봐요."),
    (["HBM", "AI 반도체", "메모리 수요"],
     "AI용 고성능 메모리(HBM) 수요 얘기예요. 요즘 반도체의 핵심 호재 키워드예요."),
    (["급등", "강세", "상승"],
     "주가가 오르고 있다는 뉴스예요."),
    (["급락", "약세", "하락"],
     "주가가 내리고 있다는 뉴스예요."),
    (["변동성"],
     "주가가 위아래로 크게 출렁이고 있다는 뉴스예요."),
]


def _easy_takeaway(text: str) -> str | None:
    for keys, msg in _TAKE_RULES:
        for k in keys:
            if re.search(k, text):
                return msg
    return None


# ----------------------------------------------------------------- 메인
def _is_english(text: str) -> bool:
    if not text:
        return False
    ascii_letters = len(re.findall(r"[A-Za-z]", text))
    hangul = len(re.findall(r"[가-힣]", text))
    return ascii_letters > 20 and ascii_letters > hangul * 2


def summarize(title: str, body: str) -> dict:
    text = (body or title or "").strip()
    combined = f"{title} {text}"
    terms = find_terms(combined)
    tone = classify_tone(combined)

    # 1) LLM (키 있을 때) — 영어면 번역까지
    llm = _summarize_llm(title, text)
    if llm:
        return {"summary": llm, "takeaway": _easy_takeaway(combined), "terms": terms,
                "tone": tone, "level": "easy", "engine": "claude"}

    # 2) 규칙 기반 폴백
    takeaway = _easy_takeaway(combined)
    if _is_english(text):
        gist = _english_gist(title, tone)
        return {"summary": gist, "takeaway": takeaway, "terms": terms,
                "tone": tone, "level": "easy", "engine": "rule-en"}

    summary = _summarize_extractive(text)
    return {"summary": summary, "takeaway": takeaway, "terms": terms,
            "tone": tone, "level": "easy", "engine": "rule"}


def _english_gist(title: str, tone: dict) -> str:
    """영어 기사를 한국어 요지 한 줄로(번역 대신 신호 기반)."""
    sig = []
    low = title.lower()
    if any(k in low for k in ["hbm", "memory", "chip", "semiconductor"]):
        sig.append("반도체·메모리")
    if any(k in low for k in ["ai", "server", "data center"]):
        sig.append("AI 수요")
    if any(k in low for k in ["target", "rating", "upgrade", "downgrade"]):
        sig.append("증권사 의견")
    if any(k in low for k in ["earnings", "profit", "revenue", "sales"]):
        sig.append("실적")
    topic = ", ".join(sig) if sig else "관련 이슈"
    tone_txt = {"positive": "긍정적", "negative": "부정적", "neutral": "중립적"}[tone["tone"]]
    return f"해외 매체 보도예요. 전반적으로 {tone_txt}인 톤이고 '{topic}'을 다룹니다. (원문 영어 — 본문 보기로 확인)"


def _summarize_extractive(text: str) -> str:
    if not text:
        return "본문이 짧아 제목을 참고하세요."
    sentences = re.split(r"(?<=[.!?다])\s+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    summary = " ".join(sentences[:2])
    return summary[:200] + ("…" if len(summary) > 200 else "")


def _summarize_llm(title: str, body: str) -> str | None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic

        client = anthropic.Anthropic()
        prompt = (
            "다음 주식 뉴스를 주식 초보자가 이해할 수 있게 한국어로 2줄 요약해줘. "
            "영어 기사면 한국어로 번역해서 요약해. 어려운 용어는 쉽게 풀고, "
            "사라/팔라는 투자 권유는 절대 하지 마. 사실만 중립적으로.\n\n"
            f"제목: {title}\n본문: {body[:1500]}"
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=220,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception:
        return None

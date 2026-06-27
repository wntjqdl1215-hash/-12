"""초보자용 뉴스 요약기.

핵심 컨셉: "예측해서 사라고 하지 않는다. 어려운 뉴스를 쉽게 풀어줄 뿐."
- 본문을 2~3줄로 요약
- 본문에 등장하는 어려운 주식 용어를 찾아 쉬운 설명을 붙여줌(초보자 도우미)

요약 방식:
1) ANTHROPIC_API_KEY가 있으면 Claude로 자연스러운 초보자 요약 생성
2) 없으면 규칙 기반(앞 문장 추출 + 용어 사전)으로 폴백 → 인터넷/키 없이도 동작
"""
from __future__ import annotations

import os
import re

# 초보자가 자주 막히는 주식 용어 사전
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
    """본문에서 어려운 용어를 찾아 설명과 함께 반환."""
    found = []
    seen = set()
    for term, explain in GLOSSARY.items():
        if term in text and term not in seen:
            found.append({"term": term, "explain": explain})
            seen.add(term)
    return found


# 뉴스 '톤' 분류용 키워드 (투자 권유가 아니라, 기사 분위기를 초보자에게 알려주는 용도)
_POS = ["상승", "강세", "급등", "호재", "최대", "경신", "개선", "상향", "순매수", "흑자",
        "서프라이즈", "확대", "성장", "반등", "신고가", "수주", "기대", "jump", "rise", "surge", "high"]
_NEG = ["하락", "약세", "급락", "악재", "쇼크", "부진", "하향", "순매도", "적자", "축소",
        "감소", "우려", "리스크", "신저가", "손실", "철회", "drop", "fall", "plunge", "loss"]


def classify_tone(text: str) -> dict:
    """기사 톤을 긍정/부정/중립으로 분류. {tone, label} 반환."""
    t = text or ""
    pos = sum(1 for w in _POS if w in t)
    neg = sum(1 for w in _NEG if w in t)
    if pos > neg:
        return {"tone": "positive", "label": "긍정"}
    if neg > pos:
        return {"tone": "negative", "label": "부정"}
    return {"tone": "neutral", "label": "중립"}


def summarize(title: str, body: str) -> dict:
    """{summary, terms, level} 반환."""
    text = (body or title or "").strip()
    combined = title + " " + text
    terms = find_terms(combined)
    tone = classify_tone(combined)

    llm = _summarize_llm(title, text)
    if llm:
        return {"summary": llm, "terms": terms, "tone": tone, "level": "easy", "engine": "claude"}

    return {"summary": _summarize_extractive(text), "terms": terms, "tone": tone,
            "level": "easy", "engine": "rule"}


def _summarize_extractive(text: str) -> str:
    """규칙 기반 폴백: 앞쪽 핵심 문장 2개를 뽑아 한 줄 요약처럼."""
    if not text:
        return "요약할 본문이 없습니다."
    sentences = re.split(r"(?<=[.!?다])\s+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    summary = " ".join(sentences[:2])
    return summary[:200] + ("…" if len(summary) > 200 else "")


def _summarize_llm(title: str, body: str) -> str | None:
    """Claude로 초보자 친화 요약. 키/SDK 없으면 None."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic

        client = anthropic.Anthropic()
        prompt = (
            "다음 주식 뉴스를 주식 초보자가 이해할 수 있게 2줄로 요약해줘. "
            "어려운 용어는 쉬운 말로 풀고, 사라/팔라는 투자 권유는 절대 하지 마. "
            "사실만 중립적으로.\n\n"
            f"제목: {title}\n본문: {body[:1500]}"
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception:
        return None

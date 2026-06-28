# 📢 공시 한눈에 (주식 정보 대시보드)

**핵심:** 어려운 **전자공시(DART)** 를 초보자도 알 수 있게 **쉽게 통역**해주고, 내 종목 공시가 뜨면 **알림**으로 알려줍니다. + 시세·뉴스도 한 화면에.

> **차별화:** "단일판매ㆍ공급계약체결" 같은 암호 같은 공시를 *"큰 납품 계약을 따냈다는 호재예요"* 로 풀어줍니다.
> 네이버·토스도 공시를 raw하게만 보여줄 뿐, **초보자용으로 통역해주는 곳은 없습니다.**
>
> **저작권 안전:** 공시는 금융감독원 **공공데이터(OpenDART)** 이고, 뉴스는 제목+링크만 쓰며 원문은 출처로 보냅니다.
> **예측해서 사라고 하지 않습니다.** 판단은 사용자가 직접.

---

## 핵심 기능

- **📢 공시 초보자 통역 (차별화 핵심)** — DART 공시를 호재/악재/주의/중립 태그 + 한 줄 쉬운 해설로. 원문은 DART 링크로.
- **공시·뉴스 알림** — 내 종목에 새 공시/뉴스가 뜨면 브라우저 알림(공시 우선)
- **관심 종목 관리** — 이름(삼성전자)/코드(005930)로 추가, 칩으로 개별 삭제, localStorage 저장(새로고침 유지)
- **다중 소스 뉴스** — 구글뉴스 RSS(국내·해외) + 네이버 금융 + 블로그(키 있을 때), 중복 제거·소스 다양성·최신순
- **초보자용 쉬운 요약** — 기사 본문을 2~3줄로 정리
- **뉴스 톤 표시** — 🟢긍정 / 🔴부정 / ⚪중립 (분위기 참고용, 투자 권유 아님)
- **어려운 용어 풀이** — 영업이익·HBM·공매도 등에 설명 칩(탭하면 뜻)
- **새 뉴스 NEW 배지** — 직전에 본 뒤 올라온 새 기사 표시
- **아침 브리핑** — 종목별 핵심 헤드라인 한 줄씩, 클릭 시 해당 섹션 이동
- **자동 새로고침** — 화면 5분 주기 + 서버 백그라운드 자동 수집
- **NEW 뉴스 알림** — 새 기사 감지 시 브라우저 알림(권한 허용 시)
- **PWA 설치** — 모바일에서 '홈 화면에 추가' → 앱처럼 실행, 오프라인 셸 캐시
- **본문 보기** — 원문은 버튼으로 새 탭에서 따로 열기
- **반응형** — 모바일 1열 / PC 2열

---

## 실행 방법

```bash
bash run.sh
# 또는
pip install -r requirements.txt
cd backend && python3 app.py
```

브라우저에서 **http://localhost:8000**. 같은 와이파이 휴대폰은 `http://<PC IP>:8000`.

### 선택 환경변수

| 변수 | 용도 |
|---|---|
| `DART_API_KEY` | **DART 실제 공시 수집** (무료 발급: opendart.fss.or.kr). 없으면 샘플 공시로 시연 |
| `ANTHROPIC_API_KEY` | 초보자 요약을 Claude로 더 자연스럽게 (없으면 규칙 기반) |
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | 네이버 블로그 소스 활성화 (없으면 자동 생략) |
| `CACHE_TTL` | 캐시 유효시간(초, 기본 300) |
| `REFRESH_INTERVAL` | 서버 자동 수집 주기(초, 기본 300) |

---

## 배포 (어디서나 휴대폰으로 접속)

### ⚡ 원클릭 배포 (Render, 무료·카드 불필요)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/wntjqdl1215-hash/-12)

위 버튼 → GitHub 로그인 → **Apply** 누르면 `render.yaml`을 읽어 자동 배포됩니다.
2~3분 후 발급되는 `https://...onrender.com` 주소를 휴대폰에서 열고 '홈 화면에 추가'.

### 다른 방법

```bash
# Docker
docker build -t stock-news . && docker run -p 8000:8000 stock-news

# Railway/Heroku 계열 — Procfile 자동 인식
```

> 배포 시작 명령(검증됨): `gunicorn --chdir backend app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4`

---

## 테스트

핵심 로직(톤 분류·중복제거·소스 다양성·종목 변환·요약)은 단위 테스트로 보호됩니다.

```bash
pip install -r requirements-dev.txt
cd backend && python -m pytest -q
```

## 구조

```
backend/
  app.py                   # Flask 서버: /api/news + 공시 + 캐시 + NEW 추적 + 스케줄러
  disclosure_translator.py # 공시 보고서명 -> 초보자 해설 + 호재/악재 태그 (핵심 자산)
  disclosures.py           # DART 공시 수집(키 있을 때) + corp_code 해석 + 샘플 폴백
  sources.py      # 다중 소스 뉴스 수집기(네이버뉴스/구글뉴스/블로그)
  crawler.py      # 소스 통합 + 중복제거 + 정렬 + 본문 추출
  summarizer.py   # 초보자 요약 + 용어 사전 + 톤 분류 (Claude 선택, 규칙 폴백)
  stocks.py       # 종목명 <-> 코드 변환
  sample_data.py  # 오프라인/차단 환경용 샘플 뉴스(다중 소스 시연)
frontend/
  index.html / style.css / app.js   # 반응형 단일 페이지
Dockerfile / Procfile / render.yaml  # 배포 설정
```

## API

```
GET /api/news?symbols=삼성전자,000660&limit=5
```

각 종목별로 `items[]`(title, source, source_type, date, url, summary, terms[], tone, is_new) 반환.

---

## 동작 메모

- **인터넷이 열린 환경**(개인 PC/배포 서버): 실제 뉴스를 여러 소스에서 가져옵니다.
- **네트워크가 차단된 환경**(일부 클라우드 샌드박스): 자동으로 번들 샘플 데이터로 폴백해
  화면·요약·소스 라벨을 그대로 시연합니다.

## ⚠️ 면책

본 서비스는 **정보 제공 목적**이며 투자 권유가 아닙니다. 뉴스 톤 표시도 기사 분위기 참고용일 뿐
매수/매도 신호가 아닙니다. 투자 판단과 책임은 본인에게 있습니다. 국내에서 종목 추천·매매신호를
제공하려면 유사투자자문업 신고 등 규제 확인이 필요합니다.

## 다음 단계 후보

- 종목별 푸시 알림(브라우저/이메일)
- 텔레그램·X(트위터) 등 소스 추가
- 종목 상세(차트·재무) 페이지
- 사용자 계정 + 서버 저장(여러 기기 동기화)

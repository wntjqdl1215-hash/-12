#!/usr/bin/env bash
# 주식 뉴스 한눈에 - 실행 스크립트
set -e
cd "$(dirname "$0")"

# 1) 의존성 설치 (최초 1회)
pip install -q -r requirements.txt

# 2) (선택) Claude 초보자 요약을 쓰려면 API 키 설정 후 anthropic 설치
#   export ANTHROPIC_API_KEY=sk-...
#   pip install anthropic

# 3) 서버 실행
cd backend
export PORT="${PORT:-8000}"
echo "▶ http://localhost:${PORT} 에서 열어보세요 (모바일은 같은 와이파이에서 PC IP:${PORT})"
python3 app.py

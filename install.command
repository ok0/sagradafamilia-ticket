#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=================================================="
echo "  사그라다 파밀리아 티켓 봇 — 초기 설치"
echo "=================================================="
echo ""

# Homebrew 확인 / 설치
if ! command -v brew &>/dev/null; then
    echo "[1/4] Homebrew 설치 중... (관리자 비밀번호가 필요할 수 있습니다)"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Apple Silicon Mac의 경우 PATH 추가
    eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null || true
else
    echo "[1/4] Homebrew 확인 완료"
fi

# Python 확인 / 설치
if ! command -v python3 &>/dev/null; then
    echo "[2/4] Python 설치 중..."
    brew install python
else
    echo "[2/4] Python 확인 완료: $(python3 --version)"
fi

# 가상환경 생성 및 패키지 설치
echo "[3/4] 패키지 설치 중..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Playwright 브라우저 설치
echo "[4/4] 브라우저 설치 중..."
playwright install chromium

echo ""
echo "=================================================="
echo "  설치 완료!"
echo "  run.command 파일을 더블클릭해서 실행하세요."
echo "=================================================="
echo ""
read -p "이 창을 닫으려면 Enter를 누르세요..."

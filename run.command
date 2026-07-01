#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "설치가 필요합니다. install.command를 먼저 더블클릭해서 실행해주세요."
    read -p "Enter를 눌러 종료..."
    exit 1
fi

source .venv/bin/activate
python main.py --auto-book
read -p "종료하려면 Enter를 누르세요..."

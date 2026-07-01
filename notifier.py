import os
import subprocess
import sys
import threading
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def _timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print(f"[Telegram 오류] {e}")


def notify(title: str, message: str):
    print(f"\n{'='*60}")
    print(f"[{_timestamp()}] {title}")
    print(message)
    print('='*60)

    _send_telegram(f"[{title}]\n{message}")

    try:
        subprocess.run(
            ["osascript", "-e", f'display notification "{message}" with title "{title}" sound name "Glass"'],
            check=False,
            capture_output=True,
        )
    except FileNotFoundError:
        pass

    sys.stdout.write("\a")
    sys.stdout.flush()


def log(message: str):
    print(f"[{_timestamp()}] {message}")


_ALERT_STOP = threading.Event()

def start_alert_sound():
    """체크아웃 도달 시 효과음을 멈출 때까지 반복 재생."""
    _ALERT_STOP.clear()
    sound = "/System/Library/Sounds/Glass.aiff"

    def _loop():
        while not _ALERT_STOP.is_set():
            try:
                subprocess.run(["afplay", sound], check=False, capture_output=True)
            except FileNotFoundError:
                sys.stdout.write("\a")
                sys.stdout.flush()
            _ALERT_STOP.wait(timeout=1.2)

    threading.Thread(target=_loop, daemon=True).start()


def stop_alert_sound():
    _ALERT_STOP.set()

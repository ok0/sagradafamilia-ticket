"""날짜별 가용 발견 횟수를 stats.json에 누적 기록한다."""
import json
from pathlib import Path

_STATS_FILE = Path(__file__).resolve().parent / "stats.json"


def _load() -> dict:
    if _STATS_FILE.exists():
        try:
            return json.loads(_STATS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: dict):
    _STATS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def record(date: str) -> str:
    """발견 횟수를 1 증가시키고 전광판 문자열을 반환한다."""
    data = _load()
    data[date] = data.get(date, 0) + 1
    _save(data)
    return _format(data)


def scoreboard() -> str:
    """현재까지 누적된 전광판 문자열을 반환한다."""
    return _format(_load())


def _format(data: dict) -> str:
    if not data:
        return "  (기록 없음)"
    return "\n".join(
        f"  {d}: {c}회 발견"
        for d, c in sorted(data.items())
    )

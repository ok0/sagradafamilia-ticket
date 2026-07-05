"""날짜별 가용 발견 횟수 + 마지막 발견 시각을 stats.json에 누적 기록한다."""
import json
from datetime import datetime
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
    entry = data.get(date, {"count": 0, "last": ""})
    # 이전 버전(값이 int)과의 호환성 처리
    if isinstance(entry, int):
        entry = {"count": entry, "last": ""}
    entry["count"] += 1
    entry["last"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data[date] = entry
    _save(data)
    return _format(data)


def scoreboard() -> str:
    """현재까지 누적된 전광판 문자열을 반환한다."""
    return _format(_load())


def _format(data: dict) -> str:
    if not data:
        return "  (기록 없음)"
    lines = []
    for d in sorted(data.keys()):
        entry = data[d]
        if isinstance(entry, int):
            lines.append(f"  {d} : {entry}회 발견")
        else:
            count = entry.get("count", 0)
            last  = entry.get("last", "")
            lines.append(f"  {d} : {count}회 발견  (마지막: {last})")
    return "\n".join(lines)

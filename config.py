import os
from dotenv import load_dotenv

load_dotenv()

TICKET_URL             = "https://tickets.sagradafamilia.org/en/1-individual/4375-sagrada-familia"
CHECK_INTERVAL_SECONDS = 30

NUM_PEOPLE    = int(os.getenv("NUM_PEOPLE", "2"))
PARALLEL_COUNT = int(os.getenv("PARALLEL_COUNT", "1"))
KEEP_BROWSER   = os.getenv("KEEP_BROWSER", "false").lower() == "true"

# ── 날짜별 시간 파싱 ─────────────────────────────────────────
# 신규 형식: TARGET_DATE_TIME=2026-07-16@17:00,18:00;2026-07-30@14:00,15:00
# 구형 호환: TARGET_DATE + TARGET_TIME (모든 날짜에 동일 시간)

DATE_TIMES: dict[str, list[str]] = {}  # {date: [times]}

_dt_raw = os.getenv("TARGET_DATE_TIME", "").strip()
if _dt_raw:
    for _entry in _dt_raw.split(";"):
        _entry = _entry.strip()
        if "@" in _entry:
            _date, _times_str = _entry.split("@", 1)
            _date  = _date.strip()
            _times = [t.strip() for t in _times_str.split(",") if t.strip()]
            if _date and _times:
                DATE_TIMES[_date] = _times
else:
    # 구형 형식 호환
    _dates = [d.strip() for d in os.getenv("TARGET_DATE", "").split(",") if d.strip()]
    _times = [t.strip() for t in os.getenv("TARGET_TIME", "").split(",") if t.strip()]
    for _d in _dates:
        DATE_TIMES[_d] = _times

TARGET_DATES = list(DATE_TIMES.keys())
TARGET_TIMES = list(dict.fromkeys(t for ts in DATE_TIMES.values() for t in ts))  # 순서 유지 중복 제거


def get_times_for_date(date: str) -> list[str]:
    return DATE_TIMES.get(date, TARGET_TIMES)


# ── 방문자 정보 ──────────────────────────────────────────────

PEOPLE = []
for i in range(1, NUM_PEOPLE + 1):
    PEOPLE.append({
        "name":     os.getenv(f"PERSON{i}_NAME", ""),
        "surname":  os.getenv(f"PERSON{i}_SURNAME", ""),
        "passport": os.getenv(f"PERSON{i}_PASSPORT", ""),
        "doc_type": "Pasaporte",
        "country":  "Korea",
    })


def validate():
    errors = []
    if not DATE_TIMES:
        errors.append("날짜와 시간이 설정되지 않았습니다. (TARGET_DATE_TIME)")
    else:
        for date, times in DATE_TIMES.items():
            if not times:
                errors.append(f"{date} 에 대한 시간이 설정되지 않았습니다.")
    for i, p in enumerate(PEOPLE, 1):
        if not p["name"]:
            errors.append(f"PERSON{i}_NAME이 설정되지 않았습니다.")
        if not p["surname"]:
            errors.append(f"PERSON{i}_SURNAME이 설정되지 않았습니다.")
        if not p["passport"]:
            errors.append(f"PERSON{i}_PASSPORT이 설정되지 않았습니다.")
    return errors

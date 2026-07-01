import os
from dotenv import load_dotenv

load_dotenv()

TICKET_URL = "https://tickets.sagradafamilia.org/en/1-individual/4375-sagrada-familia"
CHECK_INTERVAL_SECONDS = 30  # 30초

# 다중 날짜 지원: 쉼표로 구분 (예: 2026-07-15,2026-07-16)
TARGET_DATES = [d.strip() for d in os.getenv("TARGET_DATE", "").split(",") if d.strip()]
# 다중 시간 지원: 쉼표로 구분 (예: 10:00,10:15,13:00)
TARGET_TIMES = [t.strip() for t in os.getenv("TARGET_TIME", "").split(",") if t.strip()]

NUM_PEOPLE = int(os.getenv("NUM_PEOPLE", "2"))
PARALLEL_COUNT = int(os.getenv("PARALLEL_COUNT", "1"))
KEEP_BROWSER  = os.getenv("KEEP_BROWSER", "false").lower() == "true"

PEOPLE = []
for i in range(1, NUM_PEOPLE + 1):
    PEOPLE.append({
        "name": os.getenv(f"PERSON{i}_NAME", ""),
        "surname": os.getenv(f"PERSON{i}_SURNAME", ""),
        "passport": os.getenv(f"PERSON{i}_PASSPORT", ""),
        "doc_type": "Pasaporte",
        "country": "Korea",
    })



def validate():
    errors = []
    if not TARGET_DATES:
        errors.append("TARGET_DATE가 설정되지 않았습니다.")
    if not TARGET_TIMES:
        errors.append("TARGET_TIME이 설정되지 않았습니다.")
    for i, p in enumerate(PEOPLE, 1):
        if not p["name"]:
            errors.append(f"PERSON{i}_NAME이 설정되지 않았습니다.")
        if not p["surname"]:
            errors.append(f"PERSON{i}_SURNAME이 설정되지 않았습니다.")
        if not p["passport"]:
            errors.append(f"PERSON{i}_PASSPORT이 설정되지 않았습니다.")
    return errors

# Sagrada Familia Ticket Monitor & Booker

사그라다 파밀리아(Sagrada Familia) 티켓의 취소표를 모니터링하고, 가용 시 자동으로 예매(결제 전 체크아웃 페이지 대기)까지 진행해주는 자동화 봇(Bot)입니다.

## 주요 기능
- **자동 모니터링:** 지정된 여러 날짜와 시간대에 빈자리가 났는지 지속적으로 확인합니다.
- **자동 예매 (`--auto-book`):** 티켓 슬롯이 열리면 자동으로 장바구니에 담고 방문자 여권 정보를 입력한 뒤, 결제 직전 체크아웃 페이지에서 대기하며 알림음을 발생시킵니다.
- **텔레그램 알림:** 티켓이 열렸을 때 텔레그램 메신저로 즉시 알림을 발송합니다.
- **병렬 조회 및 브라우저 세션 유지:** 여러 탭/창을 띄워 다중 날짜를 병렬로 빠르게 조회할 수 있으며, `KEEP_BROWSER` 옵션을 통해 브라우저를 끄지 않고 최소화 상태로 유지하여 재조회 속도를 극대화합니다.
- **GUI 지원:** CLI 환경 외에도 직관적으로 설정을 관리하고 구동할 수 있는 데스크톱 런처(`gui.py`)를 포함합니다.

## 시스템 요구사항
- **OS**: macOS 환경 권장 (Playwright 및 알림음 시스템 종속성 고려)
- **Python**: Python 3.10 이상

## 설치 방법

1. 저장소를 클론하고 디렉토리로 이동합니다.
   ```bash
   git clone git@github.com:ok0/sagradafamilia-ticket.git
   cd sagradafamilia-ticket
   ```

2. 가상환경 생성 및 의존성 패키지를 설치합니다.
   *(또는 macOS 사용자의 경우 제공된 `install.command` 파일을 더블 클릭하여 자동 설치 가능합니다.)*
   ```bash
   # 가상환경 생성 및 활성화
   python3 -m venv .venv
   source .venv/bin/activate

   # 패키지 설치
   pip install -r requirements.txt

   # Playwright 브라우저 설치
   playwright install chromium
   ```

## 설정 및 준비 (.env)

프로젝트 루트에 있는 `.env.example` 파일을 복사하여 `.env` 파일을 생성한 후 본인의 환경에 맞게 값을 수정합니다.

```bash
cp .env.example .env
```

**주요 설정 항목 (`.env`)**
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: 텔레그램 봇 토큰 및 수신할 채팅방 ID
- `TARGET_DATE`: 희망 관람일 (`2026-08-15,2026-08-16` 형식, 콤마로 복수 선택 가능)
- `TARGET_TIME`: 희망 관람 시간 (`10:00,10:15` 형식, 콤마로 복수 선택 가능)
- `NUM_PEOPLE`: 예매할 방문객 수
- `PERSON1_NAME`, `PERSON1_SURNAME`, `PERSON1_PASSPORT` ... : 방문객 세부 정보 (자동 예매 시 폼 입력에 사용됨)
- `PARALLEL_COUNT`: 병렬로 띄울 워커 개수 (다중 날짜를 쪼개서 병렬 조회)
- `KEEP_BROWSER`: `true`일 경우 매번 브라우저를 새로 띄우지 않고 최소화 상태로 유지하여 재사용

## 실행 방법

가상환경이 활성화된 상태에서 터미널을 통해 스크립트를 실행합니다.

### 1. 모니터링 모드 (알림 전용)
조건에 맞는 티켓이 나왔을 때 텔레그램으로 알림만 전송합니다.

```bash
python main.py
```

### 2. 자동 예매 모드
티켓이 발견되면 즉시 장바구니에 담고 체크아웃 페이지까지 진행합니다. 결제 페이지에 도달하면 알람음이 울리며 화면이 전면으로 복원됩니다. 사용자는 나타난 화면에서 수동으로 결제를 완료하면 됩니다.

```bash
python main.py --auto-book
```

### 3. GUI 모드
명령어가 익숙하지 않다면 macOS 기반 데스크톱 런처를 사용할 수 있습니다.
- 폴더에서 `run.command` 파일을 더블클릭하거나 아래 명령어로 GUI 앱을 엽니다.
  ```bash
  python gui.py
  ```

## 주의 사항
- 잦은 새로고침 및 과도한 요청(짧은 조회 간격)은 해당 사이트 측에서 IP 밴(차단) 혹은 캡챠(reCAPTCHA)를 유발할 수 있습니다. 
- 결제 단계는 사용자가 브라우저에서 **직접 수동으로 결제 정보를 입력**하여 마무리해야 합니다. 프로그램은 결제 직전 단계까지만 자동화합니다.

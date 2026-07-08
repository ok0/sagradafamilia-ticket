"""
사그라다 파밀리아 티켓 모니터 & 자동 예매 메인 모듈.

사용법:
  python main.py              # 모니터링만 (가용 시 Telegram 알림)
  python main.py --auto-book  # 가용 시 자동 예매 진행 (체크아웃 페이지에서 대기)
"""
import asyncio
import argparse
import sys

import config
import notifier
import checker
import booker
import stats
from playwright.async_api import async_playwright, Page


# ── 날짜 그룹 분배 ─────────────────────────────────────────────

def _split_dates() -> list[list[str]]:
    dates = config.TARGET_DATES
    parallel = min(config.PARALLEL_COUNT, max(1, len(dates)))
    chunk = max(1, (len(dates) + parallel - 1) // parallel)
    return [dates[i:i + chunk] for i in range(0, len(dates), chunk)]


# ── 핵심 예매 로직 (브라우저 생성 없음) ──────────────────────────

async def _do_booking(
    page: Page,
    dates: list,
    done_event: asyncio.Event,
    worker_id: int,
    restore_on_checkout: bool = False,
) -> bool:
    """
    주어진 page에서 날짜·시간 조합을 순서대로 시도한다.
    체크아웃 도달 시 restore_on_checkout=True면 창을 복원 후 대기.
    """
    tag = f"[W{worker_id}]"

    for target_date in dates:
        if done_event.is_set():
            return False

        await page.goto(config.TICKET_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        notifier.log(f"{tag} 날짜 선택: {target_date}")
        date_ok = await checker._select_date(page, target_date)
        if not date_ok:
            continue

        board = stats.record(target_date)
        notifier.log(f"【 발견 현황 】\n{board}")

        await asyncio.sleep(1.5)

        for target_time in config.get_times_for_date(target_date):
            if done_event.is_set():
                return False

            notifier.log(f"{tag} 예매 시도: {target_date} {target_time}")
            time_ok = await checker._select_time(page, target_time)
            if not time_ok:
                continue

            booked = await booker.book(page)
            if booked:
                done_event.set()
                if restore_on_checkout:
                    await checker._restore_window(page)
                notifier.log(f"{tag} 체크아웃 페이지 도달! 결제를 진행하세요. (Stop 버튼으로 종료)")
                notifier.start_alert_sound()
                try:
                    input()
                except (EOFError, OSError):
                    await asyncio.sleep(3600)
                finally:
                    notifier.stop_alert_sound()
                return True

    return False


# ── 일반 모드: 매 시도마다 브라우저 열고 닫기 ─────────────────────

async def _book_worker(dates: list, done_event: asyncio.Event, worker_id: int) -> bool:
    tag = f"[W{worker_id}]"
    async with async_playwright() as pw:
        browser, context = await checker._new_context(pw, headless=False)
        page = await context.new_page()
        try:
            await page.goto(config.TICKET_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            await checker._accept_cookies(page)
            return await _do_booking(page, dates, done_event, worker_id, restore_on_checkout=False)
        except Exception as e:
            if not done_event.is_set():
                notifier.log(f"{tag} 오류: {e}")
            return False
        finally:
            try:
                await browser.close()
            except Exception:
                pass


async def run_parallel() -> bool:
    groups = _split_dates()
    notifier.log(f"병렬 {len(groups)}개 워커 시작")
    for i, g in enumerate(groups, 1):
        notifier.log(f"  W{i}: {', '.join(g)}")

    done_event = asyncio.Event()
    tasks = [
        asyncio.create_task(_book_worker(group, done_event, i + 1))
        for i, group in enumerate(groups)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return any(r is True for r in results)


# ── 유지 모드: 브라우저 한 번만 열고, 시도 중 최소화 ───────────────

async def run_persistent() -> None:
    groups = _split_dates()
    notifier.log(f"[유지 모드] 병렬 {len(groups)}개 브라우저 시작 — 최소화 상태 유지")
    for i, g in enumerate(groups, 1):
        notifier.log(f"  W{i}: {', '.join(g)}")

    async with async_playwright() as pw:
        workers: list[tuple] = []
        for i, group in enumerate(groups):
            browser, context = await checker._new_context(pw, headless=False)
            page = await context.new_page()
            await page.goto(config.TICKET_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            await checker._accept_cookies(page)
            await checker._minimize_window(page)
            workers.append((browser, page, group, i + 1))

        attempt = 0
        consecutive_errors: dict[int, int] = {}
        stop_requested = False
        while True:
            attempt += 1
            dates_str = ", ".join(config.TARGET_DATES)
            notifier.log(f"[시도 {attempt}] 날짜: {dates_str} 가용성 확인 중...")

            done_event = asyncio.Event()
            tasks = [
                asyncio.create_task(
                    _do_booking(page, group, done_event, wid, restore_on_checkout=True)
                )
                for _, page, group, wid in workers
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for (_, _, _, wid), r in zip(workers, results):
                if isinstance(r, Exception):
                    notifier.log(f"[W{wid}] 오류: {r!r}")
                    consecutive_errors[wid] = consecutive_errors.get(wid, 0) + 1
                    if consecutive_errors[wid] >= 3:
                        notifier.notify_telegram(
                            "사그라다 파밀리아 모니터 - 오류 반복으로 중단",
                            f"[W{wid}] 오류가 {consecutive_errors[wid]}회 연속 발생하여 "
                            f"모니터링을 중단합니다 (사이트 차단/캡챠 가능성).\n마지막 오류: {r!r}"
                        )
                        stop_requested = True
                else:
                    consecutive_errors[wid] = 0

            if any(r is True for r in results):
                notifier.log("예매 완료. 모니터링을 종료합니다.")
                break

            if stop_requested:
                notifier.log("오류 반복으로 모니터링을 중단합니다.")
                break

            # 다음 시도까지 모든 창 최소화 유지
            for _, page, _, _ in workers:
                await checker._minimize_window(page)

        for browser, _, _, _ in workers:
            try:
                await browser.close()
            except Exception:
                pass


# ── 메인 루프 ───────────────────────────────────────────────────

async def monitor_loop(auto_book: bool):
    if auto_book and config.KEEP_BROWSER:
        await run_persistent()
        return

    attempt = 0
    while True:
        attempt += 1
        dates_str = ", ".join(config.TARGET_DATES)
        notifier.log(f"[시도 {attempt}] 날짜: {dates_str} 가용성 확인 중...")

        if auto_book:
            success = await run_parallel()
            if success:
                notifier.log("예매 완료. 모니터링을 종료합니다.")
                break
        else:
            available, found_date, found_time = await checker.check_availability(headless=True)
            if available:
                notifier.notify(
                    "사그라다 파밀리아 티켓 가용",
                    f"{found_date} {found_time} 슬롯이 열렸습니다!\n지금 바로 예매하세요: {config.TICKET_URL}"
                )
            else:
                notifier.log("해당 슬롯 없음. 대기 중...")

        # todo
        # notifier.log(f"{config.CHECK_INTERVAL_SECONDS // 60}분 후 재시도...")
        # await asyncio.sleep(config.CHECK_INTERVAL_SECONDS)


def main():
    parser = argparse.ArgumentParser(description="사그라다 파밀리아 티켓 모니터")
    parser.add_argument(
        "--auto-book",
        action="store_true",
        help="가용 시 자동으로 예매 진행 (체크아웃 페이지에서 대기)",
    )
    args = parser.parse_args()

    errors = config.validate()
    if errors:
        print("설정 오류:")
        for e in errors:
            print(f"  - {e}")
        print("\n.env.example을 복사해 .env 파일을 만들고 값을 입력해주세요:")
        print("  cp .env.example .env")
        sys.exit(1)

    print("=" * 60)
    print("사그라다 파밀리아 티켓 모니터")
    print("=" * 60)
    print("목표 날짜/시간:")
    for _d, _ts in config.DATE_TIMES.items():
        print(f"  {_d}  →  {', '.join(_ts)}")
    print(f"인원       : General {config.NUM_PEOPLE}명")
    print(f"병렬 수    : {config.PARALLEL_COUNT}")
    print(f"브라우저   : {'유지 모드 (최소화)' if config.KEEP_BROWSER else '일반 모드 (매 시도마다 열고 닫기)'}")
    print(f"자동 예매  : {'ON' if args.auto_book else 'OFF (알림만)'}")
    print(f"조회 간격  : {config.CHECK_INTERVAL_SECONDS // 60}분")
    print("=" * 60)
    print("Ctrl+C로 종료")
    board = stats.scoreboard()
    if board.strip() != "(기록 없음)":
        print("【 누적 발견 현황 】")
        print(board)
    print()

    try:
        asyncio.run(monitor_loop(auto_book=args.auto_book))
    except KeyboardInterrupt:
        print("\n모니터링을 종료합니다.")


if __name__ == "__main__":
    main()

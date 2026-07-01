"""
사그라다 파밀리아 티켓 가용성 확인 모듈.
Playwright를 사용해 브라우저를 제어한다.
"""
import asyncio
from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout
import config
import notifier

MONTHS_EN = ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"]

_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
window.chrome = {runtime: {}};
"""


async def _new_context(pw, headless: bool, offscreen: bool = False):
    """자동화 감지를 우회하는 브라우저 컨텍스트를 생성한다."""
    args = ["--disable-blink-features=AutomationControlled"]
    if offscreen:
        args.append("--window-position=-3000,-3000")
    browser = await pw.chromium.launch(
        headless=headless,
        args=args,
    )
    context = await browser.new_context(
        locale="en-US",
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
    )
    await context.add_init_script(_STEALTH_SCRIPT)
    return browser, context


async def _minimize_window(page: Page):
    """CDP로 브라우저 창을 최소화한다."""
    try:
        client = await page.context.new_cdp_session(page)
        result = await client.send("Browser.getWindowForTarget")
        window_id = result["windowId"]
        await client.send("Browser.setWindowBounds", {
            "windowId": window_id,
            "bounds": {"windowState": "minimized"},
        })
    except Exception as e:
        notifier.log(f"창 최소화 실패: {e}")


async def _restore_window(page: Page):
    """CDP로 최소화된 브라우저 창을 화면 중앙으로 복원한다."""
    try:
        client = await page.context.new_cdp_session(page)
        result = await client.send("Browser.getWindowForTarget")
        window_id = result["windowId"]
        await client.send("Browser.setWindowBounds", {
            "windowId": window_id,
            "bounds": {"windowState": "normal", "left": 100, "top": 80, "width": 1280, "height": 800},
        })
        await page.bring_to_front()
        notifier.log("브라우저를 화면으로 복원했습니다.")
    except Exception as e:
        notifier.log(f"창 복원 실패: {e}")


async def _accept_cookies(page: Page):
    """쿠키 승인 팝업 처리. 클릭 후 페이지 새로고침 대기."""
    try:
        btn = page.locator("button.btn-cookies-primary").first
        await btn.wait_for(state="visible", timeout=8000)
        await btn.evaluate("el => el.click()")  # overlay 우회용 JS 클릭
        notifier.log("쿠키 승인 클릭")
        # 클릭 후 페이지 새로고침 대기
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
        await asyncio.sleep(1.5)
        notifier.log("쿠키 승인 완료 — 페이지 재로드됨")
    except Exception as e:
        notifier.log(f"쿠키 팝업 없음 또는 처리 불필요: {e}")


async def _select_date(page: Page, target_date: str) -> bool:
    """달력에서 희망 날짜 선택. target_date: YYYY-MM-DD"""
    from datetime import date as date_cls
    year, month, day = target_date.split("-")
    month_int = int(month)
    # data-date-id 형식: DD/MM/YYYY
    date_id = f"{int(day):02d}/{month_int:02d}/{year}"

    await page.wait_for_selector(".DayPickerNavigation_button", timeout=15000)

    today = date_cls.today()
    target_d = date_cls(int(year), month_int, int(day))
    max_steps = (target_d.year - today.year) * 12 + (target_d.month - today.month) + 2

    for step in range(max_steps + 1):
        date_btn = page.locator(f'div.CalendarDay_button[data-date-id="{date_id}"]')
        try:
            await date_btn.wait_for(state="visible", timeout=4000)
        except Exception:
            notifier.log(f"[step {step}] {date_id} 아직 안 보임 → 다음 달로 이동")
            if step < max_steps:
                next_btn = page.locator('div[aria-label="Move forward to switch to the next month."]')
                await next_btn.evaluate("el => el.click()")
                await asyncio.sleep(1.5)
            continue

        # JS가 가용성 클래스를 업데이트할 때까지 대기
        await asyncio.sleep(1.0)
        inner_class = await date_btn.locator("div").get_attribute("class") or ""
        notifier.log(f"[step {step}] {date_id} 발견 — class='{inner_class.strip()}'")

        if "no-availability" in inner_class or "disabled" in inner_class:
            notifier.log(f"날짜 {target_date} 선택 불가 (매진). 5초 후 다음 날짜로 이동...")
            await asyncio.sleep(5)
            return False
        await date_btn.click()
        notifier.log(f"날짜 {target_date} 선택 완료")
        return True

    notifier.log(f"날짜 {target_date}를 달력에서 찾지 못했습니다.")
    return False


async def _select_time(page: Page, target_time: str) -> bool:
    """구간을 순서대로 클릭하며 target_time이 있는 구간을 찾아 선택."""
    try:
        await page.wait_for_selector("div.event-group-tabs", timeout=8000)
    except PWTimeout:
        notifier.log("시간 구간 탭을 찾지 못했습니다.")
        return False

    group_btns = page.locator("div.event-group-tabs div.event-selector[role='button']")
    group_count = await group_btns.count()
    notifier.log(f"구간 버튼 {group_count}개 발견")

    for i in range(group_count):
        await group_btns.nth(i).click()
        notifier.log(f"구간 {i + 1} 클릭")
        await asyncio.sleep(0.8)

        time_btn = page.locator(f'button.event:has(span:text-is("{target_time}"))')
        if await time_btn.count() > 0:
            await time_btn.click()
            notifier.log(f"시간 '{target_time}' 선택 (구간 {i + 1})")
            return True

    notifier.log(f"시간 '{target_time}'을 찾지 못했습니다 (매진 또는 없음).")
    return False


async def check_availability(headless: bool = True) -> tuple[bool, str, str]:
    """
    모든 (date, time) 조합을 시도해 첫 번째 가용 슬롯을 반환한다.
    Returns (available, found_date, found_time).
    """
    async with async_playwright() as pw:
        browser, context = await _new_context(pw, headless=headless)
        page = await context.new_page()

        try:
            await page.goto(config.TICKET_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            await _accept_cookies(page)

            first_date = True
            for target_date in config.TARGET_DATES:
                # 날짜가 바뀔 때만 페이지 새로고침
                if not first_date:
                    await page.goto(config.TICKET_URL, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                first_date = False

                notifier.log(f"날짜 선택: {target_date}")
                date_ok = await _select_date(page, target_date)
                if not date_ok:
                    continue

                await asyncio.sleep(1.5)

                # 같은 날짜에서 시간만 순서대로 시도 (페이지 새로고침 없음)
                for target_time in config.TARGET_TIMES:
                    notifier.log(f"시간 확인: {target_date} {target_time}")
                    time_ok = await _select_time(page, target_time)
                    if time_ok:
                        return True, target_date, target_time

            return False, "", ""

        except Exception as e:
            notifier.log(f"가용성 확인 중 오류: {e}")
            return False, "", ""
        finally:
            await browser.close()

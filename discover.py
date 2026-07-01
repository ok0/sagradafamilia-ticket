"""
사이트 구조 탐색 스크립트.
실제 HTML 셀렉터를 파악하기 위해 브라우저를 열고 스크린샷 및 DOM 정보를 저장한다.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
import config


async def discover():
    output_dir = Path("discovery")
    output_dir.mkdir(exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)  # 브라우저 표시
        context = await browser.new_context(locale="en-US")
        page = await context.new_page()

        print("사이트 접속 중...")
        await page.goto(config.TICKET_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # 초기 스크린샷
        await page.screenshot(path="discovery/01_initial.png", full_page=True)
        print("스크린샷 저장: discovery/01_initial.png")

        # 쿠키 팝업 처리 시도
        for sel in ["button:has-text('Accept')", "button:has-text('Aceptar')", "#cookieAccept"]:
            try:
                await page.click(sel, timeout=3000)
                await asyncio.sleep(1)
                print(f"쿠키 동의 클릭: {sel}")
                break
            except Exception:
                pass

        await page.screenshot(path="discovery/02_after_cookie.png", full_page=True)

        # 주요 인터랙티브 요소 수집
        elements = await page.evaluate("""() => {
            const collect = (selector, label) => {
                return Array.from(document.querySelectorAll(selector)).map(el => ({
                    label,
                    tag: el.tagName,
                    id: el.id,
                    class: el.className,
                    name: el.name || '',
                    type: el.type || '',
                    text: el.innerText?.slice(0, 100) || '',
                    placeholder: el.placeholder || '',
                    'data-*': Object.fromEntries(
                        Array.from(el.attributes)
                            .filter(a => a.name.startsWith('data-'))
                            .map(a => [a.name, a.value])
                    )
                }));
            };
            return {
                buttons: collect('button', 'button'),
                inputs: collect('input', 'input'),
                selects: collect('select', 'select'),
                calendar: collect('[class*="calendar"], [class*="datepicker"]', 'calendar'),
                days: collect('[class*="day"]', 'day'),
                slots: collect('[class*="slot"], [class*="time"], [class*="schedule"]', 'slot/time'),
            };
        }""")

        with open("discovery/elements.json", "w", encoding="utf-8") as f:
            json.dump(elements, f, ensure_ascii=False, indent=2)
        print("DOM 요소 저장: discovery/elements.json")

        # 달력 영역 스크린샷 (있는 경우)
        try:
            cal = page.locator("[class*='calendar'], [class*='datepicker']").first
            await cal.screenshot(path="discovery/03_calendar.png")
            print("달력 스크린샷: discovery/03_calendar.png")
        except Exception:
            print("달력 영역을 찾지 못했습니다.")

        print("\n브라우저가 열린 상태입니다. 페이지를 탐색하고 Enter를 눌러 종료하세요.")
        input()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(discover())

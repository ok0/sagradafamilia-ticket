"""
티켓 자동 예매 모듈 (목표 2.2).
checker.py에서 날짜/시간 선택 후 이 모듈로 실제 예매를 진행한다.
"""
import asyncio
from playwright.async_api import Page, TimeoutError as PWTimeout
import config
import notifier


async def _set_general_count(page: Page, target: int):
    """General 인원 수를 target명으로 설정한다."""
    general_div = 'div.buyerType[data-buyertype-id="General"]'
    await page.wait_for_selector(general_div, timeout=10000)

    qty_input = page.locator(f'{general_div} input[name="quantity"]')
    current = int(await qty_input.get_attribute("value") or "0")

    inc_btn = f'{general_div} button[data-action-id="increment"]'
    dec_btn = f'{general_div} button[data-action-id="decrement"]'

    diff = target - current
    if diff > 0:
        for _ in range(diff):
            await page.click(inc_btn)
            await asyncio.sleep(0.3)
    elif diff < 0:
        for _ in range(-diff):
            await page.click(dec_btn)
            await asyncio.sleep(0.3)

    notifier.log(f"General {target}명 설정 완료")


async def _fill_person_details(page: Page, person: dict, index: int):
    """
    방문자 정보 입력. index는 0부터 시작.
    field IDs: 3711=Name, 3712=Surname, 3876=DocType, 3879=Country
    """
    i = index

    await page.fill(
        f'input[name="formsection-810.field-3711-bt-1-{i}[0].value"]',
        person["name"],
    )
    await page.fill(
        f'input[name="formsection-810.field-3712-bt-1-{i}[0].value"]',
        person["surname"],
    )

    # Document Type: PSP = Pasaporte
    await page.select_option(
        f'select[name="formsection-810.field-3876-bt-1-{i}[0].value"]',
        value="PSP",
    )
    await asyncio.sleep(0.8)  # Pasaporte 선택 후 여권번호 필드 등장 대기

    # Country: KR = Korea
    await page.select_option(
        f'select[name="formsection-810.field-3879-bt-1-{i}[0].value"]',
        value="KR",
    )

    # 여권번호: field-3887
    await page.fill(
        f'input[name="formsection-810.field-3887-bt-1-{i}[0].value"]',
        person["passport"],
    )

    notifier.log(f"방문자 {i+1} 정보 입력 완료: {person['name']} {person['surname']}")


async def book(page: Page) -> bool:
    """
    날짜/시간 선택이 완료된 페이지에서 예매를 진행한다.
    Returns True if booking reached checkout page.
    """
    try:
        # 인원 수 설정
        notifier.log("인원 수 설정 중...")
        await _set_general_count(page, config.NUM_PEOPLE)

        # Continue (인원 선택 후)
        await page.click("button.btn-custom-next.select-tickets")
        notifier.log("Continue 클릭 (인원 선택 후)")
        await asyncio.sleep(2)

        # 방문자 상세 정보 입력
        notifier.log("방문자 정보 입력 중...")
        for i, person in enumerate(config.PEOPLE):
            await _fill_person_details(page, person, i)

        await asyncio.sleep(1)

        # Continue (방문자 정보 입력 후) → 체크아웃 페이지
        await page.click("button.btn-custom-addToCart")
        notifier.log("Continue 클릭 (방문자 정보 후)")
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
        await asyncio.sleep(2)

        checkout_url = page.url
        notifier.log(f"체크아웃 URL: {checkout_url}")
        notifier.notify(
            "사그라다 파밀리아 티켓 예매 진행 중",
            f"체크아웃 페이지에 도달했습니다!\nURL: {checkout_url}\n결제를 완료해주세요."
        )
        return True

    except Exception as e:
        notifier.log(f"예매 진행 중 오류: {e}")
        return False

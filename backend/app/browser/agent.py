import json
import anthropic
from playwright.async_api import async_playwright
from app.config import settings
from app.browser.actions import get_page_text, click_by_test_id, fill_by_test_id, click_by_text

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

BROWSER_SYSTEM = """You are a browser automation agent for NorthShop's internal ShopAdmin portal.
You will be given a task and must complete it by issuing browser actions one step at a time.
After each action you will receive updated page content.

Portal structure:
- /admin — order list with a search input (data-testid="customer-search") and a table with columns: Order ID, Customer, Status, Total, Date.
- /admin/orders/<id> — order detail page showing customer info, items, status, and an "Issue Refund" button (data-testid="issue-refund-btn") if eligible.
- There are no navigation menus or sidebar links.

How to find orders:
- By order ID: navigate directly, e.g. {"action": "navigate", "url": "orders/1042"}
- By customer name or email: fill the search input first, e.g. {"action": "fill_testid", "testid": "customer-search", "value": "Alice Chen"}, then read the filtered results from the page and call done.
- If you can see the data you need in the current page text, call done immediately — do not navigate unnecessarily.

Available actions (respond with JSON, one action at a time):
- {"action": "navigate", "url": "<relative path>"}
- {"action": "click_testid", "testid": "<data-testid value>"}
- {"action": "click_text", "text": "<exact visible text of a button or link>"}
- {"action": "fill_testid", "testid": "<data-testid value>", "value": "<text>"}
- {"action": "done", "result": "<summary of what was accomplished or found>"}

Always respond with valid JSON and nothing else.
"""

MAX_STEPS = 15


async def run_browser_task(task: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(settings.shop_admin_url, wait_until="networkidle")

        messages = [{"role": "user", "content": f"Task: {task}\n\nCurrent page:\n{await get_page_text(page)}"}]

        for _ in range(MAX_STEPS):
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                system=BROWSER_SYSTEM,
                messages=messages,
            )

            raw = response.content[0].text.strip()
            messages.append({"role": "assistant", "content": raw})

            try:
                action = json.loads(raw)
            except json.JSONDecodeError:
                break

            if action["action"] == "done":
                await browser.close()
                return action.get("result", "Task completed.")

            try:
                await _execute_action(page, action)
                await page.wait_for_load_state("networkidle")
            except Exception as e:
                messages.append({"role": "user", "content": f"Action failed: {e}. Try a different action."})
                continue
            page_text = await get_page_text(page)
            messages.append({"role": "user", "content": f"Page updated:\n{page_text}"})

        await browser.close()
        return "Browser task did not complete within the step limit."


async def _execute_action(page, action: dict) -> None:
    match action["action"]:
        case "navigate":
            base = settings.shop_admin_url.rstrip("/")
            path = action["url"].lstrip("/")
            await page.goto(f"{base}/{path}", wait_until="networkidle")
        case "click_testid":
            await click_by_test_id(page, action["testid"])
        case "click_text":
            await click_by_text(page, action["text"])
        case "fill_testid":
            await fill_by_test_id(page, action["testid"], action["value"])

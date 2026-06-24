import json
import anthropic
from playwright.async_api import async_playwright
from app.config import settings
from app.browser.actions import snapshot, click_ref, fill_ref, select_ref
from app.browser.site_config import active_site

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

BROWSER_SYSTEM = """You are a browser automation agent. You are given a task to complete \
on a support portal and must complete it by issuing one action at a time.

After each action you receive an updated page snapshot showing:
- The page title and URL
- The visible page text (for context)
- A numbered list of interactive elements you can act on, e.g.:
    [1] input "Search by customer name or email"
    [2] button "Send"
    [3] link "Order #1042"

You act on elements using their reference number [N]. Always respond with valid JSON \
and nothing else.

Available actions:
- {"action": "click", "ref": N}                       — click element [N] (buttons, links, checkboxes, menu items)
- {"action": "fill", "ref": N, "value": "..."}        — type into input [N] (text inputs, textareas, number fields)
- {"action": "select", "ref": N, "value": "..."}      — choose an option in a <select> dropdown [N] by its visible label
- {"action": "navigate", "url": "..."}                — go to a URL (absolute or relative to site root)
- {"action": "scroll", "direction": "down"}           — scroll the page to reveal more content
- {"action": "scroll", "direction": "up"}             — scroll back up
- {"action": "go_back"}                               — navigate back to the previous page
- {"action": "read_page"}                             — re-read the current page without acting
- {"action": "done", "result": "..."}                 — task complete; summarise what was found or done

Notes on dropdowns and menus:
- A button with (collapsed) in its state is a dropdown trigger — click it to reveal options.
- After clicking a dropdown trigger, re-read the page to see the new menu items, then click the item you need.
- For <select> elements the snapshot lists all options; use the "select" action with the exact visible label.
- A <select> element showing (options: A | B | C, current: "A") requires {"action": "select", "ref": N, "value": "B"}.

Rules:
- Always call done when the task is complete or clearly impossible.
- If an element ref is not found after an action, re-read the page and try again with the new refs.
- Do not repeat the same failed action twice in a row — try a different approach.
- Never guess at information; read it from the page.
"""

MAX_STEPS = 15


async def run_browser_task(task: str, conversation_id: str | None = None) -> str:
    from app.agent.events import log_event

    site = active_site()

    async def _log(event_type: str, payload: dict) -> None:
        if conversation_id:
            await log_event(conversation_id, event_type, payload)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(site.start_url, wait_until="networkidle")

        initial_snapshot = await snapshot(page)
        task_context = (
            f"Site orientation: {site.orientation}\n\n"
            f"Task: {task}\n\n"
            f"Current page:\n{initial_snapshot}"
        )
        messages = [{"role": "user", "content": task_context}]

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
                observation = "Could not parse your response as JSON. Please respond with valid JSON only."
                messages.append({"role": "user", "content": observation})
                continue

            action_name = action.get("action", "")

            if action_name == "done":
                result = action.get("result", "Task completed.")
                await _log("browser_done", {"result": result})
                await browser.close()
                return result

            # Log before executing
            details = {k: v for k, v in action.items() if k != "action"}
            await _log("browser_action", {"action": action_name, "details": details})

            try:
                observation = await _execute_action(page, action)
            except ValueError as e:
                # Ref not found — return recoverable observation with fresh snapshot
                fresh = await snapshot(page)
                observation = f"{e}\n\nPage re-read:\n{fresh}"
                messages.append({"role": "user", "content": observation})
                continue
            except Exception as e:
                observation = f"Action failed: {e}. Try a different approach."
                messages.append({"role": "user", "content": observation})
                continue

            messages.append({"role": "user", "content": observation})

        await browser.close()
        return "Browser task did not complete within the step limit."


async def _execute_action(page, action: dict) -> str:
    """Execute one action and return a page observation string."""
    action_name = action.get("action", "")

    match action_name:
        case "navigate":
            url = action["url"]
            # Support relative URLs by joining to the site base
            if not url.startswith("http"):
                site = active_site()
                base = site.start_url.rstrip("/")
                url = f"{base}/{url.lstrip('/')}"
            await page.goto(url, wait_until="networkidle")

        case "click":
            await click_ref(page, int(action["ref"]))
            await page.wait_for_load_state("networkidle")

        case "fill":
            await fill_ref(page, int(action["ref"]), str(action.get("value", "")))

        case "select":
            await select_ref(page, int(action["ref"]), str(action.get("value", "")))

        case "scroll":
            direction = action.get("direction", "down")
            if direction == "down":
                await page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
            else:
                await page.evaluate("window.scrollBy(0, -window.innerHeight * 0.8)")

        case "go_back":
            await page.go_back(wait_until="networkidle")

        case "read_page":
            pass  # just re-snapshot below

        case _:
            return f"Unknown action '{action_name}'. Use one of: click, fill, select, navigate, scroll, go_back, read_page, done."

    page_snapshot = await snapshot(page)
    return f"Page updated:\n{page_snapshot}"
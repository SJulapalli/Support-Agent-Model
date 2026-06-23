from playwright.async_api import Page


async def get_page_text(page: Page) -> str:
    """Extract readable text and interactive elements from the current page."""
    return await page.evaluate("""() => {
        const interactive = Array.from(document.querySelectorAll('button, input, select, a[href]'))
            .map(el => {
                const tag = el.tagName.toLowerCase()
                const text = (el.innerText || '').trim() || el.value || el.placeholder || ''
                const testId = el.dataset.testid || ''
                const id = el.id || ''
                return '[' + tag + (id ? '#' + id : '') + (testId ? ' data-testid=' + testId : '') + ']: ' + text
            })
            .filter(s => s.length > 5)

        const bodyText = document.body.innerText.trim()
        const header = '=== Page: ' + document.title + ' (' + window.location.pathname + ') ==='
        return header + '\\n\\n' + bodyText + '\\n\\n=== Interactive Elements ===\\n' + interactive.join('\\n')
    }""")


async def click_by_test_id(page: Page, test_id: str) -> None:
    await page.click(f'[data-testid="{test_id}"]')


async def fill_by_test_id(page: Page, test_id: str, value: str) -> None:
    await page.fill(f'[data-testid="{test_id}"]', value)


async def click_by_text(page: Page, text: str) -> None:
    await page.get_by_text(text, exact=False).first.click()

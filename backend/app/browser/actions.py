from playwright.async_api import Page

MAX_INTERACTIVE = 60   # max elements listed in the snapshot
MAX_NAME_LEN = 80      # truncate accessible names beyond this


async def snapshot(page: Page) -> str:
    """
    Build a generic accessibility snapshot of the current page.

    Stamps transient data-agent-ref="N" on each interactive element (reassigned
    fresh every call) and returns a numbered list the agent acts on by ref index.

    Format per line:  [N] <role> "<accessible name>" (<state>)
    Followed by the page's visible body text for context.
    """
    result = await page.evaluate("""([maxInteractive, maxNameLen]) => {
        // --- Accessible-name resolution ---
        function getAccessibleName(el) {
            const ariaLabel = el.getAttribute('aria-label');
            if (ariaLabel && ariaLabel.trim()) return ariaLabel.trim();

            if (el.id) {
                const label = document.querySelector('label[for="' + el.id + '"]');
                if (label && label.innerText.trim()) return label.innerText.trim();
            }

            const wrappingLabel = el.closest('label');
            if (wrappingLabel) {
                const text = wrappingLabel.innerText.trim();
                if (text) return text;
            }

            const inner = (el.innerText || '').trim();
            if (inner) return inner;

            if (el.placeholder) return el.placeholder.trim();
            if (el.value) return el.value.toString().trim();
            if (el.title) return el.title.trim();

            const labelledBy = el.getAttribute('aria-labelledby');
            if (labelledBy) {
                const ref = document.getElementById(labelledBy);
                if (ref && ref.innerText.trim()) return ref.innerText.trim();
            }

            return '';
        }

        // --- Element role ---
        function getRole(el) {
            const explicit = el.getAttribute('role');
            if (explicit) return explicit;
            const tag = el.tagName.toLowerCase();
            const typeAttr = (el.getAttribute('type') || '').toLowerCase();
            if (tag === 'button') return 'button';
            if (tag === 'a') return 'link';
            if (tag === 'select') return 'select';
            if (tag === 'textarea') return 'textarea';
            if (tag === 'input') {
                if (typeAttr === 'checkbox') return 'checkbox';
                if (typeAttr === 'radio') return 'radio';
                if (typeAttr === 'submit' || typeAttr === 'button') return 'button';
                return 'input';
            }
            return tag;
        }

        // --- Element state ---
        function getState(el) {
            const parts = [];
            if (el.disabled) parts.push('disabled');
            if (el.checked !== undefined && el.checked) parts.push('checked');
            const tag = el.tagName.toLowerCase();
            if (tag === 'input' || tag === 'textarea') {
                const val = (el.value || '').trim();
                if (val) parts.push('value="' + val.slice(0, 40) + (val.length > 40 ? '…' : '') + '"');
            }
            if (tag === 'select') {
                const opts = Array.from(el.options).map(o => o.text).join(' | ');
                if (opts) parts.push('options: ' + opts);
                if (el.selectedIndex >= 0) parts.push('current: "' + el.options[el.selectedIndex].text + '"');
            }
            if (el.getAttribute('aria-selected') === 'true') parts.push('selected');
            const ariaExp = el.getAttribute('aria-expanded');
            if (ariaExp !== null) parts.push(ariaExp === 'true' ? 'expanded' : 'collapsed');
            return parts.length ? parts.join(', ') : '';
        }

        // --- Rough visibility check ---
        function isVisible(el) {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 && rect.height === 0) return false;
            const style = window.getComputedStyle(el);
            return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
        }

        // Clear any previous agent refs
        document.querySelectorAll('[data-agent-ref]').forEach(el => el.removeAttribute('data-agent-ref'));

        const INTERACTIVE = 'button, a[href], input, select, textarea, [role="button"], [role="link"], [role="checkbox"], [role="radio"], [role="menuitem"], [role="tab"], [tabindex]:not([tabindex="-1"])';
        const candidates = Array.from(document.querySelectorAll(INTERACTIVE))
            .filter(isVisible)
            .slice(0, maxInteractive);

        const lines = [];
        candidates.forEach((el, i) => {
            const ref = i + 1;
            el.setAttribute('data-agent-ref', String(ref));
            let name = getAccessibleName(el);
            if (name.length > maxNameLen) name = name.slice(0, maxNameLen) + '…';
            const role = getRole(el);
            const state = getState(el);
            const statePart = state ? ' (' + state + ')' : '';
            lines.push('[' + ref + '] ' + role + ' "' + name + '"' + statePart);
        });

        const header = '=== Page: ' + document.title + ' (' + window.location.pathname + ') ===';
        const bodyText = document.body.innerText.trim().slice(0, 3000);
        const interactive = '=== Interactive Elements (act on these by [ref]) ===\\n' + lines.join('\\n');
        return header + '\\n\\n' + bodyText + '\\n\\n' + interactive;
    }""", [MAX_INTERACTIVE, MAX_NAME_LEN])
    return result


async def _resolve_ref(page: Page, ref: int) -> None:
    exists = await page.evaluate(
        "(ref) => !!document.querySelector('[data-agent-ref=\"' + ref + '\"]')",
        ref,
    )
    if not exists:
        raise ValueError(f"reference [{ref}] not found on current page")


async def click_ref(page: Page, ref: int) -> None:
    await _resolve_ref(page, ref)
    await page.click(f'[data-agent-ref="{ref}"]')


async def fill_ref(page: Page, ref: int, value: str) -> None:
    await _resolve_ref(page, ref)
    await page.fill(f'[data-agent-ref="{ref}"]', value)


async def select_ref(page: Page, ref: int, value: str) -> None:
    await _resolve_ref(page, ref)
    selector = f'[data-agent-ref="{ref}"]'
    try:
        await page.select_option(selector, label=value)
    except Exception:
        await page.select_option(selector, value=value)
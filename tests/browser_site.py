"""Optional local browser regression check. Requires Playwright and a Chromium browser.

    python tests/browser_site.py --channel chrome

Loads file:// pages, blocks HTTP(S) requests, and never touches an existing browser session.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def run(channel: str | None, output: Path | None) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel=channel)
        try:
            context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
            context.route("https://**", lambda route: route.abort())
            context.route("http://**", lambda route: route.abort())
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            for relative in ("docs/index.html", "docs/en/index.html"):
                page.goto((ROOT / relative).as_uri())
                page.wait_for_load_state("networkidle")
                expect(page.locator("#pbBody tr")).to_have_count(64)
                windows = page.locator('[data-plat="windows"]')
                windows.focus()
                windows.press("Enter")
                expect(windows).to_be_focused()
                expect(windows).to_have_attribute("aria-pressed", "true")
                expect(page.locator("#pbBody tr")).to_have_count(24)
                page.locator("[data-clear]").click()
                expect(page.locator('#pbChips [data-cat=""]')).to_be_focused()

                search = page.locator("#pbSearch")
                search.fill("bitlocker")
                expect(page.locator('#pbBody tr[data-id="windows-bitlocker-recovery-triage"]')).to_be_visible()
                search.fill('<script>alert("test")</script>')
                expect(page.locator("#pbBody tr")).to_have_count(0)
                expect(page.locator("#pbEmpty")).to_be_visible()
                search.fill("")
                expect(page.locator("#pbBody tr")).to_have_count(64)

                first = page.locator(".pb-open").first
                first.click()
                expect(page.locator("#modal")).to_be_visible()
                expect(page.locator(".modal-x")).to_be_focused()
                page.keyboard.press("Shift+Tab")
                expect(page.locator("#modalSrc")).to_be_focused()
                page.keyboard.press("Escape")
                expect(first).to_be_focused()
                expect(page.locator("#modal")).to_be_hidden()

                tabs = page.locator("#installTabs .tab")
                tabs.first.focus()
                tabs.first.press("End")
                expect(tabs.last).to_be_focused()
                expect(tabs.last).to_have_attribute("aria-selected", "true")

                # Permission denial must fall back, and repeat clicks must restore the label.
                page.evaluate('''() => {
                    window.copyCalls = [];
                    document.execCommand = command => { window.copyCalls.push(command); return true; };
                    Object.defineProperty(navigator, 'clipboard', { configurable: true,
                        value: {writeText: () => Promise.reject(new Error('permission denied'))} });
                }''')
                copy = page.locator(".copybtn:visible").first
                label = copy.text_content().strip()
                copy.click()
                page.wait_for_timeout(150)
                copy.click()
                expect(copy).to_have_text(label, timeout=3000)
                assert page.evaluate("window.copyCalls.length") == 2
                assert page.locator('textarea[readonly]').count() == 0

                page.set_viewport_size({"width": 390, "height": 844})
                page.evaluate("window.scrollTo(0, 0)")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                if output:
                    output.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(output / ("mobile-en.png" if "/en/" in relative else "mobile-zh.png")))
                page.set_viewport_size({"width": 1280, "height": 900})
                print(f"PASS {relative}: filter focus, search, modal, tabs, repeat copy/fallback, mobile width")

            # Static fallback survives both disabled JavaScript and a missing data asset.
            for relative in ("docs/index.html", "docs/en/index.html"):
                fallback = browser.new_context(java_script_enabled=False)
                fallback.route("https://**", lambda route: route.abort())
                static_page = fallback.new_page()
                static_page.goto((ROOT / relative).as_uri())
                expect(static_page.locator("#pbBody tr")).to_have_count(64)
                expect(static_page.locator("#pbBody tr").first).to_be_visible()
                fallback.close()
            page.route("**/playbooks.js", lambda route: route.abort())
            page.goto((ROOT / "docs/index.html").as_uri())
            page.wait_for_load_state("networkidle")
            assert page.evaluate("typeof window.CRS_DATA") == "undefined"
            expect(page.locator("#pbBody tr")).to_have_count(64)
            page.unroute("**/playbooks.js")

            # Hover and keyboard focus are independent reasons to pause the prompt strip.
            page.emulate_media(reduced_motion="no-preference")
            page.goto((ROOT / "docs/index.html").as_uri())
            page.wait_for_load_state("networkidle")
            scroller = page.locator("#sayScroller")
            scroller.scroll_into_view_if_needed()
            scroller.hover()
            scroller.locator(".copybtn").first.focus()
            scroller.dispatch_event("pointerup")
            scroller.dispatch_event("pointerleave")
            before = scroller.evaluate("node => node.scrollLeft")
            page.wait_for_timeout(250)
            after = scroller.evaluate("node => node.scrollLeft")
            assert abs(after - before) < 1, "Prompt strip moved while keyboard focus remained inside"
            assert not errors, errors
            print("PASS static fallback, missing data asset, independent carousel pause; no page errors")
        finally:
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", help="Installed Chromium channel, e.g. chrome or msedge")
    parser.add_argument("--output", type=Path, help="Optional mobile screenshot directory")
    args = parser.parse_args()
    run(args.channel, args.output)

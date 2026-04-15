from __future__ import annotations

import argparse
from playwright.sync_api import sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure dashboard load time with Playwright.")
    parser.add_argument("--url", default="http://localhost:5173/dashboard")
    parser.add_argument("--target-ms", type=float, default=2000.0)
    parser.add_argument("--headless", action="store_true", default=False)
    args = parser.parse_args()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=args.headless)
        page = browser.new_page()
        page.goto(args.url, wait_until="load")
        page.wait_for_load_state("networkidle")
        duration = page.evaluate(
            """
            () => {
              const navigation = performance.getEntriesByType('navigation')[0];
              return navigation ? navigation.duration : 0;
            }
            """
        )
        browser.close()

    print(f"Dashboard load duration: {duration:.2f}ms (target {args.target_ms:.2f}ms)")
    if duration > args.target_ms:
        print("FAILED: dashboard load exceeded the target.")
        return 1

    print("PASSED: dashboard load met the target.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

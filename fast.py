import re
from playwright.sync_api import sync_playwright
import time


def to_bps(value, unit):
    if unit == "gbps":
        return value * 1_000_000_000
    elif unit == "mbps":
        return value * 1_000_000
    elif unit == "kbps":
        return value * 1_000
    elif unit == "bps":
        return value
    else:
        raise RuntimeError(f"Unknown download unit {unit}")

def measure():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto("https://fast.com")
        page.wait_for_load_state('networkidle', timeout=120_000)


        down = int(page.locator("#speed-value").inner_text().strip())
        up = int(page.locator("#upload-value").inner_text().strip())
        down_units = page.locator('#speed-units').inner_text().strip().lower()
        up_units = page.locator('#upload-units').inner_text().strip().lower()

        latency = int(page.locator('#latency-value').inner_text().strip())

        adj_down = to_bps(down, down_units)
        adj_up = to_bps(up, up_units)

        return {"upload_bitrate": adj_up, "download_bitrate": adj_down, "latency": latency}


if __name__ == '__main__':
    print(measure())
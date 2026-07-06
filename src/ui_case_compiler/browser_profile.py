from __future__ import annotations

from typing import Any

REALISTIC_CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

BROWSER_CONTEXT_OPTIONS: dict[str, Any] = {
    "user_agent": REALISTIC_CHROME_USER_AGENT,
    "viewport": {"width": 1920, "height": 1080},
    "locale": "zh-CN",
    "timezone_id": "Asia/Shanghai",
    "color_scheme": "light",
    "device_scale_factor": 1,
    "extra_http_headers": {"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
}

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
window.chrome = window.chrome || { runtime: {} };
"""


def browser_launch_args(browser_name: str) -> list[str]:
    if browser_name != "chromium":
        return []
    return [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
    ]

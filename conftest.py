"""
Step 4 (guide): on test failure, open a GitHub issue.

The PDF shows try/except inside one test + subprocess. A pytest hook runs after
every test and only acts when the test failed — same idea, less duplication.

Requires GITHUB_TOKEN and GITHUB_REPO (see create_issue.py).
Optional: OPENAI_API_KEY for AI issue title and summary (utils.ai_helper).
"""

import os
import re
import uuid
from typing import Optional

import pytest

from create_issue import (
    create_issue,
    format_issue,
    issue_exists_for_nodeid,
    upload_png_to_repo,
)
from utils.ai_helper import generate_ai_summary


def _try_screenshot_url(item) -> Optional[str]:
    """Capture Playwright PNG and push to repo; returns raw URL or None."""
    page = item.funcargs.get("page")
    if page is None or not hasattr(page, "screenshot"):
        return None
    try:
        png = page.screenshot(type="png", full_page=True)
    except Exception as exc:
        print(f"[conftest] Screenshot failed: {exc}")
        return None
    safe = re.sub(r"[^\w\-.]+", "_", item.nodeid)[:80]
    remote = f"screenshots/auto-fail-{uuid.uuid4().hex[:8]}-{safe}.png"
    try:
        return upload_png_to_repo(png, remote)
    except Exception as exc:
        print(f"[conftest] GitHub upload failed: {exc}")
        return None


@pytest.fixture
def page():
    """Playwright page; use this in UI tests so failures can attach a screenshot."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page()
        yield pg
        browser.close()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()

    if rep.when != "call" or not rep.failed:
        return

    if not os.environ.get("GITHUB_TOKEN") or not os.environ.get("GITHUB_REPO"):
        return

    error_text = rep.longreprtext or ""
    ai_title, ai_summary = generate_ai_summary(item.name, error_text)
    screenshot_url = _try_screenshot_url(item)
    body = format_issue(
        test_name=item.name,
        nodeid=item.nodeid,
        summary=ai_summary,
        error_text=error_text,
        screenshot_url=screenshot_url,
    )

    if issue_exists_for_nodeid(item.nodeid):
        print("Issue already exists, skipping...")
    else:
        r = create_issue(ai_title, body)
        issue_url = r.json().get("html_url")
        print(f"Issue created: {issue_url}")

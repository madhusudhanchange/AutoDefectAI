"""
Step 2 (guide): intentional failing UI check — Google’s title does not contain "Bing".
Uses the ``page`` fixture from conftest so failures can attach a screenshot to GitHub.
Run: pytest test_sample.py
"""


def test_google_title(page):
    page.goto("https://www.google.com")
    # Intentionally wrong: fails so you can wire GitHub issue creation (Steps 3-4).
    assert "Bing" in page.title()

import os
from typing import Dict, List
from textwrap import dedent
from urllib.parse import urlparse

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def sanitize_filename(domain: str) -> str:
    return domain.replace(".", "_").replace("-", "_")

def _choose_links(links: List[str], max_n: int) -> List[str]:
    if max_n <= 0:
        return []
    return links[:max_n]

def _href_selector(href: str, strategy: str) -> str:
    """
    Build a CSS selector that will be robust for relative/absolute links.
    - contains: a[href*="...path-or-full..."]
    - exact:    a[href="...full..."]
    We default to matching on the URL's path component when possible for robustness.
    """
    parsed = urlparse(href)
    target = href
    if strategy == "contains":
        # Prefer matching by path when available (more robust to absolute/relative differences)
        if parsed.path:
            target = parsed.path
        # CSS contains
        return f'a[href*="{target}"]'
    else:
        # exact match on serialized href
        return f'a[href="{href}"]'

def generate_pytest_file(
    pages: Dict[str, Dict],
    output_dir: str,
    file_prefix: str,
    include_prints: bool,
    include_comments: bool,
    domain: str,
    link_assertions_max: int = 10,
    link_match_strategy: str = "contains",
) -> str:
    ensure_dir(output_dir)
    safe = sanitize_filename(domain)
    fname = f"{file_prefix}{safe}.py"
    fpath = os.path.join(output_dir, fname)

    header_comments = dedent(f"""
    # Auto-generated Selenium tests for {domain}
    # Validations include:
    #  - <title> and first <h1>
    #  - A sample of outbound links (presence via CSS selector)
    #  - Existence of key elements (form/button/nav) if they were seen during crawl
    """)

    imports = dedent("""
    import pytest
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    """)

    helpers = dedent("""
    def wait_ready(driver, timeout=15):
        # Wait for DOM readyState to be 'complete'
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    def first_h1_text(driver):
        try:
            el = driver.find_elements(By.TAG_NAME, "h1")
            if not el:
                return ""
            return el[0].text.strip()
        except Exception:
            return ""
    """)

    body_lines = [header_comments, imports, helpers]

    for i, (url, info) in enumerate(pages.items(), start=1):
        test_name = f"test_page_{i:03d}"

        comment_block = ""
        if include_comments:
            comment_block = (
                f"    # Test URL: {url}\n"
                f"    # Validates:\n"
                f"    #   - Page title / first <h1>\n"
                f"    #   - Presence of up to {link_assertions_max} outbound links collected during crawl\n"
                f"    #   - Key elements (form/button/nav) if observed in crawl\n"
            )

        print_block = ""
        if include_prints:
            print_block = (
                f"    print('[TEST] Visiting:', {url!r})\n"
                f"    print('[TEST] Title seen during crawl:', {info.get('title','')!r})\n"
                f"    print('[TEST] H1 seen during crawl:', {info.get('h1','')!r})\n"
                f"    print('[TEST] Links sampled:', {min(len(info.get('out_links', [])), link_assertions_max)})\n"
                f"    print('[TEST] Observed counts: forms=', {info.get('form_count',0)}, "
                f"buttons=", {info.get('button_count',0)}, " nav=", {info.get('nav_count',0)})\n"
            )

        expected_title = (info.get("title") or "").strip()
        expected_h1 = (info.get("h1") or "").strip()

        links = info.get("out_links", []) or []
        sampled = _choose_links(links, link_assertions_max)

        # Build link selectors
        selector_lines = []
        for href in sampled:
            selector = _href_selector(href, link_match_strategy)
            # indent with 8 spaces inside the function
            selector_lines.append(f'        ("{href}", "{selector}"),')
        selectors_block = "[]"
        if selector_lines:
            selectors_block = "[\n" + "\n".join(selector_lines) + "\n    ]"

        # Booleans: only assert if crawler saw any
        saw_form = bool(info.get("form_count", 0))
        saw_button = bool(info.get("button_count", 0))
        saw_nav = bool(info.get("nav_count", 0))

        test_code = f"""
def {test_name}(driver):
{comment_block}{print_block}    driver.get({url!r})
    wait_ready(driver)

    # Title / H1 checks
    title_txt = (driver.title or "").strip()
    if {bool(expected_title)}:
        assert title_txt, "Missing <title> on page"
    else:
        assert title_txt is not None

    h1_txt = first_h1_text(driver)
    if {bool(expected_h1)}:
        assert h1_txt, "Missing <h1> on page (was present during crawl)"

    # Outbound link presence checks (sample)
    link_expectations = {selectors_block}
    for _href, _selector in link_expectations:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, _selector)
            assert elems, f"Expected link not found: {{_href}} (selector={{_selector}})"
        except Exception as e:
            raise AssertionError(f"Error checking link {{_href}}: {{e}}")

    # Key element existence checks (only if seen during crawl)
    if {saw_form}:
        assert driver.find_elements(By.TAG_NAME, "form"), "Expected a <form> (seen during crawl) but none found"
    if {saw_button}:
        assert driver.find_elements(By.TAG_NAME, "button"), "Expected a <button> (seen during crawl) but none found"
    if {saw_nav}:
        assert driver.find_elements(By.TAG_NAME, "nav"), "Expected a <nav> (seen during crawl) but none found"
"""
        body_lines.append(test_code)

    with open(fpath, "w", encoding="utf-8") as f:
        f.write("\n".join(body_lines))

    return fpath

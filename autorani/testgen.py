import os
from typing import Dict
from textwrap import dedent

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def sanitize_filename(domain: str) -> str:
    return domain.replace(".", "_").replace("-", "_")

def generate_pytest_file(
    pages: Dict[str, Dict],
    output_dir: str,
    file_prefix: str,
    include_prints: bool,
    include_comments: bool,
    domain: str
) -> str:
    ensure_dir(output_dir)
    safe = sanitize_filename(domain)
    fname = f"{file_prefix}{safe}.py"
    fpath = os.path.join(output_dir, fname)

    header_comments = dedent(f"""
    # Auto-generated Selenium tests for {domain}
    # Each test opens the page in a real browser and validates key markers discovered during crawl.
    # Verbose by design: prints + comments make debugging easy.
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
                f"    #   - Page is reachable in a real browser\n"
                f"    #   - <title> exists if we saw one during crawl\n"
                f"    #   - <h1> exists if we saw one during crawl\n"
            )

        print_block = ""
        if include_prints:
            print_block = (
                f"    print('[TEST] Visiting:', {url!r})\n"
                f"    print('[TEST] Expected status (from crawl):', {info.get('status')!r})\n"
                f"    print('[TEST] Expected title snippet:', {info.get('title','')!r})\n"
                f"    print('[TEST] Expected h1 snippet:', {info.get('h1','')!r})\n"
            )

        expected_title = (info.get("title") or "").strip()
        expected_h1 = (info.get("h1") or "").strip()

        test_code = f"""
def {test_name}(driver):
{comment_block}{print_block}    driver.get({url!r})
    wait_ready(driver)

    # Title checks
    title_txt = (driver.title or "").strip()
    if {bool(expected_title)}:
        assert title_txt, "Missing <title> on page"
    else:
        assert title_txt is not None

    # H1 checks
    h1_txt = first_h1_text(driver)
    if {bool(expected_h1)}:
        assert h1_txt, "Missing <h1> on page (was present during crawl)"
"""
        body_lines.append(test_code)

    with open(fpath, "w", encoding="utf-8") as f:
        f.write("\n".join(body_lines))

    return fpath

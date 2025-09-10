import requests
from bs4 import BeautifulSoup
from typing import Dict, Set, List
from .utils import is_same_domain, normalize_link

class Crawler:
    def __init__(self, base_url: str, *, max_pages: int | None, timeout_sec: int, same_domain_only: bool, user_agent: str):
        self.base_url = base_url.rstrip("/")
        self.max_pages = max_pages
        self.timeout = timeout_sec
        self.same_domain_only = same_domain_only
        self.headers = {"User-Agent": user_agent}
        # absolute hard safety cap to avoid by-accident huge crawls
        self.hard_cap = 200

    def crawl(self) -> Dict[str, Dict]:
        seen: Set[str] = set()
        queue: List[str] = [self.base_url]
        results: Dict[str, Dict] = {}

        def should_visit(u: str) -> bool:
            if self.same_domain_only and not is_same_domain(self.base_url, u):
                return False
            if u in seen:
                return False
            if self.max_pages is not None and len(seen) >= self.max_pages:
                return False
            if len(seen) >= self.hard_cap:
                return False
            return True

        while queue:
            url = queue.pop(0)
            if not should_visit(url):
                continue
            try:
                resp = requests.get(url, headers=self.headers, timeout=self.timeout)
                status = resp.status_code
                html = resp.text if "text/html" in resp.headers.get("Content-Type", "") else ""
                soup = BeautifulSoup(html, "html.parser") if html else None
                title = (soup.title.string.strip() if soup and soup.title else "")
                h1 = (soup.find("h1").get_text(strip=True) if soup and soup.find("h1") else "")

                links = []
                if soup:
                    for a in soup.find_all("a", href=True):
                        abs_url = normalize_link(url, a["href"])
                        links.append(abs_url)
                        if should_visit(abs_url):
                            queue.append(abs_url)

                results[url] = {
                    "status": status,
                    "title": title,
                    "h1": h1,
                    "out_links": links[:50],  # keep it lightweight
                }
                seen.add(url)
            except requests.RequestException as e:
                results[url] = {"status": None, "error": str(e), "out_links": []}
                seen.add(url)
        return results

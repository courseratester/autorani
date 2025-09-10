from urllib.parse import urljoin, urlparse

def is_same_domain(base_url: str, candidate: str) -> bool:
    b = urlparse(base_url)
    c = urlparse(candidate)
    return (c.netloc or b.netloc) == b.netloc

def normalize_link(base_url: str, href: str) -> str:
    return urljoin(base_url, href)

def domain_of(url: str) -> str:
    return urlparse(url).netloc

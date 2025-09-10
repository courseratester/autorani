import os
import yaml
import pytest

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.firefox import GeckoDriverManager

CONFIG_PATH = os.path.join("config", "settings.yaml")

def load_cfg():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

@pytest.fixture(scope="session")
def driver():
    cfg = load_cfg()
    s = (cfg.get("selenium") or {})
    browser = (s.get("browser") or "chrome").lower()
    headless = bool(s.get("headless", True))
    window_size = (s.get("window_size") or "1366,900")
    page_load_timeout = int(s.get("page_load_timeout_sec", 20))
    implicit_wait = int(s.get("implicit_wait_sec", 2))

    if browser == "chrome":
        opts = ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument(f"--window-size={window_size}")
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=opts)
    elif browser == "edge":
        opts = EdgeOptions()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument(f"--window-size={window_size}")
        driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=opts)
    elif browser == "firefox":
        opts = FirefoxOptions()
        if headless:
            opts.add_argument("-headless")
        driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=opts)
        if window_size and "," in window_size:
            w, h = window_size.split(",")
            driver.set_window_size(int(w), int(h))
    else:
        raise ValueError(f"Unsupported browser: {browser}")

    driver.set_page_load_timeout(page_load_timeout)
    driver.implicitly_wait(implicit_wait)

    yield driver
    driver.quit()

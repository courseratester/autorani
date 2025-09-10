import os
import yaml
import json
from typing import Any, Dict

DEFAULT_STATE_PATH = os.path.join("config", "settings.yaml")
DEFAULT_STATE_PATH = os.path.join("config", "settings.yaml")
LAST_CRAWL_PATH = os.path.join("config", "last_crawl.json")

class YAMLStore:
    """
    Basic YAML-backed store. Also holds crawl results in-memory
    for this run (saved separately if needed).
    """
    def __init__(self, settings_path: str = DEFAULT_STATE_PATH):
        self.settings_path = settings_path
        with open(settings_path, "r", encoding="utf-8") as f:
            self.settings = yaml.safe_load(f) or {}

        self.crawl_results: Dict[str, Dict[str, Any]] = {}

    def get(self, dotted: str, default=None):
        node = self.settings
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted: str, value):
        node = self.settings
        parts = dotted.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = value

    def save(self):
        with open(self.settings_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.settings, f, sort_keys=False, allow_unicode=True)

    def put_page(self, url: str, info: Dict[str, Any]):
        self.crawl_results[url] = info

    def pages(self):
        return self.crawl_results

    def save_crawl(self):
        os.makedirs(os.path.dirname(LAST_CRAWL_PATH), exist_ok=True)
        with open(LAST_CRAWL_PATH, "w", encoding="utf-8") as f:
            json.dump(self.crawl_results, f, ensure_ascii=False, indent=2)

    def load_crawl(self) -> Dict[str, Dict[str, Any]]:
        try:
            with open(LAST_CRAWL_PATH, "r", encoding="utf-8") as f:
                self.crawl_results = json.load(f)
        except FileNotFoundError:
            self.crawl_results = {}
        return self.crawl_results

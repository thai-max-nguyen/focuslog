from typing import Optional


DEFAULT_RULES = [
    {"app_name": "Code", "url_contains": None, "category": "Work"},
    {"app_name": "Xcode", "url_contains": None, "category": "Work"},
    {"app_name": "Terminal", "url_contains": None, "category": "Work"},
    {"app_name": "iTerm", "url_contains": None, "category": "Work"},
    {"app_name": "Cursor", "url_contains": None, "category": "Work"},
    {"app_name": "PyCharm", "url_contains": None, "category": "Work"},
    {"app_name": "IntelliJ", "url_contains": None, "category": "Work"},
    {"app_name": "Slack", "url_contains": None, "category": "Communication"},
    {"app_name": "Mail", "url_contains": None, "category": "Communication"},
    {"app_name": "Zoom", "url_contains": None, "category": "Communication"},
    {"app_name": "Teams", "url_contains": None, "category": "Communication"},
    {"app_name": "Discord", "url_contains": None, "category": "Communication"},
    {"app_name": "Music", "url_contains": None, "category": "Entertainment"},
    {"app_name": "Spotify", "url_contains": None, "category": "Entertainment"},
    {"app_name": "Safari", "url_contains": "youtube.com", "category": "Entertainment"},
    {"app_name": "Chrome", "url_contains": "youtube.com", "category": "Entertainment"},
    {"app_name": "Safari", "url_contains": "netflix.com", "category": "Entertainment"},
    {"app_name": "Safari", "url_contains": "github.com", "category": "Work"},
    {"app_name": "Chrome", "url_contains": "github.com", "category": "Work"},
    {"app_name": "YouTube", "url_contains": None, "category": "Entertainment"},
    {"app_name": "Netflix", "url_contains": None, "category": "Entertainment"},
    {"app_name": "Books", "url_contains": None, "category": "Learning"},
    {"app_name": "Kindle", "url_contains": None, "category": "Learning"},
]

CATEGORY_COLORS = {
    "Work": "#4f86f7",
    "Communication": "#f7c948",
    "Learning": "#4ecdc4",
    "Entertainment": "#ff6b6b",
    "Unknown": "#9e9e9e",
}


class Classifier:
    def __init__(self, rules: list[dict]):
        self.rules = rules

    @staticmethod
    def _url_matches(url_contains: str, title_lower: str) -> bool:
        """Check if the url_contains pattern matches the window title.

        Supports both exact substring match and domain-stem matching
        so that a rule like 'github.com' also matches 'GitHub - repo'.
        """
        pattern = url_contains.lower()
        if pattern in title_lower:
            return True
        # Try matching just the domain stem (strip TLD like .com/.net/…)
        stem = pattern.split(".")[0]
        if stem and stem in title_lower:
            return True
        return False

    def classify(self, app_name: str, window_title: str) -> str:
        title_lower = window_title.lower()
        app_lower = app_name.lower()

        # URL-specific rules first (more specific wins)
        for rule in self.rules:
            rule_app = (rule.get("app_name") or "").lower()
            url_contains = rule.get("url_contains")
            if not url_contains:
                continue
            if rule_app and rule_app not in app_lower:
                continue
            if self._url_matches(url_contains, title_lower):
                return rule["category"]

        # App-name rules
        for rule in self.rules:
            rule_app = (rule.get("app_name") or "").lower()
            url_contains = rule.get("url_contains")
            if url_contains:
                continue
            if rule_app and rule_app in app_lower:
                return rule["category"]

        return "Unknown"

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

BROWSER_APPS = {"arc", "chrome", "safari", "firefox", "edge", "brave", "opera", "vivaldi"}

# Titles that look like valid resolved names but are actually generic browser states
_GENERIC_BROWSER_TITLES = {
    "new tab", "arc", "chrome", "safari", "firefox", "edge", "brave",
    "opera", "vivaldi", "untitled", "newtab", "loading...", "",
}

KNOWN_SERVICES = {
    # Productivity / Work
    "jira": "Jira",
    "confluence": "Confluence",
    "notion": "Notion",
    "figma": "Figma",
    "figjam": "Figma",
    "linear": "Linear",
    "trello": "Trello",
    "asana": "Asana",
    "monday": "Monday",
    "miro": "Miro",
    "loom": "Loom",
    "github": "GitHub",
    "gitlab": "GitLab",
    "bitbucket": "Bitbucket",
    "vercel": "Vercel",
    "netlify": "Netlify",
    "railway": "Railway",
    "render": "Render",
    "aws": "AWS",
    "datadog": "Datadog",
    "sentry": "Sentry",
    "hubspot": "HubSpot",
    "salesforce": "Salesforce",
    "clickup": "ClickUp",
    "basecamp": "Basecamp",
    "airtable": "Airtable",
    # Analytics / Infra
    "tableau": "Tableau",
    "metabase": "Metabase",
    "grafana": "Grafana",
    "superset": "Superset",
    "kibana": "Kibana",
    "posthog": "PostHog",
    "mixpanel": "Mixpanel",
    "amplitude": "Amplitude",
    # AI Tools
    "claude": "Claude",
    "chatgpt": "ChatGPT",
    "gemini": "Google Gemini",
    "notebooklm": "NotebookLM",
    "grok": "Grok",
    "ollama": "Ollama",
    "perplexity": "Perplexity",
    "cursor": "Cursor",
    "copilot": "GitHub Copilot",
    # Communication
    "microsoft teams": "Microsoft Teams",
    "slack": "Slack",
    "discord": "Discord",
    "gmail": "Gmail",
    "outlook": "Outlook",
    "google meet": "Google Meet",
    "linkedin": "LinkedIn",
    "telegram": "Telegram",
    "whatsapp": "WhatsApp",
    "zalo": "Zalo",
    # Google Suite
    "google docs": "Google Docs",
    "google sheets": "Google Sheets",
    "google slides": "Google Slides",
    "google drive": "Google Drive",
    "google calendar": "Google Calendar",
    "sharepoint": "SharePoint",
    "onedrive": "OneDrive",
    # Entertainment / Social
    "youtube": "YouTube",
    "netflix": "Netflix",
    "facebook": "Facebook",
    "twitter": "Twitter",
    "x.com": "X (Twitter)",
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "reddit": "Reddit",
    "twitch": "Twitch",
    "spotify": "Spotify",
    # Learning
    "stack overflow": "Stack Overflow",
    "stackoverflow": "Stack Overflow",
    "behance": "Behance",
    "monkeytype": "Monkeytype",
    "udemy": "Udemy",
    "coursera": "Coursera",
    "medium": "Medium",
    "substack": "Substack",
    "wikipedia": "Wikipedia",
    # Developer tools / docs
    "localhost": "Localhost",
    "127.0.0.1": "Localhost",
    "mdn": "MDN Docs",
    "developer.mozilla": "MDN Docs",
    "docs.": "Documentation",
    "npmjs": "npm",
    "pypi": "PyPI",
    "docker": "Docker Hub",
    "readthedocs": "ReadTheDocs",
    # Vietnamese / ZaloPay ecosystem
    "zalopay": "ZaloPay",
    "zalo": "Zalo",
    "vnpay": "VNPay",
    "momo": "MoMo",
    "vietcombank": "Vietcombank",
    "techcombank": "Techcombank",
    "acb": "ACB",
    "vnexpress": "VnExpress",
    "dantri": "Dân Trí",
    "baomoi": "Báo Mới",
}

VALID_CATEGORIES = {"Work", "Communication", "Learning", "Entertainment", "Unknown"}

def _r(app: str, cat: str) -> dict:
    return {"app_name": app, "url_contains": None, "category": cat}


DEFAULT_RULES = [
    # --- Dev tools ---
    _r("Code", "Work"), _r("Xcode", "Work"), _r("Cursor", "Work"),
    _r("PyCharm", "Work"), _r("IntelliJ", "Work"), _r("WebStorm", "Work"),
    _r("GoLand", "Work"), _r("CLion", "Work"), _r("RubyMine", "Work"),
    _r("Android Studio", "Work"), _r("Sublime Text", "Work"), _r("Vim", "Work"),
    _r("Neovim", "Work"), _r("Emacs", "Work"), _r("Nova", "Work"),
    _r("Zed", "Work"),
    # --- Terminals ---
    _r("Terminal", "Work"), _r("iTerm", "Work"), _r("iTerm2", "Work"),
    _r("Alacritty", "Work"), _r("Warp", "Work"), _r("Ghostty", "Work"),
    _r("Kitty", "Work"),
    # --- Project / knowledge management ---
    _r("Jira", "Work"), _r("Confluence", "Work"), _r("Notion", "Work"),
    _r("Linear", "Work"), _r("Figma", "Work"), _r("FigJam", "Work"),
    _r("Miro", "Work"), _r("Trello", "Work"), _r("Asana", "Work"),
    _r("ClickUp", "Work"), _r("Monday", "Work"), _r("Loom", "Work"),
    _r("Obsidian", "Work"), _r("Logseq", "Work"), _r("Roam Research", "Work"),
    _r("Bear", "Work"), _r("Craft", "Work"), _r("Coda", "Work"),
    _r("Airtable", "Work"),
    # --- Version control / DevOps ---
    _r("GitHub", "Work"), _r("GitLab", "Work"), _r("Bitbucket", "Work"),
    _r("Fork", "Work"), _r("Tower", "Work"), _r("SourceTree", "Work"),
    _r("GitKraken", "Work"),
    _r("Vercel", "Work"), _r("Netlify", "Work"), _r("AWS", "Work"),
    _r("Datadog", "Work"), _r("Sentry", "Work"), _r("Grafana", "Work"),
    _r("Metabase", "Work"), _r("Tableau", "Work"),
    # --- AI / productivity tools ---
    _r("Claude", "Work"), _r("ChatGPT", "Work"), _r("Ollama", "Work"),
    _r("Perplexity", "Work"),
    # --- Design ---
    _r("Sketch", "Work"), _r("Adobe Photoshop", "Work"),
    _r("Adobe Illustrator", "Work"), _r("Adobe XD", "Work"),
    _r("Canva", "Work"), _r("Pixelmator Pro", "Work"),
    # --- Microsoft Office ---
    _r("Microsoft Excel", "Work"), _r("Microsoft Word", "Work"),
    _r("Microsoft PowerPoint", "Work"), _r("Microsoft Outlook", "Communication"),
    _r("Microsoft OneNote", "Work"), _r("Microsoft Teams", "Communication"),
    # --- Apple iWork ---
    _r("Numbers", "Work"), _r("Pages", "Work"), _r("Keynote", "Work"),
    # --- Apple system apps ---
    _r("Finder", "Work"), _r("Calendar", "Work"), _r("Reminders", "Work"),
    _r("Notes", "Work"), _r("Preview", "Work"), _r("TextEdit", "Work"),
    _r("Activity Monitor", "Work"), _r("Terminal", "Work"),
    _r("System Settings", "Work"), _r("System Preferences", "Work"),
    # --- Business tools ---
    _r("HubSpot", "Work"), _r("Salesforce", "Work"),
    # --- Communication ---
    _r("Slack", "Communication"), _r("Mail", "Communication"),
    _r("Zoom", "Communication"), _r("Discord", "Communication"),
    _r("Gmail", "Communication"), _r("Google Meet", "Communication"),
    _r("LinkedIn", "Communication"), _r("Telegram", "Communication"),
    _r("WhatsApp", "Communication"), _r("Zalo", "Communication"),
    _r("Skype", "Communication"), _r("FaceTime", "Communication"),
    _r("Messages", "Communication"), _r("Spark", "Communication"),
    _r("Mimestream", "Communication"), _r("Superhuman", "Communication"),
    # --- Entertainment ---
    _r("Music", "Entertainment"), _r("Spotify", "Entertainment"),
    _r("YouTube", "Entertainment"), _r("Netflix", "Entertainment"),
    _r("Reddit", "Entertainment"), _r("Twitter", "Entertainment"),
    _r("Twitch", "Entertainment"), _r("VLC", "Entertainment"),
    _r("IINA", "Entertainment"), _r("Infuse", "Entertainment"),
    # --- Learning ---
    _r("Books", "Learning"), _r("Kindle", "Learning"),
    _r("Stack Overflow", "Learning"), _r("Dash", "Learning"),
    _r("Simulator", "Work"),
    # --- Utility (track but mark work) ---
    _r("iScreen Shoter", "Work"), _r("CleanMyMac", "Work"),
    _r("1Password", "Work"), _r("Raycast", "Work"), _r("Alfred", "Work"),
    _r("Bartender", "Work"), _r("Proxyman", "Work"), _r("Paw", "Work"),
    _r("TablePlus", "Work"), _r("Postico", "Work"),
    _r("Sequel Pro", "Work"), _r("DB Browser for SQLite", "Work"),
    _r("Insomnia", "Work"), _r("Postman", "Work"),
    _r("Docker", "Work"), _r("Orbstack", "Work"),
    _r("Timelines", "Work"),
]

CATEGORY_COLORS = {
    "Work": "#4f86f7",
    "Communication": "#f7c948",
    "Learning": "#4ecdc4",
    "Entertainment": "#ff6b6b",
    "Unknown": "#9e9e9e",
}

DATA_DIR = os.path.expanduser("~/Library/Application Support/focuslog")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
AI_RULES_PATH = os.path.join(DATA_DIR, "ai_rules.json")


def _load_api_key() -> str:
    """Read ANTHROPIC_API_KEY from env or config file."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f).get("anthropic_api_key", "")
    except Exception:
        return ""


def _load_ai_rules() -> dict[str, str]:
    """Load AI-learned app→category mappings."""
    try:
        with open(AI_RULES_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_ai_rules(ai_rules: dict[str, str]):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(AI_RULES_PATH, "w") as f:
        json.dump(ai_rules, f, indent=2)


def _ask_claude(app_name: str, window_title: str) -> str:
    """Call Claude Haiku to categorize an unknown app. Returns a category string."""
    try:
        import anthropic
        key = _load_api_key()
        if not key:
            return "Unknown"

        client = anthropic.Anthropic(api_key=key)
        prompt = (
            f'Classify this app/website into exactly one category.\n\n'
            f'App name: {app_name}\n'
            f'Window title: {window_title}\n\n'
            f'Categories (pick one):\n'
            f'- Work: productivity tools, dev tools, project management, coding, design, business\n'
            f'- Communication: email, chat, video calls, social professional\n'
            f'- Learning: courses, docs, reading, research, tutorials\n'
            f'- Entertainment: videos, games, music, social media for leisure\n'
            f'- Unknown: cannot determine\n\n'
            f'Reply with only the category name, nothing else.'
        )
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        category = response.content[0].text.strip()
        if category not in VALID_CATEGORIES:
            return "Unknown"
        return category
    except Exception as e:
        logger.warning(f"AI categorization failed for {app_name!r}: {e}")
        return "Unknown"


class Classifier:
    def __init__(self, rules: list[dict]):
        self.rules = rules
        self._ai_rules: dict[str, str] = _load_ai_rules()
        self._pending: set[str] = set()
        self._lock = threading.Lock()

    @staticmethod
    def _url_matches(url_contains: str, title_lower: str) -> bool:
        pattern = url_contains.lower()
        if pattern in title_lower:
            return True
        stem = pattern.split(".")[0]
        if stem and stem in title_lower:
            return True
        return False

    @staticmethod
    def resolve_app_name(app_name: str, window_title: str, url: str = "") -> str:
        """For browser apps, extract the actual service name.

        Resolution priority:
          1. URL (AXDocument) — exact match against KNOWN_SERVICES keys in the full URL
          2. URL hostname — clean domain as fallback
          3. Window title KNOWN_SERVICES keyword scan
          4. Title separator extraction
          5. App name fallback
        """
        if app_name.lower() not in BROWSER_APPS:
            return app_name

        # --- 1 & 2: URL-based resolution (most accurate) ---
        if url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                hostname = (parsed.hostname or "").lower().removeprefix("www.")
                full_url_lower = url.lower()

                # Check KNOWN_SERVICES against the full URL (catches /jira/ paths etc.)
                for key in sorted(KNOWN_SERVICES, key=len, reverse=True):
                    if key in full_url_lower:
                        return KNOWN_SERVICES[key]

                # Return clean hostname (e.g. "metabase.zalopay.vn", "localhost:3000")
                if hostname and hostname not in _GENERIC_BROWSER_TITLES:
                    port = parsed.port
                    return f"{hostname}:{port}" if port else hostname
            except Exception:
                pass

        # --- 3: Title KNOWN_SERVICES scan ---
        if window_title:
            title_lower = window_title.lower()
            for key in sorted(KNOWN_SERVICES, key=len, reverse=True):
                if key in title_lower:
                    return KNOWN_SERVICES[key]

            # --- 4: Separator extraction ---
            for sep in (" - ", " | ", " – ", " — ", " · "):
                parts = window_title.split(sep)
                if len(parts) > 1:
                    last = parts[-1].strip()
                    if last and last.lower() not in _GENERIC_BROWSER_TITLES:
                        return last

        return app_name

    def _classify_static(self, app_name: str, window_title: str) -> str:
        """Rule-based classification only."""
        title_lower = window_title.lower()
        app_lower = app_name.lower()

        for rule in self.rules:
            rule_app = (rule.get("app_name") or "").lower()
            url_contains = rule.get("url_contains")
            if not url_contains:
                continue
            if rule_app and rule_app not in app_lower:
                continue
            if self._url_matches(url_contains, title_lower):
                return rule["category"]

        for rule in self.rules:
            rule_app = (rule.get("app_name") or "").lower()
            url_contains = rule.get("url_contains")
            if url_contains:
                continue
            if rule_app and rule_app in app_lower:
                return rule["category"]

        return "Unknown"

    def _learn_async(self, app_name: str, window_title: str):
        """Ask Claude in background, save result for future sessions."""
        def _run():
            category = _ask_claude(app_name, window_title)
            with self._lock:
                self._ai_rules[app_name] = category
                self._pending.discard(app_name)
            _save_ai_rules(self._ai_rules)
            logger.info(f"AI classified {app_name!r} → {category}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def classify(self, app_name: str, window_title: str) -> str:
        # 1. Static rules
        category = self._classify_static(app_name, window_title)
        if category != "Unknown":
            return category

        # 2. AI-learned rules
        with self._lock:
            if app_name in self._ai_rules:
                return self._ai_rules[app_name]

            # 3. Trigger background AI classification (once per unknown app)
            if app_name not in self._pending and app_name not in ("Unknown", ""):
                self._pending.add(app_name)
                self._learn_async(app_name, window_title)

        return "Unknown"

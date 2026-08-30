"""
robots.txt Fetcher and Directive Parser.

Fetches /robots.txt for a target domain and evaluates:
  - Which user-agents are blocked from which paths
  - Whether known AI crawler user-agents are explicitly blocked or allowed
  - Crawl-delay directives

Design:
  - Pure Python, zero external dependencies beyond stdlib
  - Never writes to or modifies the robots.txt
  - Graceful on HTTP errors (treats inaccessible robots.txt as "allow all")
"""

from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
from shared.http_client import SafeHTTPClient
from shared.url_utils import is_valid_url, normalize_url, get_domain
from shared.logging_utils import get_logger

logger = get_logger("robots_parser")

# Known AI crawler user-agents that should ideally be allowed for brand discoverability.
# Ordered by prevalence/importance.
KNOWN_AI_USER_AGENTS: List[str] = [
    "GPTBot",           # OpenAI ChatGPT web search
    "ChatGPT-User",     # OpenAI ChatGPT browsing
    "PerplexityBot",    # Perplexity AI
    "ClaudeBot",        # Anthropic Claude
    "Claude-Web",       # Anthropic Claude browsing
    "Google-Extended",  # Google Bard/Gemini AI training opt-out
    "Bytespider",       # ByteDance/TikTok AI
    "Applebot-Extended",# Apple AI
    "CCBot",            # Common Crawl (used by many LLMs)
    "anthropic-ai",     # Anthropic general
    "cohere-ai",        # Cohere
]


class RobotsRule:
    """Represents a single user-agent directive block from robots.txt."""
    def __init__(self, user_agent: str):
        self.user_agent = user_agent.strip().lower()
        self.disallow: List[str] = []
        self.allow: List[str] = []
        self.crawl_delay: Optional[float] = None

    def is_path_disallowed(self, path: str) -> bool:
        """Check if given path is disallowed by this rule block, respecting allow overrides."""
        path = path or "/"
        # Check allow rules first (more specific allow overrides disallow)
        for pattern in sorted(self.allow, key=len, reverse=True):
            if pattern and path.startswith(pattern):
                return False
        # Check disallow rules
        for pattern in sorted(self.disallow, key=len, reverse=True):
            if pattern == "" or pattern == "/":
                return pattern == "/" and not self.allow
            if pattern and path.startswith(pattern):
                return True
        return False


class RobotsParseResult:
    """Result of parsing a robots.txt file."""
    def __init__(
        self,
        robots_url: str,
        http_status: int,
        raw_content: str,
        is_accessible: bool,
        rules: Dict[str, RobotsRule],
        sitemap_urls: List[str],
        error: Optional[str] = None,
    ):
        self.robots_url = robots_url
        self.http_status = http_status
        self.raw_content = raw_content
        self.is_accessible = is_accessible
        self.rules = rules           # Dict[user_agent_lower -> RobotsRule]
        self.sitemap_urls = sitemap_urls
        self.error = error

    def get_blocked_ai_agents(self) -> List[str]:
        """Returns list of AI user-agents that are blocked from root '/'."""
        blocked = []
        for agent in KNOWN_AI_USER_AGENTS:
            rule = self._get_applicable_rule(agent)
            if rule and rule.is_path_disallowed("/"):
                blocked.append(agent)
        return blocked

    def get_crawl_delay(self, user_agent: str = "*") -> Optional[float]:
        """Returns crawl-delay for given user agent, falling back to wildcard rule."""
        rule = self._get_applicable_rule(user_agent)
        if rule and rule.crawl_delay is not None:
            return rule.crawl_delay
        wildcard = self.rules.get("*")
        return wildcard.crawl_delay if wildcard else None

    def is_path_allowed(self, path: str, user_agent: str = "*") -> bool:
        """Returns True if the given path is accessible to the given user-agent."""
        rule = self._get_applicable_rule(user_agent)
        if rule:
            return not rule.is_path_disallowed(path)
        return True  # No rule = allow all

    def _get_applicable_rule(self, user_agent: str) -> Optional[RobotsRule]:
        """Returns the most specific matching rule for a user-agent."""
        ua_lower = user_agent.lower()
        # Try exact match first
        if ua_lower in self.rules:
            return self.rules[ua_lower]
        # Try prefix match (e.g. "gptbot" matches "gptbot/1.0")
        for key, rule in self.rules.items():
            if key != "*" and ua_lower.startswith(key):
                return rule
        # Fall back to wildcard
        return self.rules.get("*")


class RobotsParser:
    """Fetches and parses robots.txt for a given root URL."""

    def __init__(self, http_client: Optional[SafeHTTPClient] = None):
        self.http_client = http_client or SafeHTTPClient()

    def fetch_and_parse(self, root_url: str) -> RobotsParseResult:
        """
        Fetches /robots.txt from the given root URL domain and parses directives.
        Never modifies the target; gracefully degrades on errors.
        """
        parsed = urlparse(root_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        logger.info(f"Fetching robots.txt from: {robots_url}")
        resp = self.http_client.fetch(robots_url)

        if not resp.is_success or not resp.body.strip():
            # inaccessible robots.txt = allow all (RFC 9309 §2.3.1)
            logger.info(f"robots.txt not accessible (status={resp.status_code}), treating as allow-all")
            return RobotsParseResult(
                robots_url=robots_url,
                http_status=resp.status_code,
                raw_content="",
                is_accessible=False,
                rules={},
                sitemap_urls=[],
                error=resp.error,
            )

        rules, sitemap_urls = self._parse(resp.body)
        logger.info(f"robots.txt parsed: {len(rules)} rule blocks, {len(sitemap_urls)} sitemaps declared")

        return RobotsParseResult(
            robots_url=robots_url,
            http_status=resp.status_code,
            raw_content=resp.body,
            is_accessible=True,
            rules=rules,
            sitemap_urls=sitemap_urls,
        )

    def _parse(self, content: str) -> Tuple[Dict[str, RobotsRule], List[str]]:
        """Parse raw robots.txt text into rule blocks and sitemap URLs."""
        rules: Dict[str, RobotsRule] = {}
        sitemap_urls: List[str] = []
        current_agents: List[str] = []
        current_rule: Optional[RobotsRule] = None

        for raw_line in content.splitlines():
            # Strip inline comments and whitespace
            line = raw_line.split("#")[0].strip()
            if not line:
                # Blank line ends a user-agent block
                current_agents = []
                current_rule = None
                continue

            if ":" not in line:
                continue

            field, _, value = line.partition(":")
            field = field.strip().lower()
            value = value.strip()

            if field == "user-agent":
                agent = value.lower()
                if agent not in rules:
                    rules[agent] = RobotsRule(agent)
                current_agents.append(agent)
                current_rule = rules[agent]
            elif field == "disallow" and current_agents:
                for agent in current_agents:
                    rules[agent].disallow.append(value)
            elif field == "allow" and current_agents:
                for agent in current_agents:
                    rules[agent].allow.append(value)
            elif field == "crawl-delay" and current_agents:
                try:
                    delay = float(value)
                    for agent in current_agents:
                        rules[agent].crawl_delay = delay
                except ValueError:
                    pass
            elif field == "sitemap":
                if value and is_valid_url(value):
                    sitemap_urls.append(value)

        return rules, sitemap_urls

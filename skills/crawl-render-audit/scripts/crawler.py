"""
Bounded BFS Crawl Queue and Crawler.

Implements a priority-ordered BFS URL queue that:
  - Respects a max page and max depth limit
  - Deduplicates URLs before and after fetching
  - Respects robots.txt allow/disallow for the audit user-agent
  - Applies polite per-host delays
  - Prioritises important pages (root, navigation links, key paths)
  - Returns a list of (url, depth, HTTPResponse) tuples

Design principles:
  - No hardcoded domain knowledge or CMS selectors
  - Priority based on URL depth and detected navigation importance
  - Graceful: logs and skips failed pages rather than crashing
"""

import time
import heapq
from typing import List, Tuple, Optional, Dict, Set
from urllib.parse import urlparse

from shared.http_client import SafeHTTPClient, HTTPResponse
from shared.url_utils import normalize_url, is_valid_url, is_same_domain, URLDeduplicator
from shared.logging_utils import get_logger
from skills.crawl_render_audit.scripts.robots_parser import RobotsParseResult

logger = get_logger("crawler")

# Paths that typically indicate high-value pages for AI discoverability and engagement audits
_HIGH_VALUE_PATH_SIGNALS = [
    "/about", "/company", "/team", "/mission",
    "/pricing", "/plans", "/features", "/product",
    "/contact", "/support",
    "/blog", "/news", "/articles",
    "/docs", "/documentation", "/api",
    "/privacy", "/terms",
]

# Content-type prefixes we want to crawl (HTML pages only)
_CRAWLABLE_CONTENT_TYPES = ["text/html", "application/xhtml+xml"]


class CrawledPage:
    """Represents a successfully fetched and queued page."""
    def __init__(self, url: str, depth: int, response: HTTPResponse):
        self.url = url
        self.depth = depth
        self.response = response


def _url_priority(url: str, depth: int) -> int:
    """
    Lower number = higher priority in the min-heap.
    Root page gets 0. Navigation paths get 1. Others scale with depth.
    This is CMS-agnostic — purely based on URL structure signals.
    """
    if depth == 0:
        return 0

    path = urlparse(url).path.rstrip("/").lower()

    for signal in _HIGH_VALUE_PATH_SIGNALS:
        if path == signal or path.startswith(signal + "/"):
            return depth  # Same depth but prioritized over generic pages

    # Penalize very deep or parameter-heavy URLs slightly
    segment_count = len([s for s in path.split("/") if s])
    return depth + segment_count


class BoundedCrawler:
    """
    Bounded BFS crawler. Crawls up to max_pages total pages up to max_depth hops
    from the root URL, respecting robots.txt and applying polite delays.
    """

    def __init__(
        self,
        http_client: Optional[SafeHTTPClient] = None,
        max_pages: int = 15,
        max_depth: int = 2,
        per_host_delay: float = 0.5,  # seconds between requests to same host
    ):
        self.http_client = http_client or SafeHTTPClient()
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.per_host_delay = per_host_delay

    def crawl(
        self,
        root_url: str,
        robots: Optional[RobotsParseResult] = None,
        seed_urls: Optional[List[str]] = None,
    ) -> List[CrawledPage]:
        """
        Executes a bounded BFS crawl starting from root_url.

        Args:
            root_url:   The canonical starting URL.
            robots:     Parsed robots.txt (if None, assume allow-all).
            seed_urls:  High-priority URLs to pre-populate queue (e.g. from sitemap).

        Returns:
            List of CrawledPage objects for all successfully fetched pages.
        """
        root_url = normalize_url(root_url)
        dedup = URLDeduplicator()
        crawled: List[CrawledPage] = []
        host_last_request: Dict[str, float] = {}

        # Priority queue entries: (priority_int, counter, url, depth)
        # Counter breaks ties deterministically (FIFO within same priority)
        queue: List[Tuple[int, int, str, int]] = []
        counter = 0

        def enqueue(url: str, depth: int) -> None:
            nonlocal counter
            if not is_valid_url(url):
                return
            if not is_same_domain(url, root_url):
                return
            if not dedup.add(url):
                return
            # Check robots.txt
            path = urlparse(url).path or "/"
            if robots and not robots.is_path_allowed(path):
                logger.debug(f"robots.txt disallows {url}, skipping")
                return
            prio = _url_priority(url, depth)
            heapq.heappush(queue, (prio, counter, url, depth))
            counter += 1

        # Seed the queue with root URL
        enqueue(root_url, depth=0)

        # Pre-populate with high-value sitemap/seed URLs at depth 1
        for seed in (seed_urls or []):
            enqueue(seed, depth=1)

        while queue and len(crawled) < self.max_pages:
            prio, _, url, depth = heapq.heappop(queue)

            if depth > self.max_depth:
                continue

            # Polite per-host delay
            host = urlparse(url).netloc
            last = host_last_request.get(host, 0.0)
            elapsed = time.time() - last
            if elapsed < self.per_host_delay:
                time.sleep(self.per_host_delay - elapsed)

            logger.info(f"[depth={depth}] Fetching: {url}")
            resp = self.http_client.fetch(url)
            host_last_request[host] = time.time()

            if not resp.is_success:
                logger.warning(f"  HTTP {resp.status_code} for {url}: {resp.error}")
                continue

            # Skip non-HTML responses
            ct = (resp.content_type or "").lower()
            if not any(ct.startswith(t) for t in _CRAWLABLE_CONTENT_TYPES):
                logger.debug(f"  Skipping non-HTML content-type '{ct}' at {url}")
                continue

            crawled.append(CrawledPage(url=url, depth=depth, response=resp))
            logger.info(f"  Crawled ({len(crawled)}/{self.max_pages}): {url}")

            # Only discover new links from HTML pages within depth limit
            if depth < self.max_depth and resp.body:
                discovered = self._extract_links_fast(resp.body, url)
                for link in discovered:
                    enqueue(link, depth + 1)

        logger.info(f"Crawl complete: {len(crawled)} pages fetched")
        return crawled

    def _extract_links_fast(self, html: str, base_url: str) -> List[str]:
        """
        Fast regex-based link extractor for the crawler loop.
        Full semantic extraction is done by PageAnalyser separately.
        This avoids importing BeautifulSoup inside the tight crawl loop.
        """
        import re
        links: List[str] = []
        # Match href="..." and href='...' in <a> tags
        pattern = re.compile(r'<a\b[^>]+\bhref=["\']([^"\'#][^"\']*)["\']', re.IGNORECASE)
        for match in pattern.finditer(html):
            raw = match.group(1).strip()
            if not raw or raw.startswith(("javascript:", "mailto:", "tel:", "data:")):
                continue
            from shared.url_utils import resolve_relative_url
            resolved = resolve_relative_url(base_url, raw)
            if resolved:
                links.append(resolved)
        return links

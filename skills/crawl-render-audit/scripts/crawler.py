"""
Bounded BFS Crawl Queue and Representative Template Sampler.

Implements a priority-ordered, template-aware URL queue that:
  - Samples representatively across key template types (Homepage, About/Company, Product/Pricing, Docs/API, Blog/Content)
  - Respects max page and max depth limits
  - Deduplicates URLs deterministically before fetching
  - Respects robots.txt directives for AI crawler User-Agents
  - Enforces polite per-host delays
  - Returns a list of CrawledPage objects containing HTTP responses
"""

import time
import heapq
from typing import List, Tuple, Optional, Dict, Set, Any
from urllib.parse import urlparse

from shared.http_client import SafeHTTPClient, HTTPResponse
from shared.url_utils import normalize_url, is_valid_url, is_same_domain, URLDeduplicator
from shared.logging_utils import get_logger
from .robots_parser import RobotsParseResult

logger = get_logger("crawler")

# Content-type prefixes we want to crawl (HTML pages only)
_CRAWLABLE_CONTENT_TYPES = ["text/html", "application/xhtml+xml"]

# Template Bucket Categories for Representative Sampling
TEMPLATE_HOMEPAGE = "homepage"
TEMPLATE_ABOUT_COMPANY = "about_company"
TEMPLATE_PRODUCT_PRICING = "product_pricing"
TEMPLATE_DOCS_API = "docs_api"
TEMPLATE_BLOG_CONTENT = "blog_content"
TEMPLATE_GENERIC = "generic"

_TEMPLATE_PATH_MAP = {
    TEMPLATE_ABOUT_COMPANY: ["/about", "/company", "/team", "/contact", "/support", "/mission"],
    TEMPLATE_PRODUCT_PRICING: ["/pricing", "/plans", "/features", "/product", "/services", "/solutions"],
    TEMPLATE_DOCS_API: ["/docs", "/documentation", "/api", "/guide", "/help", "/developers"],
    TEMPLATE_BLOG_CONTENT: ["/blog", "/news", "/articles", "/posts", "/changelog", "/insights"],
}

# Max pages to sample per template category (prevents 15 blog posts from eating crawl budget)
MAX_PAGES_PER_TEMPLATE = {
    TEMPLATE_HOMEPAGE: 1,
    TEMPLATE_ABOUT_COMPANY: 3,
    TEMPLATE_PRODUCT_PRICING: 4,
    TEMPLATE_DOCS_API: 4,
    TEMPLATE_BLOG_CONTENT: 3,
    TEMPLATE_GENERIC: 5,
}


def classify_template_bucket(url: str, root_url: str) -> str:
    """Classifies a URL into a representative template bucket based on path patterns."""
    parsed_root = urlparse(root_url)
    parsed_url = urlparse(url)

    # Root or homepage path
    if parsed_url.path.rstrip("/") == parsed_root.path.rstrip("/"):
        return TEMPLATE_HOMEPAGE

    path = parsed_url.path.lower()
    for bucket, patterns in _TEMPLATE_PATH_MAP.items():
        for pattern in patterns:
            if path == pattern or path.startswith(pattern + "/"):
                return bucket

    return TEMPLATE_GENERIC


def _url_priority(url: str, depth: int, template_bucket: str) -> int:
    """
    Priority calculation for min-heap queue:
    Lower number = higher priority.
    - Homepage = 0
    - Distinct key template buckets = 1..2
    - Generic pages scale with depth
    """
    if template_bucket == TEMPLATE_HOMEPAGE:
        return 0
    if template_bucket in (TEMPLATE_PRODUCT_PRICING, TEMPLATE_ABOUT_COMPANY, TEMPLATE_DOCS_API):
        return 1 + depth
    if template_bucket == TEMPLATE_BLOG_CONTENT:
        return 2 + depth

    # Generic path priority scales with URL depth and segment length
    path_segments = [s for s in urlparse(url).path.split("/") if s]
    return 3 + depth + len(path_segments)


class CrawledPage:
    """Represents a successfully fetched page in the crawl graph."""
    def __init__(self, url: str, depth: int, response: HTTPResponse, template_bucket: str):
        self.url = url
        self.depth = depth
        self.response = response
        self.template_bucket = template_bucket

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "depth": self.depth,
            "template_bucket": self.template_bucket,
            "status_code": self.response.status_code,
            "elapsed_seconds": self.response.elapsed_seconds,
        }


class BoundedCrawler:
    """
    Bounded BFS crawler with representative template sampling.
    Crawls up to max_pages total pages up to max_depth hops while enforcing polite host delays.
    """

    def __init__(
        self,
        http_client: Optional[SafeHTTPClient] = None,
        max_pages: int = 15,
        max_depth: int = 2,
        per_host_delay: float = 0.2,  # Polite delay in seconds
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
        Executes bounded, representative template crawl.
        """
        root_url = normalize_url(root_url)
        dedup = URLDeduplicator()
        crawled: List[CrawledPage] = []
        host_last_request: Dict[str, float] = {}

        # Bucket counters to ensure balanced sampling across site template types
        bucket_counts: Dict[str, int] = {k: 0 for k in MAX_PAGES_PER_TEMPLATE.keys()}

        # Queue entry format: (priority_int, counter, url, depth, template_bucket)
        queue: List[Tuple[int, int, str, int, str]] = []
        counter = 0

        def enqueue(url: str, depth: int) -> None:
            nonlocal counter
            if not is_valid_url(url):
                return
            if not is_same_domain(url, root_url):
                return
            if not dedup.add(url):
                return

            bucket = classify_template_bucket(url, root_url)
            cap = MAX_PAGES_PER_TEMPLATE.get(bucket, 5)
            if bucket_counts[bucket] >= cap and bucket != TEMPLATE_HOMEPAGE:
                logger.debug(f"Bucket cap reached for {bucket}, skipping {url}")
                return

            # Check robots.txt directives
            path = urlparse(url).path or "/"
            if robots and not robots.is_path_allowed(path):
                logger.debug(f"robots.txt disallows {url}, skipping enqueue")
                return

            prio = _url_priority(url, depth, bucket)
            heapq.heappush(queue, (prio, counter, url, depth, bucket))
            counter += 1

        # Seed queue with root URL
        enqueue(root_url, depth=0)

        # Pre-populate with high-value sitemap URLs at depth 1
        for seed in (seed_urls or []):
            enqueue(seed, depth=1)

        while queue and len(crawled) < self.max_pages:
            prio, _, url, depth, bucket = heapq.heappop(queue)

            if depth > self.max_depth:
                continue

            # Polite host rate limiting
            host = urlparse(url).netloc
            last = host_last_request.get(host, 0.0)
            elapsed = time.time() - last
            if elapsed < self.per_host_delay:
                time.sleep(self.per_host_delay - elapsed)

            logger.info(f"[depth={depth}][{bucket}] Fetching: {url}")
            resp = self.http_client.fetch(url)
            host_last_request[host] = time.time()

            if not resp.is_success:
                logger.warning(f"  HTTP {resp.status_code} for {url}: {resp.error or 'Failed'}")
                continue

            # Filter non-HTML content
            ct = (resp.content_type or "").lower()
            if not any(ct.startswith(t) for t in _CRAWLABLE_CONTENT_TYPES):
                logger.debug(f"  Skipping non-HTML content-type '{ct}' at {url}")
                continue

            bucket_counts[bucket] += 1
            crawled.append(CrawledPage(url=url, depth=depth, response=resp, template_bucket=bucket))
            logger.info(f"  Crawled ({len(crawled)}/{self.max_pages}): {url}")

            # Extract internal links for next hop if depth limit allows
            if depth < self.max_depth and resp.body:
                discovered = self._extract_links_fast(resp.body, url)
                for link in discovered:
                    enqueue(link, depth + 1)

        logger.info(f"Crawl complete. Sampled {len(crawled)} pages across buckets: {bucket_counts}")
        return crawled

    def _extract_links_fast(self, html: str, base_url: str) -> List[str]:
        """Fast regex link extraction for crawler queue population."""
        import re
        links: List[str] = []
        pattern = re.compile(r'<a\b[^>]+\bhref=["\']([^"\'#][^"\']*)["\']', re.IGNORECASE)
        for match in pattern.finditer(html):
            raw = match.group(1).strip()
            if not raw or raw.startswith(("javascript:", "mailto:", "tel:", "data:", "#")):
                continue
            from shared.url_utils import resolve_relative_url
            resolved = resolve_relative_url(base_url, raw)
            if resolved:
                links.append(resolved)
        return links

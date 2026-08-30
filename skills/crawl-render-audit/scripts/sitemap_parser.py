"""
Sitemap.xml Fetcher, XML Parser, and URL Extractor.

Handles:
  - Standard XML sitemaps (urlset)
  - Sitemap index files (sitemapindex) — one level deep only to stay bounded
  - Extracts <loc>, <lastmod>, <priority> from each <url> entry
  - Tries common fallback paths if sitemap is not declared in robots.txt

Design:
  - Pure Python stdlib xml.etree.ElementTree
  - Bounded: caps total URLs extracted to avoid runaway memory on giant sitemaps
  - Graceful on malformed XML
"""

from typing import List, Optional, Tuple
from xml.etree import ElementTree as ET
from datetime import datetime
from urllib.parse import urlparse
from shared.http_client import SafeHTTPClient
from shared.url_utils import is_valid_url, is_same_domain
from shared.logging_utils import get_logger

logger = get_logger("sitemap_parser")

# Sitemap XML namespaces
_NS_SITEMAP = "http://www.sitemaps.org/schemas/sitemap/0.9"
_NS_MAP = {"sm": _NS_SITEMAP}

# Safety caps
MAX_SITEMAP_URLS = 500       # Max URLs to extract per sitemap
MAX_SITEMAP_INDEX_DEPTH = 1  # Only follow one level of sitemap index


class SitemapEntry:
    """A single URL entry extracted from a sitemap."""
    def __init__(
        self,
        url: str,
        lastmod: Optional[str] = None,
        priority: Optional[float] = None,
        changefreq: Optional[str] = None,
    ):
        self.url = url
        self.lastmod = lastmod
        self.priority = priority if priority is not None else 0.5
        self.changefreq = changefreq

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "lastmod": self.lastmod,
            "priority": self.priority,
            "changefreq": self.changefreq,
        }


class SitemapParseResult:
    """Aggregated result from all parsed sitemap files."""
    def __init__(
        self,
        sitemap_url: Optional[str],
        http_status: int,
        is_accessible: bool,
        entries: List[SitemapEntry],
        has_lastmod: bool,
        error: Optional[str] = None,
    ):
        self.sitemap_url = sitemap_url
        self.http_status = http_status
        self.is_accessible = is_accessible
        self.entries = entries
        self.has_lastmod = has_lastmod
        self.error = error

    def get_urls(self) -> List[str]:
        return [e.url for e in self.entries]

    def get_high_priority_urls(self, min_priority: float = 0.6) -> List[str]:
        return [e.url for e in self.entries if (e.priority or 0) >= min_priority]


class SitemapParser:
    """Fetches and parses XML sitemaps, following sitemap index files one level deep."""

    # Standard fallback paths to try when sitemap URL is unknown
    FALLBACK_PATHS = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap-index.xml",
        "/sitemaps/sitemap.xml",
    ]

    def __init__(self, http_client: Optional[SafeHTTPClient] = None):
        self.http_client = http_client or SafeHTTPClient()

    def fetch_and_parse(
        self,
        root_url: str,
        declared_sitemap_urls: Optional[List[str]] = None,
    ) -> SitemapParseResult:
        """
        Fetches and parses sitemap(s). Tries declared URLs first, then fallback paths.
        Returns consolidated SitemapParseResult.
        """
        parsed_root = urlparse(root_url)
        base = f"{parsed_root.scheme}://{parsed_root.netloc}"

        candidates: List[str] = list(declared_sitemap_urls or [])
        # Add fallback paths if no declared sitemaps (or as backup)
        for path in self.FALLBACK_PATHS:
            candidate = base + path
            if candidate not in candidates:
                candidates.append(candidate)

        for sitemap_url in candidates:
            result = self._try_fetch(sitemap_url, root_url)
            if result.is_accessible:
                return result

        logger.info("No accessible sitemap found")
        return SitemapParseResult(
            sitemap_url=None,
            http_status=0,
            is_accessible=False,
            entries=[],
            has_lastmod=False,
            error="No accessible sitemap found at declared or standard paths",
        )

    def _try_fetch(self, sitemap_url: str, root_url: str) -> SitemapParseResult:
        """Fetch and attempt to parse a single sitemap URL."""
        logger.info(f"Trying sitemap: {sitemap_url}")
        resp = self.http_client.fetch(sitemap_url)

        if not resp.is_success or not resp.body.strip():
            return SitemapParseResult(
                sitemap_url=sitemap_url,
                http_status=resp.status_code,
                is_accessible=False,
                entries=[],
                has_lastmod=False,
                error=resp.error,
            )

        entries = self._parse_xml(resp.body, root_url, sitemap_url, depth=0)
        has_lastmod = any(e.lastmod for e in entries)

        logger.info(f"Sitemap parsed: {len(entries)} URLs found at {sitemap_url}")
        return SitemapParseResult(
            sitemap_url=sitemap_url,
            http_status=resp.status_code,
            is_accessible=True,
            entries=entries[:MAX_SITEMAP_URLS],
            has_lastmod=has_lastmod,
        )

    def _parse_xml(
        self,
        xml_content: str,
        root_url: str,
        current_url: str,
        depth: int,
    ) -> List[SitemapEntry]:
        """Parse sitemap XML content. Handles both urlset and sitemapindex."""
        try:
            root = ET.fromstring(xml_content.strip())
        except ET.ParseError as e:
            logger.warning(f"Malformed sitemap XML at {current_url}: {e}")
            return []

        # Strip namespace prefix for tag comparison
        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

        if tag == "sitemapindex":
            return self._parse_sitemap_index(root, root_url, depth)
        elif tag == "urlset":
            return self._parse_urlset(root, root_url)
        else:
            logger.warning(f"Unrecognized sitemap root tag: {root.tag}")
            return []

    def _parse_urlset(self, root: ET.Element, root_url: str) -> List[SitemapEntry]:
        """Parse <urlset> containing <url> entries."""
        entries = []
        for url_el in root.iter():
            if url_el.tag.split("}")[-1] != "url":
                continue

            loc = self._get_child_text(url_el, "loc")
            if not loc or not is_valid_url(loc):
                continue
            # Only include same-domain URLs
            if not is_same_domain(loc, root_url):
                continue

            lastmod = self._get_child_text(url_el, "lastmod")
            changefreq = self._get_child_text(url_el, "changefreq")
            priority_str = self._get_child_text(url_el, "priority")
            priority = None
            if priority_str:
                try:
                    priority = float(priority_str)
                except ValueError:
                    pass

            entries.append(SitemapEntry(
                url=loc,
                lastmod=lastmod,
                priority=priority,
                changefreq=changefreq,
            ))

            if len(entries) >= MAX_SITEMAP_URLS:
                break

        return entries

    def _parse_sitemap_index(
        self,
        root: ET.Element,
        root_url: str,
        depth: int,
    ) -> List[SitemapEntry]:
        """Parse <sitemapindex> and follow child sitemaps one level deep."""
        if depth >= MAX_SITEMAP_INDEX_DEPTH:
            logger.info("Sitemap index depth limit reached, not following further")
            return []

        all_entries: List[SitemapEntry] = []
        for sitemap_el in root.iter():
            if sitemap_el.tag.split("}")[-1] != "sitemap":
                continue
            loc = self._get_child_text(sitemap_el, "loc")
            if not loc or not is_valid_url(loc):
                continue

            resp = self.http_client.fetch(loc)
            if resp.is_success and resp.body.strip():
                child_entries = self._parse_xml(resp.body, root_url, loc, depth + 1)
                all_entries.extend(child_entries)

            if len(all_entries) >= MAX_SITEMAP_URLS:
                break

        return all_entries[:MAX_SITEMAP_URLS]

    def _get_child_text(self, element: ET.Element, tag: str) -> Optional[str]:
        """Extract text from a child element, handling namespace prefixes."""
        # Try with and without namespace
        for child in element:
            child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if child_tag == tag:
                return (child.text or "").strip() or None
        return None

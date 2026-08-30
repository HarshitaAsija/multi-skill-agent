"""
HTML Link Extractor and Page Content Analyser.

Extracts from a raw HTML response:
  - All <a href> internal links (same domain, not javascript/mailto)
  - <link rel="canonical"> canonical URL
  - <title> tag text
  - <meta name="description"> content
  - <meta name="robots"> directives
  - Heading tags h1..h6 in document order
  - <script type="application/ld+json"> JSON-LD blocks
  - <meta property="og:*"> and <meta name="twitter:*"> tags
  - Raw visible text length estimate (for JS hydration delta detection)
  - Navigation landmark presence (<nav>, role="navigation")
  - <link rel="alternate" hreflang> tags (multi-language sites)

Uses BeautifulSoup4 for robust parsing.
"""

from typing import Dict, List, Optional, Any, Set
from bs4 import BeautifulSoup, Tag
import json
import re
from shared.url_utils import resolve_relative_url, is_same_domain, is_valid_url
from shared.logging_utils import get_logger

logger = get_logger("page_analyser")


class PageData:
    """Structured data extracted from a single HTML page."""

    def __init__(self, url: str):
        self.url = url
        self.title: Optional[str] = None
        self.meta_description: Optional[str] = None
        self.meta_robots: Optional[str] = None
        self.canonical_url: Optional[str] = None
        self.h1_tags: List[str] = []
        self.headings: List[Dict[str, Any]] = []   # [{"level": 1, "text": "..."}]
        self.internal_links: List[str] = []         # Normalized same-domain hrefs
        self.json_ld_blocks: List[Dict[str, Any]] = []
        self.open_graph: Dict[str, str] = {}
        self.twitter_meta: Dict[str, str] = {}
        self.hreflang_tags: List[Dict[str, str]] = []
        self.has_nav_landmark: bool = False
        self.has_main_landmark: bool = False
        self.has_breadcrumb: bool = False
        self.raw_text_length: int = 0               # Text length from raw HTML body
        self.body_text_sample: str = ""             # First 2000 chars of visible text
        self.button_cta_labels: List[str] = []      # Button / CTA label text
        self.footer_text: str = ""                  # Footer text (for copyright scanning)
        self.has_h1: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "meta_description": self.meta_description,
            "canonical_url": self.canonical_url,
            "h1_tags": self.h1_tags,
            "has_h1": self.has_h1,
            "heading_count": len(self.headings),
            "internal_link_count": len(self.internal_links),
            "json_ld_count": len(self.json_ld_blocks),
            "has_nav_landmark": self.has_nav_landmark,
            "has_main_landmark": self.has_main_landmark,
            "has_breadcrumb": self.has_breadcrumb,
            "raw_text_length": self.raw_text_length,
        }


class PageAnalyser:
    """
    Extracts structured page data from raw HTML using BeautifulSoup4.
    Fully domain-agnostic — no site-specific selectors or CMS assumptions.
    """

    def analyse(self, url: str, html: str) -> PageData:
        """
        Parse raw HTML and extract all structured signals.
        Returns a PageData object; never raises on malformed HTML.
        """
        data = PageData(url=url)
        if not html or not html.strip():
            return data

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            logger.warning(f"BeautifulSoup parse failed for {url}: {e}")
            return data

        self._extract_head_metadata(soup, data, url)
        self._extract_headings(soup, data)
        self._extract_landmarks(soup, data)
        self._extract_links(soup, data, url)
        self._extract_json_ld(soup, data)
        self._extract_cta_labels(soup, data)
        self._extract_footer(soup, data)
        self._extract_text_metrics(soup, data)

        return data

    # ------------------------------------------------------------------ #
    #  Head Metadata                                                       #
    # ------------------------------------------------------------------ #
    def _extract_head_metadata(self, soup: BeautifulSoup, data: PageData, base_url: str) -> None:
        # <title>
        title_tag = soup.find("title")
        if title_tag:
            data.title = title_tag.get_text(strip=True) or None

        # <meta name="description">
        desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if desc and isinstance(desc, Tag):
            data.meta_description = desc.get("content", "").strip() or None

        # <meta name="robots">
        robots_meta = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
        if robots_meta and isinstance(robots_meta, Tag):
            data.meta_robots = robots_meta.get("content", "").strip() or None

        # <link rel="canonical">
        canonical = soup.find("link", attrs={"rel": re.compile(r"canonical", re.I)})
        if canonical and isinstance(canonical, Tag):
            href = canonical.get("href", "").strip()
            if href:
                resolved = resolve_relative_url(base_url, href) or href
                data.canonical_url = resolved

        # <link rel="alternate" hreflang="...">
        for tag in soup.find_all("link", attrs={"rel": re.compile(r"alternate", re.I), "hreflang": True}):
            if isinstance(tag, Tag):
                data.hreflang_tags.append({
                    "hreflang": tag.get("hreflang", ""),
                    "href": tag.get("href", ""),
                })

        # Open Graph <meta property="og:*">
        for og in soup.find_all("meta", property=re.compile(r"^og:", re.I)):
            if isinstance(og, Tag):
                prop = og.get("property", "").lower()
                content = og.get("content", "").strip()
                if prop and content:
                    data.open_graph[prop] = content

        # Twitter card <meta name="twitter:*">
        for tw in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:", re.I)}):
            if isinstance(tw, Tag):
                name = tw.get("name", "").lower()
                content = tw.get("content", "").strip()
                if name and content:
                    data.twitter_meta[name] = content

    # ------------------------------------------------------------------ #
    #  Headings                                                            #
    # ------------------------------------------------------------------ #
    def _extract_headings(self, soup: BeautifulSoup, data: PageData) -> None:
        for level in range(1, 7):
            for tag in soup.find_all(f"h{level}"):
                text = tag.get_text(separator=" ", strip=True)
                if text:
                    data.headings.append({"level": level, "text": text[:300]})
                    if level == 1:
                        data.h1_tags.append(text[:300])
        data.has_h1 = bool(data.h1_tags)

    # ------------------------------------------------------------------ #
    #  Landmarks & Navigation                                              #
    # ------------------------------------------------------------------ #
    def _extract_landmarks(self, soup: BeautifulSoup, data: PageData) -> None:
        # <nav> or role="navigation"
        nav = soup.find("nav") or soup.find(attrs={"role": re.compile(r"^navigation$", re.I)})
        data.has_nav_landmark = bool(nav)

        # <main> or role="main"
        main = soup.find("main") or soup.find(attrs={"role": re.compile(r"^main$", re.I)})
        data.has_main_landmark = bool(main)

        # Breadcrumbs: <nav aria-label="breadcrumb">, role="list" inside nav,
        # or Schema BreadcrumbList in JSON-LD (checked later), or common class names
        breadcrumb_signals = [
            soup.find("nav", attrs={"aria-label": re.compile(r"breadcrumb", re.I)}),
            soup.find(attrs={"class": re.compile(r"breadcrumb", re.I)}),
            soup.find(attrs={"id": re.compile(r"breadcrumb", re.I)}),
        ]
        data.has_breadcrumb = any(s for s in breadcrumb_signals)

    # ------------------------------------------------------------------ #
    #  Internal Links                                                      #
    # ------------------------------------------------------------------ #
    def _extract_links(self, soup: BeautifulSoup, data: PageData, base_url: str) -> None:
        seen: Set[str] = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "").strip()
            if not href:
                continue
            resolved = resolve_relative_url(base_url, href)
            if resolved and is_same_domain(resolved, base_url) and resolved not in seen:
                seen.add(resolved)
                data.internal_links.append(resolved)

    # ------------------------------------------------------------------ #
    #  JSON-LD                                                             #
    # ------------------------------------------------------------------ #
    def _extract_json_ld(self, soup: BeautifulSoup, data: PageData) -> None:
        for script in soup.find_all("script", type="application/ld+json"):
            raw = script.string or ""
            if not raw.strip():
                continue
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    data.json_ld_blocks.extend(parsed)
                elif isinstance(parsed, dict):
                    data.json_ld_blocks.append(parsed)
            except json.JSONDecodeError as e:
                logger.debug(f"JSON-LD parse error at {data.url}: {e}")

    # ------------------------------------------------------------------ #
    #  CTA Labels (Buttons)                                               #
    # ------------------------------------------------------------------ #
    def _extract_cta_labels(self, soup: BeautifulSoup, data: PageData) -> None:
        for btn in soup.find_all(["button", "a"], attrs={"class": re.compile(r"btn|button|cta", re.I)}):
            label = btn.get_text(separator=" ", strip=True)
            if label and len(label) < 100:
                data.button_cta_labels.append(label)
        # Also grab plain <button> elements without class
        for btn in soup.find_all("button"):
            label = btn.get_text(separator=" ", strip=True)
            if label and len(label) < 100 and label not in data.button_cta_labels:
                data.button_cta_labels.append(label)

    # ------------------------------------------------------------------ #
    #  Footer Text                                                         #
    # ------------------------------------------------------------------ #
    def _extract_footer(self, soup: BeautifulSoup, data: PageData) -> None:
        footer = soup.find("footer") or soup.find(attrs={"role": re.compile(r"^contentinfo$", re.I)})
        if footer and isinstance(footer, Tag):
            data.footer_text = footer.get_text(separator=" ", strip=True)[:1000]

    # ------------------------------------------------------------------ #
    #  Text Metrics                                                        #
    # ------------------------------------------------------------------ #
    def _extract_text_metrics(self, soup: BeautifulSoup, data: PageData) -> None:
        # Remove script, style, noscript nodes from text extraction
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        visible_text = soup.get_text(separator=" ", strip=True)
        # Collapse multiple whitespace
        visible_text = re.sub(r"\s+", " ", visible_text).strip()
        data.raw_text_length = len(visible_text)
        data.body_text_sample = visible_text[:2000]

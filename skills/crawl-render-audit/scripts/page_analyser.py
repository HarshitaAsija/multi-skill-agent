"""
HTML Content Analyser & Signal Extractor.

Extracts structured Signals from raw HTML:
  - Page titles, meta descriptions, meta robots (noindex/nofollow), canonical tags, hreflang
  - Heading tree (h1..h6), level-skips, and primary H1 tag
  - Landmarks (<nav>, <main>, <footer>, breadcrumb)
  - JSON-LD blocks and Schema.org entity types
  - Internal links (same domain)
  - Tabular data structures (<table>, <dl>)
  - Image alt text coverage (detecting facts trapped in images)
  - CTA button text and footer text
  - Visible raw text word count and sample

Uses BeautifulSoup4. Domain-agnostic.
"""

from typing import Dict, List, Optional, Any, Set
from bs4 import BeautifulSoup, Tag
import json
import re
from shared.url_utils import resolve_relative_url, is_same_domain
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
        self.headings: List[Dict[str, Any]] = []        # [{"level": 1, "text": "..."}]
        self.heading_level_skips: List[str] = []         # e.g. ["H1 -> H3"]
        self.internal_links: List[str] = []              # Normalized same-domain hrefs
        self.json_ld_blocks: List[Dict[str, Any]] = []
        self.json_ld_types: List[str] = []               # Declared Schema.org @type values
        self.open_graph: Dict[str, str] = {}
        self.twitter_meta: Dict[str, str] = {}
        self.hreflang_tags: List[Dict[str, str]] = []
        self.has_nav_landmark: bool = False
        self.has_main_landmark: bool = False
        self.has_breadcrumb: bool = False
        self.has_tabular_data: bool = False             # <table> or <dl> present
        self.total_images_count: int = 0
        self.images_missing_alt: List[str] = []         # Image src without alt text
        self.raw_text_length: int = 0                    # Text length from raw HTML body
        self.word_count: int = 0                         # Word count estimate
        self.body_text_sample: str = ""                  # First 2000 chars of visible text
        self.button_cta_labels: List[str] = []           # Button / CTA label text
        self.footer_text: str = ""                       # Footer text (for copyright scanning)
        self.has_h1: bool = False
        self.has_form: bool = False
        self.form_inputs_missing_labels: int = 0
        self.date_published: Optional[str] = None
        self.date_modified: Optional[str] = None

    @property
    def images_missing_alt_count(self) -> int:
        return len(self.images_missing_alt)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "meta_description": self.meta_description,
            "meta_robots": self.meta_robots,
            "canonical_url": self.canonical_url,
            "h1_tags": self.h1_tags,
            "has_h1": self.has_h1,
            "heading_count": len(self.headings),
            "heading_level_skips": self.heading_level_skips,
            "internal_link_count": len(self.internal_links),
            "json_ld_count": len(self.json_ld_blocks),
            "json_ld_types": self.json_ld_types,
            "has_nav_landmark": self.has_nav_landmark,
            "has_main_landmark": self.has_main_landmark,
            "has_breadcrumb": self.has_breadcrumb,
            "has_tabular_data": self.has_tabular_data,
            "total_images_count": self.total_images_count,
            "images_missing_alt_count": self.images_missing_alt_count,
            "raw_text_length": self.raw_text_length,
            "word_count": self.word_count,
        }


class PageAnalyser:
    """
    Extracts structured page signals from raw HTML using BeautifulSoup4.
    Fully domain-agnostic — no site-specific selectors or CMS assumptions.
    """

    def analyse(self, url: str, html: str) -> PageData:
        """
        Parse raw HTML and extract all structured signals.
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
        self._extract_tables_and_images(soup, data)
        self._extract_cta_labels(soup, data)
        self._extract_footer(soup, data)
        self._extract_text_metrics(soup, data)
        self._extract_temporal_dates(soup, data)
        self._extract_forms(soup, data)

        return data

    # ------------------------------------------------------------------ #
    #  Head Metadata                                                       #
    # ------------------------------------------------------------------ #
    def _extract_head_metadata(self, soup: BeautifulSoup, data: PageData, base_url: str) -> None:
        title_tag = soup.find("title")
        if title_tag:
            data.title = title_tag.get_text(strip=True) or None

        desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if desc and isinstance(desc, Tag):
            data.meta_description = desc.get("content", "").strip() or None

        robots_meta = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
        if robots_meta and isinstance(robots_meta, Tag):
            data.meta_robots = robots_meta.get("content", "").strip() or None

        canonical = soup.find("link", attrs={"rel": re.compile(r"canonical", re.I)})
        if canonical and isinstance(canonical, Tag):
            href = canonical.get("href", "").strip()
            if href:
                resolved = resolve_relative_url(base_url, href) or href
                data.canonical_url = resolved

        for tag in soup.find_all("link", attrs={"rel": re.compile(r"alternate", re.I), "hreflang": True}):
            if isinstance(tag, Tag):
                data.hreflang_tags.append({
                    "hreflang": tag.get("hreflang", ""),
                    "href": tag.get("href", ""),
                })

        for og in soup.find_all("meta", property=re.compile(r"^og:", re.I)):
            if isinstance(og, Tag):
                prop = og.get("property", "").lower()
                content = og.get("content", "").strip()
                if prop and content:
                    data.open_graph[prop] = content

        for tw in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:", re.I)}):
            if isinstance(tw, Tag):
                name = tw.get("name", "").lower()
                content = tw.get("content", "").strip()
                if name and content:
                    data.twitter_meta[name] = content

    # ------------------------------------------------------------------ #
    #  Headings & Hierarchy Skips                                         #
    # ------------------------------------------------------------------ #
    def _extract_headings(self, soup: BeautifulSoup, data: PageData) -> None:
        heading_tags = soup.find_all(re.compile(r"^h[1-6]$", re.I))
        last_level = 0
        for tag in heading_tags:
            level = int(tag.name[1])
            text = tag.get_text(separator=" ", strip=True)
            if text:
                data.headings.append({"level": level, "text": text[:300]})
                if level == 1:
                    data.h1_tags.append(text[:300])

                # Check for skipped heading levels (e.g. H1 followed immediately by H3)
                if last_level > 0 and level > last_level + 1:
                    skip_str = f"H{last_level} -> H{level}"
                    if skip_str not in data.heading_level_skips:
                        data.heading_level_skips.append(skip_str)
                last_level = level

        data.has_h1 = bool(data.h1_tags)

    # ------------------------------------------------------------------ #
    #  Landmarks & Navigation                                              #
    # ------------------------------------------------------------------ #
    def _extract_landmarks(self, soup: BeautifulSoup, data: PageData) -> None:
        nav = soup.find("nav") or soup.find(attrs={"role": re.compile(r"^navigation$", re.I)})
        data.has_nav_landmark = bool(nav)

        main = soup.find("main") or soup.find(attrs={"role": re.compile(r"^main$", re.I)})
        data.has_main_landmark = bool(main)

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
    #  JSON-LD & Schema Types                                              #
    # ------------------------------------------------------------------ #
    def _extract_json_ld(self, soup: BeautifulSoup, data: PageData) -> None:
        for script in soup.find_all("script", type="application/ld+json"):
            raw = script.string or ""
            if not raw.strip():
                continue
            try:
                parsed = json.loads(raw)
                blocks = parsed if isinstance(parsed, list) else [parsed]
                for block in blocks:
                    data.json_ld_blocks.append(block)
                    self._collect_schema_types(block, data.json_ld_types)
            except json.JSONDecodeError as e:
                logger.debug(f"JSON-LD parse error at {data.url}: {e}")

        # Check for BreadcrumbList in JSON-LD
        if "BreadcrumbList" in data.json_ld_types:
            data.has_breadcrumb = True

    def _collect_schema_types(self, obj: Any, types_list: List[str]) -> None:
        if isinstance(obj, dict):
            stype = obj.get("@type")
            if isinstance(stype, str) and stype not in types_list:
                types_list.append(stype)
            elif isinstance(stype, list):
                for t in stype:
                    if isinstance(t, str) and t not in types_list:
                        types_list.append(t)
            for v in obj.values():
                self._collect_schema_types(v, types_list)
        elif isinstance(obj, list):
            for item in obj:
                self._collect_schema_types(item, types_list)

    # ------------------------------------------------------------------ #
    #  Tables & Image Alt Coverage                                         #
    # ------------------------------------------------------------------ #
    def _extract_tables_and_images(self, soup: BeautifulSoup, data: PageData) -> None:
        data.has_tabular_data = bool(soup.find(["table", "dl"]))

        for img in soup.find_all("img"):
            data.total_images_count += 1
            alt = img.get("alt")
            src = img.get("src") or img.get("data-src") or "unknown"
            if alt is None or not str(alt).strip():
                data.images_missing_alt.append(src[:150])

    # ------------------------------------------------------------------ #
    #  CTA Labels (Buttons)                                               #
    # ------------------------------------------------------------------ #
    def _extract_cta_labels(self, soup: BeautifulSoup, data: PageData) -> None:
        for btn in soup.find_all(["button", "a"], attrs={"class": re.compile(r"btn|button|cta", re.I)}):
            label = btn.get_text(separator=" ", strip=True)
            if label and len(label) < 100:
                data.button_cta_labels.append(label)
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
        soup_copy = BeautifulSoup(str(soup), "html.parser")
        for tag in soup_copy(["script", "style", "noscript", "svg"]):
            tag.decompose()

        visible_text = soup_copy.get_text(separator=" ", strip=True)
        visible_text = re.sub(r"\s+", " ", visible_text).strip()
        data.raw_text_length = len(visible_text)
        data.word_count = len(visible_text.split())
        data.body_text_sample = visible_text[:2000]

    # ------------------------------------------------------------------ #
    #  Temporal Dates (Publication / Modified)                            #
    # ------------------------------------------------------------------ #
    def _extract_temporal_dates(self, soup: BeautifulSoup, data: PageData) -> None:
        for meta in soup.find_all("meta"):
            prop = (meta.get("property") or meta.get("name") or "").lower()
            content = (meta.get("content") or "").strip()
            if not content:
                continue
            if prop in ("article:published_time", "og:published_time", "publication_date", "datepublished"):
                data.date_published = content[:30]
            elif prop in ("article:modified_time", "og:modified_time", "last-modified", "datemodified"):
                data.date_modified = content[:30]

        if not data.date_published:
            time_tag = soup.find("time", attrs={"datetime": True})
            if time_tag and isinstance(time_tag, Tag):
                data.date_published = (time_tag.get("datetime") or "").strip()[:30]

        for block in data.json_ld_blocks:
            if isinstance(block, dict):
                pub = block.get("datePublished")
                mod = block.get("dateModified")
                if pub and not data.date_published:
                    data.date_published = str(pub).strip()[:30]
                if mod and not data.date_modified:
                    data.date_modified = str(mod).strip()[:30]

    # ------------------------------------------------------------------ #
    #  Form Accessibility & Conversion Affordances                         #
    # ------------------------------------------------------------------ #
    def _extract_forms(self, soup: BeautifulSoup, data: PageData) -> None:
        forms = soup.find_all("form")
        if not forms:
            return
        data.has_form = True

        for form in forms:
            inputs = form.find_all(["input", "textarea", "select"])
            for inp in inputs:
                itype = (inp.get("type") or "text").lower()
                if itype in ("hidden", "submit", "button", "image", "reset"):
                    continue
                iid = inp.get("id")
                has_label = False
                if iid and soup.find("label", attrs={"for": iid}):
                    has_label = True
                elif inp.find_parent("label"):
                    has_label = True
                elif inp.get("aria-label") or inp.get("aria-labelledby"):
                    has_label = True

                if not has_label:
                    data.form_inputs_missing_labels += 1

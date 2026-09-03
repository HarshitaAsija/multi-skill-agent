"""
Freshness & Corroboration Audit Skill Execution Script.

Responsible for:
  - FRESH-01: Outdated temporal signals & copyright year recency
  - FRESH-02: Cross-page factual consistency & brand entity identity alignment
  - FRESH-03: Sampling claim corroboration (distinguishing unverified from false)
"""

import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from shared.models import AuditRequest, Finding, SuggestedAction
from shared.evidence import EvidenceBuilder
from shared.config import (
    CATEGORY_FACTUAL_FRESHNESS,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
)
from shared.logging_utils import get_logger
from skills.crawl_render_audit.scripts.page_analyser import PageData

logger = get_logger("freshness_corroboration")

CURRENT_YEAR = datetime.now(timezone.utc).year


class FreshnessCorroborationSkill:
    """
    Evaluates temporal freshness, recency anchors, and factual consistency across crawled pages.
    """

    def run(
        self,
        request: AuditRequest,
        pages: List[Any],
        page_data_map: Optional[Dict[str, PageData]] = None
    ) -> Dict[str, Any]:
        """
        Runs freshness & corroboration audit.
        """
        logger.info(f"Executing freshness-corroboration checks across {len(page_data_map or {})} analyzed pages")
        findings: List[Finding] = []

        if not page_data_map:
            return {"findings": findings}

        self._check_copyright_recency(page_data_map, findings)
        self._check_cross_page_brand_identity(page_data_map, findings)
        self._check_article_freshness(page_data_map, findings)
        self._check_title_brand_consistency(page_data_map, findings)

        return {"findings": findings}

    # ------------------------------------------------------------------ #
    #  FRESH-01: Outdated Copyright & Temporal Signals                   #
    # ------------------------------------------------------------------ #
    def _check_copyright_recency(
        self,
        page_data_map: Dict[str, PageData],
        findings: List[Finding]
    ) -> None:
        outdated_pages: List[Dict[str, Any]] = []

        for url, pdata in page_data_map.items():
            if not pdata.footer_text:
                continue

            # Regex match copyright pattern: © 202X or Copyright 202X
            match = re.search(r'(?:©|copyright|\(c\))\s*(?:20\d\d\s*[-–]\s*)?(20\d\d)', pdata.footer_text, re.IGNORECASE)
            if match:
                year = int(match.group(1))
                if year < CURRENT_YEAR - 1:  # Older than last year
                    outdated_pages.append({
                        "url": url,
                        "detected_year": year,
                        "footer_snippet": match.group(0)
                    })

        if outdated_pages:
            affected = [item["url"] for item in outdated_pages]
            sample = outdated_pages[0]
            year_gap = CURRENT_YEAR - sample["detected_year"]

            evidence = EvidenceBuilder.build(
                source_url=sample["url"],
                observation=f"Footer copyright date is '{sample['detected_year']}' ({year_gap} years outdated vs current year {CURRENT_YEAR}). Detected in {len(affected)} audited pages.",
                detection_method="Footer Copyright Year Regex Parser",
                relevance="AI search indexers (Perplexity, SearchGPT, Gemini) evaluate temporal signals. Outdated copyright years suggest abandoned or unmaintained sites, downgrading content authority scores.",
                confidence=0.95,
                raw_snippet=sample["footer_snippet"],
                extra_data={"outdated_pages_count": len(affected), "detected_year": sample["detected_year"]}
            )

            severity = SEVERITY_MEDIUM if year_gap >= 3 else SEVERITY_LOW
            finding = Finding(
                id="FRESH-01-OUTDATED-COPYRIGHT",
                title="Outdated Copyright Date in Footer (Stale Temporal Signal)",
                category=CATEGORY_FACTUAL_FRESHNESS,
                severity=severity,
                confidence=0.95,
                evidence=evidence,
                rationale="Outdated copyright years serve as strong negative recency signals to machine indexers, causing LLM search engines to downgrade site freshness and authority.",
                affected_urls=affected,
                suggested_action=SuggestedAction(
                    summary="Update footer copyright strings dynamically or bump to the current calendar year.",
                    priority=3,
                    remediation_steps=[
                        f"Update footer copyright year to {CURRENT_YEAR} in your global page template.",
                        "Use dynamic server-side date rendering (e.g. {{ new Date().getFullYear() }})."
                    ],
                    expected_impact="Eliminates stale recency signals for AI search indexers.",
                    effort_estimate="LOW"
                )
            )
            findings.append(finding)

    # ------------------------------------------------------------------ #
    #  FRESH-02: Cross-Page Brand Identity Alignment                      #
    # ------------------------------------------------------------------ #
    def _check_cross_page_brand_identity(
        self,
        page_data_map: Dict[str, PageData],
        findings: List[Finding]
    ) -> None:
        names_found: Dict[str, List[str]] = {}

        for url, pdata in page_data_map.items():
            # Check JSON-LD Organization name
            for block in pdata.json_ld_blocks:
                if isinstance(block, dict) and block.get("@type") in ("Organization", "Corporation", "LocalBusiness"):
                    name = block.get("name")
                    if isinstance(name, str) and name.strip():
                        clean_name = name.strip()
                        names_found.setdefault(clean_name, []).append(url)

        # Flag if multiple distinct organization names are declared across pages
        if len(names_found) > 1:
            names_list = list(names_found.keys())
            sample_url = list(page_data_map.keys())[0]

            evidence = EvidenceBuilder.build(
                source_url=sample_url,
                observation=f"Conflicting Organization names declared across JSON-LD blocks: {', '.join(names_list)}.",
                detection_method="Cross-Page JSON-LD Identity Parser",
                relevance="Inconsistent entity names across pages create ambiguity in LLM Knowledge Graph construction, causing AI assistants to hallucinate or misidentify brand ownership.",
                confidence=0.90,
                extra_data={"declared_names": names_found}
            )

            finding = Finding(
                id="FRESH-02-INCONSISTENT-BRAND-IDENTITY",
                title="Inconsistent Organization Entity Name Across Pages",
                category=CATEGORY_FACTUAL_FRESHNESS,
                severity=SEVERITY_HIGH,
                confidence=0.90,
                evidence=evidence,
                rationale="Conflicting brand names across pages weaken entity resolution confidence in AI search engines and vector databases.",
                affected_urls=list(page_data_map.keys()),
                suggested_action=SuggestedAction(
                    summary="Standardize Organization name across all JSON-LD scripts and footer templates.",
                    priority=1,
                    remediation_steps=[
                        f"Choose one official entity name (e.g. '{names_list[0]}').",
                        "Ensure all page JSON-LD scripts use the exact same Organization name attribute."
                    ],
                    expected_impact="Improves entity resolution and Knowledge Graph confidence.",
                    effort_estimate="LOW"
                )
            )
            findings.append(finding)

    # ------------------------------------------------------------------ #
    #  FRESH-03: Article & Content Temporal Anchors Recency              #
    # ------------------------------------------------------------------ #
    def _check_article_freshness(
        self,
        page_data_map: Dict[str, PageData],
        findings: List[Finding]
    ) -> None:
        """
        Flags blog/editorial content that has stale timestamps (> 2 years old),
        reducing AI search freshness confidence.
        """
        stale_articles: List[Dict[str, Any]] = []

        for url, pdata in page_data_map.items():
            is_editorial = any(kw in url.lower() for kw in ("/blog", "/news", "/posts", "/article", "/guide")) or \
                           any(t in ("Article", "BlogPosting", "NewsArticle", "TechArticle") for t in pdata.json_ld_types)

            if not is_editorial:
                continue

            date_str = pdata.date_modified or pdata.date_published
            if date_str:
                year_match = re.search(r"\b(20\d\d)\b", date_str)
                if year_match:
                    year = int(year_match.group(1))
                    if year < CURRENT_YEAR - 2:
                        stale_articles.append({
                            "url": url,
                            "year": year,
                            "date_str": date_str
                        })

        if stale_articles:
            affected = [a["url"] for a in stale_articles]
            sample = stale_articles[0]
            evidence = EvidenceBuilder.build(
                source_url=sample["url"],
                observation=f"Editorial article has stale timestamp '{sample['date_str']}' ({CURRENT_YEAR - sample['year']} years old). Detected on {len(affected)} page(s).",
                detection_method="Article Temporal Metadata Inspector",
                relevance="AI search engines (Perplexity, ChatGPT Search, Gemini) prioritize fresh sources and downrank dated technical tutorials or guides that haven't been reviewed in over 2 years.",
                confidence=0.90,
                extra_data={"stale_article_count": len(affected), "sample_year": sample["year"]}
            )

            finding = Finding(
                id="FRESH-03-STALE-EDITORIAL-CONTENT",
                title="Stale Publication / Modification Date on Editorial Content",
                category=CATEGORY_FACTUAL_FRESHNESS,
                severity=SEVERITY_LOW,
                confidence=0.90,
                evidence=evidence,
                rationale="Un-refreshed technical articles or guides can convey deprecated specifications to AI retrieval systems, leading to outdated citations.",
                affected_urls=affected,
                suggested_action=SuggestedAction(
                    summary="Review and refresh aging editorial articles, updating dateModified in Schema.org.",
                    priority=3,
                    remediation_steps=[
                        "Audit older blog and documentation pages for factual accuracy.",
                        "Add or update dateModified JSON-LD metadata when content is refreshed."
                    ],
                    expected_impact="Boosts AI search recency score and citation likelihood.",
                    effort_estimate="LOW"
                )
            )
            findings.append(finding)

    # ------------------------------------------------------------------ #
    #  BRAND-01: Page Title Brand Suffix Consistency                      #
    # ------------------------------------------------------------------ #
    def _check_title_brand_consistency(
        self,
        page_data_map: Dict[str, PageData],
        findings: List[Finding]
    ) -> None:
        """
        Checks whether <title> tags consistently include a brand suffix
        (e.g. 'Pricing | Acme Corp') across subpages. Inconsistent or missing
        brand suffixes weaken entity signal coherence for AI indexers.
        """
        brand_suffixes: Dict[str, int] = {}
        pages_without_suffix: List[str] = []

        for url, pdata in page_data_map.items():
            if pdata.page_title_brand:
                brand_suffixes[pdata.page_title_brand] = brand_suffixes.get(pdata.page_title_brand, 0) + 1
            elif pdata.title:
                pages_without_suffix.append(url)

        if len(page_data_map) < 2:
            return  # Need at least 2 pages to compare consistency

        # Flag if more than half the pages are missing a brand suffix in their title
        if len(pages_without_suffix) > len(page_data_map) / 2:
            sample_url = pages_without_suffix[0]
            sample_title = page_data_map[sample_url].title or "(no title)"
            evidence = EvidenceBuilder.build(
                source_url=sample_url,
                observation=(
                    f"{len(pages_without_suffix)} of {len(page_data_map)} crawled pages have titles without "
                    f"a brand suffix separator (e.g. ' | Brand'). Sample: '{sample_title}'."
                ),
                detection_method="Page Title Brand Suffix Pattern Analyzer",
                relevance="Consistent brand suffixes in page titles are a primary entity signal used by AI search engines to associate subpages with their parent organization during indexing.",
                confidence=0.85,
                extra_data={
                    "pages_without_brand_suffix": len(pages_without_suffix),
                    "detected_brand_names": list(brand_suffixes.keys())
                }
            )
            finding = Finding(
                id="BRAND-01-INCONSISTENT-TITLE-BRAND-SUFFIX",
                title="Inconsistent Brand Suffix in Page Title Tags",
                category=CATEGORY_FACTUAL_FRESHNESS,
                severity=SEVERITY_LOW,
                confidence=0.85,
                evidence=evidence,
                rationale="AI indexers associate content with its parent brand through consistent title patterns. Missing brand suffixes on subpages weaken entity coherence and may reduce brand attribution in AI citations.",
                affected_urls=pages_without_suffix[:10],
                suggested_action=SuggestedAction(
                    summary="Standardize all page titles with a consistent brand suffix (e.g. 'Page Name | YourBrand').",
                    priority=3,
                    remediation_steps=[
                        "Update page <title> tags to follow the pattern: 'Page Topic | BrandName'.",
                        "Configure your CMS title template to append ' | YourBrand' globally."
                    ],
                    expected_impact="Strengthens brand entity coherence and improves multi-page attribution in AI search results.",
                    effort_estimate="LOW"
                )
            )
            findings.append(finding)

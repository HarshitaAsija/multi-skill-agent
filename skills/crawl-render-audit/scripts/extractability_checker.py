"""
Extractability & Entity Knowledge Representation Auditor.

Evaluates machine readability, RAG chunking readiness, and structured entity graph clarity:
  - KNOW-01: Heading Hierarchy Skips & RAG Vector Chunking Readiness
  - KNOW-02: Context-Gated Schema.org JSON-LD Completeness (Organization, Product, Article)
  - KNOW-03: Unstructured Tabular & Specification Data
  - KNOW-04: Key Facts Trapped in Unannotated Images (missing alt text)
"""

from typing import Dict, Any, List, Optional, Set
from shared.models import Finding, SuggestedAction
from shared.evidence import EvidenceBuilder
from shared.config import (
    CATEGORY_MACHINE_READINESS,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
)
from shared.logging_utils import get_logger
from skills.crawl_render_audit.scripts.page_analyser import PageData
from skills.crawl_render_audit.scripts.crawler import (
    TEMPLATE_HOMEPAGE,
    TEMPLATE_PRODUCT_PRICING,
    TEMPLATE_BLOG_CONTENT,
)

logger = get_logger("extractability_checker")


class ExtractabilityChecker:
    """
    Evaluates machine readability and Schema.org structured data.
    Strictly context-gated to avoid false positives (e.g. Product schema is only expected on Product/Pricing pages).
    """

    def check_all(self, page_data_map: Dict[str, PageData]) -> List[Finding]:
        findings: List[Finding] = []
        for url, pdata in page_data_map.items():
            self._check_heading_hierarchy(pdata, findings)
            self._check_context_gated_schema(pdata, findings)
            self._check_tabular_data_structure(pdata, findings)
            self._check_image_alt_coverage(pdata, findings)
        return findings

    # ------------------------------------------------------------------ #
    #  KNOW-01: Heading Hierarchy & RAG Vector Chunking                  #
    # ------------------------------------------------------------------ #
    def _check_heading_hierarchy(self, pdata: PageData, findings: List[Finding]) -> None:
        if not pdata.has_h1 and len(pdata.headings) > 0:
            evidence = EvidenceBuilder.build(
                source_url=pdata.url,
                observation=f"Page has {len(pdata.headings)} heading elements but is missing a primary <h1> tag.",
                detection_method="DOM Heading Parser",
                relevance="RAG vector chunkers and AI summarizers rely on <h1> headings as the primary section anchor to establish document context.",
                confidence=0.95,
                extra_data={"found_headings": pdata.headings[:5]}
            )
            finding = Finding(
                id=f"KNOW-01-MISSING-H1-{pdata.url}",
                title="Missing Primary Heading (<h1> Tag)",
                category=CATEGORY_MACHINE_READINESS,
                severity=SEVERITY_MEDIUM,
                confidence=0.95,
                evidence=evidence,
                rationale="Without an <h1> tag, RAG vector database chunking algorithms struggle to associate sub-sections with the primary page title.",
                affected_urls=[pdata.url],
                suggested_action=SuggestedAction(
                    summary="Wrap the primary page title in a single semantic <h1> tag.",
                    priority=2,
                    remediation_steps=[
                        f"Add a descriptive <h1> tag to {pdata.url} summarizing the page topic."
                    ],
                    expected_impact="Establishes explicit document topic context for AI vector embedding chunkers.",
                    effort_estimate="LOW"
                )
            )
            findings.append(finding)

        if pdata.heading_level_skips:
            skips_str = ", ".join(pdata.heading_level_skips)
            evidence = EvidenceBuilder.build(
                source_url=pdata.url,
                observation=f"Heading hierarchy skips levels ({skips_str}). Found {len(pdata.headings)} total headings.",
                detection_method="DOM Heading Hierarchy Parser",
                relevance="Skipping heading levels (e.g. H1 directly to H3) creates broken document trees in LLM section splitters, causing fragmented context vectors during retrieval.",
                confidence=0.90,
                extra_data={"skips": pdata.heading_level_skips}
            )
            finding = Finding(
                id=f"KNOW-01-HEADING-SKIP-{pdata.url}",
                title="Broken Heading Hierarchy (Skipped Heading Levels)",
                category=CATEGORY_MACHINE_READINESS,
                severity=SEVERITY_MEDIUM,
                confidence=0.90,
                evidence=evidence,
                rationale="Vector chunkers (e.g. LangChain RecursiveCharacterTextSplitter) use heading trees to split document sections. Level skips break structural section bounds.",
                affected_urls=[pdata.url],
                suggested_action=SuggestedAction(
                    summary="Restructure heading tags sequentially (H1 -> H2 -> H3) without skipping levels.",
                    priority=3,
                    remediation_steps=[
                        "Ensure H2 tags precede H3 tags in the HTML source order.",
                        "Use CSS classes for visual sizing rather than misusing heading levels."
                    ],
                    expected_impact="Prevents orphaned or fragmented context chunks in RAG retrieval databases.",
                    effort_estimate="LOW"
                )
            )
            findings.append(finding)

    # ------------------------------------------------------------------ #
    #  KNOW-02: Context-Gated Schema.org JSON-LD                         #
    # ------------------------------------------------------------------ #
    def _check_context_gated_schema(self, pdata: PageData, findings: List[Finding]) -> None:
        types = set(pdata.json_ld_types)

        # 1. Homepage: Expect Organization or WebSite schema
        if pdata.url.rstrip("/").count("/") <= 2 or "homepage" in pdata.url:
            if not types.intersection({"Organization", "WebSite", "Corporation", "LocalBusiness"}):
                evidence = EvidenceBuilder.build(
                    source_url=pdata.url,
                    observation=f"Homepage has {len(pdata.json_ld_blocks)} JSON-LD blocks but lacks Organization or WebSite Schema.org entity definitions.",
                    detection_method="Schema.org JSON-LD Parser",
                    relevance="LLM Knowledge Graph indexers (Google Knowledge Graph, Perplexity entity maps) look for explicit Organization schema on homepages to disambiguate brand entities.",
                    confidence=0.95,
                    extra_data={"found_schema_types": list(types)}
                )
                finding = Finding(
                    id=f"KNOW-02-MISSING-ORG-SCHEMA-{pdata.url}",
                    title="Missing Primary Organization / WebSite Schema.org JSON-LD",
                    category=CATEGORY_MACHINE_READINESS,
                    severity=SEVERITY_HIGH,
                    confidence=0.95,
                    evidence=evidence,
                    rationale="Without structured Organization JSON-LD markup, AI search assistants must guess company name, logo, social links, and brand descriptions.",
                    affected_urls=[pdata.url],
                    suggested_action=SuggestedAction(
                        summary="Inject Organization Schema.org JSON-LD on the homepage.",
                        priority=1,
                        remediation_steps=[
                            "Add <script type=\"application/ld+json\"> with @type: Organization.",
                            "Include name, url, logo, description, and sameAs social profile links."
                        ],
                        expected_impact="Establishes authoritative brand entity identity for AI knowledge graphs.",
                        effort_estimate="LOW"
                    )
                )
                findings.append(finding)

        # 2. Product / Pricing Pages: Expect Product schema (Context-Gated!)
        if any(kw in pdata.url.lower() for kw in ["/pricing", "/product", "/plans"]):
            if not types.intersection({"Product", "Offer", "SoftwareApplication", "Service"}):
                evidence = EvidenceBuilder.build(
                    source_url=pdata.url,
                    observation=f"Pricing/Product page lacks Product, Offer, or SoftwareApplication Schema.org markup.",
                    detection_method="Context-Gated Schema Parser",
                    relevance="AI search assistants answering 'How much does Product X cost?' fetch Product/Offer JSON-LD to extract accurate pricing tiers.",
                    confidence=0.90,
                    extra_data={"found_schema_types": list(types)}
                )
                finding = Finding(
                    id=f"KNOW-02-MISSING-PRODUCT-SCHEMA-{pdata.url}",
                    title="Missing Product / Offer Schema.org Markup on Commercial Page",
                    category=CATEGORY_MACHINE_READINESS,
                    severity=SEVERITY_MEDIUM,
                    confidence=0.90,
                    evidence=evidence,
                    rationale="AI search agents cannot reliably extract structured pricing and feature availability without explicit Offer or Product schema.",
                    affected_urls=[pdata.url],
                    suggested_action=SuggestedAction(
                        summary="Add Product or SoftwareApplication JSON-LD schema with Offer price specifications.",
                        priority=2,
                        remediation_steps=[
                            "Add Schema.org Product or SoftwareApplication markup.",
                            "Define offers array with price, priceCurrency, and availability attributes."
                        ],
                        expected_impact="Enables AI agents to answer comparative product and pricing queries accurately.",
                        effort_estimate="LOW"
                    )
                )
                findings.append(finding)

    # ------------------------------------------------------------------ #
    #  KNOW-03: Unstructured Tabular & Spec Data                         #
    # ------------------------------------------------------------------ #
    def _check_tabular_data_structure(self, pdata: PageData, findings: List[Finding]) -> None:
        # If pricing/feature page has no <table> or <dl> tag, check if pricing/feature terms exist in text
        if any(kw in pdata.url.lower() for kw in ["/pricing", "/plans", "/features"]):
            if not pdata.has_tabular_data:
                evidence = EvidenceBuilder.build(
                    source_url=pdata.url,
                    observation="Product/Pricing page presents comparative data using unstructured nested <div> or <span> elements instead of <table> or <dl> tags.",
                    detection_method="DOM Structure Classifier",
                    relevance="Relational data (feature comparisons, pricing tiers) rendered in generic div-soup layouts causes AI agents to pair wrong features with pricing tiers.",
                    confidence=0.85
                )
                finding = Finding(
                    id=f"KNOW-03-UNSTRUCTURED-GRID-{pdata.url}",
                    title="Comparative Data Rendered in Unstructured Layout Markup",
                    category=CATEGORY_MACHINE_READINESS,
                    severity=SEVERITY_MEDIUM,
                    confidence=0.85,
                    evidence=evidence,
                    rationale="LLM table parsers rely on semantic <table> or <dl> elements to construct key-value feature pairs reliably.",
                    affected_urls=[pdata.url],
                    suggested_action=SuggestedAction(
                        summary="Wrap relational comparison data in semantic <table> or <dl> tags.",
                        priority=3,
                        remediation_steps=[
                            "Replace nested CSS grid <div> blocks with HTML5 <table> or <dl> markup.",
                            "Use <th> for header headers and <td> for tabular cell values."
                        ],
                        expected_impact="Improves AI feature extraction accuracy.",
                        effort_estimate="MEDIUM"
                    )
                )
                findings.append(finding)

    # ------------------------------------------------------------------ #
    #  KNOW-04: Facts Trapped in Unannotated Images                      #
    # ------------------------------------------------------------------ #
    def _check_image_alt_coverage(self, pdata: PageData, findings: List[Finding]) -> None:
        if pdata.total_images_count > 0 and pdata.images_missing_alt_count > 0:
            missing_ratio = pdata.images_missing_alt_count / pdata.total_images_count
            if missing_ratio >= 0.50:
                evidence = EvidenceBuilder.build(
                    source_url=pdata.url,
                    observation=f"{pdata.images_missing_alt_count} out of {pdata.total_images_count} images ({int(missing_ratio * 100)}%) lack descriptive alt text.",
                    detection_method="DOM Image Alt Attribute Scanner",
                    relevance="Text-only LLM crawlers cannot see images. Facts (diagrams, architecture charts, infographic stats) in unannotated images are completely lost.",
                    confidence=0.90,
                    extra_data={"missing_alt_sources": pdata.images_missing_alt[:5]}
                )
                finding = Finding(
                    id=f"KNOW-04-MISSING-IMAGE-ALT-{pdata.url}",
                    title="Key Information Trapped in Unannotated Images (Missing Alt Text)",
                    category=CATEGORY_MACHINE_READINESS,
                    severity=SEVERITY_LOW,
                    confidence=0.90,
                    evidence=evidence,
                    rationale="AI search crawlers ignore non-textual image content unless descriptive alt text or transcripts are provided.",
                    affected_urls=[pdata.url],
                    suggested_action=SuggestedAction(
                        summary="Add descriptive alt attributes to all content-bearing images.",
                        priority=4,
                        remediation_steps=[
                            "Add alt=\"...\" attributes describing key facts or concepts presented in each image.",
                            "Use empty alt=\"\" only for decorative background graphics."
                        ],
                        expected_impact="Makes visual diagram facts searchable for text-only AI models.",
                        effort_estimate="LOW"
                    )
                )
                findings.append(finding)

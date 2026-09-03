"""
Engagement Audit Skill Execution Script.

Responsible for:
  - ENG-01: Above-the-fold value proposition clarity
  - ENG-02: Deep landing page context isolation (breadcrumbs & navigation landmarks)
  - ENG-03: Call-To-Action (CTA) label discoverability & ambiguity
"""

import re
from typing import Dict, Any, List, Optional
from shared.models import AuditRequest, Finding, SuggestedAction
from shared.evidence import EvidenceBuilder
from shared.config import (
    CATEGORY_ONSITE_ENGAGEMENT,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
)
from shared.logging_utils import get_logger
from skills.crawl_render_audit.scripts.page_analyser import PageData

logger = get_logger("engagement_audit")

# Generic/ambiguous CTA labels that reduce user conversion momentum
GENERIC_CTA_PATTERNS = [
    r"^click\s*here$",
    r"^learn\s*more$",
    r"^submit$",
    r"^more$",
    r"^read\s*more$",
    r"^continue$",
    r"^go$",
]


class EngagementAuditSkill:
    """
    Evaluates on-site human visitor and agent engagement friction.
    """

    def run(
        self,
        request: AuditRequest,
        pages: List[Any],
        page_data_map: Optional[Dict[str, PageData]] = None
    ) -> Dict[str, Any]:
        """
        Runs on-site engagement checks across crawled pages.
        """
        logger.info(f"Executing engagement-audit checks across {len(page_data_map or {})} analyzed pages")
        findings: List[Finding] = []

        if not page_data_map:
            return {"findings": findings}

        for url, pdata in page_data_map.items():
            self._check_above_the_fold_value_prop(pdata, findings)
            self._check_context_isolation_breadcrumbs(pdata, findings)
            self._check_cta_label_ambiguity(pdata, findings)
            self._check_form_friction(pdata, findings)

        # ENG-05: Check globally if any page has FAQ/Speakable schema
        self._check_faq_schema_presence(page_data_map, findings)

        return {"findings": findings}

    # ------------------------------------------------------------------ #
    #  ENG-01: Above-The-Fold Value Proposition Clarity                   #
    # ------------------------------------------------------------------ #
    def _check_above_the_fold_value_prop(self, pdata: PageData, findings: List[Finding]) -> None:
        # Check homepage or main landing pages
        if pdata.url.rstrip("/").count("/") <= 3:
            if not pdata.has_h1 and pdata.word_count < 30:
                evidence = EvidenceBuilder.build(
                    source_url=pdata.url,
                    observation=f"Landing page has zero <h1> headings and only {pdata.word_count} visible words in the top viewport section.",
                    detection_method="Hero Section Content Analyzer",
                    relevance="First-time human visitors and AI agents arriving on a landing page require a clear <h1> title and descriptive value proposition within 3 seconds to understand what the product/brand offers.",
                    confidence=0.90
                )
                finding = Finding(
                    id=f"ENG-01-HERO-VALUE-PROP-{pdata.url}",
                    title="Above-The-Fold Value Proposition Deficit",
                    category=CATEGORY_ONSITE_ENGAGEMENT,
                    severity=SEVERITY_HIGH,
                    confidence=0.90,
                    evidence=evidence,
                    rationale="Vague or sparse hero sections increase immediate bounce rate and fail to communicate core offerings to visiting AI agents.",
                    affected_urls=[pdata.url],
                    suggested_action=SuggestedAction(
                        summary="State what the product/brand does and who it is for in the top viewport section.",
                        priority=1,
                        remediation_steps=[
                            "Add a clear <h1> heading stating your core offering.",
                            "Include a 1-2 sentence hero description explaining key benefits."
                        ],
                        expected_impact="Reduces visitor bounce rate and clarifies brand purpose for AI indexers.",
                        effort_estimate="LOW"
                    )
                )
                findings.append(finding)

    # ------------------------------------------------------------------ #
    #  ENG-02: Deep Subpage Context Isolation (Breadcrumbs)               #
    # ------------------------------------------------------------------ #
    def _check_context_isolation_breadcrumbs(self, pdata: PageData, findings: List[Finding]) -> None:
        # Only check deep subpages (URL path depth >= 2, e.g. /docs/api or /product/features)
        url_depth = pdata.url.rstrip("/").count("/")
        if url_depth >= 4:  # Deep subpage (e.g. https://domain.com/sub/page)
            if not pdata.has_breadcrumb and not pdata.has_nav_landmark:
                evidence = EvidenceBuilder.build(
                    source_url=pdata.url,
                    observation="Deep subpage lacks breadcrumb navigation (<nav aria-label=\"breadcrumb\">) and top-level navigation landmarks.",
                    detection_method="DOM Navigation Landmark Classifier",
                    relevance="Over 60% of search and AI traffic lands directly on deep subpages. Without breadcrumbs or navigation anchors, visitors arriving on subpages experience cognitive drop-off and cannot navigate upward.",
                    confidence=0.85
                )
                finding = Finding(
                    id=f"ENG-02-CONTEXT-ISOLATION-{pdata.url}",
                    title="Deep Subpage Context Isolation (Missing Breadcrumbs)",
                    category=CATEGORY_ONSITE_ENGAGEMENT,
                    severity=SEVERITY_MEDIUM,
                    confidence=0.85,
                    evidence=evidence,
                    rationale="Visitors arriving directly on subpages via search referrals lose navigation context if parent links or breadcrumbs are absent.",
                    affected_urls=[pdata.url],
                    suggested_action=SuggestedAction(
                        summary="Add semantic breadcrumb navigation to all deep subpages.",
                        priority=3,
                        remediation_steps=[
                            "Inject <nav aria-label=\"breadcrumb\"> with links to parent sections.",
                            "Include BreadcrumbList JSON-LD schema."
                        ],
                        expected_impact="Improves user orientation and context retention on referral traffic.",
                        effort_estimate="LOW"
                    )
                )
                findings.append(finding)

    # ------------------------------------------------------------------ #
    #  ENG-03: CTA Label Ambiguity & Low Discoverability                 #
    # ------------------------------------------------------------------ #
    def _check_cta_label_ambiguity(self, pdata: PageData, findings: List[Finding]) -> None:
        ambiguous_ctas: List[str] = []

        for label in pdata.button_cta_labels:
            clean = label.strip().lower()
            for pattern in GENERIC_CTA_PATTERNS:
                if re.match(pattern, clean):
                    if label not in ambiguous_ctas:
                        ambiguous_ctas.append(label)

        if ambiguous_ctas:
            evidence = EvidenceBuilder.build(
                source_url=pdata.url,
                observation=f"Page contains {len(ambiguous_ctas)} ambiguous or generic CTA button labels: {', '.join(ambiguous_ctas)}.",
                detection_method="Button CTA Label Text Classifier",
                relevance="Generic CTA labels ('click here', 'learn more', 'submit') reduce conversion momentum. Explicit, action-oriented labels ('Start Free Trial', 'Download Guide') increase click-through rates.",
                confidence=0.90,
                extra_data={"flagged_cta_labels": ambiguous_ctas}
            )

            finding = Finding(
                id=f"ENG-03-GENERIC-CTA-{pdata.url}",
                title="Generic / Ambiguous Call-To-Action (CTA) Button Labels",
                category=CATEGORY_ONSITE_ENGAGEMENT,
                severity=SEVERITY_LOW,
                confidence=0.90,
                evidence=evidence,
                rationale="Generic CTA text provides weak information scent to visitors and machine agents deciding what action to take next.",
                affected_urls=[pdata.url],
                suggested_action=SuggestedAction(
                    summary="Replace generic CTA button labels with specific, benefit-oriented action text.",
                    priority=4,
                    remediation_steps=[
                        "Replace 'Click Here' or 'Submit' with descriptive text (e.g. 'Get Started Free', 'Download Report')."
                    ],
                    expected_impact="Increases user conversion rates and next-step action clarity.",
                    effort_estimate="LOW"
                )
            )
            findings.append(finding)

    # ------------------------------------------------------------------ #
    #  ENG-04: Form Conversion Friction & Missing Field Labels           #
    # ------------------------------------------------------------------ #
    def _check_form_friction(self, pdata: PageData, findings: List[Finding]) -> None:
        """
        Checks for forms with missing accessible labels or high input friction.
        """
        if pdata.has_form and pdata.form_inputs_missing_labels > 0:
            evidence = EvidenceBuilder.build(
                source_url=pdata.url,
                observation=f"Form contains {pdata.form_inputs_missing_labels} input field(s) lacking associated <label for='...'> tags or aria-label attributes.",
                detection_method="DOM Form Accessibility & Label Inspector",
                relevance="Unlabeled form inputs create accessibility violations and user hesitation on conversion pages, causing significant drop-off for visitors referred by AI assistants.",
                confidence=0.90,
                extra_data={"missing_label_count": pdata.form_inputs_missing_labels}
            )
            finding = Finding(
                id=f"ENG-04-FORM-INPUT-FRICTION-{pdata.url}",
                title="Form Input Accessibility & Conversion Friction (Missing Field Labels)",
                category=CATEGORY_ONSITE_ENGAGEMENT,
                severity=SEVERITY_MEDIUM if pdata.form_inputs_missing_labels >= 3 else SEVERITY_LOW,
                confidence=0.90,
                evidence=evidence,
                rationale="Visitors arriving via AI search recommendation need seamless conversion paths. Missing labels cause cognitive drop-off and screen reader barriers.",
                affected_urls=[pdata.url],
                suggested_action=SuggestedAction(
                    summary="Attach explicit <label for='...'> or aria-label attributes to all form inputs.",
                    priority=2,
                    remediation_steps=[
                        "Ensure each <input> has a unique id attribute.",
                        "Add a corresponding <label for='inputId'> with clear placeholder or title text."
                    ],
                    expected_impact="Reduces form abandonment and improves conversion rate for arriving visitors.",
                    effort_estimate="LOW"
                )
            )
            findings.append(finding)

    # ------------------------------------------------------------------ #
    #  ENG-05: FAQPage / Speakable Schema for AI Answer Eligibility      #
    # ------------------------------------------------------------------ #
    def _check_faq_schema_presence(
        self,
        page_data_map: Dict[str, PageData],
        findings: List[Finding]
    ) -> None:
        """
        Checks if any commercial or support page uses FAQPage or Speakable
        JSON-LD schema — the primary mechanism for content to appear in
        AI-generated answers and voice search results.
        """
        # Check if any page already has FAQ schema
        for pdata in page_data_map.values():
            if pdata.has_faq_schema:
                return  # Site already uses it somewhere, no finding needed

        # No FAQ schema found on any page — flag it
        affected = list(page_data_map.keys())
        sample_url = affected[0] if affected else "/"
        evidence = EvidenceBuilder.build(
            source_url=sample_url,
            observation=f"No FAQPage, Speakable, QAPage, or HowTo JSON-LD schema detected across {len(affected)} crawled page(s).",
            detection_method="JSON-LD Schema Type Inventory",
            relevance="FAQPage and Speakable JSON-LD schema are the primary mechanisms by which content is directly ingested into AI-generated answers (Google SGE, Bing Copilot, ChatGPT Search) and voice assistant responses.",
            confidence=0.90,
            extra_data={"pages_checked": len(affected)}
        )
        finding = Finding(
            id="ENG-05-MISSING-FAQ-SPEAKABLE-SCHEMA",
            title="No FAQPage / Speakable Schema for AI Answer Engine Eligibility",
            category=CATEGORY_ONSITE_ENGAGEMENT,
            severity=SEVERITY_MEDIUM,
            confidence=0.90,
            evidence=evidence,
            rationale="Sites without FAQPage or Speakable schema miss direct eligibility for AI-generated answer snippets. Competitors who implement it get their content surfaced verbatim in AI answers.",
            affected_urls=affected[:5],
            suggested_action=SuggestedAction(
                summary="Add FAQPage JSON-LD schema to commercial, pricing, or support pages with common buyer questions.",
                priority=2,
                remediation_steps=[
                    "Identify the 5-10 most common pre-purchase questions your customers ask.",
                    "Add a <script type='application/ld+json'> block with @type: FAQPage and a mainEntity array of Questions and Answers.",
                    "Validate the schema using Google's Rich Results Test."
                ],
                expected_impact="Makes content eligible for direct AI-generated answer snippets and voice search results, increasing brand visibility without requiring a click.",
                effort_estimate="LOW"
            )
        )
        findings.append(finding)

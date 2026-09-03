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

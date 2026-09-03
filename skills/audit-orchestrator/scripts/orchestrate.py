"""
Audit Orchestrator Core Execution Script.
Serves as the ONE designated entrypoint for the Agent Skill Marketplace.
Coordinates specialist skills, deduplicates findings, calibrates severities, and outputs the final AuditResult.
"""

from typing import Dict, Any, List, Optional
from shared.models import AuditRequest, AuditResult, Finding, ProactiveRecommendation
from shared.url_utils import is_valid_url, normalize_url
from shared.http_client import SafeHTTPClient
from shared.severity import SeverityEvaluator
from shared.config import (
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
    CATEGORY_AI_DISCOVERABILITY,
    CATEGORY_MACHINE_READINESS,
)
from shared.logging_utils import get_logger
from shared.report_validator import validate_report
from skills import load_skill_module

logger = get_logger("orchestrator")

# Dynamically load specialist skills from hyphenated directory paths
crawl_mod = load_skill_module("crawl-render-audit", "audit.py")
freshness_mod = load_skill_module("freshness-corroboration", "audit.py")
engagement_mod = load_skill_module("engagement-audit", "audit.py")

CrawlRenderAuditSkill = crawl_mod.CrawlRenderAuditSkill
FreshnessCorroborationSkill = freshness_mod.FreshnessCorroborationSkill
EngagementAuditSkill = engagement_mod.EngagementAuditSkill

class Orchestrator:
    """
    Sole entrypoint coordinator for the Agent Skill Marketplace.
    """

    def __init__(
        self,
        http_client: Optional[SafeHTTPClient] = None,
        crawl_skill: Optional[Any] = None,
        freshness_skill: Optional[Any] = None,
        engagement_skill: Optional[Any] = None
    ):
        self.http_client = http_client or SafeHTTPClient()
        self.crawl_skill = crawl_skill or CrawlRenderAuditSkill(http_client=self.http_client)
        self.freshness_skill = freshness_skill or FreshnessCorroborationSkill()
        self.engagement_skill = engagement_skill or EngagementAuditSkill()

    def run_audit(
        self,
        url: str,
        max_pages: int = 15,
        max_depth: int = 2,
        timeout_seconds: float = 10.0
    ) -> Dict[str, Any]:
        """
        Executes complete multi-skill audit pipeline for a given website URL.
        Returns serialized dict matching the required JSON report schema.
        """
        # 1. Input Validation & Normalization
        if not is_valid_url(url):
            logger.error(f"Invalid target URL provided: {url}")
            return self._build_invalid_url_result(url)

        normalized_url = normalize_url(url)
        logger.info(f"Initiating audit for normalized target: {normalized_url}")

        request = AuditRequest(
            url=normalized_url,
            max_pages=max_pages,
            max_depth=max_depth,
            timeout_seconds=timeout_seconds
        )

        all_findings: List[Finding] = []
        proactive_recommendations: List[ProactiveRecommendation] = []

        # 2. Execute Skill 1: crawl-render-audit (includes extractability & entity knowledge checks)
        crawl_res = self.crawl_skill.run(request)
        crawl_findings = crawl_res.get("findings", [])
        crawled_pages = crawl_res.get("pages", [])
        page_data_map = crawl_res.get("page_data_map", {})
        all_findings.extend(crawl_findings)

        # 3. Execute Skill 2: freshness-corroboration (recency & cross-page brand consistency)
        if crawled_pages:
            freshness_res = self.freshness_skill.run(
                request,
                pages=crawled_pages,
                page_data_map=page_data_map
            )
            all_findings.extend(freshness_res.get("findings", []))

        # 4. Execute Skill 3: engagement-audit (hero value prop, context retention, CTA clarity)
        if crawled_pages:
            engagement_res = self.engagement_skill.run(
                request,
                pages=crawled_pages,
                page_data_map=page_data_map
            )
            all_findings.extend(engagement_res.get("findings", []))

        # 5. Deduplicate and Calibrate Findings
        final_findings = self._deduplicate_and_calibrate(all_findings)

        # 6. Generate Contextual Proactive Recommendations
        proactive_recommendations = self._generate_proactive_recommendations(
            normalized_url, final_findings
        )

        # 7. Construct Final AuditResult Object
        result = AuditResult(
            site=normalized_url,
            findings=final_findings,
            proactive_recommendations=proactive_recommendations,
            ai_readiness_score=self._compute_ai_readiness_score(final_findings)
        )

        result_dict = result.to_dict()

        # 8. Validate output schema before returning
        is_valid, schema_errors = validate_report(result_dict)
        if not is_valid:
            logger.warning(f"Report schema validation flagged {len(schema_errors)} issue(s):")
            for err in schema_errors:
                logger.warning(f"  - {err}")
        else:
            logger.info("Report schema validation passed.")

        return result_dict

    def _normalize_finding_id(self, finding_id: str) -> str:
        """
        Strips URL suffixes from per-page finding IDs so that repeated
        issues across multiple pages group under the same base check ID.
        Example: 'DISC-05-MISSING-CANONICAL-https://site.com/about' -> 'DISC-05-MISSING-CANONICAL'
        """
        for prefix in ("-http://", "-https://"):
            if prefix in finding_id:
                return finding_id.split(prefix)[0]
        return finding_id

    def _deduplicate_and_calibrate(self, raw_findings: List[Finding]) -> List[Finding]:
        """
        Deduplicates and groups findings sharing the same base check ID, merges affected URLs,
        calibrates severities globally based on scope/confidence, and sorts by severity.
        """
        grouped: Dict[str, Finding] = {}

        for finding in raw_findings:
            base_id = self._normalize_finding_id(finding.id)
            if base_id not in grouped:
                finding.id = base_id
                grouped[base_id] = finding
            else:
                existing = grouped[base_id]
                for url in finding.affected_urls:
                    if url not in existing.affected_urls:
                        existing.affected_urls.append(url)
                if finding.confidence > existing.confidence:
                    existing.confidence = finding.confidence

        calibrated: List[Finding] = []
        for finding in grouped.values():
            finding.severity = SeverityEvaluator.calibrate_finding_severity(
                base_severity=finding.severity,
                affected_url_count=len(finding.affected_urls),
                confidence=finding.confidence
            )
            if len(finding.affected_urls) > 1 and not finding.evidence.observation.startswith("Observed across"):
                finding.evidence.observation = (
                    f"Observed across {len(finding.affected_urls)} pages. "
                    f"{finding.evidence.observation}"
                )
            calibrated.append(finding)

        # Sort order: CRITICAL > HIGH > MEDIUM > LOW, then by suggested action priority, then confidence
        severity_order = {
            SEVERITY_CRITICAL: 0,
            SEVERITY_HIGH: 1,
            SEVERITY_MEDIUM: 2,
            SEVERITY_LOW: 3,
        }
        calibrated.sort(
            key=lambda f: (
                severity_order.get(f.severity.upper(), 99),
                f.suggested_action.priority if f.suggested_action else 99,
                -f.confidence
            )
        )

        # Cap findings to prevent report bloat
        max_report_findings = 30
        return calibrated[:max_report_findings]

    def _generate_proactive_recommendations(
        self,
        site: str,
        findings: List[Finding]
    ) -> List[ProactiveRecommendation]:
        """
        Generates forward-looking architecture and AI-optimization recommendations.
        """
        recs: List[ProactiveRecommendation] = [
            ProactiveRecommendation(
                id="REC-PROACTIVE-01-LLMS-TXT",
                title="Publish an llms.txt Machine Index Manifest",
                category=CATEGORY_AI_DISCOVERABILITY,
                rationale="The /llms.txt standard provides AI assistants and autonomous agents with a curated markdown directory of authoritative pages, reducing hallucination and token overhead.",
                suggested_implementation="Publish a clean /llms.txt file at the domain root with curated markdown links to documentation, pricing, and product specs."
            ),
            ProactiveRecommendation(
                id="REC-PROACTIVE-02-FAQ-JSON-LD",
                title="Adopt Semantic FAQPage & Speakable Schema Markup",
                category=CATEGORY_MACHINE_READINESS,
                rationale="Conversational AI search engines directly ingest Question/Answer entities from FAQPage schema to construct verified answers for users.",
                suggested_implementation="Implement JSON-LD FAQPage markup on commercial and support pages answering the most common user purchase queries."
            )
        ]
        return recs

    def _build_invalid_url_result(self, raw_url: str) -> Dict[str, Any]:
        """Generates graceful error result for invalid URLs."""
        result = AuditResult(
            site=raw_url,
            findings=[]
        )
        return result.to_dict()

    def _compute_ai_readiness_score(self, findings: List[Finding]) -> int:
        """
        Computes a 0–100 AI Readiness Score weighted by severity.

        Scoring deductions per finding:
          CRITICAL: -25 pts  (blocks all machine discovery)
          HIGH:     -15 pts  (major discoverability or accessibility gap)
          MEDIUM:   -7 pts   (contextual extractability issue)
          LOW:      -3 pts   (best-practice omission)

        Score is floored at 0.
        """
        DEDUCTIONS = {
            "CRITICAL": 25,
            "HIGH": 15,
            "MEDIUM": 7,
            "LOW": 3,
        }
        score = 100
        for finding in findings:
            deduction = DEDUCTIONS.get(finding.severity.upper(), 0)
            score -= deduction
        return max(0, score)

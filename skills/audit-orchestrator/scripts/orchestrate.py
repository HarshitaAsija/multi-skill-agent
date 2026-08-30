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
from shared.logging_utils import get_logger
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

        # 2. Execute Skill 1: crawl-render-audit
        crawl_res = self.crawl_skill.run(request)
        crawl_findings = crawl_res.get("findings", [])
        crawled_pages = crawl_res.get("pages", [])
        all_findings.extend(crawl_findings)

        # 3. Execute Skill 2: freshness-corroboration (if pages crawled successfully)
        if crawled_pages:
            freshness_res = self.freshness_skill.run(request, pages=crawled_pages)
            all_findings.extend(freshness_res.get("findings", []))

        # 4. Execute Skill 3: engagement-audit (if pages crawled successfully)
        if crawled_pages:
            engagement_res = self.engagement_skill.run(request, pages=crawled_pages)
            all_findings.extend(engagement_res.get("findings", []))

        # 5. Deduplicate and Calibrate Findings
        final_findings = self._deduplicate_and_calibrate(all_findings)

        # 6. Construct Final AuditResult Object
        result = AuditResult(
            site=normalized_url,
            findings=final_findings,
            proactive_recommendations=proactive_recommendations
        )

        return result.to_dict()

    def _deduplicate_and_calibrate(self, raw_findings: List[Finding]) -> List[Finding]:
        """
        Deduplicates findings sharing the same ID and calibrates severities globally.
        """
        seen_ids = set()
        deduped: List[Finding] = []

        for finding in raw_findings:
            if finding.id in seen_ids:
                continue
            seen_ids.add(finding.id)

            # Calibrate severity using central severity module
            finding.severity = SeverityEvaluator.calibrate_finding_severity(
                base_severity=finding.severity,
                affected_url_count=len(finding.affected_urls),
                confidence=finding.confidence
            )
            deduped.append(finding)

        return deduped

    def _build_invalid_url_result(self, raw_url: str) -> Dict[str, Any]:
        """Generates graceful error result for invalid URLs."""
        result = AuditResult(
            site=raw_url,
            findings=[]
        )
        return result.to_dict()

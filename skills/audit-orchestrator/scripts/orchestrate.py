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
from shared.market_intelligence import MarketIntelligenceEngine
from shared.gemini_client import GeminiClient
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
        engagement_skill: Optional[Any] = None,
        gemini_client: Optional[Any] = None
    ):
        self.http_client = http_client or SafeHTTPClient()
        self.crawl_skill = crawl_skill or CrawlRenderAuditSkill(http_client=self.http_client)
        self.freshness_skill = freshness_skill or FreshnessCorroborationSkill()
        self.engagement_skill = engagement_skill or EngagementAuditSkill()
        self.market_intel_engine = MarketIntelligenceEngine()
        self.gemini_client = gemini_client or GeminiClient()

    def run_audit(
        self,
        url: str,
        max_pages: int = 40,
        max_depth: int = 4,
        timeout_seconds: float = 10.0,
        gemini_api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes complete multi-skill audit pipeline for a given website URL.
        Returns serialized dict matching the required JSON report schema.
        """
        if gemini_api_key:
            self.gemini_client = GeminiClient(api_key=gemini_api_key)

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

        # 6. Run AI Answerability & Market Intelligence Engine
        market_intel_report = None
        detected_industry_label = "General Business"
        if page_data_map:
            try:
                mi_obj = self.market_intel_engine.analyze(
                    root_url=normalized_url,
                    page_data_map=page_data_map,
                    gemini_client=self.gemini_client
                )
                market_intel_report = mi_obj.to_dict()
                detected_industry_label = mi_obj.industry_label
            except Exception as e:
                logger.warning(f"Market intelligence analysis encountered an issue: {e}")

        # 7. Generate Contextual Proactive Recommendations (Gemini or Calibrated)
        proactive_recommendations = self._generate_proactive_recommendations(
            site=normalized_url,
            findings=final_findings,
            page_data_map=page_data_map,
            industry_label=detected_industry_label
        )

        # 8. Executive Synthesis via Gemini if active
        executive_synthesis = None
        score = self._compute_ai_readiness_score(final_findings)
        if self.gemini_client and getattr(self.gemini_client, "is_available", lambda: False)():
            try:
                brand = self.market_intel_engine._infer_brand_name(normalized_url, page_data_map)
                cov = market_intel_report.get("market_question_coverage_pct", 0) if market_intel_report else 0
                executive_synthesis = self.gemini_client.generate_executive_synthesis(
                    brand=brand,
                    root_url=normalized_url,
                    score=score,
                    industry_label=detected_industry_label,
                    total_findings=len(final_findings),
                    coverage_pct=cov
                )
            except Exception as e:
                logger.debug(f"Executive synthesis skipped: {e}")

        # 9. Construct Final AuditResult Object
        result = AuditResult(
            site=normalized_url,
            findings=final_findings,
            proactive_recommendations=proactive_recommendations,
            ai_readiness_score=score,
            market_intelligence=market_intel_report,
            executive_synthesis=executive_synthesis
        )

        result_dict = result.to_dict()

        # 10. Validate output schema before returning
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
        findings: List[Finding],
        page_data_map: Optional[Dict[str, Any]] = None,
        industry_label: str = "General Business"
    ) -> List[ProactiveRecommendation]:
        """
        Generates forward-looking architecture and AI-optimization recommendations.
        Uses Google Gemini API for site-specific intelligence when available,
        falling back to calibrated standard recommendations.
        """
        if self.gemini_client and getattr(self.gemini_client, "is_available", lambda: False)():
            try:
                brand = self.market_intel_engine._infer_brand_name(site, page_data_map or {})
                content_sample = self.market_intel_engine._aggregate_text(page_data_map or {})
                findings_summary = [
                    {"id": f.id, "title": f.title, "severity": f.severity}
                    for f in findings[:10]
                ]
                ai_recs = self.gemini_client.generate_site_tailored_recommendations(
                    brand=brand,
                    root_url=site,
                    industry_label=industry_label,
                    findings_summary=findings_summary,
                    site_content_summary=content_sample
                )
                if ai_recs and isinstance(ai_recs, list) and len(ai_recs) >= 3:
                    parsed_recs: List[ProactiveRecommendation] = []
                    valid_cats = {
                        CATEGORY_AI_DISCOVERABILITY,
                        CATEGORY_MACHINE_READINESS,
                        "factual_freshness",
                        "onsite_engagement",
                    }
                    for idx, r in enumerate(ai_recs, 1):
                        rid = str(r.get("id") or f"REC-AI-{idx:02d}").strip()
                        rtitle = str(r.get("title") or "").strip()
                        rcat = str(r.get("category") or CATEGORY_MACHINE_READINESS).strip()
                        if rcat not in valid_cats:
                            rcat = CATEGORY_MACHINE_READINESS
                        rrat = str(r.get("rationale") or "").strip()
                        rimp = str(r.get("suggested_implementation") or "").strip()
                        if rtitle and rrat and rimp:
                            parsed_recs.append(
                                ProactiveRecommendation(
                                    id=rid,
                                    title=rtitle,
                                    category=rcat,
                                    rationale=rrat,
                                    suggested_implementation=rimp
                                )
                            )
                    if len(parsed_recs) >= 3:
                        return parsed_recs
            except Exception as e:
                logger.debug(f"Gemini proactive recommendations fallback: {e}")

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
            ),
            ProactiveRecommendation(
                id="REC-PROACTIVE-03-ENTITY-GRAPH",
                title="Deep Knowledge Graph Disambiguation via Wikidata & Multi-Registry sameAs",
                category=CATEGORY_MACHINE_READINESS,
                rationale="AI search engines resolve brand identity across the wider web by linking sameAs arrays to authoritative knowledge hubs (Wikidata Q-ID, Wikipedia, LinkedIn, Crunchbase), preventing mistaken identity when multiple brands share similar names.",
                suggested_implementation="Enrich Organization schema on the homepage with an array of verified sameAs URLs pointing to Wikipedia, Wikidata, LinkedIn, and official corporate registry entries."
            ),
            ProactiveRecommendation(
                id="REC-PROACTIVE-04-RAG-CHUNKING",
                title="Optimize Heading-to-Text Density for RAG Vector Retrievers",
                category=CATEGORY_MACHINE_READINESS,
                rationale="LLM vector chunkers (LangChain, LlamaIndex) perform best when document sub-sections are strictly bounded by sequential H2/H3 headings containing 150 to 400 words of semantic text. Overly long continuous walls of text dilute vector embedding similarity.",
                suggested_implementation="Structure content blocks so each distinct sub-concept is introduced by a descriptive H2/H3 tag followed by 150-400 words of focused, quote-ready text."
            ),
            ProactiveRecommendation(
                id="REC-PROACTIVE-05-AI-ACTION-MANIFEST",
                title="Expose Machine-Readable Action Specifications (OpenAPI Manifest)",
                category=CATEGORY_AI_DISCOVERABILITY,
                rationale="Next-generation autonomous agents (ChatGPT Operator, Claude Computer Use) transition from informational search to transactional execution. Publishing an OpenAPI specification enables autonomous agents to interact with your services programmatically.",
                suggested_implementation="Publish an OpenAPI / Swagger 3.0 specification at /.well-known/openapi.yaml or /api/spec, and link to it from /llms.txt."
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

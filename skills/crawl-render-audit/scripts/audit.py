"""
Crawl & Render Audit Skill Execution Script.
Phase 1 Skeleton: Provides clean interface for crawl & DOM parity checks.
"""

from typing import Dict, Any, List, Optional
from shared.models import AuditRequest, Finding, EvidenceItem, SuggestedAction
from shared.http_client import SafeHTTPClient, HTTPResponse
from shared.evidence import EvidenceBuilder
from shared.severity import SeverityEvaluator
from shared.config import CATEGORY_AI_DISCOVERABILITY, CATEGORY_MACHINE_READINESS, SEVERITY_CRITICAL
from shared.logging_utils import get_logger

logger = get_logger("crawl_render_audit")

class CrawlRenderAuditSkill:
    """
    Skill module responsible for HTTP accessibility, robots.txt, sitemaps, and DOM parity.
    """

    def __init__(self, http_client: Optional[SafeHTTPClient] = None):
        self.http_client = http_client or SafeHTTPClient()

    def run(self, request: AuditRequest) -> Dict[str, Any]:
        """
        Runs crawl & render checks.
        Returns dict containing 'findings' (List[Finding]) and 'pages' (List[HTTPResponse]).
        """
        logger.info(f"Starting crawl-render-audit for {request.url}")
        findings: List[Finding] = []
        crawled_pages: List[HTTPResponse] = []

        # 1. Primary Entrypoint HTTP Fetch
        resp = self.http_client.fetch(request.url)
        crawled_pages.append(resp)

        if not resp.is_success:
            evidence = EvidenceBuilder.build(
                source_url=request.url,
                observation=f"Primary HTTP request failed with status code {resp.status_code}. Error: {resp.error or 'Unreachable'}",
                detection_method="HTTP GET Fetch",
                confidence=1.0,
                http_status=resp.status_code,
                extra_data={"error": resp.error, "redirect_chain": resp.redirect_chain}
            )
            finding = Finding(
                id="DISC-00-UNREACHABLE",
                title="Target Website Unreachable via Primary HTTP GET Request",
                category=CATEGORY_AI_DISCOVERABILITY,
                severity=SEVERITY_CRITICAL,
                confidence=1.0,
                evidence=evidence,
                rationale="AI search crawlers and machine agents require standard HTTP 200 responses to index site content. An unreachable root URL completely blocks machine discovery.",
                affected_urls=[request.url],
                suggested_action=SuggestedAction(
                    summary="Ensure domain DNS records, SSL certificates, and web server ports (80/443) are properly configured.",
                    priority=1,
                    remediation_steps=[
                        "Verify DNS resolution and ping target host.",
                        "Inspect firewall/WAF settings to ensure non-authenticated HTTP GET traffic is permitted.",
                        "Test response header using 'curl -I " + request.url + "'."
                    ],
                    expected_impact="Restores full machine and human access to the website.",
                    effort_estimate="HIGH"
                )
            )
            findings.append(finding)

        logger.info(f"crawl-render-audit completed. Found {len(findings)} initial issues.")
        return {
            "findings": findings,
            "pages": crawled_pages,
        }

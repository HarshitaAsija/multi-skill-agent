"""
Crawl & Render Audit Skill Implementation.

Responsible for:
  - Robots.txt parsing & AI bot disallow checks
  - Sitemap.xml discovery, validation, and freshness checks
  - Bounded representative template crawling
  - Raw HTML page analysis (title, meta tags, canonicals, landmarks, headings)
  - Producing empirical evidence-backed findings under ai_discoverability and machine_readiness
"""

from typing import Dict, Any, List, Optional
from shared.models import AuditRequest, Finding, SuggestedAction
from shared.http_client import SafeHTTPClient, HTTPResponse
from shared.evidence import EvidenceBuilder
from shared.config import (
    CATEGORY_AI_DISCOVERABILITY,
    CATEGORY_MACHINE_READINESS,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
)
from shared.logging_utils import get_logger

from .robots_parser import RobotsParser, RobotsParseResult
from .sitemap_parser import SitemapParser, SitemapParseResult
from .crawler import BoundedCrawler, CrawledPage
from .page_analyser import PageAnalyser, PageData

logger = get_logger("crawl_render_audit")


class CrawlRenderAuditSkill:
    """
    Skill module executing access, robots.txt, sitemap, bounded crawl, and page analysis.
    """

    def __init__(self, http_client: Optional[SafeHTTPClient] = None):
        self.http_client = http_client or SafeHTTPClient()
        self.robots_parser = RobotsParser(http_client=self.http_client)
        self.sitemap_parser = SitemapParser(http_client=self.http_client)
        self.crawler = BoundedCrawler(http_client=self.http_client)
        self.analyser = PageAnalyser()

    def run(self, request: AuditRequest) -> Dict[str, Any]:
        """
        Executes crawl & render audit pipeline.
        Returns dict containing 'findings' (List[Finding]), 'pages' (List[HTTPResponse]),
        and 'page_data_map' (Dict[url, PageData]).
        """
        logger.info(f"Initiating crawl-render-audit for {request.url}")
        findings: List[Finding] = []
        crawled_responses: List[HTTPResponse] = []
        page_data_map: Dict[str, PageData] = {}

        # 1. Fetch & Parse robots.txt
        robots: RobotsParseResult = self.robots_parser.fetch_and_parse(request.url)
        self._check_robots_ai_blocks(request.url, robots, findings)

        # 2. Fetch & Parse sitemap.xml
        sitemap: SitemapParseResult = self.sitemap_parser.fetch_and_parse(
            root_url=request.url,
            declared_sitemap_urls=robots.sitemap_urls
        )
        self._check_sitemap_health(request.url, sitemap, findings)

        # 3. Execute Bounded Representative Crawl
        seed_urls = sitemap.get_high_priority_urls(min_priority=0.7)
        crawled_pages: List[CrawledPage] = self.crawler.crawl(
            root_url=request.url,
            robots=robots,
            seed_urls=seed_urls
        )

        for cp in crawled_pages:
            crawled_responses.append(cp.response)

        # Handle case where root fetch fails
        if not crawled_responses or not crawled_responses[0].is_success:
            self._handle_unreachable_target(request.url, crawled_responses, findings)
            return {
                "findings": findings,
                "pages": crawled_responses,
                "page_data_map": page_data_map,
            }

        # 4. Perform Signal Analysis on Crawled Pages
        for cp in crawled_pages:
            pdata = self.analyser.analyse(cp.url, cp.response.body)
            page_data_map[cp.url] = pdata

            # Page-level discoverability checks
            self._check_meta_robots_noindex(pdata, findings)
            self._check_canonical_integrity(pdata, findings)

        logger.info(f"crawl-render-audit completed. Found {len(findings)} discoverability issues.")
        return {
            "findings": findings,
            "pages": crawled_responses,
            "page_data_map": page_data_map,
        }

    # ------------------------------------------------------------------ #
    #  Audit Checks                                                        #
    # ------------------------------------------------------------------ #
    def _check_robots_ai_blocks(
        self,
        root_url: str,
        robots: RobotsParseResult,
        findings: List[Finding]
    ) -> None:
        if not robots.is_accessible:
            return

        blocked_ai = robots.get_blocked_ai_agents()
        if blocked_ai:
            evidence = EvidenceBuilder.build(
                source_url=robots.robots_url,
                observation=f"robots.txt explicitly blocks {len(blocked_ai)} major AI agent User-Agents from root path '/': {', '.join(blocked_ai)}",
                detection_method="robots.txt User-Agent Parser",
                relevance="LLM search engines (ChatGPT, Perplexity, Claude) respect robots.txt disallows. Blocking AI agents prevents your brand content from being indexed, summarized, or cited in AI search results.",
                confidence=1.0,
                http_status=robots.http_status,
                raw_snippet=robots.raw_content[:500],
                extra_data={"blocked_ai_agents": blocked_ai}
            )
            finding = Finding(
                id="DISC-01-ROBOTS-AI-BLOCK",
                title="AI Crawler Disallow Directives Detected in robots.txt",
                category=CATEGORY_AI_DISCOVERABILITY,
                severity=SEVERITY_HIGH,
                confidence=1.0,
                evidence=evidence,
                rationale="Explicitly blocking AI agent User-Agents in robots.txt prevents LLM search platforms (ChatGPT, Perplexity, Claude) from discovering, retrieving, and citing your brand's official content.",
                affected_urls=[robots.robots_url, root_url],
                suggested_action=SuggestedAction(
                    summary="Audit robots.txt directives and grant explicit Allow rules to preferred AI search agents.",
                    priority=1,
                    remediation_steps=[
                        f"Review User-agent rules in {robots.robots_url}.",
                        "Remove root Disallow: / directives for GPTBot, ChatGPT-User, PerplexityBot, and ClaudeBot.",
                        "Verify directive changes using Google Search Console or robots.txt testing tools."
                    ],
                    expected_impact="Restores full AI search engine indexability and citation eligibility.",
                    effort_estimate="LOW"
                )
            )
            findings.append(finding)

    def _check_sitemap_health(
        self,
        root_url: str,
        sitemap: SitemapParseResult,
        findings: List[Finding]
    ) -> None:
        if not sitemap.is_accessible:
            evidence = EvidenceBuilder.build(
                source_url=root_url,
                observation=f"No accessible sitemap.xml discovered at declared paths or standard fallback paths ({sitemap.error or '404 Not Found'}).",
                detection_method="Sitemap XML Probe",
                relevance="XML sitemaps provide machine crawlers with an authoritative index of canonical page URLs and modification dates (<lastmod>). Missing sitemaps slow down AI search indexing.",
                confidence=0.90,
                extra_data={"attempted_paths": SitemapParser.FALLBACK_PATHS}
            )
            finding = Finding(
                id="DISC-02-MISSING-SITEMAP",
                title="Missing or Unreachable XML Sitemap",
                category=CATEGORY_AI_DISCOVERABILITY,
                severity=SEVERITY_MEDIUM,
                confidence=0.90,
                evidence=evidence,
                rationale="Without an XML sitemap, machine crawlers must rely exclusively on link graph traversal, increasing the risk of missing deep product or documentation pages.",
                affected_urls=[root_url],
                suggested_action=SuggestedAction(
                    summary="Generate an automated XML sitemap and register its URL in robots.txt.",
                    priority=2,
                    remediation_steps=[
                        "Generate a standard sitemap.xml containing all canonical page URLs and <lastmod> timestamps.",
                        "Publish sitemap at https://yourdomain.com/sitemap.xml.",
                        "Add 'Sitemap: https://yourdomain.com/sitemap.xml' directive to robots.txt."
                    ],
                    expected_impact="Accelerates AI crawler discovery of new and updated content.",
                    effort_estimate="LOW"
                )
            )
            findings.append(finding)
        elif not sitemap.has_lastmod:
            evidence = EvidenceBuilder.build(
                source_url=sitemap.sitemap_url or root_url,
                observation=f"Sitemap at {sitemap.sitemap_url} contains {len(sitemap.entries)} URLs but zero <lastmod> modification timestamps.",
                detection_method="Sitemap XML Parser",
                relevance="AI search systems prioritize content recency. Without <lastmod> timestamps in sitemaps, AI crawlers cannot determine when facts or pages were updated.",
                confidence=0.95,
                http_status=sitemap.http_status,
                extra_data={"url_count": len(sitemap.entries)}
            )
            finding = Finding(
                id="DISC-03-SITEMAP-NO-LASTMOD",
                title="Sitemap Lacks Content Modification Timestamps (<lastmod>)",
                category=CATEGORY_AI_DISCOVERABILITY,
                severity=SEVERITY_LOW,
                confidence=0.95,
                evidence=evidence,
                rationale="Missing <lastmod> XML tags prevent AI search indexers from prioritizing updated content, causing search bots to fetch stale cached versions.",
                affected_urls=[sitemap.sitemap_url or root_url],
                suggested_action=SuggestedAction(
                    summary="Include ISO 8601 <lastmod> date timestamps for all entries in sitemap.xml.",
                    priority=3,
                    remediation_steps=[
                        "Configure your CMS or sitemap generator to emit <lastmod>YYYY-MM-DD</lastmod> tags.",
                        "Ensure timestamp updates whenever page content is modified."
                    ],
                    expected_impact="Improves AI index recency signals for fresh content.",
                    effort_estimate="LOW"
                )
            )
            findings.append(finding)

    def _check_meta_robots_noindex(self, pdata: PageData, findings: List[Finding]) -> None:
        if pdata.meta_robots and "noindex" in pdata.meta_robots.lower():
            evidence = EvidenceBuilder.build(
                source_url=pdata.url,
                observation=f"Page contains <meta name=\"robots\" content=\"{pdata.meta_robots}\"> directive explicitly prohibiting indexing.",
                detection_method="HTML Meta Tag Parser",
                relevance="The noindex directive instructs all search engines and AI bots to exclude the page from search indexes and retrieval systems.",
                confidence=1.0,
                raw_snippet=f"<meta name=\"robots\" content=\"{pdata.meta_robots}\">"
            )
            finding = Finding(
                id=f"DISC-04-NOINDEX-{pdata.url}",
                title="Page Explicitly Blocked from Indexing via Meta Robots Tag",
                category=CATEGORY_AI_DISCOVERABILITY,
                severity=SEVERITY_HIGH,
                confidence=1.0,
                evidence=evidence,
                rationale="Pages with noindex meta tags are completely excluded from AI assistant knowledge bases and search engine indexes.",
                affected_urls=[pdata.url],
                suggested_action=SuggestedAction(
                    summary="Remove noindex directive from indexable brand landing pages.",
                    priority=1,
                    remediation_steps=[
                        "Inspect <head> metadata for <meta name=\"robots\" content=\"noindex\">.",
                        "Change content attribute to 'index, follow' on public marketing or product pages."
                    ],
                    expected_impact="Allows AI assistants to index and cite the page.",
                    effort_estimate="LOW"
                )
            )
            findings.append(finding)

    def _check_canonical_integrity(self, pdata: PageData, findings: List[Finding]) -> None:
        if not pdata.canonical_url:
            evidence = EvidenceBuilder.build(
                source_url=pdata.url,
                observation="Page lacks a <link rel=\"canonical\"> tag in the HTML <head> section.",
                detection_method="HTML Canonical Parser",
                relevance="Canonical URLs prevent duplicate content penalties and instruct AI indexers which URL variant is the authoritative source.",
                confidence=0.90
            )
            finding = Finding(
                id=f"DISC-05-MISSING-CANONICAL-{pdata.url}",
                title="Missing Canonical Tag (<link rel=\"canonical\">)",
                category=CATEGORY_AI_DISCOVERABILITY,
                severity=SEVERITY_LOW,
                confidence=0.90,
                evidence=evidence,
                rationale="Missing canonical URL tags can cause AI indexers to split authority across query parameter variants or trailing slash permutations.",
                affected_urls=[pdata.url],
                suggested_action=SuggestedAction(
                    summary="Add self-referential canonical URL tag to page <head>.",
                    priority=4,
                    remediation_steps=[
                        f"Inject <link rel=\"canonical\" href=\"{pdata.url}\"> into the page <head>."
                    ],
                    expected_impact="Consolidates page authority for machine indexers.",
                    effort_estimate="LOW"
                )
            )
            findings.append(finding)

    def _handle_unreachable_target(
        self,
        target_url: str,
        responses: List[HTTPResponse],
        findings: List[Finding]
    ) -> None:
        status = responses[0].status_code if responses else 0
        error = responses[0].error if responses else "Unreachable"
        evidence = EvidenceBuilder.build(
            source_url=target_url,
            observation=f"Primary HTTP GET request failed with status code {status}. Error: {error}",
            detection_method="HTTP GET Fetch",
            relevance="An unreachable target URL prevents machine agents and human users from accessing the site.",
            confidence=1.0,
            http_status=status
        )
        finding = Finding(
            id="DISC-00-UNREACHABLE",
            title="Target Website Unreachable via HTTP GET Request",
            category=CATEGORY_AI_DISCOVERABILITY,
            severity=SEVERITY_CRITICAL,
            confidence=1.0,
            evidence=evidence,
            rationale="AI search crawlers and machine agents require standard HTTP 200 responses to index site content. An unreachable root URL completely blocks machine discovery.",
            affected_urls=[target_url],
            suggested_action=SuggestedAction(
                summary="Ensure web server ports (80/443), DNS resolution, and SSL certificates are properly configured.",
                priority=1,
                remediation_steps=[
                    "Verify domain DNS records.",
                    "Ensure firewall/WAF permits non-authenticated HTTP GET traffic.",
                    "Inspect web server access and error logs."
                ],
                expected_impact="Restores website availability.",
                effort_estimate="HIGH"
            )
        )
        findings.append(finding)

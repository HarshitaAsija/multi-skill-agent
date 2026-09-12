"""
Tests for sitemap.xml parser.
"""

import unittest
from skills import load_skill_module

sitemap_mod = load_skill_module("crawl-render-audit", "sitemap_parser.py")
SitemapParser = sitemap_mod.SitemapParser

SAMPLE_SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <url>
      <loc>https://example.com/</loc>
      <lastmod>2026-01-15</lastmod>
      <priority>1.0</priority>
   </url>
   <url>
      <loc>https://example.com/pricing</loc>
      <lastmod>2026-02-01</lastmod>
      <priority>0.8</priority>
   </url>
   <url>
      <loc>https://example.com/about</loc>
      <priority>0.5</priority>
   </url>
</urlset>
"""

class TestSitemapParser(unittest.TestCase):

    def test_parse_urlset_xml(self):
        parser = SitemapParser()
        entries = parser._parse_xml(SAMPLE_SITEMAP_XML, root_url="https://example.com", current_url="https://example.com/sitemap.xml", depth=0)

        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].url, "https://example.com/")
        self.assertEqual(entries[0].lastmod, "2026-01-15")
        self.assertEqual(entries[0].priority, 1.0)
        self.assertEqual(entries[1].url, "https://example.com/pricing")
        self.assertEqual(entries[1].priority, 0.8)

    def test_malformed_xml_fallback(self):
        """Edge case: Malformed XML should gracefully return empty entries and record syntax errors."""
        parser = SitemapParser()
        entries = parser._parse_xml("<?xml version='1.0'?><urlset><url><loc>no-close-tag", root_url="https://example.com", current_url="https://example.com/sitemap.xml", depth=0)
        self.assertEqual(len(entries), 0)
        self.assertTrue(len(parser._current_parse_errors) > 0)

    def test_sitemap_health_check_emits_disc_02b_on_syntax_error(self):
        """Verify malformed XML emits DISC-02B-SITEMAP-PARSE-ERROR (MEDIUM) instead of DISC-03 (LOW)."""
        from skills import load_skill_module
        audit_mod = load_skill_module("crawl-render-audit", "audit.py")
        CrawlRenderAuditSkill = audit_mod.CrawlRenderAuditSkill
        SitemapParseResult = sitemap_mod.SitemapParseResult

        skill = CrawlRenderAuditSkill()
        findings = []
        malformed_result = SitemapParseResult(
            sitemap_url="https://example.com/sitemap.xml",
            http_status=200,
            is_accessible=True,
            entries=[],
            has_lastmod=False,
            has_syntax_errors=True,
            parse_errors=["XML syntax error: unclosed token"]
        )

        skill._check_sitemap_health("https://example.com", malformed_result, findings)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].id, "DISC-02B-SITEMAP-PARSE-ERROR")
        self.assertEqual(findings[0].severity, "MEDIUM")

    def test_sitemap_health_check_emits_disc_03_only_when_entries_exist(self):
        """Verify DISC-03-SITEMAP-NO-LASTMOD only fires when entries > 0 and has_lastmod is False."""
        from skills import load_skill_module
        audit_mod = load_skill_module("crawl-render-audit", "audit.py")
        CrawlRenderAuditSkill = audit_mod.CrawlRenderAuditSkill
        SitemapParseResult = sitemap_mod.SitemapParseResult
        SitemapEntry = sitemap_mod.SitemapEntry

        skill = CrawlRenderAuditSkill()
        findings = []
        valid_entries = [SitemapEntry(url="https://example.com/page1")]
        no_lastmod_result = SitemapParseResult(
            sitemap_url="https://example.com/sitemap.xml",
            http_status=200,
            is_accessible=True,
            entries=valid_entries,
            has_lastmod=False,
            has_syntax_errors=False
        )

        skill._check_sitemap_health("https://example.com", no_lastmod_result, findings)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].id, "DISC-03-SITEMAP-NO-LASTMOD")
        self.assertEqual(findings[0].severity, "LOW")

    def test_sitemap_health_check_emits_disc_02c_on_degraded_index(self):
        """Verify DISC-02C-SITEMAP-DEGRADED fires when >50% of sub-sitemaps fail, even if entries > 0."""
        from skills import load_skill_module
        audit_mod = load_skill_module("crawl-render-audit", "audit.py")
        CrawlRenderAuditSkill = audit_mod.CrawlRenderAuditSkill
        SitemapParseResult = sitemap_mod.SitemapParseResult
        SitemapEntry = sitemap_mod.SitemapEntry

        skill = CrawlRenderAuditSkill()
        findings = []
        # 3 out of 4 sub-sitemaps failed, only 2 URLs recovered
        surviving_entries = [SitemapEntry(url="https://example.com/p1"), SitemapEntry(url="https://example.com/p2")]
        degraded_result = SitemapParseResult(
            sitemap_url="https://example.com/sitemap_index.xml",
            http_status=200,
            is_accessible=True,
            entries=surviving_entries,
            has_lastmod=False,
            has_syntax_errors=True,
            parse_errors=["XML syntax error on sub-file 1", "XML syntax error on sub-file 2", "XML syntax error on sub-file 3"],
            sub_sitemaps_attempted=4,
            sub_sitemaps_failed=3,
        )

        skill._check_sitemap_health("https://example.com", degraded_result, findings)

        finding_ids = [f.id for f in findings]
        self.assertIn("DISC-02C-SITEMAP-DEGRADED", finding_ids, "Should emit DISC-02C when majority of sub-sitemaps fail")
        self.assertIn("DISC-03-SITEMAP-NO-LASTMOD", finding_ids, "Should also check surviving URLs for lastmod")

        disc_02c = next(f for f in findings if f.id == "DISC-02C-SITEMAP-DEGRADED")
        self.assertEqual(disc_02c.severity, "MEDIUM")

    def test_sub_sitemap_fetch_cap(self):
        """Verify sitemap parser bounds sub-sitemap fetches to MAX_SUB_SITEMAPS_TO_FETCH."""
        from unittest.mock import MagicMock
        from shared.http_client import HTTPResponse

        mock_client = MagicMock()
        # Mock index with 15 sub-sitemaps
        index_xml = "<sitemapindex>" + "".join(f"<sitemap><loc>https://example.com/sub_{i}.xml</loc></sitemap>" for i in range(15)) + "</sitemapindex>"
        sub_xml = "<urlset><url><loc>https://example.com/page</loc></url></urlset>"

        def mock_fetch(url, *args, **kwargs):
            if "index" in url:
                return HTTPResponse(url=url, final_url=url, status_code=200, is_success=True, body=index_xml)
            return HTTPResponse(url=url, final_url=url, status_code=200, is_success=True, body=sub_xml)

        mock_client.fetch.side_effect = mock_fetch

        parser = sitemap_mod.SitemapParser(http_client=mock_client)
        result = parser.fetch_and_parse("https://example.com", ["https://example.com/index.xml"])

        self.assertLessEqual(result.sub_sitemaps_attempted, sitemap_mod.MAX_SUB_SITEMAPS_TO_FETCH)
        self.assertEqual(result.sub_sitemaps_attempted, sitemap_mod.MAX_SUB_SITEMAPS_TO_FETCH)


if __name__ == "__main__":
    unittest.main()


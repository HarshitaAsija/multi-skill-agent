"""
Tests for Template Bucket Sampling and Bounded Crawler.
"""

import unittest
from skills import load_skill_module

crawler_mod = load_skill_module("crawl-render-audit", "crawler.py")
classify_template_bucket = crawler_mod.classify_template_bucket
TEMPLATE_HOMEPAGE = crawler_mod.TEMPLATE_HOMEPAGE
TEMPLATE_ABOUT_COMPANY = crawler_mod.TEMPLATE_ABOUT_COMPANY
TEMPLATE_PRODUCT_PRICING = crawler_mod.TEMPLATE_PRODUCT_PRICING
TEMPLATE_DOCS_API = crawler_mod.TEMPLATE_DOCS_API
TEMPLATE_BLOG_CONTENT = crawler_mod.TEMPLATE_BLOG_CONTENT
TEMPLATE_GENERIC = crawler_mod.TEMPLATE_GENERIC

class TestCrawlerSampling(unittest.TestCase):

    def test_classify_template_buckets(self):
        root = "https://example.com"
        self.assertEqual(classify_template_bucket("https://example.com/", root), TEMPLATE_HOMEPAGE)
        self.assertEqual(classify_template_bucket("https://example.com/about", root), TEMPLATE_ABOUT_COMPANY)
        self.assertEqual(classify_template_bucket("https://example.com/contact-us", root), TEMPLATE_GENERIC)
        self.assertEqual(classify_template_bucket("https://example.com/pricing", root), TEMPLATE_PRODUCT_PRICING)
        self.assertEqual(classify_template_bucket("https://example.com/features/ai-agent", root), TEMPLATE_PRODUCT_PRICING)
        self.assertEqual(classify_template_bucket("https://example.com/docs/api-reference", root), TEMPLATE_DOCS_API)
        self.assertEqual(classify_template_bucket("https://example.com/blog/2026-release", root), TEMPLATE_BLOG_CONTENT)

    def test_conservative_domain_matching(self):
        from shared.url_utils import is_same_domain, get_host_alias
        # Apex <-> www symmetry
        self.assertTrue(is_same_domain("https://example.com/page", "https://www.example.com/"))
        self.assertTrue(is_same_domain("https://www.example.com/page", "https://example.com/"))
        self.assertTrue(is_same_domain("https://example.com/", "https://example.com/foo"))

        # Conservative: arbitrary subdomains are not treated as identical without PSL
        self.assertFalse(is_same_domain("https://open.example.com", "https://example.com"))
        self.assertFalse(is_same_domain("https://attacker.com", "https://example.com"))

        # get_host_alias test
        self.assertEqual(get_host_alias("https://example.com/"), "https://www.example.com/")
        self.assertEqual(get_host_alias("https://www.example.com/pricing"), "https://example.com/pricing")

    def test_crawler_host_alias_fallback_on_bot_block(self):
        """Verify crawler fails over to host alias when root returns WAF 403 or connection drop."""
        from unittest.mock import MagicMock
        from shared.http_client import HTTPResponse
        BoundedCrawler = crawler_mod.BoundedCrawler

        mock_client = MagicMock()
        def mock_fetch(url, *args, **kwargs):
            if url.rstrip("/") == "https://example.com":
                return HTTPResponse(url=url, final_url=url, status_code=403, is_success=False, error="WAF Bot Challenge", body="")
            elif "www.example.com" in url:
                return HTTPResponse(url=url, final_url=url, status_code=200, is_success=True, content_type="text/html", body="<html><body><h1>Welcome</h1></body></html>")
            return HTTPResponse(url=url, final_url=url, status_code=404, is_success=False)

        mock_client.fetch.side_effect = mock_fetch

        crawler = BoundedCrawler(http_client=mock_client, max_pages=2)
        crawled = crawler.crawl("https://example.com")

        self.assertEqual(crawler.host_alias_used, "https://www.example.com/")
        self.assertEqual(len(crawled), 1)
        self.assertEqual(crawled[0].url, "https://www.example.com/")
        self.assertTrue(crawled[0].response.is_success)

    def test_crawler_accepts_html_when_content_type_absent(self):
        """Crawler must not discard pages that return HTTP 200 + HTML body but omit Content-Type header.
        This reproduces the Spotify CDN behaviour seen in production."""
        from unittest.mock import MagicMock
        from shared.http_client import HTTPResponse
        BoundedCrawler = crawler_mod.BoundedCrawler

        mock_client = MagicMock()
        def mock_fetch(url, *args, **kwargs):
            # No content_type header — simulates CDN omitting the header
            return HTTPResponse(
                url=url, final_url=url, status_code=200, is_success=True,
                content_type=None,  # ← the problematic case
                body="<!DOCTYPE html><html><body><h1>Music for everyone</h1></body></html>",
            )

        mock_client.fetch.side_effect = mock_fetch
        crawler = BoundedCrawler(http_client=mock_client, max_pages=1)
        crawled = crawler.crawl("https://example.com")

        self.assertEqual(len(crawled), 1, "Page with absent Content-Type but HTML body must be crawled")
        self.assertEqual(crawled[0].url, "https://example.com/")


if __name__ == "__main__":
    unittest.main()

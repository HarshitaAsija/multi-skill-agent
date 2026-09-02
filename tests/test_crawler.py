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

if __name__ == "__main__":
    unittest.main()

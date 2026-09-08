"""
Tests for Extractability & Entity Knowledge Representation Auditor.
"""

import unittest
from skills import load_skill_module

extract_mod = load_skill_module("crawl-render-audit", "extractability_checker.py")
analyser_mod = load_skill_module("crawl-render-audit", "page_analyser.py")

ExtractabilityChecker = extract_mod.ExtractabilityChecker
PageAnalyser = analyser_mod.PageAnalyser

HTML_WITH_HEADING_SKIPS = """<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
    <h1>Primary Page Title</h1>
    <h3>Skipped H2 Tag Directly to H3</h3>
</body>
</html>
"""

class TestExtractabilityChecker(unittest.TestCase):

    def test_heading_skip_detection(self):
        analyser = PageAnalyser()
        pdata = analyser.analyse("https://example.com/test", HTML_WITH_HEADING_SKIPS)

        checker = ExtractabilityChecker()
        findings = checker.check_all({"https://example.com/test": pdata})

        skip_findings = [f for f in findings if "HEADING-SKIP" in f.id]
        self.assertTrue(len(skip_findings) > 0)
        self.assertEqual(skip_findings[0].severity, "MEDIUM")

    def test_subpage_missing_breadcrumb_schema(self):
        analyser = PageAnalyser()
        html = """<!DOCTYPE html>
<html>
<head><title>Product Features</title></head>
<body>
    <h1>Product Features</h1>
    <p>Detailed capabilities and specifications.</p>
</body>
</html>"""
        pdata = analyser.analyse("https://example.com/products/ai-suite", html)
        checker = ExtractabilityChecker()
        findings = checker.check_all({"https://example.com/products/ai-suite": pdata})

        breadcrumb_findings = [f for f in findings if "KNOW-06-MISSING-BREADCRUMB-SCHEMA" in f.id]
        self.assertTrue(len(breadcrumb_findings) > 0)
        self.assertEqual(breadcrumb_findings[0].severity, "LOW")

    def test_blog_post_missing_article_schema(self):
        analyser = PageAnalyser()
        html = """<!DOCTYPE html>
<html>
<head><title>Guide to RAG Architectures</title></head>
<body>
    <h1>Guide to RAG Architectures</h1>
    <p>Published on September 1, 2026 by Tech Lead.</p>
</body>
</html>"""
        pdata = analyser.analyse("https://example.com/blog/guide-to-rag", html)
        checker = ExtractabilityChecker()
        findings = checker.check_all({"https://example.com/blog/guide-to-rag": pdata})

        article_findings = [f for f in findings if "KNOW-07-MISSING-ARTICLE-SCHEMA" in f.id]
        self.assertTrue(len(article_findings) > 0)
        self.assertEqual(article_findings[0].severity, "MEDIUM")

    def test_facts_trapped_in_embedded_objects(self):
        analyser = PageAnalyser()
        html = """<!DOCTYPE html>
<html>
<head><title>Product Catalog</title></head>
<body>
    <h1>Product Catalog</h1>
    <iframe src="https://docs.google.com/viewer?url=https://example.com/catalog.pdf"></iframe>
</body>
</html>"""
        pdata = analyser.analyse("https://example.com/catalog", html)
        checker = ExtractabilityChecker()
        findings = checker.check_all({"https://example.com/catalog": pdata})

        embed_findings = [f for f in findings if "KNOW-08-FACTS-TRAPPED-IN-EMBED" in f.id]
        self.assertTrue(len(embed_findings) > 0)
        self.assertEqual(embed_findings[0].severity, "MEDIUM")


if __name__ == "__main__":
    unittest.main()


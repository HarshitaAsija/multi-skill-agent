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

if __name__ == "__main__":
    unittest.main()

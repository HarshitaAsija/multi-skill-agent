"""
Tests for Freshness & Corroboration Audit Skill.
"""

import unittest
from skills import load_skill_module
from shared.models import AuditRequest

fresh_mod = load_skill_module("freshness-corroboration", "audit.py")
analyser_mod = load_skill_module("crawl-render-audit", "page_analyser.py")

FreshnessCorroborationSkill = fresh_mod.FreshnessCorroborationSkill
PageAnalyser = analyser_mod.PageAnalyser

OUTDATED_FOOTER_HTML = """<!DOCTYPE html>
<html>
<head><title>Stale Page</title></head>
<body>
    <h1>Welcome</h1>
    <footer><p>© 2021 Acme Corp. All rights reserved.</p></footer>
</body>
</html>
"""

class TestFreshnessSkill(unittest.TestCase):

    def test_outdated_copyright_detection(self):
        analyser = PageAnalyser()
        pdata = analyser.analyse("https://example.com/", OUTDATED_FOOTER_HTML)

        skill = FreshnessCorroborationSkill()
        req = AuditRequest(url="https://example.com/")
        res = skill.run(req, pages=[], page_data_map={"https://example.com/": pdata})

        findings = res.get("findings", [])
        self.assertTrue(len(findings) > 0)
        self.assertEqual(findings[0].id, "FRESH-01-OUTDATED-COPYRIGHT")

    def test_stale_article_date_detection(self):
        stale_article_html = """<!DOCTYPE html>
        <html>
        <head>
            <title>Old Tech Article</title>
            <meta property="article:published_time" content="2020-05-15T08:00:00Z">
        </head>
        <body>
            <h1>Outdated Tutorial</h1>
            <p>Content from 2020.</p>
        </body>
        </html>
        """
        analyser = PageAnalyser()
        pdata = analyser.analyse("https://example.com/blog/tutorial", stale_article_html)

        skill = FreshnessCorroborationSkill()
        req = AuditRequest(url="https://example.com/")
        res = skill.run(req, pages=[], page_data_map={"https://example.com/blog/tutorial": pdata})

        findings = res.get("findings", [])
        fresh_03 = [f for f in findings if "FRESH-03" in f.id]
        self.assertTrue(len(fresh_03) > 0)
        self.assertEqual(fresh_03[0].severity, "LOW")

if __name__ == "__main__":
    unittest.main()

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

if __name__ == "__main__":
    unittest.main()

"""
Tests for Engagement Audit Skill.
"""

import unittest
from skills import load_skill_module
from shared.models import AuditRequest

engagement_mod = load_skill_module("engagement-audit", "audit.py")
analyser_mod = load_skill_module("crawl-render-audit", "page_analyser.py")

EngagementAuditSkill = engagement_mod.EngagementAuditSkill
PageAnalyser = analyser_mod.PageAnalyser

GENERIC_CTA_HTML = """<!DOCTYPE html>
<html>
<head><title>Engagement Page</title></head>
<body>
    <h1>Our Product Features</h1>
    <p>Read more about how our solution works.</p>
    <button class="btn">Click Here</button>
    <button class="btn">Learn More</button>
</body>
</html>
"""

class TestEngagementSkill(unittest.TestCase):

    def test_generic_cta_detection(self):
        analyser = PageAnalyser()
        pdata = analyser.analyse("https://example.com/features", GENERIC_CTA_HTML)

        skill = EngagementAuditSkill()
        req = AuditRequest(url="https://example.com/features")
        res = skill.run(req, pages=[], page_data_map={"https://example.com/features": pdata})

        findings = res.get("findings", [])
        cta_findings = [f for f in findings if "GENERIC-CTA" in f.id]
        self.assertTrue(len(cta_findings) > 0)
        self.assertIn("Click Here", cta_findings[0].evidence.observation)

if __name__ == "__main__":
    unittest.main()

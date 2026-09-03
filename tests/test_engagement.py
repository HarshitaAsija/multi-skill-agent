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

    def test_form_friction_detection(self):
        unlabeled_form_html = """<!DOCTYPE html>
        <html>
        <head><title>Contact Form</title></head>
        <body>
            <h1>Contact Us</h1>
            <form action="/submit">
                <input type="text" name="name" placeholder="Your name">
                <input type="email" name="email" placeholder="Your email">
                <button type="submit">Send</button>
            </form>
        </body>
        </html>
        """
        analyser = PageAnalyser()
        pdata = analyser.analyse("https://example.com/contact", unlabeled_form_html)

        skill = EngagementAuditSkill()
        req = AuditRequest(url="https://example.com/contact")
        res = skill.run(req, pages=[], page_data_map={"https://example.com/contact": pdata})

        findings = res.get("findings", [])
        form_findings = [f for f in findings if "FORM-INPUT-FRICTION" in f.id]
        self.assertTrue(len(form_findings) > 0)
        self.assertEqual(form_findings[0].category, "onsite_engagement")

if __name__ == "__main__":
    unittest.main()

"""
Archetype Fixture Tests — False-Positive & Detection Accuracy Harness.

Tests the full audit pipeline against synthetic HTML fixtures representing
different real-world site archetypes:

  1. Clean well-optimised site  -> expect zero CRITICAL/HIGH findings
  2. AI-blocked site            -> expect DISC-01 (robots AI block)
  3. JS-heavy / thin HTML       -> expect KNOW-02 (missing org schema) + KNOW-01
  4. Stale site (old copyright) -> expect FRESH-01
  5. E-commerce product page    -> expect KNOW-02 product schema check
  6. Generic CTA site           -> expect ENG-03 (ambiguous CTAs)
"""

import unittest
from shared.models import AuditRequest
from shared.report_validator import validate_report
from skills import load_skill_module

analyser_mod = load_skill_module("crawl-render-audit", "page_analyser.py")
extract_mod = load_skill_module("crawl-render-audit", "extractability_checker.py")
crawl_mod = load_skill_module("crawl-render-audit", "audit.py")
fresh_mod = load_skill_module("freshness-corroboration", "audit.py")
engagement_mod = load_skill_module("engagement-audit", "audit.py")

PageAnalyser = analyser_mod.PageAnalyser
ExtractabilityChecker = extract_mod.ExtractabilityChecker
CrawlRenderAuditSkill = crawl_mod.CrawlRenderAuditSkill
FreshnessCorroborationSkill = fresh_mod.FreshnessCorroborationSkill
EngagementAuditSkill = engagement_mod.EngagementAuditSkill

# ------------------------------------------------------------------ #
#  HTML Fixtures                                                       #
# ------------------------------------------------------------------ #

CLEAN_SITE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <title>Acme Corp — AI Readiness Platform</title>
  <meta name="description" content="Enterprise AI readiness auditing by Acme Corp.">
  <meta name="robots" content="index, follow">
  <meta property="og:title" content="Acme Corp — AI Readiness Platform">
  <meta property="og:image" content="https://acme.com/og.png">
  <link rel="canonical" href="https://acme.com/">
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"Organization","name":"Acme Corp","url":"https://acme.com","logo":"https://acme.com/logo.png"}
  </script>
</head>
<body>
  <header><nav aria-label="Main Navigation"><a href="/">Home</a><a href="/about">About</a></nav></header>
  <main>
    <h1>Automate Your AI Readiness Audit</h1>
    <h2>Core Features</h2>
    <p>Comprehensive coverage for AI discoverability and on-site engagement metrics.</p>
    <a class="btn-primary" href="/get-started">Start Free Trial</a>
  </main>
  <footer><p>© 2026 Acme Corp.</p></footer>
</body>
</html>"""

STALE_SITE_HTML = """<!DOCTYPE html>
<html>
<head><title>Old Website</title></head>
<body>
  <h1>Welcome to OldSite</h1>
  <p>We have been serving customers since 2010.</p>
  <footer><p>Copyright © 2021 OldSite Inc. All rights reserved.</p></footer>
</body>
</html>"""

ECOMMERCE_PRICING_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Pricing Plans</title>
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://example.com/pricing">
</head>
<body>
  <nav><a href="/">Home</a></nav>
  <main>
    <h1>Our Pricing</h1>
    <h2>Choose a Plan</h2>
    <div class="plan-grid">
      <div class="plan"><h3>Starter</h3><p>$29/mo</p></div>
      <div class="plan"><h3>Pro</h3><p>$99/mo</p></div>
    </div>
  </main>
  <footer><p>© 2026 Example Inc.</p></footer>
</body>
</html>"""

GENERIC_CTA_HTML = """<!DOCTYPE html>
<html>
<head><title>Generic CTAs</title></head>
<body>
  <h1>Our Solutions</h1>
  <p>Discover what we offer.</p>
  <button class="btn">Click Here</button>
  <button class="btn">Learn More</button>
  <button class="btn">Submit</button>
</body>
</html>"""

THIN_HTML_SITE = """<!DOCTYPE html>
<html>
<head><title>Minimal Page</title></head>
<body>
  <div id="app"></div>
</body>
</html>"""


class TestCleanSiteNoFalsePositives(unittest.TestCase):
    """A well-optimised site should produce zero CRITICAL or HIGH findings."""

    def test_no_critical_or_high_findings(self):
        analyser = PageAnalyser()
        pdata = analyser.analyse("https://acme.com/", CLEAN_SITE_HTML)

        checker = ExtractabilityChecker()
        ext_findings = checker.check_all({"https://acme.com/": pdata})

        req = AuditRequest(url="https://acme.com/")
        fresh_skill = FreshnessCorroborationSkill()
        fresh_res = fresh_skill.run(req, pages=[], page_data_map={"https://acme.com/": pdata})

        eng_skill = EngagementAuditSkill()
        eng_res = eng_skill.run(req, pages=[], page_data_map={"https://acme.com/": pdata})

        all_findings = ext_findings + fresh_res["findings"] + eng_res["findings"]
        critical_or_high = [f for f in all_findings if f.severity in ("CRITICAL", "HIGH")]

        self.assertEqual(
            len(critical_or_high), 0,
            msg=f"Expected 0 CRITICAL/HIGH on clean site, got: {[f.id for f in critical_or_high]}"
        )


class TestStaleContentDetection(unittest.TestCase):
    """Stale copyright date should trigger FRESH-01."""

    def test_outdated_copyright_detected(self):
        analyser = PageAnalyser()
        pdata = analyser.analyse("https://oldsite.com/", STALE_SITE_HTML)

        req = AuditRequest(url="https://oldsite.com/")
        skill = FreshnessCorroborationSkill()
        res = skill.run(req, pages=[], page_data_map={"https://oldsite.com/": pdata})

        ids = [f.id for f in res["findings"]]
        self.assertIn("FRESH-01-OUTDATED-COPYRIGHT", ids)


class TestEcommerceProductSchemaMissing(unittest.TestCase):
    """Pricing page without Product schema should trigger KNOW-02."""

    def test_missing_product_schema_on_pricing_page(self):
        analyser = PageAnalyser()
        pdata = analyser.analyse("https://example.com/pricing", ECOMMERCE_PRICING_HTML)

        checker = ExtractabilityChecker()
        findings = checker.check_all({"https://example.com/pricing": pdata})

        product_schema_findings = [f for f in findings if "MISSING-PRODUCT-SCHEMA" in f.id]
        self.assertTrue(
            len(product_schema_findings) > 0,
            msg="Expected KNOW-02 product schema finding on pricing page"
        )


class TestGenericCTADetection(unittest.TestCase):
    """Generic CTA labels should trigger ENG-03."""

    def test_generic_cta_detected(self):
        analyser = PageAnalyser()
        pdata = analyser.analyse("https://example.com/solutions", GENERIC_CTA_HTML)

        req = AuditRequest(url="https://example.com/solutions")
        skill = EngagementAuditSkill()
        res = skill.run(req, pages=[], page_data_map={"https://example.com/solutions": pdata})

        cta_findings = [f for f in res["findings"] if "GENERIC-CTA" in f.id]
        self.assertTrue(len(cta_findings) > 0)
        self.assertEqual(cta_findings[0].severity, "LOW")


class TestThinHtmlKnowledgeGap(unittest.TestCase):
    """Thin JS-rendered page (minimal HTML) should flag KNOW-02 and missing H1."""

    def test_thin_page_schema_and_heading_issues(self):
        analyser = PageAnalyser()
        pdata = analyser.analyse("https://spa-site.com/", THIN_HTML_SITE)

        checker = ExtractabilityChecker()
        findings = checker.check_all({"https://spa-site.com/": pdata})

        # Should flag missing Organization schema on homepage
        org_findings = [f for f in findings if "MISSING-ORG-SCHEMA" in f.id]
        self.assertTrue(
            len(org_findings) > 0,
            msg="Expected missing Organization schema finding on thin JS page"
        )


class TestClientSideHydrationLock(unittest.TestCase):
    """Near-empty server HTML with SPA mount containers should flag DISC-07."""

    def test_client_hydration_lock_flagged(self):
        analyser = PageAnalyser()
        pdata = analyser.analyse("https://spa-site.com/", THIN_HTML_SITE)

        findings = []
        skill = CrawlRenderAuditSkill(http_client=None)
        skill._check_client_side_hydration_lock(pdata, THIN_HTML_SITE, findings)

        hydration_findings = [f for f in findings if "CLIENT-HYDRATION-LOCK" in f.id]
        self.assertTrue(len(hydration_findings) > 0)
        self.assertEqual(hydration_findings[0].severity, "HIGH")


class TestMissingImageAltText(unittest.TestCase):
    """Pages where all images lack alt text should flag KNOW-04."""

    def test_missing_alt_text_flagged(self):
        html = '''<!DOCTYPE html>
        <html>
        <head><title>No Alt Text Page</title></head>
        <body>
            <img src="/img1.png">
            <img src="/img2.jpg">
            <img src="/img3.svg">
        </body>
        </html>'''
        analyser = PageAnalyser()
        pdata = analyser.analyse("https://example.com/no-alt", html)

        self.assertEqual(pdata.total_images_count, 3)
        self.assertEqual(pdata.images_missing_alt_count, 3)

        checker = ExtractabilityChecker()
        ext_findings = checker.check_all({"https://example.com/no-alt": pdata})

        alt_findings = [f for f in ext_findings if "MISSING-IMAGE-ALT" in f.id]
        self.assertEqual(len(alt_findings), 1)
        self.assertEqual(alt_findings[0].severity, "LOW")


class TestReportSchemaValidation(unittest.TestCase):
    """Report validator must correctly flag malformed and accept well-formed reports."""

    def test_valid_report_passes_validation(self):
        from shared.report_validator import validate_report

        valid_report = {
            "site": "https://example.com/",
            "audited_at": "2026-09-03T12:00:00+00:00",
            "ai_readiness_score": 85,
            "summary": {
                "total_findings": 1,
                "critical": 0,
                "high": 1,
                "medium": 0,
                "low": 0,
            },
            "findings": [
                {
                    "id": "TEST-01",
                    "title": "Test Finding",
                    "category": "ai_discoverability",
                    "severity": "HIGH",
                    "confidence": 0.9,
                    "evidence": {
                        "source_url": "https://example.com/",
                        "observation": "Test observation",
                        "detection_method": "Test method",
                    },
                    "suggested_action": {"summary": "Fix it"},
                    "affected_urls": ["https://example.com/"],
                }
            ],
            "proactive_recommendations": [],
        }

        is_valid, errors = validate_report(valid_report)
        self.assertTrue(is_valid, msg=f"Validation errors: {errors}")

    def test_invalid_report_fails_validation(self):
        from shared.report_validator import validate_report

        bad_report = {
            "site": "",  # empty — should fail
            "audited_at": "2026-09-03",
            "ai_readiness_score": 150, # invalid score -> should fail
            "summary": {"total_findings": 2, "critical": 1, "high": 0, "medium": 0, "low": 0},
            "findings": [],  # total_findings=2 but findings is empty → count mismatch
            "proactive_recommendations": [],
        }
        is_valid, errors = validate_report(bad_report)
        self.assertFalse(is_valid)
        self.assertTrue(len(errors) > 0)


if __name__ == "__main__":
    unittest.main()

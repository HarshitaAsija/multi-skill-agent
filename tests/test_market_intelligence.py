"""
Tests for AI Answerability & Market Intelligence Engine.
"""

import unittest
from shared.market_intelligence import MarketIntelligenceEngine


class MockPageData:
    def __init__(self, title="", meta_description="", json_ld_types=None, h1_tags=None, button_cta_labels=None, footer_text=""):
        self.title = title
        self.meta_description = meta_description
        self.json_ld_types = json_ld_types or []
        self.h1_tags = h1_tags or []
        self.button_cta_labels = button_cta_labels or []
        self.footer_text = footer_text
        self.page_title_brand = "TestBrand"


class TestMarketIntelligenceEngine(unittest.TestCase):

    def setUp(self):
        self.engine = MarketIntelligenceEngine()

    def test_restaurant_industry_detection_and_answerability(self):
        pages = {
            "https://bistro.com/": MockPageData(
                title="Luigi's Italian Bistro | Authentic Pasta & Wine",
                meta_description="Fine dining Italian restaurant with handmade pasta, fresh seafood, and wood-fired pizza.",
                json_ld_types=["Restaurant", "FoodEstablishment"],
                footer_text="Open daily Monday to Friday 11am - 10pm, Saturday 10am - 11pm. Located at 123 Main Street.",
                button_cta_labels=["Reserve a Table", "View Menu"]
            ),
            "https://bistro.com/menu": MockPageData(
                title="Dinner Menu | Luigi's Bistro",
                meta_description="Explore our pasta, appetizers, vegetarian dishes, entrees, and desserts.",
                h1_tags=["Dinner & Wine Menu"],
                button_cta_labels=["Book Online"]
            )
        }

        report = self.engine.analyze("https://bistro.com", pages, brand_name="Luigi's Bistro")

        self.assertEqual(report.detected_industry, "RESTAURANT")
        self.assertTrue(report.confidence >= 0.70)
        self.assertEqual(report.questions_checked, 5)

        # Hours should be answerable
        hours_q = next(q for q in report.questions if q.id == "REST-Q1")
        self.assertEqual(hours_q.status, "ANSWERABLE")

        # Menu should be answerable
        menu_q = next(q for q in report.questions if q.id == "REST-Q3")
        self.assertEqual(menu_q.status, "ANSWERABLE")

        # Dietary options (vegetarian mentioned)
        diet_q = next(q for q in report.questions if q.id == "REST-Q4")
        self.assertEqual(diet_q.status, "ANSWERABLE")

        # Reservation should be answerable
        res_q = next(q for q in report.questions if q.id == "REST-Q5")
        self.assertEqual(res_q.status, "ANSWERABLE")

        self.assertTrue(report.market_question_coverage_pct >= 80)

    def test_ecommerce_question_gap_identification(self):
        pages = {
            "https://shop.local/": MockPageData(
                title="Trendy Apparel | Online Fashion Boutique",
                meta_description="Shop women's dresses, shoes, and accessories online.",
                json_ld_types=["Product", "Store"],
                h1_tags=["Summer Collection - All dresses $49.99"],
                button_cta_labels=["Add to Cart"]
            )
        }

        report = self.engine.analyze("https://shop.local", pages, brand_name="Trendy Apparel")

        self.assertEqual(report.detected_industry, "ECOMMERCE")
        self.assertTrue(report.missing_count > 0 or report.partial_count > 0)
        self.assertTrue(len(report.question_gaps) > 0)
        self.assertTrue(len(report.roadmap) > 0)

        # Priority 1 should have suggested FAQ JSON-LD
        top_rec = report.roadmap[0]
        self.assertEqual(top_rec.priority, 1)
        self.assertIn("@context", top_rec.suggested_faq_json_ld)
        self.assertEqual(top_rec.suggested_faq_json_ld["@type"], "Question")

    def test_general_business_fallback(self):
        pages = {
            "https://unknown-site.org/": MockPageData(
                title="Generic Organization Portal",
                meta_description="Welcome to our organizational homepage.",
                json_ld_types=["Organization"]
            )
        }

        report = self.engine.analyze("https://unknown-site.org", pages)
        self.assertEqual(report.detected_industry, "GENERAL_BUSINESS")
        self.assertEqual(report.questions_checked, 5)

    def test_simulated_ai_prompts_and_risk(self):
        pages = {
            "https://clinic.local/": MockPageData(
                title="Downtown Dental Clinic",
                meta_description="Comprehensive family dentistry.",
                json_ld_types=["Dentist", "MedicalOrganization"]
            )
        }

        report = self.engine.analyze("https://clinic.local", pages, brand_name="Downtown Dental")
        self.assertEqual(report.detected_industry, "HEALTHCARE")

        for q in report.questions:
            self.assertIn("Downtown Dental", q.simulated_prompt)
            if q.status != "ANSWERABLE":
                self.assertTrue(len(q.ai_risk) > 10)


if __name__ == "__main__":
    unittest.main()

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

    def test_real_estate_industry_detection_and_questions(self):
        pages = {
            "https://pinnacle-homes.com/": MockPageData(
                title="Pinnacle Properties | Luxury Homes & Real Estate",
                meta_description="Browse exclusive properties for sale, modern condos, and luxury homes.",
                json_ld_types=["RealEstateAgent"],
                button_cta_labels=["Schedule a Tour", "View Listings"],
                footer_text="Licensed broker serving Downtown and Westside neighborhoods."
            )
        }
        report = self.engine.analyze("https://pinnacle-homes.com", pages, brand_name="Pinnacle Properties")
        self.assertEqual(report.detected_industry, "REAL_ESTATE")
        self.assertEqual(report.industry_label, "Real Estate & Property")
        self.assertEqual(report.questions_checked, 5)

        q1 = next(q for q in report.questions if q.id == "REAL-Q1")
        self.assertEqual(q1.status, "ANSWERABLE")

        q3 = next(q for q in report.questions if q.id == "REAL-Q3")
        self.assertEqual(q3.status, "ANSWERABLE")

    def test_legal_industry_detection_and_questions(self):
        pages = {
            "https://sterling-law.com/": MockPageData(
                title="Sterling & Associates | Premier Litigation & Legal Counsel",
                meta_description="Experienced attorneys specializing in corporate law, litigation, and personal injury.",
                json_ld_types=["LawFirm", "LegalService"],
                button_cta_labels=["Free Case Evaluation", "Contact an Attorney"],
                footer_text="Contingency fee representation. Admitted to practice before the State Bar."
            )
        }
        report = self.engine.analyze("https://sterling-law.com", pages, brand_name="Sterling Law")
        self.assertEqual(report.detected_industry, "LEGAL")
        self.assertEqual(report.industry_label, "Legal & Law Services")
        self.assertEqual(report.questions_checked, 5)

        q1 = next(q for q in report.questions if q.id == "LEGL-Q1")
        self.assertEqual(q1.status, "ANSWERABLE")

        q2 = next(q for q in report.questions if q.id == "LEGL-Q2")
        self.assertEqual(q2.status, "ANSWERABLE")

    def test_sports_fitness_industry_detection_and_questions(self):
        pages = {
            "https://apex-gym.com/": MockPageData(
                title="Apex Athletics | 24/7 Gym & Fitness Center",
                meta_description="State-of-the-art gym equipment, cardio machines, free weights, and certified personal trainers.",
                json_ld_types=["HealthClub", "ExerciseGym"],
                button_cta_labels=["Free Day Pass", "Join Now"],
                footer_text="Open 24/7. All personal trainers are NASM certified."
            )
        }
        report = self.engine.analyze("https://apex-gym.com", pages, brand_name="Apex Gym")
        self.assertEqual(report.detected_industry, "SPORTS_FITNESS")
        self.assertEqual(report.industry_label, "Sports, Fitness & Gym")
        self.assertEqual(report.questions_checked, 5)

        q1 = next(q for q in report.questions if q.id == "SPRT-Q1")
        self.assertEqual(q1.status, "ANSWERABLE")

        q4 = next(q for q in report.questions if q.id == "SPRT-Q4")
        self.assertEqual(q4.status, "ANSWERABLE")

    def test_food_delivery_industry_detection_and_questions(self):
        pages = {
            "https://quickbites-delivery.com/": MockPageData(
                title="QuickBites | Fast Gourmet Food Delivery",
                meta_description="Online ordering with fast delivery, real-time courier tracking, and tamper-evident packaging.",
                json_ld_types=["DeliveryChargeSpecification", "FoodEstablishment"],
                button_cta_labels=["Order Online", "Track My Order"],
                footer_text="Delivery fee $2.99 with free delivery over $30. 5 mile radius."
            )
        }
        report = self.engine.analyze("https://quickbites-delivery.com", pages, brand_name="QuickBites")
        self.assertEqual(report.detected_industry, "FOOD_DELIVERY")
        self.assertEqual(report.industry_label, "Food Delivery & Cloud Kitchen")
        self.assertEqual(report.questions_checked, 5)

        q1 = next(q for q in report.questions if q.id == "FDEL-Q1")
        self.assertEqual(q1.status, "ANSWERABLE")

        q3 = next(q for q in report.questions if q.id == "FDEL-Q3")
        self.assertEqual(q3.status, "ANSWERABLE")


if __name__ == "__main__":
    unittest.main()


"""
Tests for Markdown Report Generator.
"""

import unittest
from shared.report_generator import generate_markdown_report


class TestReportGenerator(unittest.TestCase):

    def test_generate_markdown_report_comprehensive(self):
        sample_report = {
            "site": "https://bistro.com/",
            "audited_at": "2026-09-08T12:00:00Z",
            "ai_readiness_score": 85,
            "summary": {
                "total_findings": 1,
                "critical": 0,
                "high": 1,
                "medium": 0,
                "low": 0
            },
            "findings": [
                {
                    "id": "KNOW-02-MISSING-ORG-SCHEMA",
                    "title": "Missing Primary Organization Schema",
                    "category": "machine_readiness",
                    "severity": "HIGH",
                    "rationale": "Brand cannot be disambiguated by LLM Knowledge Graph.",
                    "evidence": {
                        "observation": "0 JSON-LD blocks on homepage."
                    },
                    "suggested_action": {
                        "summary": "Inject Organization Schema.org JSON-LD.",
                        "remediation_steps": ["Add script tag", "Include name and logo"]
                    },
                    "affected_urls": ["https://bistro.com/"]
                }
            ],
            "proactive_recommendations": [
                {
                    "title": "Publish an llms.txt Machine Index Manifest",
                    "rationale": "Provides AI assistants with a clean index.",
                    "suggested_implementation": "Publish /llms.txt at root."
                }
            ],
            "market_intelligence": {
                "detected_industry": "RESTAURANT",
                "industry_label": "Restaurant & Dining",
                "market_question_coverage_pct": 80,
                "clear_count": 4,
                "partial_count": 0,
                "missing_count": 1,
                "questions": [
                    {
                        "question": "What are the opening hours and operational days?",
                        "status": "ANSWERABLE",
                        "simulated_prompt": "What are the opening hours for Bistro?",
                        "ai_risk": "None"
                    },
                    {
                        "question": "Can customers reserve a table or order online?",
                        "status": "NOT_ANSWERABLE",
                        "simulated_prompt": "How do I book a table at Bistro?",
                        "ai_risk": "Autonomous booking agents cannot complete reservations."
                    }
                ],
                "roadmap": [
                    {
                        "priority": 1,
                        "action_title": "Implement Online Reservation Process",
                        "why": "Eliminates friction for booking.",
                        "impact": "HIGH",
                        "effort": "MEDIUM",
                        "suggested_faq_json_ld": {
                            "@type": "Question",
                            "name": "How can I reserve a table?",
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": "Reserve online at bistro.com."
                            }
                        }
                    }
                ]
            }
        }

        md = generate_markdown_report(sample_report)

        self.assertIn("# AI Readiness & Market Intelligence Audit Report", md)
        self.assertIn("https://bistro.com/", md)
        self.assertIn("85 / 100", md)
        self.assertIn("Restaurant & Dining", md)
        self.assertIn("80%", md)
        self.assertIn("KNOW-02-MISSING-ORG-SCHEMA", md)
        self.assertIn("Implement Online Reservation Process", md)
        self.assertIn("FAQPage", md)

    def test_generate_markdown_report_minimal(self):
        minimal_report = {
            "site": "https://example.com/",
            "audited_at": "2026-09-08T12:00:00Z",
            "ai_readiness_score": 100,
            "summary": {"total_findings": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
            "findings": [],
            "proactive_recommendations": []
        }

        md = generate_markdown_report(minimal_report)
        self.assertIn("100 / 100", md)
        self.assertIn("Optimal", md)
        self.assertIn("No technical issues detected", md)


if __name__ == "__main__":
    unittest.main()

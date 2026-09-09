"""
Unit tests for Google Gemini API Client integration.
Tests both active (mocked) and keyless fallback behaviors.
"""

import json
import unittest
from unittest.mock import patch, MagicMock
from shared.gemini_client import GeminiClient
from skills import load_skill_module

orch_mod = load_skill_module("audit-orchestrator", "orchestrate.py")
Orchestrator = orch_mod.Orchestrator


class TestGeminiClientBasics(unittest.TestCase):
    """Tests basic initialization and availability checks."""

    def test_client_without_key_is_unavailable(self):
        with patch.dict("os.environ", {}, clear=True):
            client = GeminiClient(api_key="")
            self.assertFalse(client.is_available())
            self.assertIsNone(client.generate_json("test prompt"))
            self.assertIsNone(client.evaluate_website_answerability(
                brand="TestBrand",
                root_url="https://test.com",
                industry_label="E-Commerce",
                questions=[],
                aggregated_content="Some content"
            ))
            self.assertIsNone(client.generate_site_tailored_recommendations(
                brand="TestBrand",
                root_url="https://test.com",
                industry_label="E-Commerce",
                findings_summary=[],
                site_content_summary="Some content"
            ))
            self.assertIsNone(client.generate_executive_synthesis(
                brand="TestBrand",
                root_url="https://test.com",
                score=85,
                industry_label="E-Commerce",
                total_findings=2,
                coverage_pct=80
            ))

    def test_client_with_key_is_available(self):
        client = GeminiClient(api_key="AIzaSyDummyKeyForTesting12345")
        self.assertTrue(client.is_available())


class TestGeminiClientMockedCalls(unittest.TestCase):
    """Tests Gemini API calls and response handling with mocked HTTP responses."""

    def setUp(self):
        self.client = GeminiClient(api_key="AIzaSyDummyKeyForTesting12345")

    @patch("urllib.request.urlopen")
    def test_generate_json_success(self, mock_urlopen):
        # Mock valid Gemini REST API candidate response
        fake_api_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "```json\n{\"status\": \"ok\", \"count\": 42}\n```"}
                        ]
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_api_response).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = self.client.generate_json("Test prompt")
        self.assertIsNotNone(result)
        self.assertEqual(result.get("status"), "ok")
        self.assertEqual(result.get("count"), 42)

    @patch("urllib.request.urlopen")
    def test_evaluate_website_answerability(self, mock_urlopen):
        fake_ai_output = {
            "detected_industry_refined": "SaaS / Technology",
            "industry_summary": "Cloud analytics platform for modern data teams.",
            "questions": [
                {
                    "id": "SAAS-Q1",
                    "question": "What are the subscription pricing tiers?",
                    "status": "ANSWERABLE",
                    "evidence_found": "Starter plan is $29/mo, Enterprise plan is custom.",
                    "simulated_prompt": "How much does TestSaaS cost per month?",
                    "ai_risk": "None — verified clear signal.",
                    "impact": "HIGH",
                    "effort": "LOW",
                    "faq_q": "What are your pricing plans?",
                    "faq_a": "Plans start at $29/month."
                }
            ]
        }
        fake_api_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": json.dumps(fake_ai_output)}
                        ]
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_api_response).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        result = self.client.evaluate_website_answerability(
            brand="TestSaaS",
            root_url="https://testsaas.io",
            industry_label="Software & Technology (SaaS)",
            questions=[{"id": "SAAS-Q1", "question": "What are the subscription pricing tiers?"}],
            aggregated_content="Starter plan is $29/mo with unlimited seats."
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.get("detected_industry_refined"), "SaaS / Technology")
        questions = result.get("questions", [])
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["status"], "ANSWERABLE")

    @patch("urllib.request.urlopen")
    def test_generate_site_tailored_recommendations(self, mock_urlopen):
        fake_recs = [
            {
                "id": "REC-AI-01-SCHEMA-PRICING",
                "title": "Publish Pricing Offer JSON-LD",
                "category": "machine_readiness",
                "rationale": "Enables ChatGPT to quote $29 starter price accurately.",
                "suggested_implementation": "Add Schema.org Offer structured data to /pricing."
            },
            {
                "id": "REC-AI-02-OPENAPI",
                "title": "Expose OpenAPI Specification",
                "category": "ai_discoverability",
                "rationale": "Allows autonomous agents to query API endpoints directly.",
                "suggested_implementation": "Link /.well-known/openapi.json in /llms.txt."
            },
            {
                "id": "REC-AI-03-FAQ",
                "title": "Add FAQPage for Integration Docs",
                "category": "onsite_engagement",
                "rationale": "Captures conversational queries about third-party tools.",
                "suggested_implementation": "Embed FAQPage schema on integrations directory."
            }
        ]
        fake_api_response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": json.dumps(fake_recs)}
                        ]
                    }
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_api_response).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        recs = self.client.generate_site_tailored_recommendations(
            brand="TestSaaS",
            root_url="https://testsaas.io",
            industry_label="Software & Technology (SaaS)",
            findings_summary=[],
            site_content_summary="Pricing and developer docs"
        )

        self.assertIsNotNone(recs)
        self.assertEqual(len(recs), 3)
        self.assertEqual(recs[0]["category"], "machine_readiness")


class TestOrchestratorGeminiIntegration(unittest.TestCase):
    """Tests Orchestrator pipeline when Gemini is provided."""

    def test_orchestrator_gemini_active_mode(self):
        mock_gemini = MagicMock()
        mock_gemini.is_available.return_value = True
        mock_gemini.generate_site_tailored_recommendations.return_value = [
            {
                "id": "REC-AI-01",
                "title": "Custom Recommendation 1",
                "category": "machine_readiness",
                "rationale": "Rationale 1",
                "suggested_implementation": "Step 1"
            },
            {
                "id": "REC-AI-02",
                "title": "Custom Recommendation 2",
                "category": "ai_discoverability",
                "rationale": "Rationale 2",
                "suggested_implementation": "Step 2"
            },
            {
                "id": "REC-AI-03",
                "title": "Custom Recommendation 3",
                "category": "onsite_engagement",
                "rationale": "Rationale 3",
                "suggested_implementation": "Step 3"
            }
        ]
        mock_gemini.generate_executive_synthesis.return_value = "Test executive synthesis paragraph."

        orch = Orchestrator(gemini_client=mock_gemini)
        # Mock crawl skill to return simple homepage
        mock_crawl = MagicMock()
        mock_crawl.run.return_value = {
            "findings": [],
            "pages": ["https://example.com"],
            "page_data_map": {}
        }
        orch.crawl_skill = mock_crawl
        orch.freshness_skill = MagicMock()
        orch.freshness_skill.run.return_value = {"findings": []}
        orch.engagement_skill = MagicMock()
        orch.engagement_skill.run.return_value = {"findings": []}

        report = orch.run_audit("https://example.com")
        self.assertIn("executive_synthesis", report)
        self.assertEqual(report["executive_synthesis"], "Test executive synthesis paragraph.")
        self.assertEqual(len(report["proactive_recommendations"]), 3)
        self.assertEqual(report["proactive_recommendations"][0]["id"], "REC-AI-01")


if __name__ == "__main__":
    unittest.main()

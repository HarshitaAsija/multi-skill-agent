"""
Tests for Shared Data Models: AuditRequest, Finding, EvidenceItem, SuggestedAction, AuditResult.
"""

import unittest
from shared.models import (
    AuditRequest,
    EvidenceItem,
    SuggestedAction,
    Finding,
    AuditResult,
    SeveritySummary
)
from shared.config import (
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
    CATEGORY_AI_DISCOVERABILITY,
)

class TestModels(unittest.TestCase):

    def test_audit_request_creation(self):
        req = AuditRequest(url="https://example.com")
        self.assertEqual(req.url, "https://example.com")
        self.assertEqual(req.max_pages, 15)
        self.assertIsInstance(req.to_dict(), dict)

    def test_evidence_item_confidence_bounding(self):
        ev1 = EvidenceItem(
            source_url="https://example.com",
            observation="Test observation",
            detection_method="Unit Test",
            confidence=1.5
        )
        self.assertEqual(ev1.confidence, 1.0)

        ev2 = EvidenceItem(
            source_url="https://example.com",
            observation="Test observation",
            detection_method="Unit Test",
            confidence=-0.5
        )
        self.assertEqual(ev2.confidence, 0.0)

    def test_finding_invalid_severity_raises(self):
        ev = EvidenceItem("https://example.com", "Observed issue", "Test")
        action = SuggestedAction("Fix issue")

        with self.assertRaises(ValueError):
            Finding(
                id="TEST-01",
                title="Invalid Severity Finding",
                category=CATEGORY_AI_DISCOVERABILITY,
                severity="INVALID_SEVERITY",
                confidence=1.0,
                evidence=ev,
                rationale="Test rationale",
                affected_urls=["https://example.com"],
                suggested_action=action
            )

    def test_audit_result_serialization_schema(self):
        ev = EvidenceItem("https://example.com", "Observed issue", "Test")
        action = SuggestedAction("Fix issue")
        f1 = Finding(
            id="DISC-01",
            title="Sample Finding",
            category=CATEGORY_AI_DISCOVERABILITY,
            severity=SEVERITY_HIGH,
            confidence=0.9,
            evidence=ev,
            rationale="Impacts machine indexing",
            affected_urls=["https://example.com"],
            suggested_action=action
        )

        res = AuditResult(
            site="https://example.com",
            findings=[f1]
        )
        res_dict = res.to_dict()

        self.assertIn("site", res_dict)
        self.assertIn("audited_at", res_dict)
        self.assertIn("summary", res_dict)
        self.assertEqual(res_dict["summary"]["total_findings"], 1)
        self.assertEqual(res_dict["summary"]["high"], 1)
        self.assertEqual(res_dict["summary"]["critical"], 0)
        self.assertEqual(len(res_dict["findings"]), 1)
        self.assertEqual(res_dict["findings"][0]["id"], "DISC-01")

if __name__ == "__main__":
    unittest.main()

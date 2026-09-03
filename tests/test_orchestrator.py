"""
Tests for Orchestrator initialization and execution flow.
"""

import unittest
from skills import load_skill_module

orch_mod = load_skill_module("audit-orchestrator", "orchestrate.py")
Orchestrator = orch_mod.Orchestrator

class TestOrchestrator(unittest.TestCase):

    def test_orchestrator_initialization(self):
        orch = Orchestrator()
        self.assertIsNotNone(orch.http_client)
        self.assertIsNotNone(orch.crawl_skill)
        self.assertIsNotNone(orch.freshness_skill)
        self.assertIsNotNone(orch.engagement_skill)

    def test_orchestrator_invalid_url(self):
        orch = Orchestrator()
        result = orch.run_audit("invalid-url-string")

        self.assertEqual(result["site"], "invalid-url-string")
        self.assertEqual(result["summary"]["total_findings"], 0)
        self.assertEqual(result["summary"]["critical"], 0)

    def test_normalize_finding_id(self):
        orch = Orchestrator()
        normalized = orch._normalize_finding_id("DISC-05-MISSING-CANONICAL-https://example.com/pricing")
        self.assertEqual(normalized, "DISC-05-MISSING-CANONICAL")

        normalized_http = orch._normalize_finding_id("KNOW-01-MISSING-H1-http://example.com/")
        self.assertEqual(normalized_http, "KNOW-01-MISSING-H1")

        plain = orch._normalize_finding_id("FRESH-01-OUTDATED-COPYRIGHT")
        self.assertEqual(plain, "FRESH-01-OUTDATED-COPYRIGHT")

    def test_deduplication_merges_affected_urls_and_sorts_by_severity(self):
        from shared.models import Finding, EvidenceItem, SuggestedAction
        from shared.config import (
            CATEGORY_AI_DISCOVERABILITY,
            CATEGORY_MACHINE_READINESS,
            SEVERITY_LOW,
            SEVERITY_HIGH,
        )

        orch = Orchestrator()

        ev1 = EvidenceItem(
            source_url="https://example.com/p1",
            observation="Missing canonical tag on p1",
            detection_method="Parser"
        )
        f1 = Finding(
            id="DISC-05-MISSING-CANONICAL-https://example.com/p1",
            title="Missing Canonical Tag",
            category=CATEGORY_AI_DISCOVERABILITY,
            severity=SEVERITY_LOW,
            confidence=0.90,
            evidence=ev1,
            rationale="Rationale",
            affected_urls=["https://example.com/p1"],
            suggested_action=SuggestedAction(summary="Add canonical", priority=4)
        )

        ev2 = EvidenceItem(
            source_url="https://example.com/p2",
            observation="Missing canonical tag on p2",
            detection_method="Parser"
        )
        f2 = Finding(
            id="DISC-05-MISSING-CANONICAL-https://example.com/p2",
            title="Missing Canonical Tag",
            category=CATEGORY_AI_DISCOVERABILITY,
            severity=SEVERITY_LOW,
            confidence=0.90,
            evidence=ev2,
            rationale="Rationale",
            affected_urls=["https://example.com/p2"],
            suggested_action=SuggestedAction(summary="Add canonical", priority=4)
        )

        ev3 = EvidenceItem(
            source_url="https://example.com/",
            observation="Missing Org schema",
            detection_method="Parser"
        )
        f3 = Finding(
            id="KNOW-02-MISSING-ORG-SCHEMA",
            title="Missing Org Schema",
            category=CATEGORY_MACHINE_READINESS,
            severity=SEVERITY_HIGH,
            confidence=0.95,
            evidence=ev3,
            rationale="Rationale",
            affected_urls=["https://example.com/"],
            suggested_action=SuggestedAction(summary="Add schema", priority=1)
        )

        deduped = orch._deduplicate_and_calibrate([f1, f2, f3])

        # Should merge f1 and f2 under base ID DISC-05-MISSING-CANONICAL
        self.assertEqual(len(deduped), 2)
        # HIGH severity should come first (f3 before f1/f2)
        self.assertEqual(deduped[0].id, "KNOW-02-MISSING-ORG-SCHEMA")
        self.assertEqual(deduped[0].severity, "HIGH")

        # The canonical finding should have both URLs
        canonical_finding = deduped[1]
        self.assertEqual(canonical_finding.id, "DISC-05-MISSING-CANONICAL")
        self.assertIn("https://example.com/p1", canonical_finding.affected_urls)
        self.assertIn("https://example.com/p2", canonical_finding.affected_urls)

    def test_proactive_recommendations_conform_to_schema(self):
        from shared.report_validator import validate_report

        orch = Orchestrator()
        recs = orch._generate_proactive_recommendations("https://example.com", [])
        self.assertTrue(len(recs) >= 2)

        # Build dummy audit report containing these recommendations
        report = {
            "site": "https://example.com",
            "audited_at": "2026-09-03T12:00:00+00:00",
            "ai_readiness_score": 100,
            "summary": {
                "total_findings": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "findings": [],
            "proactive_recommendations": [r.to_dict() for r in recs]
        }
        is_valid, errors = validate_report(report)
        self.assertTrue(is_valid, msg=f"Validation errors: {errors}")

    def test_unreachable_target(self):
        # We can mock HTTP client to timeout and check if DISC-00 is produced.
        class TimeoutMockClient:
            def fetch(self, url, *args, **kwargs):
                from shared.http_client import HTTPResponse
                return HTTPResponse(url=url, final_url=url, status_code=0, is_success=False, headers={}, body="", error="Timeout")
            def get(self, url, *args, **kwargs):
                from shared.http_client import HTTPResponse
                return HTTPResponse(url=url, final_url=url, status_code=0, is_success=False, headers={}, body="", error="Timeout")

        orch = Orchestrator(http_client=TimeoutMockClient())
        result = orch.run_audit("https://unreachable.local")

        findings = result.get("findings", [])
        disc_00 = [f for f in findings if "DISC-00-UNREACHABLE" in f["id"]]
        self.assertTrue(len(disc_00) > 0, msg="Expected DISC-00-UNREACHABLE finding on timeout")
        self.assertEqual(disc_00[0]["severity"], "CRITICAL")
        self.assertTrue(result.get("ai_readiness_score") < 100)


if __name__ == "__main__":
    unittest.main()

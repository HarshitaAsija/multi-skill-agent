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

if __name__ == "__main__":
    unittest.main()

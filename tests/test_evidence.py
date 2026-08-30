"""
Tests for Evidence Standardization & EvidenceBuilder.
"""

import unittest
from shared.evidence import EvidenceBuilder

class TestEvidence(unittest.TestCase):

    def test_evidence_builder_fields(self):
        ev = EvidenceBuilder.build(
            source_url="https://example.com/page1",
            observation="Missing main title element in DOM.",
            detection_method="DOM Tag Parser",
            relevance="Search engines and AI agents use the <title> tag as the primary page label for indexing and citation.",
            confidence=0.95,
            dom_selector="head > title",
            http_status=200,
            extra_data={"tag_count": 0}
        )

        self.assertEqual(ev.source_url, "https://example.com/page1")
        self.assertEqual(ev.observation, "Missing main title element in DOM.")
        self.assertEqual(ev.detection_method, "DOM Tag Parser")
        self.assertEqual(ev.confidence, 0.95)
        self.assertIn("search engines", ev.relevance.lower())

        ev_dict = ev.to_dict()
        self.assertIn("timestamp", ev_dict)
        self.assertIn("relevance", ev_dict)
        self.assertEqual(ev_dict["supporting_data"]["dom_selector"], "head > title")
        self.assertEqual(ev_dict["supporting_data"]["http_status"], 200)
        self.assertEqual(ev_dict["supporting_data"]["tag_count"], 0)

if __name__ == "__main__":
    unittest.main()

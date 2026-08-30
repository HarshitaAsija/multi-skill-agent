"""
Tests for Centralized Severity Evaluation & Calibration.
"""

import unittest
from shared.severity import SeverityEvaluator
from shared.config import (
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW
)

class TestSeverity(unittest.TestCase):

    def test_severity_evaluation_blocking_global(self):
        sev = SeverityEvaluator.evaluate(
            impact_machine_access="BLOCKING",
            scope_affected="GLOBAL_SITE",
            blocks_core_function=True,
            confidence=1.0
        )
        self.assertEqual(sev, SEVERITY_CRITICAL)

    def test_severity_demoted_on_low_confidence(self):
        sev = SeverityEvaluator.evaluate(
            impact_machine_access="BLOCKING",
            scope_affected="GLOBAL_SITE",
            blocks_core_function=True,
            confidence=0.30
        )
        self.assertEqual(sev, SEVERITY_LOW)

    def test_best_practice_never_exceeds_medium(self):
        sev = SeverityEvaluator.evaluate(
            impact_machine_access="SEVERE",
            scope_affected="GLOBAL_SITE",
            blocks_core_function=False,
            confidence=0.95,
            is_optional_best_practice=True
        )
        self.assertEqual(sev, SEVERITY_MEDIUM)

    def test_severity_calibration_affected_urls(self):
        calibrated = SeverityEvaluator.calibrate_finding_severity(
            base_severity=SEVERITY_MEDIUM,
            affected_url_count=12,
            confidence=0.90,
            is_best_practice_only=False
        )
        self.assertEqual(calibrated, SEVERITY_HIGH)

if __name__ == "__main__":
    unittest.main()

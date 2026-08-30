"""
Centralized Severity Evaluation & Calibration Engine.
Evaluates severity deterministically based on machine accessibility impact, scope, core function blocking, and finding confidence.
"""

from typing import Dict, Any, List
from shared.config import (
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
    VALID_SEVERITIES,
)

class SeverityEvaluator:
    """
    Evaluates finding severity deterministically.
    Avoids arbitrary severity inflation or labeling missing optional best practices as HIGH.
    """

    @staticmethod
    def evaluate(
        impact_machine_access: str,  # "BLOCKING", "SEVERE", "MODERATE", "NEGLIGIBLE"
        scope_affected: str,         # "GLOBAL_SITE", "MULTI_PAGE", "SINGLE_PAGE"
        blocks_core_function: bool,
        confidence: float,
        is_optional_best_practice: bool = False
    ) -> str:
        """
        Determines calibrated severity string.
        """
        # Low confidence (< 0.5) demotes severity to prevent false alarm panic
        if confidence < 0.50:
            return SEVERITY_LOW

        # Optional best practices (e.g. missing optional meta tag) can never exceed MEDIUM
        if is_optional_best_practice:
            if impact_machine_access == "SEVERE" and scope_affected == "GLOBAL_SITE":
                return SEVERITY_MEDIUM
            return SEVERITY_LOW

        # CRITICAL: Blocks machine access globally across site OR breaks core functionality completely
        if blocks_core_function and (scope_affected in ("GLOBAL_SITE", "MULTI_PAGE")):
            return SEVERITY_CRITICAL
        if impact_machine_access == "BLOCKING" and scope_affected == "GLOBAL_SITE":
            return SEVERITY_CRITICAL

        # HIGH: Severe impact on machine indexing or core page content without total site lock
        if impact_machine_access in ("BLOCKING", "SEVERE") and scope_affected in ("GLOBAL_SITE", "MULTI_PAGE"):
            return SEVERITY_HIGH
        if blocks_core_function and scope_affected == "SINGLE_PAGE":
            return SEVERITY_HIGH

        # MEDIUM: Moderate impact or localized issue on key content
        if impact_machine_access in ("SEVERE", "MODERATE") or scope_affected in ("MULTI_PAGE", "SINGLE_PAGE"):
            if impact_machine_access == "NEGLIGIBLE":
                return SEVERITY_LOW
            return SEVERITY_MEDIUM

        # LOW: Minor / localized / low impact
        return SEVERITY_LOW

    @staticmethod
    def calibrate_finding_severity(
        base_severity: str,
        affected_url_count: int,
        confidence: float,
        is_best_practice_only: bool = False
    ) -> str:
        """
        Calibrates a skill's proposed base severity based on global context.
        """
        if base_severity not in VALID_SEVERITIES:
            base_severity = SEVERITY_MEDIUM

        # Downscale if best practice or low confidence
        if is_best_practice_only and base_severity in (SEVERITY_CRITICAL, SEVERITY_HIGH):
            return SEVERITY_MEDIUM
        if confidence < 0.60 and base_severity == SEVERITY_CRITICAL:
            return SEVERITY_HIGH
        if confidence < 0.40 and base_severity in (SEVERITY_HIGH, SEVERITY_MEDIUM):
            return SEVERITY_LOW

        # Upscale if global across many URLs
        if affected_url_count >= 10 and base_severity == SEVERITY_MEDIUM and not is_best_practice_only:
            return SEVERITY_HIGH

        return base_severity

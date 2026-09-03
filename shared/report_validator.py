"""
JSON Schema Validator for Audit Report output.

Validates that the final AuditResult JSON produced by the marketplace matches the required submission schema:
  - site (str, required)
  - audited_at (ISO 8601 str, required)
  - summary with counts by severity (required)
  - findings array where each finding has id, title, severity, evidence, suggested_action (required)
  - proactive_recommendations array (required, can be empty)
"""

from typing import Dict, Any, List, Tuple


VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
VALID_CATEGORIES = {
    "ai_discoverability",
    "machine_readiness",
    "factual_freshness",
    "onsite_engagement",
}


def validate_report(report: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates a report dict against the required schema.
    Returns (is_valid: bool, errors: List[str]).
    """
    errors: List[str] = []

    # Top-level required fields
    if not isinstance(report.get("site"), str) or not report["site"]:
        errors.append("Missing or invalid 'site' field (must be non-empty string)")

    if not isinstance(report.get("audited_at"), str) or not report["audited_at"]:
        errors.append("Missing or invalid 'audited_at' field (must be ISO 8601 string)")

    summary = report.get("summary")
    if not isinstance(summary, dict):
        errors.append("Missing or invalid 'summary' field (must be an object)")
    else:
        for key in ("total_findings", "critical", "high", "medium", "low"):
            if not isinstance(summary.get(key), int):
                errors.append(f"summary.{key} must be an integer")

        # Validate counts are consistent
        declared_total = summary.get("total_findings", 0)
        computed_total = sum(
            summary.get(k, 0) for k in ("critical", "high", "medium", "low")
        )
        if declared_total != computed_total:
            errors.append(
                f"summary.total_findings ({declared_total}) does not match "
                f"sum of severity counts ({computed_total})"
            )

    findings = report.get("findings")
    if not isinstance(findings, list):
        errors.append("Missing or invalid 'findings' field (must be an array)")
    else:
        for i, finding in enumerate(findings):
            finding_errors = _validate_finding(finding, i)
            errors.extend(finding_errors)

    recs = report.get("proactive_recommendations")
    if not isinstance(recs, list):
        errors.append("Missing or invalid 'proactive_recommendations' field (must be an array)")

    is_valid = len(errors) == 0
    return is_valid, errors


def _validate_finding(finding: Dict[str, Any], index: int) -> List[str]:
    errors: List[str] = []
    prefix = f"findings[{index}]"

    if not isinstance(finding.get("id"), str) or not finding["id"]:
        errors.append(f"{prefix}.id is missing or empty")

    if not isinstance(finding.get("title"), str) or not finding["title"]:
        errors.append(f"{prefix}.title is missing or empty")

    severity = finding.get("severity")
    if severity not in VALID_SEVERITIES:
        errors.append(f"{prefix}.severity '{severity}' is invalid (must be CRITICAL/HIGH/MEDIUM/LOW)")

    category = finding.get("category")
    if category not in VALID_CATEGORIES:
        errors.append(f"{prefix}.category '{category}' is invalid")

    confidence = finding.get("confidence")
    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
        errors.append(f"{prefix}.confidence must be a float between 0.0 and 1.0")

    evidence = finding.get("evidence")
    if not isinstance(evidence, dict):
        errors.append(f"{prefix}.evidence must be an object")
    else:
        for field in ("source_url", "observation", "detection_method"):
            if not isinstance(evidence.get(field), str) or not evidence[field]:
                errors.append(f"{prefix}.evidence.{field} is missing or empty")

    action = finding.get("suggested_action")
    if not isinstance(action, dict):
        errors.append(f"{prefix}.suggested_action must be an object")
    else:
        if not isinstance(action.get("summary"), str) or not action["summary"]:
            errors.append(f"{prefix}.suggested_action.summary is missing or empty")

    affected_urls = finding.get("affected_urls")
    if not isinstance(affected_urls, list) or len(affected_urls) == 0:
        errors.append(f"{prefix}.affected_urls must be a non-empty array")

    return errors

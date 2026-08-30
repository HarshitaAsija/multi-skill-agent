"""
Shared Data Models for Agent Skill Marketplace.
Provides strongly structured classes for AuditRequest, AuditResult, Finding, EvidenceItem, SuggestedAction, and SeveritySummary.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from shared.config import (
    DEFAULT_MAX_PAGES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_USER_AGENT,
    SEVERITY_MEDIUM,
    VALID_SEVERITIES,
    VALID_CATEGORIES,
    CATEGORY_AI_DISCOVERABILITY,
)

def utc_now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()

@dataclass
class AuditRequest:
    url: str
    max_pages: int = DEFAULT_MAX_PAGES
    max_depth: int = DEFAULT_MAX_DEPTH
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    user_agent: str = DEFAULT_USER_AGENT
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class EvidenceItem:
    source_url: str         # WHERE: URL where the observation was made
    observation: str        # WHAT: What was concretely observed
    detection_method: str   # HOW: Technique used to detect this (e.g. "robots.txt parse", "DOM diffing")
    relevance: str = ""     # WHY: Why this observation matters for AI discoverability or engagement
    confidence: float = 1.0
    timestamp: str = field(default_factory=utc_now_iso)
    supporting_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Bound confidence between 0.0 and 1.0
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_url": self.source_url,
            "observation": self.observation,
            "detection_method": self.detection_method,
            "relevance": self.relevance,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "supporting_data": self.supporting_data,
        }

@dataclass
class SuggestedAction:
    summary: str
    priority: int = 1
    remediation_steps: List[str] = field(default_factory=list)
    expected_impact: str = ""
    effort_estimate: str = "MEDIUM"  # LOW, MEDIUM, HIGH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "priority": self.priority,
            "remediation_steps": self.remediation_steps,
            "expected_impact": self.expected_impact,
            "effort_estimate": self.effort_estimate,
        }

@dataclass
class Finding:
    id: str
    title: str
    category: str
    severity: str
    confidence: float
    evidence: EvidenceItem
    rationale: str
    affected_urls: List[str]
    suggested_action: SuggestedAction

    def __post_init__(self):
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{self.severity}'. Must be one of {VALID_SEVERITIES}")
        if self.category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{self.category}'. Must be one of {VALID_CATEGORIES}")
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "severity": self.severity,
            "confidence": self.confidence,
            "evidence": self.evidence.to_dict() if isinstance(self.evidence, EvidenceItem) else self.evidence,
            "rationale": self.rationale,
            "affected_urls": self.affected_urls,
            "suggested_action": self.suggested_action.to_dict() if isinstance(self.suggested_action, SuggestedAction) else self.suggested_action,
        }

@dataclass
class ProactiveRecommendation:
    id: str
    title: str
    category: str
    rationale: str
    suggested_implementation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "rationale": self.rationale,
            "suggested_implementation": self.suggested_implementation,
        }

@dataclass
class SeveritySummary:
    total_findings: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "total_findings": self.total_findings,
            "critical": self.critical,
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
        }

@dataclass
class AuditResult:
    site: str
    audited_at: str = field(default_factory=utc_now_iso)
    summary: SeveritySummary = field(default_factory=SeveritySummary)
    findings: List[Finding] = field(default_factory=list)
    proactive_recommendations: List[ProactiveRecommendation] = field(default_factory=list)

    def calculate_summary(self) -> None:
        """Recalculates counts by severity from current findings list."""
        summary = SeveritySummary(total_findings=len(self.findings))
        for f in self.findings:
            sev = f.severity.upper()
            if sev == "CRITICAL":
                summary.critical += 1
            elif sev == "HIGH":
                summary.high += 1
            elif sev == "MEDIUM":
                summary.medium += 1
            elif sev == "LOW":
                summary.low += 1
        self.summary = summary

    def to_dict(self) -> Dict[str, Any]:
        self.calculate_summary()
        return {
            "site": self.site,
            "audited_at": self.audited_at,
            "summary": self.summary.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "proactive_recommendations": [r.to_dict() for r in self.proactive_recommendations],
        }

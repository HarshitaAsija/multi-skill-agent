"""
Standardized Evidence Utility.
Ensures every finding is traceable back to concrete empirical observations.
"""

from typing import Dict, Any, Optional
from shared.models import EvidenceItem, utc_now_iso

class EvidenceBuilder:
    """
    Factory class for constructing standardized, fully traceable EvidenceItem objects.
    """

    @staticmethod
    def build(
        source_url: str,
        observation: str,
        detection_method: str,
        relevance: str = "",
        confidence: float = 1.0,
        dom_selector: Optional[str] = None,
        raw_snippet: Optional[str] = None,
        rendered_snippet: Optional[str] = None,
        http_status: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> EvidenceItem:
        """
        Builds a robust, traceable EvidenceItem answering all four traceability questions:
        - What was observed? (observation)
        - Where was it observed? (source_url, dom_selector)
        - How was it detected? (detection_method)
        - Why does it matter? (relevance)
        """
        supporting: Dict[str, Any] = {}

        if dom_selector:
            supporting["dom_selector"] = dom_selector
        if raw_snippet:
            supporting["raw_snippet"] = raw_snippet[:500]  # Truncate snippet to 500 chars max
        if rendered_snippet:
            supporting["rendered_snippet"] = rendered_snippet[:500]
        if http_status is not None:
            supporting["http_status"] = http_status
        if headers:
            supporting["http_headers"] = headers
        if extra_data:
            supporting.update(extra_data)

        return EvidenceItem(
            source_url=source_url,
            observation=observation,
            detection_method=detection_method,
            relevance=relevance,
            confidence=confidence,
            timestamp=utc_now_iso(),
            supporting_data=supporting
        )

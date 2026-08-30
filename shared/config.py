"""
Global Configuration & Constants for Agent Skill Marketplace.
"""

from typing import Dict, Any

# Marketplace Details
MARKETPLACE_NAME = "agent-skill-marketplace"
MARKETPLACE_VERSION = "1.0.0"
ENTRYPOINT_SKILL = "audit-orchestrator"

# Execution & Runtime Bounds
DEFAULT_MAX_PAGES = 15
DEFAULT_MAX_DEPTH = 2
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_POLITE_DELAY_SECONDS = 0.2
DEFAULT_MAX_RETRIES = 2
DEFAULT_USER_AGENT = "AgentReadinessAuditor/1.0 (+https://github.com/adobe-hackathon/agent-skill-marketplace)"

# Supported Skill Names
SKILL_ORCHESTRATOR = "audit-orchestrator"
SKILL_CRAWL_RENDER = "crawl-render-audit"
SKILL_FRESHNESS = "freshness-corroboration"
SKILL_ENGAGEMENT = "engagement-audit"

ALL_SKILLS = [
    SKILL_ORCHESTRATOR,
    SKILL_CRAWL_RENDER,
    SKILL_FRESHNESS,
    SKILL_ENGAGEMENT,
]

# Severity Levels
SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"

VALID_SEVERITIES = {
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
}

# Finding Categories
CATEGORY_AI_DISCOVERABILITY = "ai_discoverability"
CATEGORY_MACHINE_READINESS = "machine_readiness"
CATEGORY_FACTUAL_FRESHNESS = "factual_freshness"
CATEGORY_ONSITE_ENGAGEMENT = "onsite_engagement"

VALID_CATEGORIES = {
    CATEGORY_AI_DISCOVERABILITY,
    CATEGORY_MACHINE_READINESS,
    CATEGORY_FACTUAL_FRESHNESS,
    CATEGORY_ONSITE_ENGAGEMENT,
}

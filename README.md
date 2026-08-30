# Agent Skill Marketplace: AI Readiness & On-Site Engagement Auditor

## Overview
The **Agent Skill Marketplace** is a lightweight, non-destructive, highly generalizable website auditing engine built for **Adobe University Hackathon 2026 (Round 3)**.

It evaluates any website URL across four core dimensions:
1. **AI Discoverability**: Why AI search engines (Perplexity, SearchGPT, ChatGPT) and machine crawlers may fail to find, parse, or cite content.
2. **Machine/Agent Readiness**: Structured schema (Schema.org / JSON-LD) completeness, RAG vector chunking readiness, and JavaScript hydration lock.
3. **Factual Freshness & Entity Trust**: Outdated copyright timestamps, stale temporal signals, and cross-page entity identity contradictions.
4. **On-Site Engagement**: Above-the-fold value proposition clarity, navigation hierarchy, context retention on deep subpages, and Call-To-Action (CTA) discoverability.

---

## Skill Architecture

The marketplace consists of four modular skills:

| Skill Name | Role | Description |
| :--- | :--- | :--- |
| **`audit-orchestrator`** | **Designated Entrypoint** | Primary coordinator. Accepts audit requests, manages execution across specialist skills, deduplicates findings, calibrates severities, and emits the final JSON audit report. |
| **`crawl-render-audit`** | Specialist Skill | Audits HTTP accessibility, `robots.txt` AI agent directives, `sitemap.xml`, crawlability limits, raw server HTML vs rendered DOM text deltas, and machine-readable metadata. |
| **`freshness-corroboration`** | Specialist Skill | Audits temporal freshness signals, copyright recency, publication timestamps, and cross-page factual identity consistency for brand identity attributes. |
| **`engagement-audit`** | Specialist Skill | Audits on-site human/agent engagement factors: hero value proposition clarity, navigation hierarchy, subpage context retention, and Call-To-Action (CTA) discoverability. |

---

## Safety & Runtime Constraints
- **Strictly Read-Only**: Performs HTTP GET and HEAD requests only. Never authenticates, submits forms, or executes POST/PUT/DELETE operations.
- **Provider-Neutral & Portable**: Pure Python 3.11 implementation with standard library foundation and minimal lightweight dependencies.
- **Size & Performance**: Total package size < 15 MB (well under 50 MB limit). Completes typical audits in under 3 minutes.
- **Robots.txt Compliant**: Respects `Disallow` directives and rate-limits host requests (polite delay).

---

## Installation & Setup

```bash
# Clone repository
cd goofy-davinci

# Install lightweight dependencies
pip install -r requirements.txt
```

---

## Usage

### Run Audit CLI
```bash
python run_audit.py --url https://example.com
```

### Run Audit Programmatically
```python
from skills import load_skill_module

orch_mod = load_skill_module("audit-orchestrator", "orchestrate.py")
orchestrator = orch_mod.Orchestrator()

result = orchestrator.run_audit("https://example.com", max_pages=15)
print(result)
```

---

## Running Test Suite

```bash
pytest tests/
```

---

## JSON Report Schema

```json
{
  "site": "https://example.com/",
  "audited_at": "2026-08-29T18:15:00Z",
  "summary": {
    "total_findings": 1,
    "critical": 0,
    "high": 1,
    "medium": 0,
    "low": 0
  },
  "findings": [
    {
      "id": "DISC-01",
      "title": "Core Content Dependent on Client-Side JavaScript Hydration",
      "category": "ai_discoverability",
      "severity": "HIGH",
      "confidence": 0.95,
      "evidence": {
        "source_url": "https://example.com/",
        "observation": "Raw HTTP HTML response contains 120 words vs rendered DOM 1450 words.",
        "detection_method": "Dual-Stage DOM Hydration Delta",
        "confidence": 0.95,
        "timestamp": "2026-08-29T18:15:00Z",
        "supporting_data": {
          "dom_selector": "body > main"
        }
      },
      "rationale": "Non-rendering AI crawlers fail to index 91.7% of main page copy.",
      "affected_urls": ["https://example.com/"],
      "suggested_action": {
        "summary": "Implement Server-Side Rendering (SSR) or Dynamic Pre-rendering",
        "priority": 1,
        "remediation_steps": [
          "Configure SSR in application framework.",
          "Verify raw HTML output using 'curl -A \"GPTBot\" https://example.com/'."
        ],
        "expected_impact": "100% visibility for AI search crawlers and RAG indexers.",
        "effort_estimate": "MEDIUM"
      }
    }
  ],
  "proactive_recommendations": []
}
```

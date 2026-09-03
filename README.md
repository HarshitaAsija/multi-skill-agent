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
git clone https://github.com/HarshitaAsija/multi-skill-agent.git
cd multi-skill-agent

# Install lightweight dependencies (only beautifulsoup4)
pip install -r requirements.txt
```

---

## Local Testing Guide

### Step 1 — Run an Audit on Any Website

```bash
# Option A: Human-readable executive summary in terminal (recommended for quick testing)
python run_audit.py --url https://example.com --summary

# Option B: Full structured JSON report to stdout
python run_audit.py --url https://example.com

# Option C: Audit with custom page limit and save report to a file
python run_audit.py --url https://example.com --max-pages 5 --max-depth 2 --output report.json
```

`--summary` produces a formatted terminal view with severity badges, affected page counts, fix summaries, and proactive recommendations.

### Step 2 — Run the Automated Test Suite

```bash
python -m unittest discover tests
```

Expected output:
```
Ran 41 tests in ~1.0s
OK
```

### Step 3 — Build & Validate the Submission Package

```bash
python scripts/package_submission.py
```

This automated validator:
1. Executes all 41 unit tests.
2. Validates `marketplace.json` and agentskills.io `SKILL.md` compliance for all skills.
3. Creates `agent-skill-marketplace-submission.zip` (~72 KB, well within the 50 MB limit).
4. Unpacks the archive into an isolated temporary sandbox and confirms standalone CLI execution.

---

## Usage

### CLI Options Reference

| Flag | Shorthand | Description | Default |
| :--- | :--- | :--- | :--- |
| `--url` | `-u` | Target website URL to audit | *(Required)* |
| `--summary` | `-s` | Display formatted terminal executive summary | `False` |
| `--output` | `-o` | Save JSON report to a file path | `None` (stdout) |
| `--max-pages` | `-p` | Maximum pages to crawl across template buckets | `15` |
| `--max-depth` | `-d` | Maximum crawl link depth | `2` |
| `--timeout` | `-t` | Per-request HTTP timeout in seconds | `10.0` |

### Run Audit Programmatically

```python
from skills import load_skill_module

orch_mod = load_skill_module("audit-orchestrator", "orchestrate.py")
orchestrator = orch_mod.Orchestrator()

result = orchestrator.run_audit("https://example.com", max_pages=15, max_depth=2)
print(result)
```

---

## Evidence Model & False-Positive Prevention

Every finding emitted by the marketplace adheres to a strict four-part evidence contract:
1. **WHAT** (`observation`): Concrete, reproducible measurement or parsed string.
2. **WHERE** (`source_url` & `affected_urls`): The exact page URLs where the issue was observed.
3. **HOW** (`detection_method`): The deterministic parsing or structural heuristic used.
4. **WHY** (`relevance` & `rationale`): Direct explanation of why this impacts AI discoverability, RAG vector retrieval, factual freshness, or user engagement.

### False-Positive Controls
- **Context-Gated Schema Checks**: `Product` / `Offer` schema is only expected on commercial pages (`/pricing`, `/product`, `/plans`). `Organization` schema is only expected on root/homepages. Missing product schema is never flagged on blog posts or documentation.
- **Severity Boundaries**: Best practices (e.g. missing optional tags) are hard-capped at `MEDIUM` and never auto-elevated to `CRITICAL` or `HIGH`.
- **Intelligent Deduplication**: URL-specific occurrences of the same underlying issue (e.g. missing canonical tags across multiple subpages) are unified into a single base finding with merged `affected_urls`, rather than polluting the report with repetitive entries.
- **Output Schema Validation**: The orchestrator validates the final report against the required JSON schema with count consistency verification before returning.

---

## JSON Report Schema

```json
{
  "site": "https://example.com/",
  "audited_at": "2026-09-03T20:45:00Z",
  "summary": {
    "total_findings": 1,
    "critical": 0,
    "high": 1,
    "medium": 0,
    "low": 0
  },
  "findings": [
    {
      "id": "KNOW-02-MISSING-ORG-SCHEMA",
      "title": "Missing Primary Organization / WebSite Schema.org JSON-LD",
      "category": "machine_readiness",
      "severity": "HIGH",
      "confidence": 0.95,
      "evidence": {
        "source_url": "https://example.com/",
        "observation": "Homepage has 0 JSON-LD blocks but lacks Organization or WebSite Schema.org entity definitions.",
        "detection_method": "Schema.org JSON-LD Parser",
        "relevance": "LLM Knowledge Graph indexers look for explicit Organization schema on homepages to disambiguate brand entities.",
        "confidence": 0.95,
        "timestamp": "2026-09-03T20:45:00Z",
        "supporting_data": {
          "found_schema_types": []
        }
      },
      "rationale": "Without structured Organization JSON-LD markup, AI search assistants must guess company name, logo, social links, and brand descriptions.",
      "affected_urls": [
        "https://example.com/"
      ],
      "suggested_action": {
        "summary": "Inject Organization Schema.org JSON-LD on the homepage.",
        "priority": 1,
        "remediation_steps": [
          "Add <script type=\"application/ld+json\"> with @type: Organization.",
          "Include name, url, logo, description, and sameAs social profile links."
        ],
        "expected_impact": "Establishes authoritative brand entity identity for AI knowledge graphs.",
        "effort_estimate": "LOW"
      }
    }
  ],
  "proactive_recommendations": [
    {
      "id": "REC-PROACTIVE-01-LLMS-TXT",
      "title": "Publish an llms.txt Machine Index Manifest",
      "category": "ai_discoverability",
      "rationale": "The /llms.txt standard provides AI assistants and autonomous agents with a curated markdown directory of authoritative pages, reducing hallucination and token overhead.",
      "suggested_implementation": "Publish a clean /llms.txt file at the domain root with curated markdown links to documentation, pricing, and product specs."
    }
  ]
}
```

---

## Submission Packaging & Verification

To build and verify the standalone marketplace submission archive:

```bash
python scripts/package_submission.py
```

This automated validator:
1. Executes all 41 automated unit tests.
2. Validates `marketplace.json` schema and agentskills.io compliance for every `SKILL.md`.
3. Creates a clean, compressed submission archive (`agent-skill-marketplace-submission.zip`).
4. Verifies the archive size is well within the 50 MB limit (< 100 KB).
5. Unpacks the archive into an isolated temporary directory and confirms standalone CLI execution.

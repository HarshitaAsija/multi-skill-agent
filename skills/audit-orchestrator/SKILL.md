---
name: audit-orchestrator
description: Sole designated entrypoint for the Agent Skill Marketplace. Audits any website for AI discoverability, crawlability, structured data quality, factual freshness, and on-site engagement. Run via: python run_audit.py --url <target_url> --summary
---

# audit-orchestrator

## Overview
The `audit-orchestrator` is the **single entrypoint** for this Agent Skill Marketplace.
Point it at any website URL and it produces a structured JSON report with a 0–100 AI
Readiness Score, prioritised findings (each with evidence + remediation), and optional
LLM-generated recommendations.

## How to invoke

### Install dependencies (once)
```bash
pip install -r requirements.txt
```

### Run an audit
```bash
# Print a formatted terminal summary (recommended for grading / demos)
python run_audit.py --url https://example.com --summary

# Write a Markdown report to a file
python run_audit.py --url https://example.com --markdown report.md --summary

# Write structured JSON output to a file
python run_audit.py --url https://example.com --output report.json

# With Gemini LLM reasoning enabled
python run_audit.py --url https://example.com --summary --gemini-api-key "YOUR_KEY"
```

### Full CLI reference
| Flag | Description | Default |
|:---|:---|:---|
| `--url` | Target website URL *(required)* | — |
| `--summary` | Print formatted terminal summary | `false` |
| `--markdown FILE` | Write Markdown report to a file | none |
| `--output FILE` | Write JSON report to a file (stdout if omitted) | stdout |
| `--gemini-api-key KEY` | Google Gemini API key for LLM synthesis | reads `GEMINI_API_KEY` env / `.env` |
| `--max-pages N` | Max pages to crawl (1–200) | `40` |
| `--max-depth N` | Max link depth from root (1–10) | `4` |
| `--timeout SECS` | Per-request HTTP timeout (1.0–60.0) | `10.0` |
| `--allow-private` | Allow auditing private/loopback IPs | `false` |
| `--insecure` | Disable TLS certificate verification | `false` |
| `--debug` | Verbose stack traces | `false` |

## Inputs
- `url` — target website URL (required)
- All other inputs are optional CLI flags with sensible defaults shown above.

## Output
A single `AuditResult` JSON object with:
- `site` — normalised root URL
- `audited_at` — ISO-8601 timestamp
- `ai_readiness_score` — integer 0–100
- `score_status` — `"computed"` or `"not_computed"` (if zero pages crawled)
- `summary` — finding counts by severity (CRITICAL / HIGH / MEDIUM / LOW)
- `findings[]` — each with `id`, `title`, `severity`, `evidence`, `suggested_action`
- `crawl_metadata` — pages crawled, host alias used, sitemap status
- `proactive_recommendations[]` — site-specific improvement actions
- `market_intelligence` — question-answerability analysis for the detected industry

## Gemini LLM mode (optional)
Set `GEMINI_API_KEY` as an environment variable or in a `.env` file in the project root.
Without a key the audit runs in **fully deterministic, evidence-only mode** — this is a
normal, supported mode, not a degraded fallback.

## What this skill coordinates
The orchestrator invokes three specialist sub-skills internally (no separate invocation needed):
- **`crawl-render-audit`** — BFS crawl, robots.txt, sitemap health, JSON-LD, SPA detection
- **`freshness-corroboration`** — copyright year, timestamp staleness, brand consistency
- **`engagement-audit`** — hero value prop, form labels, CTA clarity, FAQPage/Speakable schema

## Guardrails
- Read-only — GET / HEAD requests only, no write or authenticated actions
- Respects `robots.txt` (does not crawl disallowed paths)
- SSRF-protected — private/loopback IPs blocked by default
- Hard time cap — 180-second crawl ceiling, full audit completes in under 5 minutes
- Graceful failure — unreachable domains emit a structured CRITICAL finding, never an unhandled exception

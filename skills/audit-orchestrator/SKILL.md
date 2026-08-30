---
name: audit-orchestrator
description: Sole designated entrypoint for the Agent Skill Marketplace. Coordinates audit requests, executes specialist skills, deduplicates findings, calibrates severities, and outputs the final JSON audit report.
---

# audit-orchestrator

## Overview
The `audit-orchestrator` is the **ONE designated entrypoint skill** for the Agent Skill Marketplace. It receives the target website URL, initializes the shared audit context, triggers execution across specialist skills, collects and deduplicates findings, calibrates finding severities, and generates the final structured audit report.

## When to Use
Use `audit-orchestrator` as the primary entrypoint whenever auditing any website for AI discoverability, machine readiness, factual freshness, or on-site engagement.

## Inputs
- `url`: Target website URL (string, required)
- `max_pages`: Crawl page limit (default: 15)
- `max_depth`: Crawl depth limit (default: 2)
- `timeout_seconds`: Per-request timeout in seconds (default: 10.0)

## Outputs
- Standardized `AuditResult` JSON object containing site metadata, timestamp, severity summary counts, evidence-backed findings, and proactive recommendations.

## Procedure
1. Validate and normalize the target URL using `shared.url_utils`.
2. Construct the global `AuditRequest` context.
3. Invoke specialist skills:
   - `crawl-render-audit`
   - `freshness-corroboration`
   - `engagement-audit`
4. Collect all skill `Finding` lists.
5. Deduplicate overlapping findings across skills based on check ID and target URL.
6. Calibrate finding severities using `shared.severity.SeverityEvaluator`.
7. Compile and emit the final `AuditResult` dictionary.

## Constraints
- Must remain 100% read-only (GET/HEAD requests only).
- Must complete execution within 5 minutes.
- Must handle network failures gracefully without crashing.

## Failure Handling
- If the target URL is invalid or unreachable, return a structured `AuditResult` containing a CRITICAL finding detailing the connection/validation failure rather than throwing an unhandled exception.

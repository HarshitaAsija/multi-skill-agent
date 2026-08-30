---
name: crawl-render-audit
description: Audits website HTTP accessibility, robots.txt AI bot directives, sitemaps, crawlability bounds, raw server HTML vs rendered DOM text deltas, and machine-readable metadata.
---

# crawl-render-audit

## Overview
Evaluates whether a website can be fetched, crawled, and parsed by machine agents. Audits robots.txt rules, sitemap health, canonical link integrity, and client-side JavaScript hydration lock.

## When to Use
Invoked by `audit-orchestrator` during the crawl phase.

## Inputs
- `request`: `AuditRequest` object (contains `url`, `max_pages`, `max_depth`, `timeout_seconds`)
- `http_client`: Instance of `shared.http_client.SafeHTTPClient` (injected by orchestrator)

## Outputs
- List of `Finding` objects under `ai_discoverability` and `machine_readiness` categories.
- List of crawled page HTTP responses for downstream skill analysis.

## Procedure
1. Fetch and parse `robots.txt` for AI agent user-agent blocks (`GPTBot`, `PerplexityBot`, etc.).
2. Fetch `sitemap.xml` and verify link reachability.
3. Perform bounded crawl up to `max_pages`.
4. Inspect raw HTML for canonical tags, title, meta descriptions, and heading hierarchy.
5. Compute raw HTML text metrics to detect JavaScript client-side hydration dependency.

## Constraints
- Strictly read-only GET/HEAD requests.
- Must respect robots.txt disallows.

## Failure Handling
- Log HTTP timeouts per page and continue auditing remaining pages.

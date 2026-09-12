---
name: freshness-corroboration
description: Audits temporal freshness signals, copyright recency, publication timestamps, and cross-page factual consistency for brand identity attributes.
---

# freshness-corroboration

## Overview
Evaluates temporal freshness signals (copyright years, article modification timestamps) and conducts intra-site factual corroboration (verifying that entity identity, company name, brand claims, and contact attributes remain consistent and uncontradicted across multiple pages on the audited domain).

## When to Use
Invoked by `audit-orchestrator` during the comprehensive site audit phase.

## Inputs
- `pages`: List of crawled page objects containing extracted text and HTTP metadata
- `http_client`: Shared HTTP client
- `page_data_map`: Mapping of URL to structured PageData objects

## Outputs
- List of `Finding` objects under `factual_freshness` category.

## Procedure
1. Scan page footers and meta tags for copyright years and publication dates.
2. Flag copyright dates older than the current calendar year (`FRESH-01`).
3. Corroborate core brand and entity statements (e.g. JSON-LD Organization name vs page title brands) across homepage and subpages (`FRESH-02`).
4. Detect stale editorial content lacking recent updates or clear publication anchors (`FRESH-03`).
5. Verify brand naming consistency across page title suffixes.

## Constraints & Security Boundary
- **Bounded Verification**: Audits intra-domain cross-page claim consistency and declared entity links. Operates strictly within polite crawler bounds without executing unbounded third-party web crawling.

## Failure Handling
- If text extraction fails on a specific page, skip and continue evaluating remaining pages.

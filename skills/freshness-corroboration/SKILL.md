---
name: freshness-corroboration
description: Audits temporal freshness signals, copyright recency, publication timestamps, and cross-page factual consistency for brand identity attributes.
---

# freshness-corroboration

## Overview
Evaluates temporal signals (outdated copyright years, missing modified dates) and verifies that entity identity facts (company name, contact details, core attributes) remain consistent across audited pages.

## When to Use
Invoked by `audit-orchestrator` during the audit phase.

## Inputs
- `pages`: List of crawled page objects containing extracted text and HTTP metadata
- `http_client`: Shared HTTP client

## Outputs
- List of `Finding` objects under `factual_freshness` category.

## Procedure
1. Scan page footers and meta tags for copyright years and publication dates.
2. Flag copyright dates older than the current calendar year.
3. Extract core brand claims (organization name, primary contact) across pages.
4. Detect discrepancies between homepage claims and subpage claims.

## Constraints
- Safe, bounded checks only. No un-bounded web searches across external third-party sites.

## Failure Handling
- If text extraction fails on a specific page, skip and continue evaluating remaining pages.

---
name: engagement-audit
description: Audits on-site human/agent engagement factors: above-the-fold value proposition clarity, navigation hierarchy, subpage context retention, and Call-To-Action (CTA) discoverability.
---

# engagement-audit

## Overview
Evaluates whether visitors and machine agents arriving on the site can immediately understand what the brand offers, navigate effectively, retain context on deep subpages, and identify clear next-step actions.

## When to Use
Invoked by `audit-orchestrator` during the audit phase.

## Inputs
- `pages`: List of crawled page objects containing DOM trees and text blocks

## Outputs
- List of `Finding` objects under `onsite_engagement` category.

## Procedure
1. Inspect hero/above-the-fold section of the homepage for clear value proposition text.
2. Evaluate navigation menu structure and breadcrumb presence on subpages (context isolation).
3. Scan for interactive buttons and styled primary CTAs.
4. Flag ambiguous or generic CTA labels ("click here", "submit").

## Constraints
- Read-only analysis. Does not simulate user clicks or form submissions.

## Failure Handling
- Gracefully handle pages without explicit hero headers or subpage navigation menus.

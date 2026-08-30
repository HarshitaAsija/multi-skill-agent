# audit-orchestrator Reference Guide

The orchestrator manages the global execution pipeline:
1. `validate_and_prepare()`: Validates target URL and builds `AuditRequest`.
2. `run_pipeline()`: Calls `crawl-render-audit`, `freshness-corroboration`, and `engagement-audit`.
3. `deduplicate_and_calibrate()`: Merges findings, removes duplicates, and calibrates severities.
4. `generate_report()`: Emits `AuditResult` JSON matching the official report schema.

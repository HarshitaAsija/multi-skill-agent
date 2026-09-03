# Audit Orchestrator Architecture & Composition Reference

## 1. Role as the Designated Entrypoint
`audit-orchestrator` is the single entrypoint declared in `marketplace.json` (`is_entrypoint: true`). It coordinates all specialist skills, deduplicates findings, executes severity calibration, and guarantees schema conformity.

## 2. Dynamic Hyphenated Module Loading
The marketplace loader (`skills/__init__.py`) utilizes synthetic Python package injection to resolve relative module imports across hyphenated directory names:
```python
from skills import load_skill_module
orchestrator = load_skill_module("audit-orchestrator", "orchestrate.py").Orchestrator()
```

## 3. Intelligent Deduplication & Aggregation Algorithm
- **Base ID Normalization**: Strips URL suffixes (`-http://...`) from finding IDs so that repeated occurrences (e.g. missing canonical tags on 10 subpages) group under a single finding (`DISC-05-MISSING-CANONICAL`).
- **URL Union**: Merges `affected_urls` into a unique, ordered list.
- **Dynamic Observation Enrichment**: Updates evidence observation with multi-page scope notes (`"Observed across N pages..."`).
- **Severity Ordering**: Sorts findings deterministically by severity (`CRITICAL` > `HIGH` > `MEDIUM` > `LOW`), action priority, and confidence.
- **Report Capping**: Caps total output findings at 30 to prevent report bloat.

## 4. Deterministic Severity Calibration Matrix
Calibrates severity based on scope, accessibility impact, and confidence:
- `CRITICAL`: Global site-wide accessibility blockage or core machine function lock.
- `HIGH`: Major discoverability / indexing prevention on primary pages.
- `MEDIUM`: Contextual extractability gaps or localized structural issues.
- `LOW`: Minor best-practice omissions or informational opportunities.
- **Guardrail**: Best practices are hard-capped at `MEDIUM` and never auto-escalate to `CRITICAL` or `HIGH`.

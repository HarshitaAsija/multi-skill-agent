#!/usr/bin/env python3
"""
CLI Runner for Agent Skill Marketplace.
Usage: python run_audit.py --url https://example.com
"""

import sys
import json
import argparse
from skills import load_skill_module

# Load designated entrypoint orchestrator module dynamically
orch_mod = load_skill_module("audit-orchestrator", "orchestrate.py")
Orchestrator = orch_mod.Orchestrator

def main():
    parser = argparse.ArgumentParser(
        description="Agent Skill Marketplace: AI Discoverability & On-site Engagement Auditor"
    )
    parser.add_argument(
        "--url", "-u",
        required=True,
        help="Target website URL to audit (e.g., https://example.com)"
    )
    parser.add_argument(
        "--max-pages", "-p",
        type=int,
        default=15,
        help="Maximum pages to crawl (default: 15)"
    )
    parser.add_argument(
        "--max-depth", "-d",
        type=int,
        default=2,
        help="Maximum crawl link depth (default: 2)"
    )
    parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=10.0,
        help="Per-request HTTP timeout in seconds (default: 10.0)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Optional file path to write JSON report output"
    )
    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="Display human-readable executive summary in terminal instead of raw JSON"
    )

    args = parser.parse_args()

    orchestrator = Orchestrator()
    result = orchestrator.run_audit(
        url=args.url,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        timeout_seconds=args.timeout
    )

    json_output = json.dumps(result, indent=2)

    # If --output file specified, save to disk
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_output)

    # Output formatted summary or clean JSON report to stdout
    if args.summary:
        print_summary(result)
    else:
        print(json_output)


def print_summary(report: dict) -> None:
    site = report.get("site", "Unknown")
    audited_at = report.get("audited_at", "")
    score = report.get("ai_readiness_score", 100)
    summary = report.get("summary", {})
    findings = report.get("findings", [])
    recs = report.get("proactive_recommendations", [])

    print("\n" + "=" * 70)
    print("  AGENT SKILL MARKETPLACE — AUDIT EXECUTIVE SUMMARY")
    print("=" * 70)
    print(f"Target Site:   {site}")
    print(f"Audited At:    {audited_at}")
    print(f"AI Readiness:  {score} / 100")
    print(f"Total Issues:  {summary.get('total_findings', 0)} "
          f"(CRITICAL: {summary.get('critical', 0)} | "
          f"HIGH: {summary.get('high', 0)} | "
          f"MEDIUM: {summary.get('medium', 0)} | "
          f"LOW: {summary.get('low', 0)})")
    print("-" * 70)

    if not findings:
        print("  [OK] No critical issues detected. Site demonstrates high AI readiness.")
    else:
        for idx, f in enumerate(findings, 1):
            sev = f.get("severity", "INFO").upper()
            fid = f.get("id", "")
            title = f.get("title", "")
            action = f.get("suggested_action", {}).get("summary", "")
            affected = len(f.get("affected_urls", []))
            print(f"\n{idx}. [{sev}] {fid}")
            print(f"   Title:    {title}")
            print(f"   Scope:    Affects {affected} page(s)")
            print(f"   Fix:      {action}")

    if recs:
        print("\n" + "-" * 70)
        print("  PROACTIVE RECOMMENDATIONS")
        print("-" * 70)
        for r in recs:
            print(f"  * {r.get('title')}: {r.get('suggested_implementation')}")

    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    main()

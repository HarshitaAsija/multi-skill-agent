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
        default=40,
        help="Maximum pages to crawl (default: 40)"
    )
    parser.add_argument(
        "--max-depth", "-d",
        type=int,
        default=4,
        help="Maximum crawl link depth (default: 4)"
    )
    parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=10.0,
        help="Per-request HTTP timeout in seconds (default: 10.0)"
    )
    parser.add_argument(
        "--gemini-api-key", "-g",
        type=str,
        default=None,
        help="Optional Google Gemini API Key for deep LLM answerability and recommendations (or set GEMINI_API_KEY env var)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Optional file path to write JSON report output"
    )
    parser.add_argument(
        "--markdown", "-m",
        type=str,
        default=None,
        help="Optional file path to export formatted Markdown audit report (e.g., audit-report.md)"
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
        timeout_seconds=args.timeout,
        gemini_api_key=args.gemini_api_key
    )

    json_output = json.dumps(result, indent=2)

    # If --output file specified, save to disk
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_output)

    # If --markdown file specified, export formatted Markdown document
    if args.markdown:
        from shared.report_generator import generate_markdown_report
        md_content = generate_markdown_report(result)
        with open(args.markdown, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"[REPORT] Exported Markdown audit document to: {args.markdown}")

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

    exec_synthesis = report.get("executive_synthesis")

    print("\n" + "=" * 70)
    print("  AGENT SKILL MARKETPLACE - AUDIT EXECUTIVE SUMMARY")
    print("=" * 70)
    print(f"Target Site:   {site}")
    print(f"Audited At:    {audited_at}")
    print(f"AI Readiness:  {score} / 100")
    if exec_synthesis:
        print(f"AI Engine:     Google Gemini (Active LLM Reasoning)")
    else:
        print(f"AI Engine:     Deterministic Heuristic Mode (Set GEMINI_API_KEY to activate Gemini)")
    print(f"Total Issues:  {summary.get('total_findings', 0)} "
          f"(CRITICAL: {summary.get('critical', 0)} | "
          f"HIGH: {summary.get('high', 0)} | "
          f"MEDIUM: {summary.get('medium', 0)} | "
          f"LOW: {summary.get('low', 0)})")
    print("-" * 70)

    if exec_synthesis:
        print("\n" + "-" * 70)
        print("  EXECUTIVE AI DISCOVERABILITY SYNTHESIS (Google Gemini)")
        print("-" * 70)
        print(exec_synthesis)
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

    mi = report.get("market_intelligence")
    if mi:
        print("\n" + "=" * 70)
        print("  AI ANSWERABILITY & MARKET INTELLIGENCE REPORT")
        print("=" * 70)
        print(f"Detected Industry:        {mi.get('industry_label', 'Unknown')}")
        print(f"Market Question Coverage: {mi.get('market_question_coverage_pct', 0)}% "
              f"({mi.get('clear_count', 0)} Answerable | "
              f"{mi.get('partial_count', 0)} Partial | "
              f"{mi.get('missing_count', 0)} Missing)")
        print("-" * 70)
        print("  HIGH-INTENT QUESTIONS CHECKED:")
        status_icons = {
            "ANSWERABLE": "[OK]",
            "PARTIAL": "[PARTIAL]",
            "NOT_ANSWERABLE": "[GAP]",
        }
        for q in mi.get("questions", []):
            st = status_icons.get(q.get("status"), "[?]")
            print(f"  {st:<10} {q.get('question')}")
            if q.get("status") != "ANSWERABLE":
                print(f"             Simulated AI Query: \"{q.get('simulated_prompt')}\"")
                print(f"             AI Risk: {q.get('ai_risk')}")

        roadmap = mi.get("roadmap", [])
        if roadmap:
            print("\n" + "-" * 70)
            print("  SMART GROWTH ROADMAP (PRIORITIZED ACTION PLAN)")
            print("-" * 70)
            for item in roadmap:
                print(f"  Priority {item.get('priority')} [{item.get('impact')} Impact | {item.get('effort')} Effort]")
                print(f"    Action: {item.get('action_title')}")
                print(f"    Why:    {item.get('why')}")

    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    main()

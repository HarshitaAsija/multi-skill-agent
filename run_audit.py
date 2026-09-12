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

    parser.add_argument(
        "--allow-private",
        action="store_true",
        help="Permit auditing of private or loopback networks (disabled by default for SSRF protection)"
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification (intended only for auditing staging or self-signed test sites)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable full verbose debugging stack traces"
    )

    args = parser.parse_args()

    # 1. Input Boundary Validation
    from shared.security import validate_runtime_bounds, is_safe_url, is_safe_output_path

    valid_bounds, bounds_err = validate_runtime_bounds(args.max_pages, args.max_depth, args.timeout)
    if not valid_bounds:
        sys.stderr.write(f"[INPUT ERROR] {bounds_err}\n")
        sys.exit(1)

    # 2. SSRF Security Validation
    is_safe, safety_reason = is_safe_url(args.url, allow_private=args.allow_private)
    if not is_safe:
        sys.stderr.write(f"[SECURITY ERROR] Target URL rejected: {safety_reason}\n")
        sys.exit(1)

    # 3. Path Traversal Validation for Export Files
    if args.output:
        safe_out, resolved_out = is_safe_output_path(args.output)
        if not safe_out:
            sys.stderr.write(f"[SECURITY ERROR] Invalid --output path: {resolved_out}\n")
            sys.exit(1)
        args.output = resolved_out

    if args.markdown:
        safe_md, resolved_md = is_safe_output_path(args.markdown)
        if not safe_md:
            sys.stderr.write(f"[SECURITY ERROR] Invalid --markdown path: {resolved_md}\n")
            sys.exit(1)
        args.markdown = resolved_md

    # 4. Safe Execution Pipeline
    try:
        from shared.http_client import SafeHTTPClient
        client = SafeHTTPClient(
            timeout=args.timeout,
            allow_private=args.allow_private,
            verify_ssl=not args.insecure
        )
        orchestrator = Orchestrator(http_client=client)
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

    except KeyboardInterrupt:
        sys.stderr.write("\n[INTERRUPTED] Audit halted by user.\n")
        sys.exit(130)
    except Exception as e:
        if args.debug:
            raise
        sys.stderr.write(f"\n[ERROR] Audit execution failed: {e}\n")
        sys.exit(1)


def print_summary(report: dict) -> None:
    site = report.get("site", "Unknown")
    audited_at = report.get("audited_at", "")
    score = report.get("ai_readiness_score")
    score_status = report.get("score_status", "COMPUTED")
    summary = report.get("summary", {})
    findings = report.get("findings", [])
    recs = report.get("proactive_recommendations", [])
    crawl_meta = report.get("crawl_metadata", {})

    exec_synthesis = report.get("executive_synthesis")

    print("\n" + "=" * 70)
    print("  AGENT SKILL MARKETPLACE - AUDIT EXECUTIVE SUMMARY")
    print("=" * 70)
    print(f"Target Site:   {site}")
    print(f"Audited At:    {audited_at}")
    if score is not None:
        print(f"AI Readiness:  {score} / 100")
    else:
        print(f"AI Readiness:  NOT_COMPUTED (0 pages crawled - abstained)")
    if crawl_meta:
        c_stat = crawl_meta.get("crawl_status", "UNKNOWN")
        c_count = crawl_meta.get("pages_crawled", 0)
        c_alias = f" (via alias {crawl_meta.get('host_alias_used')})" if crawl_meta.get("host_alias_used") else ""
        print(f"Crawl Summary: {c_stat} — {c_count} page(s) analyzed{c_alias}")
    is_abstained = score_status == "NOT_COMPUTED" or crawl_meta.get("pages_crawled", 0) == 0

    if is_abstained:
        print(f"AI Engine:     Abstained (Zero pages retrieved — LLM reasoning withheld to prevent hallucination)")
    else:
        gemini_active = False
        if exec_synthesis and not exec_synthesis.startswith("Audit Incomplete"):
            gemini_active = True
        elif report.get("market_intelligence"):
            questions = report.get("market_intelligence", {}).get("questions", [])
            if any("Gemini" in str(q.get("evidence_found", "")) or "Gemini" in str(q.get("ai_risk", "")) for q in questions):
                gemini_active = True

        if gemini_active:
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
        if is_abstained:
            print("  AUDIT ABSTENTION NOTICE")
        else:
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
            evidence = q.get('evidence_found', '')
            if evidence and q.get('status') == "ANSWERABLE":
                print(f"             Verified Signal: {evidence[:100]}")
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

            # Print Suggested FAQ Schema JSON-LD
            faq_entities = [item.get("suggested_faq_json_ld") for item in roadmap if item.get("suggested_faq_json_ld")]
            if faq_entities:
                print("\n" + "-" * 70)
                print("  READY-TO-PASTE FAQ SCHEMA (REMEDIATES DETECTED GAPS)")
                print("-" * 70)
                composite_faq = {
                    "@context": "https://schema.org",
                    "@type": "FAQPage",
                    "mainEntity": faq_entities[:3],
                }
                print(json.dumps(composite_faq, indent=2))

    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    main()

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
        "--timeout", "-t",
        type=float,
        default=10.0,
        help="Per-request HTTP timeout in seconds (default: 10.0)"
    )

    args = parser.parse_args()

    orchestrator = Orchestrator()
    result = orchestrator.run_audit(
        url=args.url,
        max_pages=args.max_pages,
        timeout_seconds=args.timeout
    )

    # Output clean JSON report to stdout
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()

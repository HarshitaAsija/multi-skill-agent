#!/usr/bin/env python3
"""
Submission Packaging & Verification Script.

Prepares and validates the submission package for Adobe University Hackathon Round 3:
  1. Runs all automated unit tests to ensure zero regressions.
  2. Verifies marketplace.json integrity and agentskills.io compliance.
  3. Verifies each skill directory contains valid SKILL.md with YAML frontmatter.
  4. Bundles clean ZIP archive without temporary artifacts.
  5. Verifies package size (< 50 MB limit).
  6. Unpacks into temporary sandbox and verifies CLI entrypoint execution.
"""

import sys
import os
import json
import zipfile
import tempfile
import subprocess
import re
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
MARKETPLACE_JSON = ROOT_DIR / "marketplace.json"
OUTPUT_ZIP = ROOT_DIR / "agent-skill-marketplace-submission.zip"

MAX_PACKAGE_BYTES = 50 * 1024 * 1024  # 50 MB limit


def run_step(step_name: str, fn):
    print(f"\n[STEP] {step_name}...")
    try:
        fn()
        print(f"  [OK] {step_name} passed.")
    except Exception as e:
        print(f"  [FAILED] {step_name}: {e}")
        sys.exit(1)


def step_run_tests():
    cmd = [sys.executable, "-m", "unittest", "discover", "tests"]
    result = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError(f"Unit tests failed with code {result.returncode}")
    print(f"       Ran test suite successfully ({result.stderr.strip().splitlines()[-1]})")


def step_verify_marketplace_config():
    if not MARKETPLACE_JSON.exists():
        raise FileNotFoundError("marketplace.json not found in root")

    with open(MARKETPLACE_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    for field in ("name", "version", "entrypoint", "skills"):
        if field not in data:
            raise ValueError(f"marketplace.json missing required field: {field}")

    entrypoint_name = data["entrypoint"]
    entrypoints = [s for s in data["skills"] if s.get("is_entrypoint") is True]

    if len(entrypoints) != 1:
        raise ValueError(f"marketplace.json must declare EXACTLY 1 entrypoint, found {len(entrypoints)}")

    if entrypoints[0]["name"] != entrypoint_name:
        raise ValueError(
            f"Declared entrypoint '{entrypoint_name}' does not match entrypoint skill '{entrypoints[0]['name']}'"
        )

    for skill in data["skills"]:
        path = ROOT_DIR / skill["path"]
        if not path.exists():
            raise FileNotFoundError(f"SKILL.md not found at declared path: {skill['path']}")

        # Verify YAML frontmatter
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            raise ValueError(f"{skill['path']} missing opening YAML frontmatter '---'")

        match = re.search(r"^name:\s*([^\s]+)", content, re.MULTILINE)
        if not match or match.group(1).strip() != skill["name"]:
            raise ValueError(f"{skill['path']} YAML frontmatter name does not match skill name '{skill['name']}'")


def step_create_zip():
    included_patterns = [
        "marketplace.json",
        "README.md",
        "requirements.txt",
        "run_audit.py",
        "shared",
        "skills",
        "tests",
    ]

    ignored_names = {
        "__pycache__", ".pytest_cache", ".git", ".gitignore",
        "env", "venv", ".venv", ".DS_Store"
    }

    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in included_patterns:
            item_path = ROOT_DIR / item
            if item_path.is_file():
                zf.write(item_path, arcname=item)
            elif item_path.is_dir():
                for root, dirs, files in os.walk(item_path):
                    # Filter out ignored dirs in-place
                    dirs[:] = [d for d in dirs if d not in ignored_names and not d.endswith(".pyc")]
                    for file in files:
                        if file.endswith((".pyc", ".pyo")) or file in ignored_names:
                            continue
                        full_path = Path(root) / file
                        arcname = full_path.relative_to(ROOT_DIR)
                        zf.write(full_path, arcname=str(arcname).replace("\\", "/"))

    size_bytes = OUTPUT_ZIP.stat().st_size
    size_kb = size_bytes / 1024
    print(f"       Created archive: {OUTPUT_ZIP.name} ({size_kb:.1f} KB)")

    if size_bytes > MAX_PACKAGE_BYTES:
        raise ValueError(f"ZIP package size ({size_kb:.1f} KB) exceeds 50 MB limit!")


def step_verify_unpacked_execution():
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(OUTPUT_ZIP, "r") as zf:
            zf.extractall(tmpdir)

        # Test CLI help in the unpacked directory
        cmd = [sys.executable, "run_audit.py", "--help"]
        res = subprocess.run(cmd, cwd=tmpdir, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"run_audit.py --help failed in unpacked sandbox: {res.stderr}")

        # Test quick validation audit on example.com in unpacked sandbox
        cmd_audit = [sys.executable, "run_audit.py", "--url", "https://example.com", "--max-pages", "1"]
        res_audit = subprocess.run(cmd_audit, cwd=tmpdir, capture_output=True, text=True)
        if res_audit.returncode != 0:
            raise RuntimeError(f"run_audit.py execution failed in unpacked sandbox: {res_audit.stderr}")

        # Verify output is valid JSON
        stdout = res_audit.stdout.strip()
        json_start = stdout.find("{")
        if json_start == -1:
            raise ValueError(f"Unpacked audit did not produce JSON output: {stdout}")

        report = json.loads(stdout[json_start:])
        if "summary" not in report or "findings" not in report:
            raise ValueError("Unpacked audit report missing required keys")

        print(f"       Unpacked standalone execution verified: audit produced valid report for {report['site']}")


def main():
    print("=================================================================")
    print("  Agent Skill Marketplace - Submission Package Validator")
    print("=================================================================")

    run_step("1. Automated Test Suite", step_run_tests)
    run_step("2. marketplace.json & SKILL.md Compliance", step_verify_marketplace_config)
    run_step("3. ZIP Packaging", step_create_zip)
    run_step("4. Standalone Sandbox Execution Verification", step_verify_unpacked_execution)

    print("\n=================================================================")
    print("  [SUCCESS] All verification steps passed!")
    print(f"  Package ready: {OUTPUT_ZIP.name}")
    print("=================================================================\n")


if __name__ == "__main__":
    main()

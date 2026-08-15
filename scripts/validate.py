#!/usr/bin/env python3
"""
DL Training Skill validation script.
Validates skill output files against expected format.
Usage: python validate.py <output_file.md>
"""

import re
import sys
from pathlib import Path


def validate_workflow_output(filepath: str) -> dict:
    """Validate a workflow output markdown file."""
    results = {"passed": [], "failed": []}
    content = Path(filepath).read_text(encoding='utf-8')

    # Check 1: Has a title
    if re.search(r'^# .+', content, re.MULTILINE):
        results["passed"].append("Has title (H1 heading)")
    else:
        results["failed"].append("Missing H1 title")

    # Check 2: Has training method section
    if re.search(r'(SFT|LoRA|DPO|GRPO)', content):
        results["passed"].append("Mentions training methods")
    else:
        results["failed"].append("Missing training method references")

    # Check 3: Has dry-run mention
    if re.search(r'dry.?run|--dry-run', content, re.IGNORECASE):
        results["passed"].append("Mentions dry-run safety")
    else:
        results["failed"].append("Missing dry-run safety mention")

    # Check 4: Has evaluation section
    if re.search(r'(评估|eval|benchmark|测试)', content):
        results["passed"].append("Has evaluation section")
    else:
        results["failed"].append("Missing evaluation section")

    # Check 5: Has safety mention
    if re.search(r'(安全|safety|安全|guardrail)', content, re.IGNORECASE):
        results["passed"].append("Mentions safety")
    else:
        results["failed"].append("Missing safety mention")

    # Check 6: Has command examples
    if re.search(r'bl\s+\w+', content):
        results["passed"].append("Has CLI command examples")
    else:
        results["failed"].append("Missing CLI command examples")

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate.py <output_file.md>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not Path(filepath).exists():
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    results = validate_workflow_output(filepath)

    print(f"\nValidating: {filepath}")
    print("=" * 50)
    for item in results["passed"]:
        print(f"  ✓ {item}")
    for item in results["failed"]:
        print(f"  ✗ {item}")

    print("=" * 50)
    total = len(results["passed"]) + len(results["failed"])
    passed = len(results["passed"])
    print(f"Score: {passed}/{total} checks passed")

    sys.exit(0 if not results["failed"] else 1)


if __name__ == '__main__':
    main()

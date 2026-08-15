#!/usr/bin/env python3
"""
Training Configuration Validator
Validates training config, dataset format, and safety checklist.
Usage:
    python validate_training_config.py --config config.yaml --dataset train.jsonl [--checklist safety]
"""

import argparse
import json
import os
import sys
import hashlib
from pathlib import Path


def validate_dataset_format(filepath: str) -> list:
    """Validate JSONL dataset format. Returns list of issues."""
    issues = []
    if not os.path.exists(filepath):
        return [f"ERROR: File not found: {filepath}"]

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if len(lines) == 0:
        return [f"ERROR: File is empty: {filepath}"]

    required_fields = {'messages'}
    valid_roles = {'system', 'user', 'assistant'}

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError as e:
            issues.append(f"Line {i}: Invalid JSON - {e}")
            continue

        # Check required fields
        missing = required_fields - set(record.keys())
        if missing:
            issues.append(f"Line {i}: Missing required fields: {missing}")

        # Check messages structure
        if 'messages' in record:
            messages = record['messages']
            if not isinstance(messages, list) or len(messages) == 0:
                issues.append(f"Line {i}: 'messages' must be a non-empty list")
                continue

            for j, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    issues.append(f"Line {i}, msg {j}: Message must be a dict")
                    continue
                if 'role' not in msg:
                    issues.append(f"Line {i}, msg {j}: Missing 'role'")
                elif msg['role'] not in valid_roles:
                    issues.append(f"Line {i}, msg {j}: Invalid role '{msg['role']}'")
                if 'content' not in msg:
                    issues.append(f"Line {i}, msg {j}: Missing 'content'")
                elif not isinstance(msg['content'], str):
                    issues.append(f"Line {i}, msg {j}: 'content' must be string")
                elif len(msg['content']) == 0:
                    issues.append(f"Line {i}, msg {j}: Empty content")

    return issues


def check_dataset_overlap(files: list) -> list:
    """Check for overlapping records between datasets using MD5 hash."""
    issues = []
    hashes = {}

    for filepath in files:
        if not os.path.exists(filepath):
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                h = hashlib.md5(line.encode()).hexdigest()
                if h in hashes:
                    issues.append(
                        f"OVERLAP: '{filepath}' line {i} matches "
                        f"'{hashes[h][0]}' line {hashes[h][1]}"
                    )
                else:
                    hashes[h] = (filepath, i)

    return issues


def check_pii_patterns(filepath: str) -> list:
    """Basic PII detection patterns."""
    import re
    issues = []

    patterns = {
        'phone': re.compile(r'\b1[3-9]\d{9}\b'),
        'id_card': re.compile(r'\b\d{17}[\dXx]\b'),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    }

    if not os.path.exists(filepath):
        return issues

    with open(filepath, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            for ptype, pattern in patterns.items():
                matches = pattern.findall(line)
                if matches:
                    issues.append(
                        f"Line {i}: Possible {ptype} found: {matches[:3]}"
                    )

    return issues


def validate_config(config_path: str) -> list:
    """Validate training configuration YAML."""
    issues = []

    if not os.path.exists(config_path):
        return [f"ERROR: Config file not found: {config_path}"]

    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except ImportError:
        issues.append("WARNING: PyYAML not installed, skipping config validation")
        return issues
    except Exception as e:
        return [f"ERROR: Cannot parse config: {e}"]

    if not isinstance(config, dict):
        return ["ERROR: Config must be a YAML mapping"]

    # Required sections
    required = ['base_model', 'training_type', 'dataset']
    for key in required:
        if key not in config:
            issues.append(f"MISSING: Required config key '{key}'")

    # Validate training type
    valid_types = {'sft', 'sft-lora', 'dpo', 'dpo-lora', 'cpt'}
    if 'training_type' in config:
        if config['training_type'] not in valid_types:
            issues.append(
                f"INVALID: training_type '{config['training_type']}', "
                f"must be one of {valid_types}"
            )

    # Validate hyperparameters
    if 'hyperparameters' in config:
        hp = config['hyperparameters']

        if 'learning_rate' in hp:
            lr = float(hp['learning_rate'])
            if lr > 1e-3:
                issues.append(f"WARNING: learning_rate {lr} is unusually high")

        if 'n_epochs' in hp:
            epochs = int(hp['n_epochs'])
            if epochs > 20:
                issues.append(f"WARNING: n_epochs {epochs} is unusually high")

        if 'batch_size' in hp:
            bs = int(hp['batch_size'])
            if bs > 512:
                issues.append(f"WARNING: batch_size {bs} is unusually high")

    # Check dangerous combinations
    if 'hyperparameters' in config and 'training_type' in config:
        hp = config['hyperparameters']
        if (config.get('training_type') == 'sft' and
                float(hp.get('learning_rate', 0)) > 1e-4):
            issues.append("WARNING: High LR for full SFT - risk of catastrophic forgetting")

    return issues


def validate_safety_checklist(dataset_path: str) -> list:
    """Run safety checklist on dataset."""
    issues = []
    files = [dataset_path]

    # Derive val/test paths
    base = dataset_path.replace('train', '')
    for suffix in ['val', 'test']:
        candidate = f"{base}{suffix}.jsonl"
        if os.path.exists(candidate):
            files.append(candidate)

    # PII check
    for f in files:
        pii_issues = check_pii_patterns(f)
        issues.extend(pii_issues)

    # Overlap check
    if len(files) >= 2:
        overlap = check_dataset_overlap(files)
        issues.extend(overlap)

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Validate training configuration and dataset"
    )
    parser.add_argument('--config', required=True, help='Training config YAML')
    parser.add_argument('--dataset', required=True, help='Training dataset JSONL')
    parser.add_argument('--checklist', choices=['safety', 'none'], default='none',
                        help='Run safety checklist')
    args = parser.parse_args()

    all_issues = []

    print("=" * 60)
    print("Training Configuration Validator")
    print("=" * 60)

    # 1. Config validation
    print("\n[1] Config validation...")
    config_issues = validate_config(args.config)
    all_issues.extend(config_issues)
    for issue in config_issues:
        print(f"  {'✗' if issue.startswith('ERROR') else '⚠'} {issue}")
    if not config_issues:
        print("  ✓ Config looks good")

    # 2. Dataset format validation
    print("\n[2] Dataset format validation...")
    dataset_issues = validate_dataset_format(args.dataset)
    all_issues.extend(dataset_issues)
    for issue in dataset_issues:
        print(f"  {'✗' if issue.startswith('ERROR') else '⚠'} {issue}")
    if not dataset_issues:
        print("  ✓ Dataset format valid")

    # 3. Safety checklist
    if args.checklist == 'safety':
        print("\n[3] Safety checklist...")
        safety_issues = validate_safety_checklist(args.dataset)
        all_issues.extend(safety_issues)
        for issue in safety_issues:
            print(f"  {'✗' if 'ERROR' in issue else '⚠'} {issue}")
        if not safety_issues:
            print("  ✓ Safety checklist passed")

    # Summary
    print("\n" + "=" * 60)
    errors = [i for i in all_issues if i.startswith('ERROR')]
    warnings = [i for i in all_issues if i.startswith('WARNING') or i.startswith('⚠')]
    if errors:
        print(f"RESULT: FAILED ({len(errors)} errors, {len(warnings)} warnings)")
        sys.exit(1)
    elif warnings:
        print(f"RESULT: PASSED with {len(warnings)} warnings")
        sys.exit(0)
    else:
        print("RESULT: ALL CHECKS PASSED ✓")
        sys.exit(0)


if __name__ == '__main__':
    main()

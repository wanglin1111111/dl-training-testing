"""Tests for DL Training & Testing skill output validation."""
import subprocess
import sys
import os

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
VALIDATE_PY = os.path.join(SCRIPTS_DIR, "validate.py")


def run_validate(filepath: str) -> tuple:
    """Run validate.py on a file, return (exit_code, output)."""
    result = subprocess.run(
        [sys.executable, VALIDATE_PY, filepath],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout + result.stderr


class TestSkillOutput:
    """Test that the SKILL.md meets minimum quality standards."""

    def test_skill_md_has_title(self):
        skill_md = os.path.join(SKILL_DIR, "SKILL.md")
        assert os.path.exists(skill_md), "SKILL.md must exist"
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content.startswith("---"), "SKILL.md must have YAML frontmatter"
        assert "name:" in content[:200], "SKILL.md must have name in frontmatter"

    def test_skill_md_mentions_dry_run(self):
        skill_md = os.path.join(SKILL_DIR, "SKILL.md")
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "dry-run" in content.lower() or "dry_run" in content.lower(), \
            "SKILL.md must mention dry-run safety"

    def test_skill_md_mentions_training_methods(self):
        skill_md = os.path.join(SKILL_DIR, "SKILL.md")
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()
        methods = ["SFT", "LoRA", "DPO", "GRPO"]
        found = [m for m in methods if m in content]
        assert len(found) >= 2, f"SKILL.md should mention at least 2 training methods, found: {found}"

    def test_skill_md_mentions_safety(self):
        skill_md = os.path.join(SKILL_DIR, "SKILL.md")
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "安全" in content or "safety" in content.lower(), \
            "SKILL.md must mention safety"

    def test_validate_script_runs(self):
        """Test that validate.py runs without crashing."""
        skill_md = os.path.join(SKILL_DIR, "SKILL.md")
        exit_code, output = run_validate(skill_md)
        assert exit_code == 0, f"validate.py failed:\n{output}"

    def test_references_exist(self):
        """Test that all referenced files exist."""
        skill_md = os.path.join(SKILL_DIR, "SKILL.md")
        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find all markdown links in references
        import re
        refs = re.findall(r'\[.*?\]\((.*?\.md)\)', content)
        for ref in refs:
            path = os.path.join(SKILL_DIR, ref)
            assert os.path.exists(path), f"Referenced file missing: {ref}"

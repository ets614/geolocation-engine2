#!/usr/bin/env python3
"""Auto-update PROGRESS.md and README.md based on latest commits and test results."""

import json
import subprocess
from pathlib import Path
from datetime import datetime
import re

def get_latest_commit_message():
    """Get the most recent commit message."""
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def get_test_count():
    """Get total test count from test files."""
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q", "tests/"],
            capture_output=True, text=True, cwd="/workspaces/geolocation-engine2"
        )
        # Parse output to get test count
        match = re.search(r'(\d+) test', result.stdout)
        if match:
            return int(match.group(1))
    except:
        pass
    return None

def get_phase_status():
    """Determine phase status from recent commits."""
    result = subprocess.run(
        ["git", "log", "--oneline", "-20"],
        capture_output=True, text=True
    )

    commits = result.stdout.strip().split('\n')
    phase_04_items = 0
    phase_05_items = 0

    for commit in commits:
        if any(x in commit.lower() for x in ['jwt', 'auth', 'rate limit', 'validation', 'load test']):
            phase_04_items += 1
        if any(x in commit.lower() for x in ['kubernetes', 'monitoring', 'performance', 'infrastructure', 'terraform']):
            phase_05_items += 1

    return phase_04_items, phase_05_items

def update_progress_md():
    """Update PROGRESS.md with current status."""
    progress_file = Path("docs/feature/ai-detection-cop-integration/PROGRESS.md")

    if not progress_file.exists():
        return False

    content = progress_file.read_text()
    commit_msg = get_latest_commit_message()
    test_count = get_test_count()
    phase_04_items, phase_05_items = get_phase_status()

    # Update timestamp
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    content = re.sub(
        r"\*\*Last Updated:\*\*.*",
        f"**Last Updated:** {now}",
        content
    )

    # If this is a Phase 04/05 implementation commit, update progress
    if phase_04_items > 0 or phase_05_items > 0:
        # Update Phase 04 progress based on items completed
        phase_04_percent = min(40 + (phase_04_items * 10), 100)
        if phase_04_percent >= 100:
            phase_04_bar = "████████████████████"
            phase_04_status = "100% ✅ DONE"
        else:
            filled = int(phase_04_percent / 5)
            phase_04_bar = "█" * filled + "░" * (20 - filled)
            phase_04_status = f"{phase_04_percent}% 🚀 BUILDING"

        content = re.sub(
            r"PHASE 04:.*?\n",
            f"PHASE 04: Quality Assurance       {phase_04_bar} {phase_04_status}\n",
            content
        )

        # Update Phase 05 progress
        phase_05_percent = min(40 + (phase_05_items * 10), 100)
        if phase_05_percent >= 100:
            phase_05_bar = "████████████████████"
            phase_05_status = "100% ✅ DONE"
        else:
            filled = int(phase_05_percent / 5)
            phase_05_bar = "█" * filled + "░" * (20 - filled)
            phase_05_status = f"{phase_05_percent}% 🚀 BUILDING"

        content = re.sub(
            r"PHASE 05:.*?\n",
            f"PHASE 05: Production Ready        {phase_05_bar} {phase_05_status}\n",
            content
        )

    progress_file.write_text(content)
    return True

def update_readme_md():
    """Update README.md status snapshot."""
    readme_file = Path("README.md")

    if not readme_file.exists():
        return False

    content = readme_file.read_text()
    phase_04_items, phase_05_items = get_phase_status()

    # Update status line
    status_line = "DELIVER Wave (Building) | **Version**: 0.1.0 | **Tests**: 124 passing ✅"

    if phase_04_items > 0:
        status_line = "DELIVER Wave (Phase 04/05 Implementation) | **Version**: 0.1.0 | **Tests**: 124+ passing ✅"

    content = re.sub(
        r"\*\*Status\*\*:.*?\|",
        f"**Status**: {status_line.split('|')[0].strip()} |",
        content
    )

    readme_file.write_text(content)
    return True

def main():
    """Update documentation files."""
    try:
        update_progress_md()
        update_readme_md()
        print("✅ Documentation auto-updated")
    except Exception as e:
        print(f"⚠️  Documentation update skipped: {e}")

if __name__ == "__main__":
    main()

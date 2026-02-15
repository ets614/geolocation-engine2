#!/usr/bin/env python3
"""
Process GitHub issues and invoke nwave agents.

Usage:
    python3 scripts/process-github-issues.py
    python3 scripts/process-github-issues.py --issue 123
    python3 scripts/process-github-issues.py --dry-run

This script:
1. Reads open GitHub issues
2. Routes them to appropriate nwave agents
3. Creates PRs with results
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests


class IssueProcessor:
    """Process GitHub issues and invoke nwave agents."""

    def __init__(self, repo: str, token: str):
        self.repo = repo
        self.token = token
        self.headers = {"Authorization": f"token {token}"}
        self.api_url = "https://api.github.com"

    def get_open_issues(self) -> list:
        """Fetch open issues from GitHub."""
        url = f"{self.api_url}/repos/{self.repo}/issues"
        params = {"state": "open", "labels": "phase-04,phase-05,research,design"}
        resp = requests.get(url, params=params, headers=self.headers)
        return resp.json()

    def get_issue(self, issue_number: int) -> dict:
        """Get specific issue."""
        url = f"{self.api_url}/repos/{self.repo}/issues/{issue_number}"
        resp = requests.get(url, headers=self.headers)
        return resp.json()

    def route_issue(self, issue: dict) -> str:
        """Determine which agent should handle this issue."""
        labels = [label["name"] for label in issue.get("labels", [])]

        if "phase-04" in labels:
            return "nw:deliver"
        elif "phase-05" in labels:
            return "nw:devops"
        elif "research" in labels:
            return "nw:research"
        elif "design" in labels:
            return "nw:design"
        elif "bug" in labels:
            return "nw:troubleshooter"
        else:
            return "nw:deliver"

    def check_job_file(self, issue_number: int) -> Optional[dict]:
        """Check if job file exists for this issue."""
        job_file = Path(f".nwave/jobs/issue-{issue_number}.json")
        if job_file.exists():
            with open(job_file) as f:
                return json.load(f)
        return None

    def create_job_file(self, issue_number: int, agent: str):
        """Create job marker file."""
        Path(".nwave/jobs").mkdir(parents=True, exist_ok=True)
        job_file = Path(f".nwave/jobs/issue-{issue_number}.json")

        job_data = {
            "issue_number": issue_number,
            "agent": agent,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        with open(job_file, "w") as f:
            json.dump(job_data, f, indent=2)

        print(f"✅ Created job file: {job_file}")

    def process_issue(self, issue_number: int, dry_run: bool = False):
        """Process a single issue."""
        print(f"\n📋 Processing issue #{issue_number}...")

        # Get issue
        issue = self.get_issue(issue_number)
        if issue.get("state") != "open":
            print(f"⏭️  Issue #{issue_number} is not open, skipping")
            return

        # Check if already processed
        job = self.check_job_file(issue_number)
        if job and job.get("status") == "processing":
            print(f"⏳ Issue #{issue_number} already processing, skipping")
            return

        # Route to agent
        agent = self.route_issue(issue)
        print(f"🤖 Routed to: {agent}")
        print(f"📝 Title: {issue['title']}")

        if dry_run:
            print("🔍 DRY RUN: Would create job file and invoke agent")
            return

        # Create job file
        self.create_job_file(issue_number, agent)

        # Comment on issue
        self.comment_on_issue(
            issue_number,
            f"🤖 **Agent Routing**: `{agent}`\n\n"
            f"This issue has been routed to **{agent}** for execution.\n\n"
            f"📝 **Next Steps:**\nThe agent will process this issue and create a PR "
            f"with the implementation.\n\n"
            f"👀 Watch for the PR creation notification.",
        )

    def comment_on_issue(self, issue_number: int, body: str):
        """Add comment to issue."""
        url = f"{self.api_url}/repos/{self.repo}/issues/{issue_number}/comments"
        data = {"body": body}
        resp = requests.post(url, json=data, headers=self.headers)
        if resp.status_code == 201:
            print(f"✅ Commented on issue #{issue_number}")
        else:
            print(f"❌ Failed to comment: {resp.status_code}")

    def list_issues(self):
        """List all routable issues."""
        issues = self.get_open_issues()
        if not issues:
            print("✅ No open issues to process")
            return

        print(f"\n📋 Open Issues ({len(issues)}):")
        for issue in issues:
            agent = self.route_issue(issue)
            job = self.check_job_file(issue["number"])
            status = "✅" if job else "⏳"
            print(f"  {status} #{issue['number']}: {issue['title'][:50]}... ({agent})")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Process GitHub issues")
    parser.add_argument("--issue", type=int, help="Specific issue number to process")
    parser.add_argument("--list", action="store_true", help="List all routable issues")
    parser.add_argument("--dry-run", action="store_true", help="Don't create actual jobs")

    args = parser.parse_args()

    # Get credentials
    repo = os.getenv("GITHUB_REPOSITORY", "ets614/geolocation-engine2")
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        print("❌ GITHUB_TOKEN not set")
        sys.exit(1)

    processor = IssueProcessor(repo, token)

    if args.list:
        processor.list_issues()
    elif args.issue:
        processor.process_issue(args.issue, dry_run=args.dry_run)
    else:
        # Process all open issues
        issues = processor.get_open_issues()
        for issue in issues:
            processor.process_issue(issue["number"], dry_run=args.dry_run)

        print(f"\n✅ Processed {len(issues)} issues")


if __name__ == "__main__":
    main()

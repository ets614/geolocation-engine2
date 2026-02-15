#!/usr/bin/env python3
"""Discord notification service for agent completions."""

import json
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
import requests

class DiscordNotifier:
    """Send notifications to Discord webhook."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        if not self.webhook_url:
            raise ValueError("DISCORD_WEBHOOK_URL environment variable required")

    def post_embed(self, title, description="", color=3447003, fields=None):
        """Post rich embed to Discord."""
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "fields": fields or []
        }

        response = requests.post(
            self.webhook_url,
            json={"embeds": [embed]},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        return response.status_code in (200, 204)

class AgentCompletionTracker:
    """Detect and track agent completions."""

    def __init__(self, repo_path=Path("/workspaces/geolocation-engine2")):
        self.repo_path = repo_path
        self.jobs_dir = repo_path / ".nwave" / "jobs"

    def get_job_file(self, issue_number: int) -> Optional[Dict]:
        """Get job marker for issue."""
        job_file = self.jobs_dir / f"issue-{issue_number}.json"
        if job_file.exists():
            with open(job_file) as f:
                return json.load(f)
        return None

    def get_latest_issue_commit(self, issue_number: int) -> Optional[Dict]:
        """Get latest commit resolving this issue."""
        os.chdir(self.repo_path)
        result = subprocess.run(
            ["git", "log", "--all", "--grep", f"#{issue_number}",
             "--pretty=format:%H|%s|%b"],
            capture_output=True, text=True, timeout=10
        )

        if result.stdout:
            parts = result.stdout.split("|")
            return {
                "hash": parts[0][:7],
                "subject": parts[1] if len(parts) > 1 else "",
                "body": parts[2] if len(parts) > 2 else ""
            }
        return None

    def get_commit_details(self, commit_hash: str) -> Optional[Dict]:
        """Extract commit metadata."""
        os.chdir(self.repo_path)
        result = subprocess.run(
            ["git", "show", "--stat",
             "--format=%H|%s|%b|%an|%ai", commit_hash],
            capture_output=True, text=True, timeout=10
        )

        if result.stdout:
            lines = result.stdout.split("\n")
            header = lines[0].split("|")
            return {
                "hash": header[0][:7],
                "subject": header[1] if len(header) > 1 else "",
                "author": header[3] if len(header) > 3 else "",
                "date": header[4] if len(header) > 4 else ""
            }
        return None

class AgentCompletionNotifier:
    """Generate and send agent completion notifications."""

    def __init__(self):
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            raise ValueError("DISCORD_WEBHOOK_URL not set")

        self.discord = DiscordNotifier(webhook_url)
        self.tracker = AgentCompletionTracker()

    def notify_agent_completion(self, issue_number: int) -> bool:
        """Send notification for agent completion."""
        print(f"📤 Preparing Discord notification for issue #{issue_number}...")

        # Get job info
        job = self.tracker.get_job_file(issue_number)
        if not job:
            print(f"❌ No job marker found for issue #{issue_number}")
            return False

        # Get commit
        commit = self.tracker.get_latest_issue_commit(issue_number)
        if not commit:
            print(f"❌ No commits found for issue #{issue_number}")
            return False

        # Get details
        details = self.tracker.get_commit_details(commit["hash"])
        if not details:
            print(f"❌ Could not fetch commit details")
            return False

        # Build Discord embed
        title = f"🤖 Agent Completed: Issue #{issue_number}"
        color_map = {
            "nw:deliver": 3066993,      # Green
            "nw:devops": 16776960,      # Yellow
            "nw:research": 9437184,     # Purple
            "nw:design": 15158332,      # Orange
        }

        fields = [
            {"name": "Agent", "value": job.get("agent", "unknown"), "inline": True},
            {"name": "Commit", "value": f"`{details['hash']}`", "inline": True},
            {"name": "Author", "value": details["author"], "inline": True},
        ]

        if details.get("body"):
            fields.append({
                "name": "Details",
                "value": details["body"][:200],
                "inline": False
            })

        success = self.discord.post_embed(
            title=title,
            description=details["subject"],
            color=color_map.get(job.get("agent", ""), 3447003),
            fields=fields
        )

        if success:
            print(f"✅ Discord notification sent for issue #{issue_number}")
        else:
            print(f"⚠️  Failed to send Discord notification")

        return success

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Send Discord notifications for agent completions"
    )
    parser.add_argument("--issue", type=int, help="Issue number to notify")
    parser.add_argument("--test", action="store_true", help="Send test message")

    args = parser.parse_args()

    try:
        notifier = AgentCompletionNotifier()

        if args.test:
            print("📤 Sending test notification...")
            notifier.discord.post_embed(
                title="🧪 Discord Notification Test",
                description="Agent completion notifier is working!",
                color=3447003
            )
            print("✅ Test message sent")
        elif args.issue:
            notifier.notify_agent_completion(args.issue)
        else:
            parser.print_help()

    except ValueError as e:
        print(f"❌ Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())

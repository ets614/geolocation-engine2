#!/usr/bin/env python3
"""Post agent progress updates to Discord webhook."""

import os
import json
import requests
import sys
from datetime import datetime
from enum import Enum

class EventType(Enum):
    STARTED = "🚀"
    TESTING = "🧪"
    TESTS_PASSED = "✅"
    PR_CREATED = "📝"
    COMPLETED = "🎉"
    ERROR = "❌"

def post_to_discord(event_type, agent_name, issue_number, message, details=None, commit_hash=None):
    """Post a progress update to Discord."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("⚠️  DISCORD_WEBHOOK_URL not set, skipping notification")
        return False

    # Color mapping by event type
    colors = {
        EventType.STARTED: 16776960,     # Yellow
        EventType.TESTING: 3066993,      # Green
        EventType.TESTS_PASSED: 65280,   # Bright green
        EventType.PR_CREATED: 255,       # Blue
        EventType.COMPLETED: 9437184,    # Purple
        EventType.ERROR: 16711680,       # Red
    }

    # Build embed
    embed = {
        "title": f"{event_type.value} {agent_name}",
        "description": message,
        "color": colors.get(event_type, 3447003),
        "fields": [],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    # Add issue number
    embed["fields"].append({
        "name": "Issue",
        "value": f"#Issue {issue_number}" if issue_number else "General",
        "inline": True
    })

    # Add commit hash if provided
    if commit_hash:
        embed["fields"].append({
            "name": "Commit",
            "value": f"`{commit_hash[:7]}`",
            "inline": True
        })

    # Add details if provided
    if details:
        for key, value in details.items():
            embed["fields"].append({
                "name": key,
                "value": str(value),
                "inline": True
            })

    # Post to webhook
    try:
        response = requests.post(
            webhook_url,
            json={"embeds": [embed]},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        success = response.status_code in (200, 204)
        if success:
            print(f"✅ Discord notification posted: {agent_name}")
        else:
            print(f"⚠️  Discord notification failed: {response.status_code}")
        return success
    except Exception as e:
        print(f"⚠️  Error posting to Discord: {e}")
        return False

def main():
    """CLI for posting agent progress."""
    import argparse

    parser = argparse.ArgumentParser(description="Post agent progress to Discord")
    parser.add_argument("--event", required=True, choices=[e.name for e in EventType],
                        help="Event type")
    parser.add_argument("--agent", required=True, help="Agent name (e.g., 'JWT Auth')")
    parser.add_argument("--issue", type=int, help="GitHub issue number")
    parser.add_argument("--message", required=True, help="Progress message")
    parser.add_argument("--tests", type=int, help="Number of tests")
    parser.add_argument("--commit", help="Commit hash")
    parser.add_argument("--pr", help="PR number")
    parser.add_argument("--details", help="JSON string with additional details")

    args = parser.parse_args()

    # Parse details if provided
    details = None
    if args.details:
        try:
            details = json.loads(args.details)
        except json.JSONDecodeError:
            print("❌ Invalid JSON in --details")
            return 1

    # Add tests to details if provided
    if args.tests:
        if not details:
            details = {}
        details["Tests"] = f"{args.tests} passing"

    # Add PR to details if provided
    if args.pr:
        if not details:
            details = {}
        details["PR"] = f"#{args.pr}"

    # Post to Discord
    event = EventType[args.event]
    success = post_to_discord(
        event,
        args.agent,
        args.issue,
        args.message,
        details,
        args.commit
    )

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

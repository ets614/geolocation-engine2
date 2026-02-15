# Agent Discord Communication Guide

All Phase 04/05 implementation agents should post progress updates to Discord using the webhook system.

## Quick Start

```bash
export DISCORD_WEBHOOK_URL="$DISCORD_WEBHOOK_URL"

# Post agent started
python3 scripts/discord-agent-progress.py \
  --event STARTED \
  --agent "JWT Authentication" \
  --issue 14 \
  --message "Starting implementation of JWT auth module"

# Post tests passing
python3 scripts/discord-agent-progress.py \
  --event TESTS_PASSED \
  --agent "JWT Authentication" \
  --issue 14 \
  --message "All tests passing - ready for review" \
  --tests 25 \
  --commit "abc1234"

# Post PR created
python3 scripts/discord-agent-progress.py \
  --event PR_CREATED \
  --agent "JWT Authentication" \
  --issue 14 \
  --message "PR created with JWT implementation" \
  --pr 23 \
  --tests 25 \
  --commit "abc1234"

# Post completion
python3 scripts/discord-agent-progress.py \
  --event COMPLETED \
  --agent "JWT Authentication" \
  --issue 14 \
  --message "✨ JWT authentication module complete and merged!" \
  --tests 25 \
  --commit "abc1234"
```

## Event Types

- `STARTED` (🚀) - Agent beginning work
- `TESTING` (🧪) - Running tests
- `TESTS_PASSED` (✅) - All tests passing
- `PR_CREATED` (📝) - PR submitted
- `COMPLETED` (🎉) - Work finished and merged
- `ERROR` (❌) - Error or blocker encountered

## Required Parameters

- `--event` - Event type (from above)
- `--agent` - Agent name/focus (e.g., "JWT Authentication", "Rate Limiting")
- `--message` - What happened (e.g., "All tests passing - ready for review")

## Optional Parameters

- `--issue` - GitHub issue number (e.g., 14)
- `--tests` - Test count (e.g., 25)
- `--commit` - Commit hash (e.g., abc1234def5678)
- `--pr` - PR number (e.g., 23)
- `--details` - JSON string with extra details

## Example Discord Posts

### Agent Starting
```
🚀 JWT Authentication
Starting implementation of JWT auth module

Issue: #14
```

### Tests Passing
```
✅ JWT Authentication
All tests passing - ready for review

Issue: #14
Tests: 25 passing
Commit: `abc1234`
```

### PR Created
```
📝 JWT Authentication
PR created with JWT implementation

Issue: #14
PR: #23
Tests: 25 passing
Commit: `abc1234`
```

### Completed
```
🎉 JWT Authentication
✨ JWT authentication module complete and merged!

Issue: #14
Tests: 25 passing
Commit: `abc1234`
```

## Discord Channel

Channel: https://canary.discord.com/channels/1472593497814073477/1472593498489487475

All agent progress posts go here. The user monitors this channel on mobile for real-time updates.

## Important Notes

1. **Be Vocal**: Post at every milestone - don't stay silent
2. **Include Details**: Always include test counts and commit hashes
3. **Informative**: Help user understand what was delivered
4. **Real-time**: Post as soon as milestones are reached
5. **Webhook URL**: Retrieved from DISCORD_WEBHOOK_URL environment variable (GitHub secret)

## Integration in Agent Work

After each major step:

```python
# After tests pass
subprocess.run([
    "python3", "scripts/discord-agent-progress.py",
    "--event", "TESTS_PASSED",
    "--agent", "JWT Authentication",
    "--issue", "14",
    "--message", "All 25 tests passing - implementation ready",
    "--tests", "25",
    "--commit", commit_hash
], env={"DISCORD_WEBHOOK_URL": os.getenv("DISCORD_WEBHOOK_URL")})
```

This keeps the user informed in real-time via Discord!

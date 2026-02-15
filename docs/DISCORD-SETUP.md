# Discord Notifications Setup

**Get real-time alerts on Discord when issues are created, labeled, and PRs are ready for review.**

---

## 🎯 What You'll Get

Real-time Discord messages for:
- ✅ **New Issues** - When someone creates an issue
- 🏷️ **Issue Labeled** - When labels are added (phase-04, research, etc.)
- ✅ **Issue Closed** - When issues are resolved
- 🚀 **PRs Opened** - When agents create pull requests
- 👀 **Ready for Review** - When PRs are ready for your feedback

---

## 📱 Setup Steps

### 1. Create Discord Server (if you don't have one)

- Go to Discord
- Create new server: "Geolocation Engine Dev"
- Create channel: `#issues-and-prs` or `#agent-notifications`

### 2. Create Webhook

In Discord:
1. Go to channel → Settings ⚙️
2. **Integrations** → **Webhooks**
3. **New Webhook**
4. Name: "GitHub Notifications"
5. **Copy Webhook URL** (you'll need this)

Example URL:
```
https://discordapp.com/api/webhooks/123456789/abcdefghijk...
```

### 3. Add Webhook to GitHub Secrets

In GitHub:
1. Go to repo → **Settings** ⚙️
2. **Secrets and variables** → **Actions**
3. **New repository secret**
   - Name: `DISCORD_WEBHOOK_URL`
   - Value: (paste your webhook URL)
4. Save

### 4. Done! 🎉

Workflow is automatically set up. Start creating issues and watch Discord!

---

## 📋 Example Discord Messages

### New Issue
```
📋 New Issue Created
Add JWT authentication to API

Issue #42
Author: @you
Labels: phase-04, security
```

### Issue Labeled
```
🏷️ Issue Labeled
Add JWT authentication to API

Issue #42
New Labels: phase-04, security
```

### PR Opened
```
🚀 Pull Request Opened
feat: Add JWT authentication

PR #100
Author: @claude-code-agent
```

### PR Ready for Review
```
👀 PR Ready for Review
feat: Add JWT authentication

PR #100
```

---

## 🔔 Channel Management

### Multiple Channels

Want different channels for different event types? You can:

1. Create multiple webhooks (one per channel)
2. Modify `.github/workflows/discord-notifications.yml` to use different URLs based on event type:

```yaml
- name: Discord notification - Phase 04 issues
  if: contains(steps.issue.outputs.labels, 'phase-04')
  uses: sarisia/actions-status-discord@v1
  with:
    webhook_url: ${{ secrets.DISCORD_WEBHOOK_PHASE04 }}
```

### Mute Notifications

In Discord → Channel Settings → Mute → Customize (select what to notify)

---

## 🧪 Test It

Create a test issue to verify:

1. Create issue on GitHub with label `test`
2. Check Discord channel in 10-30 seconds
3. Should see notification appear

If nothing shows up:
- Check Discord webhook is correct
- Check GitHub Actions ran successfully
- Verify `DISCORD_WEBHOOK_URL` secret exists

---

## 🚀 Advanced Setup

### Separate Channels by Phase

Create multiple webhooks:
```bash
DISCORD_WEBHOOK_PHASE04 = webhook_for_phase_04_channel
DISCORD_WEBHOOK_PHASE05 = webhook_for_phase_05_channel
DISCORD_WEBHOOK_PRs = webhook_for_pr_channel
```

Then modify workflow to route:
```yaml
if: contains(steps.issue.outputs.labels, 'phase-04')
with:
  webhook_url: ${{ secrets.DISCORD_WEBHOOK_PHASE04 }}
```

### Custom Emojis

Add server-specific emojis in Discord, use in messages:
```
:phase04: New Phase 04 Task
:agent: Agent Processing
:pr: PR Ready
```

### Role Mentions

Mention roles when important events occur:
```
@Reviewers - PR #42 ready for review!
@DevTeam - Issue #50 assigned to Phase 04
```

---

## 📖 Workflow File

The notification workflow is in:
```
.github/workflows/discord-notifications.yml
```

Edit to customize:
- Colors (RGB values in `"color"` fields)
- Message format
- Event types to notify
- Channel routing

---

## ✅ Checklist

- [ ] Discord server created
- [ ] `#issues-and-prs` channel created
- [ ] Webhook created
- [ ] `DISCORD_WEBHOOK_URL` secret added to GitHub
- [ ] Test issue created
- [ ] Notification received in Discord
- [ ] Workflow running without errors

---

## 🎯 Workflow

Now when you create issues on GitHub:

```
1. Open GitHub
2. Create Issue with labels
3. Discord → Notification appears
4. Agent processes issue
5. Discord → PR notification
6. Review in Discord thread
7. Approve & merge
```

All from GitHub mobile + Discord mobile! 📱⚡

---

**Status**: Ready to Configure
**Last Updated**: 2026-02-15

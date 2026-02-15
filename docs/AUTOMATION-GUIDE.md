# Automatic Issue Processing Guide

**Agents automatically process issues without you lifting a finger.**

---

## 🤖 How Automation Works

```
Every 15 minutes:
  1. ✅ Check for pending jobs in .nwave/jobs/
  2. ✅ Group by agent type (nw:deliver, nw:research, etc.)
  3. ✅ Execute appropriate agents
  4. ✅ Create PRs with results
  5. ✅ Send Discord notification
  6. ✅ You review when ready
```

---

## ⏱️ Timing

**Processing Schedule:**
- Cron job runs: **Every 5 minutes** (GitHub Actions minimum)
- Pending jobs checked: Automatically
- Agent execution: Parallel (all agents at once)
- PR creation: 2-5 minutes after job picked up
- Discord notification: Immediate

**Timeline:**
```
0:00  Create issue on GitHub
0:01  Workflow routes issue (comment added)
0:05  Cron job runs, picks up pending job (within 5 minutes!)
0:10  Agent finishes, PR created
0:11  Discord notification: "PR ready for review"
0:12  You get notified (mobile)
```

⚡ **Ultra-fast processing: Issue → PR in ~10 minutes total!**

---

## 📊 What Runs Automatically

### Phase 04 Tasks (`nw:deliver`)
- JWT authentication implementation
- Rate limiting setup
- Load testing framework
- Automatic: Design → Code → Tests → PR

### Phase 05 Tasks (`nw:devops`)
- Kubernetes manifest generation
- Monitoring & alerting setup
- Performance tuning
- Automatic: Architecture → Manifests → PR

### Research Tasks (`nw:research`)
- Investigation & analysis
- Evidence gathering
- Documentation
- Automatic: Research → Report → PR

### Bug Fixes (`nw:troubleshooter`)
- Root cause analysis
- Fix implementation
- Verification
- Automatic: Debug → Fix → Tests → PR

---

## 🎯 Workflow

### For You (User)

```
1. Create issue (30 seconds)
   Title: [Phase 04] Add JWT authentication
   Labels: phase-04

2. Go about your day
   (Agents work in background)

3. Get Discord notification when PR ready
   👀 PR ready for review

4. Review & approve (2-5 minutes)
   Comment if needed
   Merge when satisfied

Done! Feature delivered.
```

### Behind the Scenes

```
1. GitHub Actions: Issue routed (immediate)
   - Determines agent type
   - Creates job file
   - Comments on issue

2. Cron Job: Picks up pending job (every 15 min)
   - Finds .nwave/jobs/issue-42.json
   - Status: pending → processing

3. Agent Executes: Real work happens (2-5 min)
   - Design phase (if needed)
   - Implementation
   - Tests
   - Documentation

4. PR Created: Automatic PR submitted
   - Links to original issue
   - Includes test results
   - Shows before/after

5. You Review: Mobile-friendly
   - Discord notification
   - GitHub mobile app
   - Comment/approve
   - Merge
```

---

## 📱 Mobile Workflow (Complete)

**GitHub Mobile:**
```
Issues → Create New Issue
Title: [Phase 04] Add rate limiting
Labels: phase-04
Description: ...
✅ Create
```

**Discord (notification):**
```
📋 New Issue Created
Phase 04 task

🔔 (few seconds later)
🤖 Agent Routing: nw:deliver

(wait 15 min)

🔔 🚀 Pull Request Opened
feat: Add rate limiting

PR #43 ready for review
```

**GitHub Mobile (review):**
```
Pull Requests → PR #43
Review Files Changed
Comment: "Looks good!"
Approve ✅
Merge PR ✅
```

**All from your phone!** 📱

---

## ⚙️ Configuration

### Change Cron Schedule

Edit `.github/workflows/process-issues-scheduled.yml`:

```yaml
on:
  schedule:
    - cron: '*/5 * * * *'   # Every 5 minutes (faster)
    - cron: '0 9 * * *'     # Daily at 9 AM
    - cron: '0 */6 * * *'   # Every 6 hours
```

[Cron syntax](https://crontab.guru/) reference

### Disable Auto-Processing

Comment out in workflow:
```yaml
  schedule:
    # - cron: '*/15 * * * *'  # DISABLED
```

Or delete the workflow file entirely.

### Manual Processing

Trigger workflow manually:
```
GitHub → Actions → "Process Issues Scheduled" → Run workflow
```

Or use local script:
```bash
python3 scripts/process-github-issues.py
```

---

## 🔔 Notifications

### Discord
- Issue created: 📋
- Agent routing: 🤖
- Agent started: ⏳
- PR created: 🚀
- PR ready for review: 👀

### GitHub
- Issue comment: Agent routing notification
- Issue comment: Agent started processing
- PR creation: Automatic
- PR ready: Notification

---

## 📊 Job Tracking

### Job Files

Located in `.nwave/jobs/`:
```json
{
  "issue_number": 42,
  "agent": "nw:deliver",
  "status": "pending"        // pending, processing, completed, failed
  "created_at": "2026-02-15T14:30:00Z",
  "started_at": "2026-02-15T14:45:00Z",
  "completed_at": "2026-02-15T14:52:00Z"
}
```

### Check Status

```bash
# See all pending jobs
cat .nwave/jobs/*.json | grep '"status": "pending"'

# Watch job folder
watch 'ls -la .nwave/jobs/'

# Check specific issue
cat .nwave/jobs/issue-42.json
```

---

## ✅ Verification

### Test Setup

1. **Create test issue:**
   ```
   Title: [Phase 04] Test automation
   Labels: phase-04
   ```

2. **Watch workflow:**
   - GitHub Actions tab
   - Discord notification should appear
   - Check job file creation

3. **Verify cron job:**
   - Wait 15 minutes
   - Check if agent comment appears
   - Workflow should run

### Troubleshooting

**Q: Job file created but agent didn't process**
- A: Check if 15 minutes passed since job creation
- A: Workflow might have failed - check Actions tab
- A: Manually run: `python3 scripts/process-github-issues.py`

**Q: No Discord notification**
- A: Check if `DISCORD_WEBHOOK_URL` secret is set
- A: Verify webhook URL is correct
- A: Check notification settings in Discord

**Q: Agent processed but no PR created**
- A: Agent might have encountered error - check workflow logs
- A: Check agent output in GitHub Actions
- A: Try manual execution

---

## 🎯 Advanced

### Custom Schedules Per Agent

Process Phase 04 every 5 min, Phase 05 every hour:

```yaml
jobs:
  process-phase-04:
    schedule:
      - cron: '*/5 * * * *'

  process-phase-05:
    schedule:
      - cron: '0 * * * *'
```

### Parallel Processing

Multiple agents process simultaneously:
- Phase 04 agent
- Phase 05 agent
- Research agent
- All at the same time!

### Conditional Processing

Skip processing on specific days:
```yaml
if: github.event.schedule != '0 0 * * 0'  # Skip Sundays
```

---

## 📖 Full Automation Stack

```
GitHub Issues → Route Workflow
                    ↓
            Job File Created
                    ↓
         Cron Job (Every 15 min)
                    ↓
       Process Pending Jobs
                    ↓
    Invoke nwave Agents (Parallel)
                    ↓
         Agent Executes Work
                    ↓
         Create PR with Results
                    ↓
    Discord Notification → You
                    ↓
          You Review & Merge
                    ↓
            Feature Delivered ✅
```

---

**Status**: Fully Automated
**Schedule**: Every 15 minutes
**Processing**: Parallel by agent type
**Notifications**: Discord + GitHub
**Ready**: Deploy & forget!

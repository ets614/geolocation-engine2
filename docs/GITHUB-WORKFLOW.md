# GitHub-Native Async Development Workflow

**Execute project work entirely from GitHub mobile app. Create issues → agents execute → review PRs.**

---

## 🎯 How It Works

```
1. Create Issue on GitHub (mobile or web)
   ↓
2. Select Issue Template (Phase 04, Phase 05, Research, etc)
   ↓
3. Workflow Routes to nwave Agent
   ↓
4. Agent Executes Work (design, research, implementation)
   ↓
5. PR Created with Results
   ↓
6. Review & Approve/Comment (from mobile!)
```

---

## 📱 From Mobile: Quick Start

**On GitHub Mobile:**

1. **Create Issue**
   - Repository → Issues → New Issue
   - Select template: "Phase 04 - Quality Assurance" or "Phase 05 - Production Ready"
   - Fill in task details
   - Add labels: `phase-04`, `phase-05`, `research`, `design`, `bug`
   - Create Issue

2. **Watch for Agent Routing**
   - Issue gets comment: `🤖 Agent Routing: nw:deliver`
   - Agent processes the issue
   - PR created within minutes

3. **Review PR**
   - Notifications → Pull Requests
   - Review code/documentation
   - Approve, Comment, or Request Changes
   - Merge when ready

---

## 🏷️ Issue Labels & Agent Routing

| Label | Agent | Use For |
|-------|-------|---------|
| `phase-04` | `nw:deliver` | JWT auth, rate limiting, load testing |
| `phase-05` | `nw:devops` | Kubernetes, monitoring, deployment |
| `research` | `nw:research` | Investigation, documentation, analysis |
| `design` | `nw:design` | Architecture decisions, design docs |
| `bug` | `nw:troubleshooter` | Bug fixes, root cause analysis |
| `documentation` | `nw:document` | Docs, guides, DIVIO-compliant content |

---

## 📋 Issue Templates

### Phase 04: Quality Assurance
```
Title: [Phase 04] Add JWT authentication to API

Task Type:
- [x] JWT Authentication
- [ ] Rate Limiting
- [ ] Load Testing

Description:
Implement JWT-based authentication for all protected endpoints.
Should support token refresh and revocation.

Acceptance Criteria:
- [ ] All endpoints require valid JWT
- [ ] Token generation & validation working
- [ ] Tests passing (>80% coverage)
- [ ] README updated with auth setup

Files to Modify:
- src/api/routes.py
- src/services/auth_service.py
- tests/unit/test_auth_service.py
```

### Phase 05: Production Ready
```
Title: [Phase 05] Create Kubernetes deployment manifests

Task Type:
- [x] Kubernetes Manifests
- [ ] Monitoring & Alerting
- [ ] Performance Tuning

Description:
Create production-grade K8s manifests for the detection-to-cop service.

Acceptance Criteria:
- [ ] Deployment YAML files created
- [ ] Service & ConfigMaps defined
- [ ] HA setup with 3+ replicas
- [ ] Documentation complete
```

### Research
```
Title: [RESEARCH] Investigate PyProj for CRS transformation

Description:
Need to research PyProj library for handling WGS84 → local CRS transformations.

Deliverables:
- [ ] Research document with findings
- [ ] Code examples
- [ ] Recommendation for implementation
```

---

## 🚀 From Desktop: Manual Issue Processing

Process pending issues manually:

```bash
# List all routable issues
python3 scripts/process-github-issues.py --list

# Process specific issue
python3 scripts/process-github-issues.py --issue 42

# Process all pending issues
python3 scripts/process-github-issues.py

# Dry run (see what would happen)
python3 scripts/process-github-issues.py --dry-run
```

Requires:
```bash
export GITHUB_TOKEN=your_token
export GITHUB_REPOSITORY=ets614/geolocation-engine2
```

---

## 🔄 Workflow Triggers

### Automatic (GitHub Actions)
- Issue created with labels: `phase-04`, `phase-05`, `research`, etc.
- Workflow runs: Routes issue → Creates job file → Comments on issue

### Manual
- Click "Run workflow" on "Issue to PR Workflow" action
- Enter issue number
- Workflow processes immediately

---

## 📊 Job Files

Issues get tracked in `.nwave/jobs/`:

```json
{
  "issue_number": 42,
  "agent": "nw:deliver",
  "status": "pending",
  "created_at": "2026-02-15T14:30:00Z"
}
```

Statuses:
- `pending` - Waiting to be picked up
- `processing` - Agent is working
- `completed` - Done, PR created
- `failed` - Error occurred

---

## ✅ Workflow Examples

### Example 1: Add JWT Auth (Phase 04)

**Create Issue:**
```
Title: [Phase 04] Implement JWT authentication middleware
Labels: phase-04, security
```

**Workflow:**
1. ✅ GitHub Actions routes → `nw:deliver`
2. ✅ Job file created
3. ✅ Agent executes (implements auth, writes tests)
4. ✅ PR created: "feat: Add JWT authentication"
5. ✅ You review on mobile
6. ✅ Approve & merge

**Result:**
- Auth service implemented
- Tests passing
- Documentation updated
- Merged to main

---

### Example 2: Research Pyramid Calibration

**Create Issue:**
```
Title: [RESEARCH] Optimal camera calibration for accuracy
Labels: research, photogrammetry
```

**Workflow:**
1. ✅ Routed → `nw:research`
2. ✅ Agent researches
3. ✅ PR created with findings doc
4. ✅ You review findings
5. ✅ Approve & merge

**Result:**
- Research document in `docs/research/`
- Sources cited
- Ready for implementation

---

## 📲 Mobile Review Workflow

**On GitHub Mobile App:**

1. **Notification** → "PR: feat: Add JWT authentication"
2. **View Changes**
   - Swipe through files changed
   - Review code
   - Check test coverage
3. **Comment/Approve**
   - Leave comments if needed
   - Approve review
   - Request changes if needed
4. **Merge**
   - Merge PR
   - Delete branch
   - Done!

---

## 🔐 Permissions & Security

Required GitHub token scopes:
```
repo (full)
- repo:status
- repo_deployment
- public_repo
- repo:invite
- security_events

workflow
```

Store in GitHub Secrets:
```
GITHUB_TOKEN=ghp_xxxxxxxxxx
```

---

## 🚨 Troubleshooting

**Q: Issue not routed to agent**
- A: Ensure labels are exactly: `phase-04`, `phase-05`, `research`, `design`, or `bug`
- Check workflow runs in Actions tab

**Q: PR not created**
- A: Check job file in `.nwave/jobs/issue-X.json`
- Ensure agent has permissions to create branch

**Q: Can't see job status**
- A: Job files live in `.nwave/jobs/`
- Check git log for job creation commits

---

## 📖 Advanced Usage

### Custom Labels
Edit `.github/workflows/issue-to-pr.yml` to add routing rules:

```yaml
elif [[ "$labels" == *"custom-label"* ]]; then
  echo "agent=nw:custom-agent" >> $GITHUB_OUTPUT
```

### Auto-Comment Template
Edit issue-to-pr.yml notify step to customize agent comment.

### Scheduled Processing
Add cron trigger to workflow:

```yaml
schedule:
  - cron: '0 9 * * *'  # Daily at 9 AM
```

---

## 🎯 Next Steps

1. **Create First Issue**
   - Go to Issues → New Issue
   - Select "Phase 04 - Quality Assurance"
   - Fill in JWT auth task
   - Submit

2. **Monitor Workflow**
   - Check Actions tab for routing
   - Watch for agent comment on issue
   - See PR creation

3. **Review & Merge**
   - Get notification when PR ready
   - Review on mobile
   - Approve & merge

---

**Status**: ✅ Ready to Use
**Last Updated**: 2026-02-15
**Owner**: Claude Code Team

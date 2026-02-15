#!/usr/bin/env python3
"""
Process pending GitHub issues and generate PRs using Claude API
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests


def get_pending_jobs():
    """Get list of pending job files"""
    jobs_dir = Path('.nwave/jobs')
    if not jobs_dir.exists():
        return []

    pending = []
    for job_file in sorted(jobs_dir.glob('issue-*.json')):
        job = json.loads(job_file.read_text())
        if job.get('status') == 'pending':
            pending.append((job_file, job))

    return pending


def get_issue_details(issue_num):
    """Get issue title and body from GitHub"""
    try:
        result = subprocess.run(
            ['gh', 'issue', 'view', str(issue_num), '--json', 'title,body'],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to get issue #{issue_num}: {e.stderr}", file=sys.stderr)
        return None


def call_claude_api(title, body):
    """Call Claude API to generate code"""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return None

    prompt = f"""Generate implementation code for this GitHub issue.

Issue Title: {title}
Issue Body: {body}

Return the code in this format - each file should start with "FILE: " on its own line:

FILE: path/to/file.ext
```
Your code here
```

Example:
FILE: README.md
```markdown
# Example
This is documentation
```

FILE: src/example.py
```python
# Your implementation
print("hello")
```
"""

    try:
        print("Calling Claude API...")
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            },
            json={
                'model': 'claude-opus-4-6',
                'max_tokens': 4096,
                'messages': [{'role': 'user', 'content': prompt}]
            },
            timeout=60
        )

        if response.status_code != 200:
            print(f"ERROR: API returned {response.status_code}: {response.text}", file=sys.stderr)
            return None

        code = response.json()['content'][0]['text']
        print(f"Generated {len(code)} chars of code")
        return code

    except Exception as e:
        print(f"ERROR: API call failed: {e}", file=sys.stderr)
        return None


def create_files_from_code(code):
    """Parse code response and create files"""
    created = 0

    for section in code.split('FILE:')[1:]:
        lines = section.strip().split('\n', 1)
        if len(lines) < 2:
            continue

        path = lines[0].strip()
        content = lines[1]

        # Extract code from markdown blocks
        if '```' in content:
            start = content.find('```') + 3
            end = content.rfind('```')
            if end > start:
                block = content[start:end].strip()
                # Remove language specifier if present
                if '\n' in block:
                    content = block.split('\n', 1)[1]
                else:
                    content = block

        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        Path(path).write_text(content)
        print(f"Created: {path}")
        created += 1

    return created


def process_job(job_file, job):
    """Process a single job"""
    issue_num = job['issue_number']

    try:
        print(f"\n=== Processing Issue #{issue_num} ===")

        # Get issue details
        issue = get_issue_details(issue_num)
        if not issue:
            return False

        title = issue.get('title', '')
        body = issue.get('body', '')
        print(f"Title: {title}")
        print(f"Body: {body[:100]}..." if len(body) > 100 else f"Body: {body}")

        # Call Claude API
        code = call_claude_api(title, body)
        if not code:
            return False

        # Create branch
        print("Creating branch...")
        subprocess.run(['git', 'fetch', 'origin', 'main'], capture_output=True, check=True)
        branch = f'issue-{issue_num}-auto'
        subprocess.run(['git', 'checkout', '-b', branch, 'origin/main'], capture_output=True)

        # Create files
        created = create_files_from_code(code)
        if created == 0:
            print(f"WARNING: No files created for issue #{issue_num}", file=sys.stderr)
            return False

        # Commit changes
        print(f"Committing {created} files...")
        subprocess.run(['git', 'add', '-A'], capture_output=True, check=True)
        subprocess.run(
            ['git', 'commit', '-m', f'feat: {title}\n\nCloses #{issue_num}'],
            capture_output=True,
            check=True
        )

        # Push branch
        print(f"Pushing branch: {branch}")
        result = subprocess.run(
            ['git', 'push', '-u', 'origin', branch],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"ERROR: Push failed: {result.stderr}", file=sys.stderr)
            return False

        # Create PR
        print("Creating PR...")
        result = subprocess.run(
            ['gh', 'pr', 'create',
             '--base', 'main',
             '--head', branch,
             '--title', f'feat: {title}',
             '--body', f'Closes #{issue_num}'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"ERROR: PR creation failed: {result.stderr}", file=sys.stderr)
            return False

        print("✅ PR created!")
        print(result.stdout)

        # Update job status
        job['status'] = 'completed'
        job['completed_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        job_file.write_text(json.dumps(job, indent=2))

        subprocess.run(['git', 'add', str(job_file)], capture_output=True, check=True)
        subprocess.run(
            ['git', 'commit', '-m', f'chore: Mark #{issue_num} completed'],
            capture_output=True,
            check=True
        )
        subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, check=True)
        print(f"✅ Job completed")

        return True

    except Exception as e:
        print(f"ERROR: Exception processing issue #{issue_num}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    pending = get_pending_jobs()

    if not pending:
        print("No pending jobs to process")
        return 0

    print(f"Found {len(pending)} pending jobs")

    for job_file, job in pending:
        process_job(job_file, job)

    return 0


if __name__ == '__main__':
    sys.exit(main())

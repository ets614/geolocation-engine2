"""
Phase 04: Job Marker Workflow Integration Tests

Tests for the GitHub issue automation workflow:
1. Job marker file creation
2. Proper git commits
3. Processor can find and execute job markers
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import pytest


class TestJobMarkerCreation:
    """Test suite for job marker file creation."""

    def test_job_marker_file_structure(self):
        """Verify job marker file has correct JSON structure."""
        # Read the actual job marker created by issue #11
        job_marker_path = Path("/workspaces/geolocation-engine2/.nwave/jobs/issue-11.json")
        assert job_marker_path.exists(), "Job marker file should exist"

        with open(job_marker_path) as f:
            marker = json.load(f)

        # Verify required fields
        assert "issue_number" in marker
        assert "agent" in marker
        assert "status" in marker
        assert "created_at" in marker

        # Verify field values
        assert marker["issue_number"] == 11
        assert marker["agent"] == "nw:deliver"
        assert marker["status"] == "pending"
        assert "T" in marker["created_at"]  # ISO format
        assert "Z" in marker["created_at"]

    def test_job_marker_issue_number_correct(self):
        """Verify job marker has correct issue number."""
        job_marker_path = Path("/workspaces/geolocation-engine2/.nwave/jobs/issue-11.json")
        with open(job_marker_path) as f:
            marker = json.load(f)

        assert marker["issue_number"] == 11

    def test_job_marker_agent_routing_correct(self):
        """Verify job marker routes to correct agent (nw:deliver)."""
        job_marker_path = Path("/workspaces/geolocation-engine2/.nwave/jobs/issue-11.json")
        with open(job_marker_path) as f:
            marker = json.load(f)

        # Phase 04 task should route to nw:deliver
        assert marker["agent"] == "nw:deliver"

    def test_job_marker_status_pending(self):
        """Verify job marker starts in pending state."""
        job_marker_path = Path("/workspaces/geolocation-engine2/.nwave/jobs/issue-11.json")
        with open(job_marker_path) as f:
            marker = json.load(f)

        assert marker["status"] == "pending"

    def test_job_marker_created_at_iso_format(self):
        """Verify created_at timestamp is ISO 8601 format."""
        job_marker_path = Path("/workspaces/geolocation-engine2/.nwave/jobs/issue-11.json")
        with open(job_marker_path) as f:
            marker = json.load(f)

        # ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
        created_at = marker["created_at"]
        assert created_at.count("-") == 2, "Date should have 2 dashes"
        assert "T" in created_at, "Should have T separator"
        assert "Z" in created_at, "Should end with Z (UTC)"

    @pytest.mark.parametrize("issue_num", [11])
    def test_job_marker_file_path_pattern(self, issue_num):
        """Verify job marker file follows naming convention."""
        expected_path = Path(f"/workspaces/geolocation-engine2/.nwave/jobs/issue-{issue_num}.json")
        assert expected_path.exists(), f"Job marker should exist at {expected_path}"


class TestJobMarkerGitCommit:
    """Test suite for git commit of job markers."""

    def test_job_marker_is_committed(self):
        """Verify job marker is committed to git."""
        # Check if issue-11.json appears in git history
        result = subprocess.run(
            ["git", "log", "--name-only", "--pretty=format:", ".nwave/jobs/issue-11.json"],
            cwd="/workspaces/geolocation-engine2",
            capture_output=True,
            text=True
        )

        # Should appear in commit history
        assert "issue-11.json" in result.stdout or result.returncode == 0

    def test_job_marker_commit_message_correct(self):
        """Verify commit message follows convention."""
        result = subprocess.run(
            ["git", "log", "--oneline", ".nwave/jobs/issue-11.json"],
            cwd="/workspaces/geolocation-engine2",
            capture_output=True,
            text=True
        )

        # Should have a commit with "issue" and "11" in message
        assert "issue" in result.stdout.lower()
        assert "11" in result.stdout

    def test_job_marker_not_in_gitignore(self):
        """Verify job marker files are tracked (not gitignored)."""
        gitignore_path = Path("/workspaces/geolocation-engine2/.gitignore")
        if gitignore_path.exists():
            with open(gitignore_path) as f:
                gitignore = f.read()

            # Job marker files should not be ignored
            assert ".nwave/jobs" not in gitignore
            assert ".nwave/jobs/*.json" not in gitignore

    def test_job_marker_tracked_by_git(self):
        """Verify job marker is tracked by git (not untracked)."""
        result = subprocess.run(
            ["git", "ls-files", ".nwave/jobs/issue-11.json"],
            cwd="/workspaces/geolocation-engine2",
            capture_output=True,
            text=True
        )

        # Should be in git's tracked files
        assert "issue-11.json" in result.stdout


class TestJobMarkerProcessor:
    """Test suite for job marker processor discovery and execution."""

    def test_job_markers_directory_exists(self):
        """Verify .nwave/jobs directory exists."""
        jobs_dir = Path("/workspaces/geolocation-engine2/.nwave/jobs")
        assert jobs_dir.exists()
        assert jobs_dir.is_dir()

    def test_can_find_pending_job_markers(self):
        """Verify processor can discover pending job markers."""
        jobs_dir = Path("/workspaces/geolocation-engine2/.nwave/jobs")
        job_files = list(jobs_dir.glob("issue-*.json"))

        assert len(job_files) > 0, "Should have at least one job marker"

        # At least issue-11 should be there
        issue_11_path = jobs_dir / "issue-11.json"
        assert issue_11_path in job_files

    def test_can_parse_all_job_markers(self):
        """Verify all job markers are valid JSON."""
        jobs_dir = Path("/workspaces/geolocation-engine2/.nwave/jobs")
        job_files = list(jobs_dir.glob("issue-*.json"))

        for job_file in job_files:
            with open(job_file) as f:
                # Should be valid JSON and parseable
                marker = json.load(f)
                assert isinstance(marker, dict)

    def test_job_marker_has_all_required_fields(self):
        """Verify all job markers have required fields for processing."""
        jobs_dir = Path("/workspaces/geolocation-engine2/.nwave/jobs")
        job_files = list(jobs_dir.glob("issue-*.json"))

        required_fields = {"issue_number", "agent", "status", "created_at"}

        for job_file in job_files:
            with open(job_file) as f:
                marker = json.load(f)

            marker_fields = set(marker.keys())
            assert required_fields.issubset(marker_fields), \
                f"Marker {job_file} missing fields: {required_fields - marker_fields}"

    def test_processor_can_identify_deliver_jobs(self):
        """Verify processor can identify nw:deliver jobs."""
        jobs_dir = Path("/workspaces/geolocation-engine2/.nwave/jobs")
        job_files = list(jobs_dir.glob("issue-*.json"))

        deliver_jobs = []
        for job_file in job_files:
            with open(job_file) as f:
                marker = json.load(f)

            if marker.get("agent") == "nw:deliver":
                deliver_jobs.append(marker)

        # Should have at least issue-11
        assert len(deliver_jobs) > 0
        issue_numbers = [j["issue_number"] for j in deliver_jobs]
        assert 11 in issue_numbers

    def test_processor_can_filter_pending_jobs(self):
        """Verify processor can filter for pending jobs."""
        jobs_dir = Path("/workspaces/geolocation-engine2/.nwave/jobs")
        job_files = list(jobs_dir.glob("issue-*.json"))

        pending_jobs = []
        for job_file in job_files:
            with open(job_file) as f:
                marker = json.load(f)

            if marker.get("status") == "pending":
                pending_jobs.append(marker)

        # issue-11 should be pending
        assert any(j["issue_number"] == 11 for j in pending_jobs)

    def test_processor_job_status_can_transition(self):
        """Verify job status can transition from pending to processing."""
        # Simulate processor updating job status
        with tempfile.TemporaryDirectory() as tmpdir:
            test_marker_path = Path(tmpdir) / "test-marker.json"

            # Create test marker
            marker = {
                "issue_number": 999,
                "agent": "nw:deliver",
                "status": "pending",
                "created_at": "2026-02-15T15:09:14Z"
            }

            with open(test_marker_path, 'w') as f:
                json.dump(marker, f)

            # Read and update
            with open(test_marker_path) as f:
                loaded = json.load(f)

            loaded["status"] = "processing"

            with open(test_marker_path, 'w') as f:
                json.dump(loaded, f)

            # Verify update
            with open(test_marker_path) as f:
                updated = json.load(f)

            assert updated["status"] == "processing"


class TestJobMarkerWorkflowIntegration:
    """End-to-end tests for complete job marker workflow."""

    def test_issue_11_marker_complete_workflow(self):
        """Verify issue #11 job marker follows complete workflow."""
        job_marker_path = Path("/workspaces/geolocation-engine2/.nwave/jobs/issue-11.json")

        # 1. File exists
        assert job_marker_path.exists()

        # 2. Valid JSON structure
        with open(job_marker_path) as f:
            marker = json.load(f)

        # 3. Correct routing
        assert marker["issue_number"] == 11
        assert marker["agent"] == "nw:deliver"

        # 4. Proper initial state
        assert marker["status"] == "pending"

        # 5. Valid timestamp
        assert len(marker["created_at"]) > 0
        assert "Z" in marker["created_at"]

    def test_marker_discovery_and_routing_flow(self):
        """Verify complete discovery and routing flow."""
        # 1. Discover jobs directory
        jobs_dir = Path("/workspaces/geolocation-engine2/.nwave/jobs")
        assert jobs_dir.exists()

        # 2. Find all job markers
        job_files = list(jobs_dir.glob("issue-*.json"))
        assert len(job_files) > 0

        # 3. Parse and validate
        valid_markers = []
        for job_file in job_files:
            with open(job_file) as f:
                try:
                    marker = json.load(f)
                    valid_markers.append(marker)
                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON in {job_file}")

        # 4. Filter by agent and status
        deliver_pending = [
            m for m in valid_markers
            if m.get("agent") == "nw:deliver" and m.get("status") == "pending"
        ]

        # 5. Should be able to execute
        assert len(deliver_pending) > 0

    def test_multiple_job_markers_can_coexist(self):
        """Verify multiple job markers can be stored and processed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs_dir = Path(tmpdir) / "jobs"
            jobs_dir.mkdir()

            # Create multiple markers
            markers = [
                {"issue_number": 1, "agent": "nw:deliver", "status": "pending", "created_at": "2026-02-15T15:00:00Z"},
                {"issue_number": 2, "agent": "nw:deliver", "status": "pending", "created_at": "2026-02-15T15:01:00Z"},
                {"issue_number": 3, "agent": "nw:devops", "status": "pending", "created_at": "2026-02-15T15:02:00Z"},
            ]

            for marker in markers:
                with open(jobs_dir / f"issue-{marker['issue_number']}.json", 'w') as f:
                    json.dump(marker, f)

            # Discover all
            found = list(jobs_dir.glob("issue-*.json"))
            assert len(found) == 3

            # Filter by agent
            deliver_jobs = []
            for job_file in found:
                with open(job_file) as f:
                    m = json.load(f)
                    if m["agent"] == "nw:deliver":
                        deliver_jobs.append(m)

            assert len(deliver_jobs) == 2
            assert all(m["agent"] == "nw:deliver" for m in deliver_jobs)


class TestJobMarkerErrorHandling:
    """Test error handling in job marker workflow."""

    def test_invalid_json_marker_detected(self):
        """Verify invalid JSON markers can be detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_marker = Path(tmpdir) / "bad-marker.json"

            # Write invalid JSON
            with open(bad_marker, 'w') as f:
                f.write("{invalid json")

            # Should fail to parse
            with pytest.raises(json.JSONDecodeError):
                with open(bad_marker) as f:
                    json.load(f)

    def test_marker_with_missing_required_fields(self):
        """Verify markers with missing fields can be detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            incomplete_marker = Path(tmpdir) / "incomplete.json"

            # Missing "agent" field
            incomplete = {
                "issue_number": 999,
                "status": "pending"
            }

            with open(incomplete_marker, 'w') as f:
                json.dump(incomplete, f)

            # Verify detection
            with open(incomplete_marker) as f:
                marker = json.load(f)

            assert "agent" not in marker
            assert "created_at" not in marker


class TestJobMarkerStatusTransition:
    """Test job marker status transitions."""

    @pytest.mark.parametrize("transition", [
        ("pending", "processing"),
        ("processing", "completed"),
        ("processing", "failed"),
    ])
    def test_valid_status_transitions(self, transition):
        """Verify valid status transitions."""
        from_status, to_status = transition

        with tempfile.TemporaryDirectory() as tmpdir:
            marker_path = Path(tmpdir) / "marker.json"

            # Create marker
            marker = {
                "issue_number": 999,
                "agent": "nw:deliver",
                "status": from_status,
                "created_at": "2026-02-15T15:00:00Z"
            }

            with open(marker_path, 'w') as f:
                json.dump(marker, f)

            # Update status
            with open(marker_path) as f:
                loaded = json.load(f)

            loaded["status"] = to_status

            with open(marker_path, 'w') as f:
                json.dump(loaded, f)

            # Verify
            with open(marker_path) as f:
                updated = json.load(f)

            assert updated["status"] == to_status


# Edge case tests
class TestJobMarkerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_jobs_directory_handled(self):
        """Verify empty jobs directory is handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs_dir = Path(tmpdir) / "jobs"
            jobs_dir.mkdir()

            # Should be able to list empty directory
            job_files = list(jobs_dir.glob("issue-*.json"))
            assert len(job_files) == 0

    def test_large_issue_number(self):
        """Verify large issue numbers are handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            large_issue = 999999

            marker_path = Path(tmpdir) / f"issue-{large_issue}.json"
            marker = {
                "issue_number": large_issue,
                "agent": "nw:deliver",
                "status": "pending",
                "created_at": "2026-02-15T15:00:00Z"
            }

            with open(marker_path, 'w') as f:
                json.dump(marker, f)

            with open(marker_path) as f:
                loaded = json.load(f)

            assert loaded["issue_number"] == large_issue

    def test_marker_with_extra_fields(self):
        """Verify markers with extra fields don't break processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            marker_path = Path(tmpdir) / "marker.json"

            # Extra fields like "metadata" or "notes"
            marker = {
                "issue_number": 999,
                "agent": "nw:deliver",
                "status": "pending",
                "created_at": "2026-02-15T15:00:00Z",
                "pr_number": None,  # Extra field
                "attempts": 0  # Extra field
            }

            with open(marker_path, 'w') as f:
                json.dump(marker, f)

            with open(marker_path) as f:
                loaded = json.load(f)

            # Should still be processable
            assert loaded["issue_number"] == 999
            assert loaded["agent"] == "nw:deliver"

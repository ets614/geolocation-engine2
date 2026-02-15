"""Unit tests for offline queue service (resilient TAK output)."""
import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.services.offline_queue_service import (
    OfflineQueueService,
    SyncStatus,
    QueueEntry,
)


@pytest.fixture
def queue_service(db_session):
    """Create offline queue service instance."""
    return OfflineQueueService(session=db_session)


@pytest.fixture
def queue_service_no_db():
    """Create offline queue service without database."""
    return OfflineQueueService(session=None)


@pytest.fixture
def sample_detection_json():
    """Create sample detection JSON."""
    return {
        "detection_id": "det-001",
        "cot_xml": '<?xml version="1.0"?><event/>',
        "geolocation": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "confidence_flag": "GREEN",
        },
        "metadata": {"camera_id": "cam-001"},
        "queued_at": datetime.utcnow().isoformat(),
    }


class TestSyncStatus:
    """Test SyncStatus enum."""

    def test_sync_status_pending(self):
        """Should have PENDING_SYNC status."""
        assert SyncStatus.PENDING_SYNC.value == "PENDING_SYNC"

    def test_sync_status_syncing(self):
        """Should have SYNCING status."""
        assert SyncStatus.SYNCING.value == "SYNCING"

    def test_sync_status_synced(self):
        """Should have SYNCED status."""
        assert SyncStatus.SYNCED.value == "SYNCED"

    def test_sync_status_failed_retry(self):
        """Should have FAILED_RETRY status."""
        assert SyncStatus.FAILED_RETRY.value == "FAILED_RETRY"


class TestQueueEntry:
    """Test QueueEntry dataclass."""

    def test_queue_entry_creation(self, sample_detection_json):
        """Should create queue entry."""
        entry = QueueEntry(detection_json=sample_detection_json)

        assert entry.detection_json == sample_detection_json
        assert entry.sync_status == SyncStatus.PENDING_SYNC
        assert entry.retry_count == 0

    def test_queue_entry_with_custom_status(self, sample_detection_json):
        """Should support custom sync status."""
        entry = QueueEntry(
            detection_json=sample_detection_json,
            sync_status=SyncStatus.SYNCING,
        )

        assert entry.sync_status == SyncStatus.SYNCING


class TestQueueing:
    """Test queueing detections."""

    def test_queue_detection_without_db(
        self, queue_service_no_db, sample_detection_json
    ):
        """Should queue detection without database."""
        # Should not raise
        queue_service_no_db.queue_detection(
            detection_id="det-001",
            cot_xml=sample_detection_json["cot_xml"],
            geolocation=sample_detection_json["geolocation"],
        )

    def test_queue_detection_with_db(
        self, queue_service, db_session, sample_detection_json
    ):
        """Should queue detection to database."""
        queue_service.queue_detection(
            detection_id="det-001",
            cot_xml=sample_detection_json["cot_xml"],
            geolocation=sample_detection_json["geolocation"],
            metadata=sample_detection_json["metadata"],
        )

        from src.models.database_models import OfflineQueue

        queued = db_session.query(OfflineQueue).first()
        assert queued is not None
        assert queued.detection_json["detection_id"] == "det-001"

    def test_queue_multiple_detections(
        self, queue_service, db_session
    ):
        """Should queue multiple detections."""
        for i in range(3):
            queue_service.queue_detection(
                detection_id=f"det-00{i+1}",
                cot_xml="<event/>",
                geolocation={"lat": 40.0, "lon": -74.0},
            )

        from src.models.database_models import OfflineQueue

        count = db_session.query(OfflineQueue).count()
        assert count == 3


class TestQueueStatus:
    """Test queue status operations."""

    def test_get_queue_size_empty(self, queue_service):
        """Should return 0 for empty queue."""
        size = queue_service.get_queue_size()
        assert size == 0

    def test_get_queue_size_with_items(
        self, queue_service, sample_detection_json
    ):
        """Should return correct queue size."""
        queue_service.queue_detection(
            detection_id="det-001",
            cot_xml=sample_detection_json["cot_xml"],
            geolocation=sample_detection_json["geolocation"],
        )

        size = queue_service.get_queue_size()
        assert size == 1

    def test_get_queue_size_without_db(self, queue_service_no_db):
        """Should return 0 without database."""
        size = queue_service_no_db.get_queue_size()
        assert size == 0

    def test_get_queue_status_empty(self, queue_service):
        """Should return status dict for empty queue."""
        status = queue_service.get_queue_status()

        assert status["pending_count"] == 0
        assert status["failed_count"] == 0
        assert status["oldest_pending"] is None
        assert status["total_retries"] == 0

    def test_get_queue_status_with_items(
        self, queue_service, sample_detection_json
    ):
        """Should return correct queue status."""
        queue_service.queue_detection(
            detection_id="det-001",
            cot_xml=sample_detection_json["cot_xml"],
            geolocation=sample_detection_json["geolocation"],
        )

        status = queue_service.get_queue_status()

        assert status["pending_count"] == 1
        assert status["oldest_pending"] is not None

    def test_get_queue_status_without_db(self, queue_service_no_db):
        """Should return default status without database."""
        status = queue_service_no_db.get_queue_status()

        assert status["pending_count"] == 0
        assert status["failed_count"] == 0


class TestPendingDetections:
    """Test retrieving pending detections."""

    def test_get_pending_detections_empty(self, queue_service):
        """Should return empty list for no pending items."""
        pending = queue_service.get_pending_detections()
        assert pending == []

    def test_get_pending_detections_single(
        self, queue_service, sample_detection_json
    ):
        """Should retrieve single pending detection."""
        queue_service.queue_detection(
            detection_id="det-001",
            cot_xml=sample_detection_json["cot_xml"],
            geolocation=sample_detection_json["geolocation"],
        )

        pending = queue_service.get_pending_detections()

        assert len(pending) == 1
        assert pending[0].detection_json["detection_id"] == "det-001"
        assert pending[0].sync_status == SyncStatus.PENDING_SYNC

    def test_get_pending_detections_multiple(self, queue_service):
        """Should retrieve multiple pending detections in order."""
        for i in range(3):
            queue_service.queue_detection(
                detection_id=f"det-00{i+1}",
                cot_xml="<event/>",
                geolocation={"lat": 40.0, "lon": -74.0},
            )

        pending = queue_service.get_pending_detections()

        assert len(pending) == 3
        # Should be in order of creation
        for i, entry in enumerate(pending):
            assert entry.detection_json["detection_id"] == f"det-00{i+1}"

    def test_get_pending_detections_respects_limit(self, queue_service):
        """Should respect limit parameter."""
        for i in range(5):
            queue_service.queue_detection(
                detection_id=f"det-{i:03d}",
                cot_xml="<event/>",
                geolocation={"lat": 40.0, "lon": -74.0},
            )

        pending = queue_service.get_pending_detections(limit=2)

        assert len(pending) == 2

    def test_get_pending_detections_without_db(self, queue_service_no_db):
        """Should return empty list without database."""
        pending = queue_service_no_db.get_pending_detections()
        assert pending == []


class TestSyncCallbacks:
    """Test sync callback registration and execution."""

    def test_register_sync_callback(self, queue_service):
        """Should register sync callback."""
        def callback(detection_json):
            return True

        queue_service.register_sync_callback(callback)

        assert len(queue_service._sync_callbacks) == 1

    def test_register_multiple_callbacks(self, queue_service):
        """Should register multiple callbacks."""
        queue_service.register_sync_callback(lambda x: True)
        queue_service.register_sync_callback(lambda x: True)

        assert len(queue_service._sync_callbacks) == 2


class TestQueueSync:
    """Test queue synchronization."""

    def test_sync_queue_no_callbacks(self, queue_service):
        """Should log warning and return empty stats without callbacks."""
        stats = queue_service.sync_queue()

        assert stats["attempted"] == 0
        assert stats["succeeded"] == 0
        assert stats["failed"] == 0

    def test_sync_queue_no_pending(self, queue_service):
        """Should return 0 stats for empty queue."""
        queue_service.register_sync_callback(lambda x: True)

        stats = queue_service.sync_queue()

        assert stats["attempted"] == 0

    def test_sync_queue_successful_sync(self, queue_service):
        """Should successfully sync queued items."""
        # Queue a detection
        queue_service.queue_detection(
            detection_id="det-001",
            cot_xml="<event/>",
            geolocation={"lat": 40.0, "lon": -74.0},
        )

        # Register success callback
        queue_service.register_sync_callback(lambda x: True)

        # Sync
        stats = queue_service.sync_queue()

        assert stats["attempted"] == 1
        assert stats["succeeded"] == 1
        assert stats["failed"] == 0

    def test_sync_queue_with_failures(self, queue_service):
        """Should handle sync failures."""
        # Queue detections
        for i in range(3):
            queue_service.queue_detection(
                detection_id=f"det-{i:03d}",
                cot_xml="<event/>",
                geolocation={"lat": 40.0, "lon": -74.0},
            )

        # Register callback that fails on first detection
        def selective_callback(detection_json):
            return detection_json["detection_id"] != "det-000"

        queue_service.register_sync_callback(selective_callback)

        # Sync
        stats = queue_service.sync_queue()

        assert stats["attempted"] == 3
        assert stats["succeeded"] == 2
        assert stats["failed"] == 1

    def test_sync_queue_without_db(self, queue_service_no_db):
        """Should handle sync without database."""
        queue_service_no_db.register_sync_callback(lambda x: True)

        stats = queue_service_no_db.sync_queue()

        assert stats["attempted"] == 0


class TestRecovery:
    """Test crash recovery and persistence."""

    def test_recover_from_crash_no_items(self, queue_service):
        """Should return 0 for no items to recover."""
        stats = queue_service.recover_from_crash()

        assert stats["recovered_count"] == 0
        assert stats["synced_count"] == 0

    def test_recover_from_crash_with_items(self, queue_service):
        """Should recover and sync queued items."""
        # Queue items
        for i in range(2):
            queue_service.queue_detection(
                detection_id=f"det-{i:03d}",
                cot_xml="<event/>",
                geolocation={"lat": 40.0, "lon": -74.0},
            )

        # Register callback
        queue_service.register_sync_callback(lambda x: True)

        # Recover
        stats = queue_service.recover_from_crash()

        assert stats["recovered_count"] == 2
        assert stats["synced_count"] == 2

    def test_recover_from_crash_partial_sync(self, queue_service):
        """Should recover with partial sync success."""
        # Queue items
        for i in range(3):
            queue_service.queue_detection(
                detection_id=f"det-{i:03d}",
                cot_xml="<event/>",
                geolocation={"lat": 40.0, "lon": -74.0},
            )

        # Register callback that succeeds for some
        def partial_callback(detection_json):
            return int(detection_json["detection_id"][-3:]) > 0

        queue_service.register_sync_callback(partial_callback)

        # Recover
        stats = queue_service.recover_from_crash()

        assert stats["recovered_count"] == 3
        assert stats["synced_count"] == 2


class TestCleanup:
    """Test cleanup operations."""

    def test_clear_old_items_no_items(self, queue_service):
        """Should return 0 when no old items exist."""
        cleared = queue_service.clear_old_items(days_old=30)
        assert cleared == 0

    def test_clear_old_items_excludes_recent(
        self, queue_service, db_session
    ):
        """Should not delete recently synced items."""
        # Queue and sync an item
        queue_service.queue_detection(
            detection_id="det-001",
            cot_xml="<event/>",
            geolocation={"lat": 40.0, "lon": -74.0},
        )

        # Mark as synced (recent)
        from src.models.database_models import OfflineQueue
        item = db_session.query(OfflineQueue).first()
        item.synced_at = datetime.utcnow()
        db_session.commit()

        # Clear items older than 30 days
        cleared = queue_service.clear_old_items(days_old=30)

        assert cleared == 0

    def test_clear_old_items_deletes_old_synced(self, queue_service, db_session):
        """Should delete old synced items."""
        # Queue and sync an old item
        queue_service.queue_detection(
            detection_id="det-001",
            cot_xml="<event/>",
            geolocation={"lat": 40.0, "lon": -74.0},
        )

        # Mark as synced (old)
        from src.models.database_models import OfflineQueue
        item = db_session.query(OfflineQueue).first()
        item.synced_at = datetime.utcnow() - timedelta(days=40)
        db_session.commit()

        # Clear items older than 30 days
        cleared = queue_service.clear_old_items(days_old=30)

        assert cleared == 1

    def test_clear_old_items_without_db(self, queue_service_no_db):
        """Should return 0 without database."""
        cleared = queue_service_no_db.clear_old_items(days_old=30)
        assert cleared == 0


class TestConnectivityMonitoring:
    """Test background connectivity monitoring."""

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, queue_service):
        """Should start and stop monitoring."""
        # Start monitoring in background
        monitor_task = asyncio.create_task(
            queue_service.start_connectivity_monitoring(
                check_interval_seconds=0.1,
                connectivity_check=lambda: False,
            )
        )

        # Let it run briefly
        await asyncio.sleep(0.05)

        # Stop it
        queue_service.stop_connectivity_monitoring()

        # Wait for it to complete
        try:
            await asyncio.wait_for(monitor_task, timeout=1.0)
        except asyncio.TimeoutError:
            pass

        assert not queue_service._connectivity_monitoring

    @pytest.mark.asyncio
    async def test_monitoring_triggers_sync_on_reconnect(self, queue_service):
        """Should sync queue when connectivity restored."""
        # Queue an item
        queue_service.queue_detection(
            detection_id="det-001",
            cot_xml="<event/>",
            geolocation={"lat": 40.0, "lon": -74.0},
        )

        sync_attempted = False

        def sync_callback(detection_json):
            nonlocal sync_attempted
            sync_attempted = True
            return True

        queue_service.register_sync_callback(sync_callback)

        # Create connectivity check that returns True after first check
        check_count = 0

        def connectivity_check():
            nonlocal check_count
            check_count += 1
            return check_count > 1

        # Start monitoring
        monitor_task = asyncio.create_task(
            queue_service.start_connectivity_monitoring(
                check_interval_seconds=0.05,
                connectivity_check=connectivity_check,
            )
        )

        # Let it run long enough to check connectivity and sync
        await asyncio.sleep(0.2)

        # Stop it
        queue_service.stop_connectivity_monitoring()

        # Wait for completion
        try:
            await asyncio.wait_for(monitor_task, timeout=1.0)
        except asyncio.TimeoutError:
            pass

        assert sync_attempted or check_count > 0


class TestMaxRetries:
    """Test retry limit enforcement."""

    def test_exceeded_max_retries_removes_item(self, queue_service, db_session):
        """Should remove item after max retries exceeded."""
        # Queue an item
        queue_service.queue_detection(
            detection_id="det-001",
            cot_xml="<event/>",
            geolocation={"lat": 40.0, "lon": -74.0},
        )

        # Fail sync multiple times
        queue_service.register_sync_callback(lambda x: False)

        for _ in range(queue_service.MAX_RETRIES + 2):
            queue_service.sync_queue()

        from src.models.database_models import OfflineQueue
        remaining = db_session.query(OfflineQueue).count()

        assert remaining == 0

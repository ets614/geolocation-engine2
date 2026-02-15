"""Offline queue service for resilient TAK output with automatic sync."""
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Callable, Any
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.orm import Session
from src.models.database_models import OfflineQueue


class SyncStatus(str, Enum):
    """Status of queue entry."""

    PENDING_SYNC = "PENDING_SYNC"
    SYNCING = "SYNCING"
    SYNCED = "SYNCED"
    FAILED_RETRY = "FAILED_RETRY"


@dataclass
class QueueEntry:
    """Queue entry for offline storage."""

    detection_json: dict
    sync_status: SyncStatus = SyncStatus.PENDING_SYNC
    retry_count: int = 0
    created_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None


class OfflineQueueService:
    """Manages offline queue for resilient CoT output to TAK server."""

    MAX_RETRIES = 3
    RETRY_BACKOFF_SECONDS = 5
    SYNC_BATCH_SIZE = 10

    def __init__(self, session: Optional[Session] = None):
        """Initialize offline queue service.

        Args:
            session: SQLAlchemy session for persistence (optional)
        """
        self.session = session
        self.logger = logging.getLogger(__name__)
        self._sync_callbacks: List[Callable[[dict], bool]] = []
        self._connectivity_monitoring = False

    def register_sync_callback(self, callback: Callable[[dict], bool]) -> None:
        """Register callback for syncing queued items.

        Args:
            callback: Function that takes a detection dict and returns True on success
        """
        self._sync_callbacks.append(callback)

    def queue_detection(
        self,
        detection_id: str,
        cot_xml: str,
        geolocation: dict,
        metadata: dict = None,
    ) -> None:
        """Queue detection to offline queue when TAK server unavailable.

        Args:
            detection_id: Detection identifier
            cot_xml: CoT XML content
            geolocation: Geolocation data dict
            metadata: Additional metadata

        Raises:
            RuntimeError: If queue persistence fails
        """
        try:
            detection_json = {
                "detection_id": detection_id,
                "cot_xml": cot_xml,
                "geolocation": geolocation,
                "metadata": metadata or {},
                "queued_at": datetime.utcnow().isoformat(),
            }

            if self.session:
                queue_entry = OfflineQueue(
                    detection_json=detection_json,
                    created_at=datetime.utcnow(),
                    retry_count=0,
                )
                self.session.add(queue_entry)
                self.session.commit()

            self.logger.info(
                f"Detection queued: {detection_id} "
                f"(TAK server unavailable)"
            )

        except Exception as e:
            self.logger.error(f"Failed to queue detection: {str(e)}")
            if self.session:
                self.session.rollback()
            raise RuntimeError(f"Queue persistence failed: {str(e)}")

    def get_queue_size(self) -> int:
        """Get current queue size.

        Returns:
            Number of pending items in queue
        """
        if not self.session:
            return 0

        try:
            count = (
                self.session.query(OfflineQueue)
                .filter(OfflineQueue.synced_at.is_(None))
                .count()
            )
            return count
        except Exception as e:
            self.logger.error(f"Failed to get queue size: {str(e)}")
            return 0

    def get_queue_status(self) -> dict:
        """Get detailed queue status.

        Returns:
            dict with queue statistics
        """
        if not self.session:
            return {
                "pending_count": 0,
                "failed_count": 0,
                "oldest_pending": None,
                "total_retries": 0,
            }

        try:
            pending = (
                self.session.query(OfflineQueue)
                .filter(OfflineQueue.synced_at.is_(None))
                .order_by(OfflineQueue.created_at.asc())
                .all()
            )

            failed = sum(1 for item in pending if item.retry_count > 0)
            oldest = pending[0].created_at if pending else None
            total_retries = sum(item.retry_count for item in pending)

            return {
                "pending_count": len(pending),
                "failed_count": failed,
                "oldest_pending": oldest,
                "total_retries": total_retries,
            }
        except Exception as e:
            self.logger.error(f"Failed to get queue status: {str(e)}")
            return {
                "pending_count": 0,
                "failed_count": 0,
                "oldest_pending": None,
                "total_retries": 0,
            }

    def get_pending_detections(self, limit: int = 100) -> List[QueueEntry]:
        """Get pending detections from queue.

        Args:
            limit: Maximum number of items to retrieve

        Returns:
            List of pending queue entries
        """
        if not self.session:
            return []

        try:
            db_items = (
                self.session.query(OfflineQueue)
                .filter(OfflineQueue.synced_at.is_(None))
                .order_by(OfflineQueue.created_at.asc())
                .limit(limit)
                .all()
            )

            entries = [
                QueueEntry(
                    detection_json=item.detection_json,
                    sync_status=SyncStatus.PENDING_SYNC,
                    retry_count=item.retry_count,
                    created_at=item.created_at,
                    synced_at=item.synced_at,
                )
                for item in db_items
            ]

            return entries
        except Exception as e:
            self.logger.error(f"Failed to get pending detections: {str(e)}")
            return []

    def sync_queue(self) -> dict:
        """Sync all pending queue items to TAK server.

        Returns:
            dict with sync statistics (attempted, succeeded, failed)

        Raises:
            RuntimeError: If sync process fails
        """
        if not self._sync_callbacks:
            self.logger.warning("No sync callbacks registered")
            return {"attempted": 0, "succeeded": 0, "failed": 0}

        try:
            pending = self.get_pending_detections(limit=self.SYNC_BATCH_SIZE)

            attempted = 0
            succeeded = 0
            failed = 0

            for entry in pending:
                attempted += 1

                # Try all registered callbacks
                success = False
                for callback in self._sync_callbacks:
                    try:
                        if callback(entry.detection_json):
                            success = True
                            break
                    except Exception as e:
                        self.logger.debug(f"Sync callback failed: {str(e)}")
                        continue

                if success:
                    # Mark as synced
                    self._mark_synced(entry.detection_json["detection_id"])
                    succeeded += 1
                else:
                    # Increment retry count
                    self._increment_retry(
                        entry.detection_json["detection_id"]
                    )
                    failed += 1

            stats = {
                "attempted": attempted,
                "succeeded": succeeded,
                "failed": failed,
            }

            self.logger.info(
                f"Queue sync completed: {stats['succeeded']}/{stats['attempted']} "
                f"succeeded"
            )

            return stats

        except Exception as e:
            self.logger.error(f"Queue sync failed: {str(e)}")
            raise RuntimeError(f"Queue sync error: {str(e)}")

    def _mark_synced(self, detection_id: str) -> None:
        """Mark detection as synced.

        Args:
            detection_id: Detection identifier
        """
        if not self.session:
            return

        try:
            # Get all pending items and check in Python
            queue_items = (
                self.session.query(OfflineQueue)
                .filter(OfflineQueue.synced_at.is_(None))
                .all()
            )

            for item in queue_items:
                if item.detection_json.get("detection_id") == detection_id:
                    item.synced_at = datetime.utcnow()

            self.session.commit()
            self.logger.debug(f"Marked detection as synced: {detection_id}")

        except Exception as e:
            self.logger.error(f"Failed to mark synced: {str(e)}")
            if self.session:
                self.session.rollback()

    def _increment_retry(self, detection_id: str) -> None:
        """Increment retry count for detection.

        Args:
            detection_id: Detection identifier
        """
        if not self.session:
            return

        try:
            # Get pending items and check in Python
            queue_items = (
                self.session.query(OfflineQueue)
                .filter(OfflineQueue.synced_at.is_(None))
                .all()
            )

            for item in queue_items:
                if item.detection_json.get("detection_id") == detection_id:
                    item.retry_count += 1
                    # Remove if max retries exceeded
                    if item.retry_count > self.MAX_RETRIES:
                        self.logger.warning(
                            f"Detection exceeded max retries: {detection_id}"
                        )
                        self.session.delete(item)

            self.session.commit()

        except Exception as e:
            self.logger.error(f"Failed to increment retry: {str(e)}")
            if self.session:
                self.session.rollback()

    async def start_connectivity_monitoring(
        self,
        check_interval_seconds: int = 30,
        connectivity_check: Optional[Callable[[], bool]] = None,
    ) -> None:
        """Start background monitoring for TAK connectivity.

        Args:
            check_interval_seconds: How often to check connectivity
            connectivity_check: Function that returns True if TAK is reachable
        """
        self._connectivity_monitoring = True
        self.logger.info(
            "Starting connectivity monitoring "
            f"(interval: {check_interval_seconds}s)"
        )

        try:
            while self._connectivity_monitoring:
                await asyncio.sleep(check_interval_seconds)

                # Check connectivity
                is_connected = (
                    connectivity_check() if connectivity_check else False
                )

                if is_connected:
                    self.logger.info(
                        "TAK connectivity restored - syncing queue"
                    )
                    try:
                        stats = self.sync_queue()
                        self.logger.info(
                            f"Queue sync completed after reconnect: {stats}"
                        )
                    except Exception as e:
                        self.logger.error(f"Queue sync failed: {str(e)}")

        except asyncio.CancelledError:
            self.logger.info("Connectivity monitoring stopped")
            self._connectivity_monitoring = False

    def stop_connectivity_monitoring(self) -> None:
        """Stop background connectivity monitoring."""
        self._connectivity_monitoring = False
        self.logger.info("Stopping connectivity monitoring")

    def recover_from_crash(self) -> dict:
        """Recover queued items from previous crash.

        Returns:
            dict with recovery statistics (recovered_count, synced_count)
        """
        if not self.session:
            return {"recovered_count": 0, "synced_count": 0}

        try:
            # Get all pending items
            pending = self.get_pending_detections(limit=None)
            recovered_count = len(pending)

            if recovered_count == 0:
                self.logger.info("No items to recover from crash")
                return {
                    "recovered_count": 0,
                    "synced_count": 0,
                }

            self.logger.info(
                f"Recovering {recovered_count} items from offline queue"
            )

            # Attempt sync
            stats = self.sync_queue()

            return {
                "recovered_count": recovered_count,
                "synced_count": stats["succeeded"],
            }

        except Exception as e:
            self.logger.error(f"Crash recovery failed: {str(e)}")
            return {"recovered_count": 0, "synced_count": 0}

    def clear_old_items(self, days_old: int = 30) -> int:
        """Clear synced items older than specified days.

        Args:
            days_old: Items synced more than this many days ago are deleted

        Returns:
            Number of items deleted
        """
        if not self.session:
            return 0

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            deleted_count = (
                self.session.query(OfflineQueue)
                .filter(OfflineQueue.synced_at.isnot(None))
                .filter(OfflineQueue.synced_at < cutoff_date)
                .delete()
            )

            self.session.commit()
            self.logger.info(
                f"Cleared {deleted_count} synced items older than {days_old} days"
            )

            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to clear old items: {str(e)}")
            if self.session:
                self.session.rollback()
            return 0

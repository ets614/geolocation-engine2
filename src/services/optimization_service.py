"""Query optimization and pagination service.

Provides efficient pagination, batching, and query optimization for large datasets.
"""

import logging
from typing import List, Optional, Any, TypeVar, Generic
from dataclasses import dataclass
from math import ceil

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class PaginationParams:
    """Pagination parameters."""
    offset: int = 0
    limit: int = 50
    sort_by: Optional[str] = None
    sort_order: str = "asc"  # asc or desc

    def __post_init__(self):
        """Validate pagination parameters."""
        if self.offset < 0:
            raise ValueError("offset must be >= 0")
        if self.limit < 1 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if self.sort_order not in ("asc", "desc"):
            raise ValueError("sort_order must be 'asc' or 'desc'")


@dataclass
class PaginatedResult(Generic[T]):
    """Paginated result set."""
    items: List[T]
    offset: int
    limit: int
    total: int
    has_next: bool
    has_previous: bool
    page_count: int
    current_page: int

    @property
    def pages(self) -> range:
        """Get range of available pages."""
        return range(1, self.page_count + 1)


class PaginationService:
    """Efficient pagination with metadata."""

    @staticmethod
    def paginate(
        items: List[T],
        offset: int = 0,
        limit: int = 50,
        sort_key: Optional[str] = None,
        reverse: bool = False,
    ) -> PaginatedResult[T]:
        """Paginate items with optional sorting.

        Args:
            items: List of items to paginate
            offset: Starting index
            limit: Maximum items per page
            sort_key: Optional key function for sorting
            reverse: Sort in descending order

        Returns:
            PaginatedResult with paginated items and metadata
        """
        params = PaginationParams(offset=offset, limit=limit)

        # Sort if needed
        if sort_key:
            items = sorted(items, key=sort_key, reverse=reverse)

        total = len(items)
        page_count = ceil(total / limit) if limit > 0 else 1
        current_page = (offset // limit) + 1 if limit > 0 else 1

        # Slice items
        start = offset
        end = offset + limit
        paginated_items = items[start:end]

        return PaginatedResult(
            items=paginated_items,
            offset=offset,
            limit=limit,
            total=total,
            has_next=(offset + limit) < total,
            has_previous=offset > 0,
            page_count=page_count,
            current_page=current_page,
        )

    @staticmethod
    def cursor_paginate(
        items: List[T],
        cursor: Optional[str] = None,
        limit: int = 50,
        cursor_key: Optional[str] = None,
    ) -> tuple[List[T], Optional[str]]:
        """Cursor-based pagination (more efficient for large datasets).

        Args:
            items: List of items to paginate
            cursor: Opaque cursor from previous request
            limit: Maximum items per page
            cursor_key: Key to use for cursor positioning

        Returns:
            Tuple of (paginated_items, next_cursor)
        """
        start_idx = 0

        if cursor and cursor_key:
            # Find starting position from cursor
            try:
                start_idx = int(cursor)
            except ValueError:
                logger.warning(f"Invalid cursor: {cursor}")
                start_idx = 0

        end_idx = start_idx + limit
        paginated_items = items[start_idx:end_idx]

        # Generate next cursor
        next_cursor = None
        if end_idx < len(items):
            next_cursor = str(end_idx)

        return paginated_items, next_cursor


class QueryOptimizer:
    """Optimize database queries through batching and prefetching."""

    def __init__(self, batch_size: int = 100):
        """Initialize query optimizer.

        Args:
            batch_size: Default batch size for batch operations
        """
        self.batch_size = batch_size
        self.query_cache = {}
        self.stats = {
            "batch_queries": 0,
            "prefetch_hits": 0,
            "prefetch_misses": 0,
        }

    def batch_query(
        self,
        ids: List[Any],
        fetch_fn,
        batch_size: Optional[int] = None,
    ) -> dict:
        """Execute query in batches to optimize performance.

        Args:
            ids: List of identifiers to query
            fetch_fn: Function to fetch items (receives list of ids)
            batch_size: Override default batch size

        Returns:
            Dictionary mapping id -> item
        """
        batch_size = batch_size or self.batch_size
        results = {}

        for i in range(0, len(ids), batch_size):
            batch = ids[i:i + batch_size]
            try:
                batch_results = fetch_fn(batch)
                results.update(batch_results)
                self.stats["batch_queries"] += 1
            except Exception as e:
                logger.error(f"Batch query failed for {batch}: {e}")

        return results

    def prefetch(
        self,
        primary_ids: List[Any],
        related_fetch_fn,
        batch_size: Optional[int] = None,
    ) -> dict:
        """Prefetch related items to avoid N+1 queries.

        Args:
            primary_ids: List of primary identifiers
            related_fetch_fn: Function to fetch related items
            batch_size: Override default batch size

        Returns:
            Dictionary mapping id -> related_items
        """
        results = self.batch_query(primary_ids, related_fetch_fn, batch_size)
        self.stats["prefetch_hits"] += len([r for r in results.values() if r])
        self.stats["prefetch_misses"] += len([r for r in results.values() if not r])
        return results

    def get_stats(self) -> dict:
        """Get query optimization statistics."""
        return self.stats.copy()


class BatchProcessor:
    """Process items in batches for efficient computation."""

    def __init__(self, batch_size: int = 100):
        """Initialize batch processor.

        Args:
            batch_size: Size of batches to process
        """
        self.batch_size = batch_size

    def process_batch(self, items: List[T], process_fn) -> List[Any]:
        """Process items in batches.

        Args:
            items: Items to process
            process_fn: Function to process batch

        Returns:
            List of results from all batches
        """
        results = []

        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            try:
                batch_results = process_fn(batch)
                results.extend(batch_results)
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")

        return results

    def process_batch_async(self, items: List[T], async_process_fn):
        """Process items in batches asynchronously.

        Note: Returns async generator for streaming results.

        Args:
            items: Items to process
            async_process_fn: Async function to process batch

        Returns:
            Async generator yielding batch results
        """
        async def _async_batches():
            for i in range(0, len(items), self.batch_size):
                batch = items[i:i + self.batch_size]
                try:
                    batch_results = await async_process_fn(batch)
                    yield batch_results
                except Exception as e:
                    logger.error(f"Async batch processing failed: {e}")

        return _async_batches()


class ImageProcessingOptimizer:
    """Optimize image processing through caching and lazy evaluation."""

    def __init__(self):
        """Initialize image processing optimizer."""
        self.intermediate_cache = {}
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "lazy_evaluated": 0,
        }

    def cache_intermediate_step(self, step_name: str, image_id: str, data: Any) -> None:
        """Cache intermediate processing results.

        Args:
            step_name: Name of processing step
            image_id: Image identifier
            data: Intermediate result to cache
        """
        cache_key = f"{step_name}:{image_id}"
        self.intermediate_cache[cache_key] = data

    def get_cached_intermediate(self, step_name: str, image_id: str) -> Optional[Any]:
        """Retrieve cached intermediate result.

        Args:
            step_name: Name of processing step
            image_id: Image identifier

        Returns:
            Cached data or None if not found
        """
        cache_key = f"{step_name}:{image_id}"
        if cache_key in self.intermediate_cache:
            self.stats["cache_hits"] += 1
            return self.intermediate_cache[cache_key]
        self.stats["cache_misses"] += 1
        return None

    def lazy_evaluate(self, compute_fn, cache_key: str, max_age_seconds: int = 3600):
        """Lazy evaluation with memoization.

        Args:
            compute_fn: Function to compute value
            cache_key: Key for caching result
            max_age_seconds: Maximum age of cached result

        Returns:
            Computed or cached value
        """
        if cache_key in self.intermediate_cache:
            self.stats["cache_hits"] += 1
            return self.intermediate_cache[cache_key]

        result = compute_fn()
        self.intermediate_cache[cache_key] = result
        self.stats["lazy_evaluated"] += 1
        return result

    def clear_cache(self) -> None:
        """Clear intermediate cache."""
        self.intermediate_cache.clear()

    def get_stats(self) -> dict:
        """Get image processing statistics."""
        return self.stats.copy()

"""Unit tests for optimization service.

Tests pagination, cursor pagination, batch queries, prefetching,
and image processing optimization.
"""

import pytest
from src.services.optimization_service import (
    PaginationService,
    PaginationParams,
    PaginatedResult,
    QueryOptimizer,
    BatchProcessor,
    ImageProcessingOptimizer,
)


class TestPaginationParams:
    """Test pagination parameter validation."""

    def test_valid_pagination_params(self):
        """Test valid pagination parameters."""
        params = PaginationParams(offset=0, limit=50)
        assert params.offset == 0
        assert params.limit == 50

    def test_invalid_negative_offset(self):
        """Test negative offset raises error."""
        with pytest.raises(ValueError):
            PaginationParams(offset=-1, limit=50)

    def test_invalid_limit_too_small(self):
        """Test limit < 1 raises error."""
        with pytest.raises(ValueError):
            PaginationParams(offset=0, limit=0)

    def test_invalid_limit_too_large(self):
        """Test limit > 1000 raises error."""
        with pytest.raises(ValueError):
            PaginationParams(offset=0, limit=1001)

    def test_invalid_sort_order(self):
        """Test invalid sort order raises error."""
        with pytest.raises(ValueError):
            PaginationParams(offset=0, limit=50, sort_order="invalid")


class TestPagination:
    """Test basic pagination."""

    def test_paginate_simple(self):
        """Test simple pagination."""
        items = list(range(100))
        result = PaginationService.paginate(items, offset=0, limit=10)

        assert len(result.items) == 10
        assert result.items == list(range(10))
        assert result.offset == 0
        assert result.limit == 10
        assert result.total == 100
        assert result.has_next is True
        assert result.has_previous is False

    def test_paginate_middle_page(self):
        """Test pagination in the middle."""
        items = list(range(100))
        result = PaginationService.paginate(items, offset=50, limit=10)

        assert result.items == list(range(50, 60))
        assert result.has_next is True
        assert result.has_previous is True

    def test_paginate_last_page(self):
        """Test pagination on last page."""
        items = list(range(100))
        result = PaginationService.paginate(items, offset=90, limit=10)

        assert result.items == list(range(90, 100))
        assert result.has_next is False
        assert result.has_previous is True

    def test_paginate_empty_list(self):
        """Test pagination of empty list."""
        result = PaginationService.paginate([], offset=0, limit=10)

        assert len(result.items) == 0
        assert result.total == 0
        assert result.has_next is False
        # Empty list has 0 pages (ceil(0/10) = 0)
        assert result.page_count == 0

    def test_paginate_page_count(self):
        """Test page count calculation."""
        items = list(range(100))

        result = PaginationService.paginate(items, offset=0, limit=10)
        assert result.page_count == 10

        result = PaginationService.paginate(items, offset=0, limit=33)
        assert result.page_count == 4

    def test_paginate_current_page(self):
        """Test current page calculation."""
        items = list(range(100))

        result = PaginationService.paginate(items, offset=0, limit=10)
        assert result.current_page == 1

        result = PaginationService.paginate(items, offset=50, limit=10)
        assert result.current_page == 6

    def test_paginate_with_sort(self):
        """Test pagination with sorting."""
        items = [{"id": 3}, {"id": 1}, {"id": 2}]
        result = PaginationService.paginate(
            items,
            offset=0,
            limit=10,
            sort_key=lambda x: x["id"]
        )

        assert result.items[0]["id"] == 1
        assert result.items[1]["id"] == 2
        assert result.items[2]["id"] == 3

    def test_paginate_with_reverse_sort(self):
        """Test pagination with reverse sort."""
        items = [{"id": 1}, {"id": 3}, {"id": 2}]
        result = PaginationService.paginate(
            items,
            offset=0,
            limit=10,
            sort_key=lambda x: x["id"],
            reverse=True
        )

        assert result.items[0]["id"] == 3
        assert result.items[1]["id"] == 2
        assert result.items[2]["id"] == 1

    def test_paginate_page_range(self):
        """Test pages property."""
        items = list(range(100))
        result = PaginationService.paginate(items, offset=0, limit=10)

        pages = list(result.pages)
        assert pages == list(range(1, 11))


class TestCursorPagination:
    """Test cursor-based pagination."""

    def test_cursor_paginate_first_page(self):
        """Test cursor pagination first page."""
        items = list(range(100))
        result, next_cursor = PaginationService.cursor_paginate(
            items,
            cursor=None,
            limit=10
        )

        assert result == list(range(10))
        assert next_cursor == "10"

    def test_cursor_paginate_next_page(self):
        """Test cursor pagination with cursor."""
        items = list(range(100))
        result, next_cursor = PaginationService.cursor_paginate(
            items,
            cursor="10",
            limit=10
        )

        assert result == list(range(10, 20))
        assert next_cursor == "20"

    def test_cursor_paginate_last_page(self):
        """Test cursor pagination last page."""
        items = list(range(100))
        result, next_cursor = PaginationService.cursor_paginate(
            items,
            cursor="90",
            limit=10
        )

        assert result == list(range(90, 100))
        assert next_cursor is None

    def test_cursor_paginate_invalid_cursor(self):
        """Test cursor pagination with invalid cursor."""
        items = list(range(100))
        result, next_cursor = PaginationService.cursor_paginate(
            items,
            cursor="invalid",
            limit=10
        )

        assert result == list(range(10))


class TestBatchQuery:
    """Test batch query optimization."""

    def test_batch_query_single_batch(self):
        """Test batch query with single batch."""
        ids = [1, 2, 3, 4, 5]

        def fetch_fn(batch):
            return {id: f"item_{id}" for id in batch}

        result = QueryOptimizer().batch_query(ids, fetch_fn, batch_size=10)

        assert result == {
            1: "item_1",
            2: "item_2",
            3: "item_3",
            4: "item_4",
            5: "item_5",
        }

    def test_batch_query_multiple_batches(self):
        """Test batch query with multiple batches."""
        ids = list(range(1, 26))  # 25 items
        optimizer = QueryOptimizer()

        def fetch_fn(batch):
            return {id: f"item_{id}" for id in batch}

        result = optimizer.batch_query(ids, fetch_fn, batch_size=10)

        assert len(result) == 25
        assert optimizer.stats["batch_queries"] == 3  # 10 + 10 + 5

    def test_batch_query_with_error(self):
        """Test batch query with fetch error."""
        ids = [1, 2, 3, 4]

        def fetch_fn(batch):
            if 2 in batch:
                raise ValueError("Fetch error")
            return {id: f"item_{id}" for id in batch}

        optimizer = QueryOptimizer()
        result = optimizer.batch_query(ids, fetch_fn, batch_size=2)

        # Should continue despite error - batch [1,2] fails, [3,4] succeeds
        assert 3 in result
        assert 4 in result


class TestPrefetch:
    """Test prefetch optimization."""

    def test_prefetch_related_items(self):
        """Test prefetching related items."""
        optimizer = QueryOptimizer()

        def fetch_fn(ids):
            return {id: [f"related_{id}_{i}" for i in range(3)] for id in ids}

        result = optimizer.prefetch([1, 2, 3], fetch_fn)

        assert 1 in result
        assert len(result[1]) == 3


class TestBatchProcessor:
    """Test batch processing."""

    def test_process_batch(self):
        """Test batch processing."""
        processor = BatchProcessor(batch_size=5)
        items = list(range(20))

        def process_fn(batch):
            return [x * 2 for x in batch]

        result = processor.process_batch(items, process_fn)

        assert len(result) == 20
        assert result[0] == 0
        assert result[19] == 38

    def test_process_batch_uneven(self):
        """Test batch processing with uneven batches."""
        processor = BatchProcessor(batch_size=3)
        items = list(range(10))

        def process_fn(batch):
            return [x * 2 for x in batch]

        result = processor.process_batch(items, process_fn)

        assert len(result) == 10  # 3 + 3 + 3 + 1

    def test_process_batch_with_error(self):
        """Test batch processing with errors."""
        processor = BatchProcessor(batch_size=5)
        items = list(range(20))

        def process_fn(batch):
            if 5 in batch:
                raise ValueError("Processing error")
            return [x * 2 for x in batch]

        result = processor.process_batch(items, process_fn)

        # Should continue despite error - batches [5-9] fails, others succeed
        assert len(result) >= 12  # At least 3 batches of 5 and the partial batch


class TestImageProcessingOptimization:
    """Test image processing optimization."""

    def test_cache_intermediate_step(self):
        """Test caching intermediate processing results."""
        optimizer = ImageProcessingOptimizer()

        data = {"processed": "result"}
        optimizer.cache_intermediate_step("edge_detection", "img_1", data)

        assert optimizer.get_cached_intermediate("edge_detection", "img_1") == data

    def test_cache_hit_miss_tracking(self):
        """Test cache hit/miss tracking."""
        optimizer = ImageProcessingOptimizer()

        # Cache miss
        assert optimizer.get_cached_intermediate("edge_detection", "img_1") is None
        assert optimizer.stats["cache_misses"] == 1

        # Cache hit
        optimizer.cache_intermediate_step("edge_detection", "img_1", {"data": "value"})
        assert optimizer.get_cached_intermediate("edge_detection", "img_1") is not None
        assert optimizer.stats["cache_hits"] == 1

    def test_lazy_evaluation(self):
        """Test lazy evaluation with caching."""
        optimizer = ImageProcessingOptimizer()

        call_count = 0

        def compute_fn():
            nonlocal call_count
            call_count += 1
            return {"result": "computed"}

        # First call evaluates
        result1 = optimizer.lazy_evaluate(compute_fn, "key1")
        assert call_count == 1
        assert optimizer.stats["lazy_evaluated"] == 1

        # Second call uses cache
        result2 = optimizer.lazy_evaluate(compute_fn, "key1")
        assert call_count == 1  # Not called again
        assert result1 == result2
        assert optimizer.stats["cache_hits"] == 1

    def test_multiple_intermediate_steps(self):
        """Test caching multiple processing steps."""
        optimizer = ImageProcessingOptimizer()

        img_id = "img_1"
        steps = ["edge_detection", "corner_detection", "feature_extraction"]

        for step in steps:
            optimizer.cache_intermediate_step(step, img_id, {f"{step}": "result"})

        for step in steps:
            result = optimizer.get_cached_intermediate(step, img_id)
            assert result is not None
            assert f"{step}" in result

    def test_clear_cache(self):
        """Test clearing image processing cache."""
        optimizer = ImageProcessingOptimizer()

        optimizer.cache_intermediate_step("step1", "img_1", {"data": "value"})
        assert optimizer.get_cached_intermediate("step1", "img_1") is not None

        optimizer.clear_cache()
        assert optimizer.get_cached_intermediate("step1", "img_1") is None

    def test_get_stats(self):
        """Test image processing statistics."""
        optimizer = ImageProcessingOptimizer()

        optimizer.cache_intermediate_step("step1", "img_1", {"data": "value"})
        optimizer.get_cached_intermediate("step1", "img_1")  # Hit
        optimizer.get_cached_intermediate("step2", "img_2")  # Miss

        stats = optimizer.get_stats()
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert stats["lazy_evaluated"] == 0


@pytest.mark.parametrize("offset,limit,expected_page", [
    (0, 10, 1),
    (10, 10, 2),
    (50, 10, 6),
    (100, 10, 11),
])
def test_pagination_current_page_calculation(offset, limit, expected_page):
    """Test current page calculation with various offsets."""
    items = list(range(200))
    result = PaginationService.paginate(items, offset=offset, limit=limit)
    assert result.current_page == expected_page


@pytest.mark.parametrize("total,limit,expected_pages", [
    (100, 10, 10),
    (100, 25, 4),
    (100, 50, 2),
    (100, 100, 1),
    (100, 101, 1),
])
def test_pagination_page_count_calculation(total, limit, expected_pages):
    """Test page count calculation with various sizes."""
    items = list(range(total))
    result = PaginationService.paginate(items, offset=0, limit=limit)
    assert result.page_count == expected_pages

#!/usr/bin/env bash
# Load test runner for Detection API
# Usage: ./tests/load/run_load_test.sh [HOST] [USERS] [SPAWN_RATE] [DURATION]
#
# Performance Targets:
#   P50 < 100ms | P95 < 300ms | P99 < 500ms | Throughput > 1000 req/sec | Error < 0.1%

set -euo pipefail

HOST="${1:-http://localhost:8000}"
USERS="${2:-200}"
SPAWN_RATE="${3:-20}"
DURATION="${4:-5m}"
RESULTS_DIR="results/load_test_$(date +%Y%m%d_%H%M%S)"

echo "========================================"
echo "  Detection API Load Test"
echo "========================================"
echo "  Host:        $HOST"
echo "  Users:       $USERS"
echo "  Spawn rate:  $SPAWN_RATE/sec"
echo "  Duration:    $DURATION"
echo "  Results:     $RESULTS_DIR"
echo "========================================"

mkdir -p "$RESULTS_DIR"

locust \
    -f tests/load/locustfile.py \
    --host "$HOST" \
    --headless \
    -u "$USERS" \
    -r "$SPAWN_RATE" \
    --run-time "$DURATION" \
    --csv "$RESULTS_DIR/results" \
    --html "$RESULTS_DIR/report.html" \
    --logfile "$RESULTS_DIR/locust.log" \
    --print-stats \
    --only-summary 2>&1 | tee "$RESULTS_DIR/console_output.txt"

echo ""
echo "Results saved to: $RESULTS_DIR/"
echo "  - report.html    (interactive HTML report)"
echo "  - results_stats.csv (request statistics)"
echo "  - results_failures.csv (failure details)"
echo "  - console_output.txt (SLO compliance report)"

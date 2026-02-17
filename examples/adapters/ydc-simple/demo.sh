#!/bin/bash
# Demo: Run YDC Adapter + Mock YDC Server + Geolocation-Engine2

set -e

PROJECT_ROOT="/workspaces/geolocation-engine2"
DEMO_DIR="$PROJECT_ROOT/examples/adapters/ydc-simple"

echo "🚀 Starting YDC ↔ Geolocation-Engine2 Demo"
echo "============================================"
echo ""

# Check if dependencies are installed
echo "📦 Checking dependencies..."
cd "$PROJECT_ROOT"
pip install -q websockets httpx fastapi uvicorn 2>/dev/null || true

echo "✅ Dependencies ready"
echo ""

# Start geolocation-engine2 API
echo "1️⃣  Starting Geolocation-Engine2 API on http://localhost:8000"
echo "   (runs in background...)"
cd "$PROJECT_ROOT"
nohup python -m uvicorn src.main:app --host localhost --port 8000 --log-level error > /tmp/geolocation.log 2>&1 &
GEOLOCATION_PID=$!
echo "   PID: $GEOLOCATION_PID"
sleep 2

# Check if API is running
if ! curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "❌ Failed to start Geolocation-Engine2"
    kill $GEOLOCATION_PID 2>/dev/null || true
    exit 1
fi
echo "✅ Geolocation-Engine2 API is running"
echo ""

# Start mock YDC server
echo "2️⃣  Starting Mock YDC Server on ws://localhost:5173"
echo "   (runs in background...)"
cd "$DEMO_DIR"
nohup python mock_ydc_server.py > /tmp/mock_ydc.log 2>&1 &
MOCK_YDC_PID=$!
echo "   PID: $MOCK_YDC_PID"
sleep 1
echo "✅ Mock YDC Server is running"
echo ""

# Start adapter
echo "3️⃣  Starting YDC Adapter"
echo "   (in foreground - you'll see detections...)"
echo ""
echo "============================================"
cd "$DEMO_DIR"
python adapter.py

# Cleanup on exit
trap "kill $GEOLOCATION_PID $MOCK_YDC_PID 2>/dev/null; echo ''; echo 'Demo stopped.'" EXIT

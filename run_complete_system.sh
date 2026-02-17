#!/bin/bash
# Complete System Startup Script
# Starts: Geolocation Engine API + Web Dashboard with Real Adapters

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     🌍 GEOLOCATION ENGINE 2 - COMPLETE SYSTEM STARTUP         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                    SHUTTING DOWN SYSTEM                        ║"
    echo "╚════════════════════════════════════════════════════════════════╝"

    echo "⏹️  Stopping all services..."
    pkill -f "uvicorn" || true
    wait
    echo "✅ All services stopped"
}

trap cleanup EXIT

# Start Geolocation Engine API
echo "1️⃣  Starting Geolocation Engine API (port 8000)..."
python -m uvicorn src.main:app --host localhost --port 8000 > /tmp/geolocation-api.log 2>&1 &
API_PID=$!
echo "   PID: $API_PID"
sleep 2

# Check if API started
if ! kill -0 $API_PID 2>/dev/null; then
    echo "❌ Failed to start Geolocation Engine API"
    cat /tmp/geolocation-api.log
    exit 1
fi
echo "   ✅ API running"
echo ""

# Start Web Dashboard
echo "2️⃣  Starting Web Dashboard (port 8888)..."
cd web_dashboard
python app.py > /tmp/dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo "   PID: $DASHBOARD_PID"
sleep 2

# Check if Dashboard started
if ! kill -0 $DASHBOARD_PID 2>/dev/null; then
    echo "❌ Failed to start Web Dashboard"
    cat /tmp/dashboard.log
    exit 1
fi
echo "   ✅ Dashboard running"
echo ""

# Print access information
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                   ✨ SYSTEM READY ✨                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "🎯 ACCESS DASHBOARD:"
echo "   http://localhost:8888"
echo ""
echo "📊 WHAT'S RUNNING:"
echo "   ✅ Geolocation Engine API (port 8000)"
echo "   ✅ Web Dashboard (port 8888)"
echo "   ✅ Real Adapter Service (integrated)"
echo ""
echo "🚀 HOW TO USE:"
echo "   1. Open http://localhost:8888 in browser"
echo "   2. Select a landmark from dropdown"
echo "   3. Click 'Start Live Feed' button"
echo "   4. Watch detections appear in real-time"
echo "   5. See CoT XML generated automatically"
echo ""
echo "📡 AVAILABLE FEEDS:"
echo "   🗽 Times Square, NYC"
echo "   🗼 Eiffel Tower, Paris"
echo "   🗾 Tokyo Tower, Japan"
echo "   🗿 Christ the Redeemer, Rio"
echo "   🏛️  Big Ben, London"
echo ""
echo "💡 TIPS:"
echo "   • All adapters run in parallel"
echo "   • Real geolocation calculations happening"
echo "   • CoT XML ready for TAK/ATAK"
echo "   • Check logs: tail -f /tmp/geolocation-api.log"
echo ""
echo "Press Ctrl+C to stop all services..."
echo ""

# Keep running
wait

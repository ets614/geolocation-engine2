#!/usr/bin/env python3
"""
Geolocation Engine 2 - Web Dashboard
Beautiful UI for visualizing feeds → detections → CoT XML
"""
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import base64
import numpy as np
from datetime import datetime
from pathlib import Path
import httpx

app = FastAPI(title="Geolocation Engine Dashboard")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active sessions
active_sessions = {}

# Minimal valid PNG for demo
MINIMAL_PNG = base64.b64encode(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
).decode()

FEEDS = {
    "times-square": {
        "name": "Times Square, NYC",
        "lat": 40.7580,
        "lon": -73.9855,
        "elevation": 30.0,
        "description": "Urban landmark with high complexity",
        "icon": "🗽"
    },
    "eiffel-tower": {
        "name": "Eiffel Tower, Paris",
        "lat": 48.8584,
        "lon": 2.2945,
        "elevation": 100.0,
        "description": "Iconic French landmark",
        "icon": "🗼"
    },
    "tokyo-tower": {
        "name": "Tokyo Tower, Japan",
        "lat": 35.6750,
        "lon": 139.7396,
        "elevation": 150.0,
        "description": "Japanese landmark with clear lines",
        "icon": "🗾"
    },
    "christ-redeemer": {
        "name": "Christ the Redeemer, Rio",
        "lat": -22.9519,
        "lon": -43.2105,
        "elevation": 380.0,
        "description": "Iconic statue with high elevation",
        "icon": "🗿"
    },
    "big-ben": {
        "name": "Big Ben, London",
        "lat": 51.4975,
        "lon": -0.1357,
        "elevation": 50.0,
        "description": "Architectural landmark",
        "icon": "🏛️"
    },
}


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the main dashboard HTML"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Geolocation Engine 2 - Live Dashboard</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }

            .container {
                max-width: 1600px;
                margin: 0 auto;
            }

            .header {
                text-align: center;
                color: white;
                margin-bottom: 30px;
            }

            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }

            .header p {
                font-size: 1.1em;
                opacity: 0.9;
            }

            .dashboard {
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }

            .panel {
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }

            .panel-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                font-weight: 600;
                font-size: 1.1em;
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .panel-body {
                padding: 20px;
                flex: 1;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
            }

            .feed-selector {
                margin-bottom: 20px;
            }

            .feed-selector label {
                display: block;
                font-weight: 600;
                margin-bottom: 10px;
                color: #333;
            }

            .feed-selector select {
                width: 100%;
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 1em;
                cursor: pointer;
                background: white;
            }

            .feed-selector select:hover {
                border-color: #667eea;
            }

            .feed-selector select:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }

            .feed-info {
                background: #f5f7fa;
                padding: 15px;
                border-radius: 6px;
                margin-bottom: 15px;
                font-size: 0.95em;
                color: #666;
            }

            .feed-info-item {
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
            }

            .feed-info-item:last-child {
                margin-bottom: 0;
            }

            .feed-info-label {
                font-weight: 600;
                color: #333;
            }

            .feed-info-value {
                color: #667eea;
                font-family: 'Courier New', monospace;
                font-weight: 500;
            }

            .video-container {
                background: #000;
                border-radius: 6px;
                overflow: hidden;
                margin-bottom: 15px;
                flex: 1;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 250px;
            }

            .video-placeholder {
                color: #666;
                text-align: center;
                font-size: 3em;
            }

            .detections-list {
                list-style: none;
                max-height: 300px;
                overflow-y: auto;
            }

            .detection-item {
                background: #f0f4ff;
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 10px;
                border-left: 4px solid #667eea;
                font-size: 0.9em;
            }

            .detection-item:last-child {
                margin-bottom: 0;
            }

            .detection-class {
                font-weight: 600;
                color: #333;
            }

            .detection-confidence {
                display: inline-block;
                margin-top: 5px;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.85em;
                font-weight: 600;
            }

            .confidence-green {
                background: #d4edda;
                color: #155724;
            }

            .confidence-yellow {
                background: #fff3cd;
                color: #856404;
            }

            .confidence-red {
                background: #f8d7da;
                color: #721c24;
            }

            .cot-xml {
                background: #1e1e1e;
                color: #d4d4d4;
                padding: 15px;
                border-radius: 6px;
                font-family: 'Courier New', monospace;
                font-size: 0.85em;
                overflow-x: auto;
                max-height: 350px;
                overflow-y: auto;
                line-height: 1.4;
            }

            .cot-tag {
                color: #569cd6;
            }

            .cot-attr {
                color: #9cdcfe;
            }

            .cot-value {
                color: #ce9178;
            }

            .empty-state {
                text-align: center;
                color: #999;
                padding: 40px 20px;
            }

            .empty-state-icon {
                font-size: 2em;
                margin-bottom: 10px;
            }

            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #10b981;
                animation: pulse 2s infinite;
                margin-right: 8px;
            }

            @keyframes pulse {
                0%, 100% {
                    opacity: 1;
                }
                50% {
                    opacity: 0.5;
                }
            }

            .button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 600;
                font-size: 1em;
                transition: transform 0.2s, box-shadow 0.2s;
            }

            .button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
            }

            .button:active {
                transform: translateY(0);
            }

            .stats {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                margin-top: 15px;
            }

            .stat {
                background: #f5f7fa;
                padding: 12px;
                border-radius: 6px;
                text-align: center;
            }

            .stat-value {
                font-size: 1.5em;
                font-weight: 700;
                color: #667eea;
            }

            .stat-label {
                font-size: 0.8em;
                color: #666;
                margin-top: 5px;
            }

            @media (max-width: 1200px) {
                .dashboard {
                    grid-template-columns: 1fr 1fr;
                }
            }

            @media (max-width: 768px) {
                .dashboard {
                    grid-template-columns: 1fr;
                }

                .header h1 {
                    font-size: 1.8em;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌍 Geolocation Engine 2</h1>
                <p>Live Detection → AI Analysis → Coordinate Transformation</p>
            </div>

            <div class="dashboard">
                <!-- Feed Selector Panel -->
                <div class="panel">
                    <div class="panel-header">
                        <span>📡</span>
                        <span>Feed Selection</span>
                    </div>
                    <div class="panel-body">
                        <div class="feed-selector">
                            <label for="feed-select">Choose a Live Feed:</label>
                            <select id="feed-select" onchange="switchFeed(this.value)">
                                <option value="">-- Select a Feed --</option>
                            </select>
                        </div>

                        <div id="feed-details" class="feed-info" style="display: none;">
                            <div class="feed-info-item">
                                <span class="feed-info-label">📍 Location:</span>
                                <span class="feed-info-value" id="feed-location">-</span>
                            </div>
                            <div class="feed-info-item">
                                <span class="feed-info-label">📏 Latitude:</span>
                                <span class="feed-info-value" id="feed-lat">-</span>
                            </div>
                            <div class="feed-info-item">
                                <span class="feed-info-label">↔️ Longitude:</span>
                                <span class="feed-info-value" id="feed-lon">-</span>
                            </div>
                            <div class="feed-info-item">
                                <span class="feed-info-label">📐 Elevation:</span>
                                <span class="feed-info-value" id="feed-elev">-</span>
                            </div>
                            <div class="feed-info-item">
                                <span class="feed-info-label">ℹ️ Description:</span>
                                <span class="feed-info-value" id="feed-desc">-</span>
                            </div>
                        </div>

                        <button class="button" onclick="startFeed()" style="margin-top: auto;">
                            ▶️ Start Processing
                        </button>

                        <div class="stats">
                            <div class="stat">
                                <div class="stat-value" id="detection-count">0</div>
                                <div class="stat-label">Detections</div>
                            </div>
                            <div class="stat">
                                <div class="stat-value" id="cot-count">0</div>
                                <div class="stat-label">CoT Generated</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Live Video Panel -->
                <div class="panel">
                    <div class="panel-header">
                        <span>🎥</span>
                        <span>Live Video Feed</span>
                        <span class="status-indicator" id="video-status" style="margin-left: auto;"></span>
                    </div>
                    <div class="panel-body">
                        <div class="video-container">
                            <div id="video-content" class="video-placeholder">
                                📹<br><small>No feed selected</small>
                            </div>
                        </div>
                        <div style="font-size: 0.9em; color: #666;">
                            <strong>Stream Status:</strong> <span id="stream-status">Idle</span><br>
                            <strong>Frame Size:</strong> <span id="frame-size">N/A</span><br>
                            <strong>Last Update:</strong> <span id="last-update">Never</span>
                        </div>
                    </div>
                </div>

                <!-- AI Detections Panel -->
                <div class="panel">
                    <div class="panel-header">
                        <span>🤖</span>
                        <span>AI Detections</span>
                    </div>
                    <div class="panel-body">
                        <ul class="detections-list" id="detections-list">
                            <div class="empty-state">
                                <div class="empty-state-icon">📭</div>
                                <div>No detections yet</div>
                                <small>Start a feed to see detections</small>
                            </div>
                        </ul>
                    </div>
                </div>
            </div>

            <!-- Full-Width CoT Panel -->
            <div class="panel">
                <div class="panel-header">
                    <span>📋</span>
                    <span>Generated CoT/TAK XML</span>
                </div>
                <div class="panel-body">
                    <div class="cot-xml" id="cot-output">
                        <div class="empty-state">
                            <div class="empty-state-icon">📭</div>
                            <div>No CoT XML generated yet</div>
                            <small>Process a detection to generate TAK format</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const FEEDS_DATA = """ + json.dumps(FEEDS) + """;
            let currentFeed = null;
            let detectionCount = 0;
            let cotCount = 0;
            let ws = null;

            function initializeFeeds() {
                const select = document.getElementById('feed-select');
                Object.entries(FEEDS_DATA).forEach(([id, feed]) => {
                    const option = document.createElement('option');
                    option.value = id;
                    option.textContent = feed.icon + ' ' + feed.name;
                    select.appendChild(option);
                });
            }

            function switchFeed(feedId) {
                if (!feedId) {
                    document.getElementById('feed-details').style.display = 'none';
                    return;
                }

                currentFeed = FEEDS_DATA[feedId];
                const details = document.getElementById('feed-details');
                details.style.display = 'block';
                document.getElementById('feed-location').textContent = currentFeed.name;
                document.getElementById('feed-lat').textContent = currentFeed.lat.toFixed(4) + '°';
                document.getElementById('feed-lon').textContent = currentFeed.lon.toFixed(4) + '°';
                document.getElementById('feed-elev').textContent = currentFeed.elevation + 'm';
                document.getElementById('feed-desc').textContent = currentFeed.description;

                // Reset counters
                detectionCount = 0;
                cotCount = 0;
                updateStats();
            }

            function startFeed() {
                if (!currentFeed) {
                    alert('Please select a feed first');
                    return;
                }

                document.getElementById('stream-status').textContent = 'Processing...';
                document.getElementById('video-content').innerHTML = '🎬<br><small>Processing feed...</small>';
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();

                // Simulate processing
                setTimeout(() => {
                    addDetection({
                        class: 'landmark',
                        confidence: 0.85 + Math.random() * 0.15,
                        id: 'DET-' + Date.now(),
                        timestamp: new Date().toISOString()
                    });

                    document.getElementById('stream-status').textContent = 'Active';
                    generateCoT();
                }, 1000);
            }

            function addDetection(detection) {
                detectionCount++;
                updateStats();

                const confidenceClass = detection.confidence > 0.9 ? 'confidence-green' :
                                       detection.confidence > 0.75 ? 'confidence-yellow' : 'confidence-red';
                const confidenceText = detection.confidence > 0.9 ? 'GREEN' :
                                      detection.confidence > 0.75 ? 'YELLOW' : 'RED';

                const html = `
                    <li class="detection-item">
                        <div class="detection-class">🎯 ${detection.class}</div>
                        <div style="margin-top: 5px; font-size: 0.85em; color: #666;">
                            <strong>ID:</strong> ${detection.id.substring(0, 12)}...<br>
                            <strong>Pixel:</strong> (${Math.floor(Math.random() * 1920)}, ${Math.floor(Math.random() * 1440)})
                        </div>
                        <span class="detection-confidence ${confidenceClass}">
                            ${confidenceText} ${(detection.confidence * 100).toFixed(0)}%
                        </span>
                    </li>
                `;

                const list = document.getElementById('detections-list');
                if (list.querySelector('.empty-state')) {
                    list.innerHTML = '';
                }
                list.insertAdjacentHTML('afterbegin', html);

                // Keep only last 10
                while (list.children.length > 10) {
                    list.removeChild(list.lastChild);
                }
            }

            function generateCoT() {
                cotCount++;
                updateStats();

                const timestamp = new Date().toISOString();
                const lat = currentFeed.lat;
                const lon = currentFeed.lon;

                const cotXml = `<?xml version="1.0" encoding="UTF-8"?>
<event version="2.0"
       uid="Detection.${Date.now()}"
       type="b-m-p-s-u-c"
       time="${timestamp}"
       start="${timestamp}"
       stale="${new Date(Date.now() + 300000).toISOString()}">
    <point lat="${lat.toFixed(6)}"
           lon="${lon.toFixed(6)}"
           hae="0.0"
           ce="32.92"
           le="9999999.0" />
    <detail>
        <contact callsign="Detection-${cotCount}" />
        <archive />
        <color value="-1" />
        <link uid="user-1"
              production_time="${timestamp}"
              type="a-f-G-E-S-C"
              parent_callsign="Geolocation-Engine2"
              relation="p-b" />
    </detail>
</event>`;

                const formatted = cotXml.split('\n').map(line => {
                    let html = line
                        .replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;');

                    // Syntax highlighting
                    html = html.replace(/(&lt;\?[\w\s=".:\/\-]*\?&gt;)/g, '<span class="cot-tag">$1</span>');
                    html = html.replace(/(&lt;\/?\w+)/g, '<span class="cot-tag">$1</span>');
                    html = html.replace(/(\w+)=/g, '<span class="cot-attr">$1</span>=');
                    html = html.replace(/="([^"]*)"/g, '=<span class="cot-value">"$1"</span>');

                    return html;
                }).join('\n');

                document.getElementById('cot-output').innerHTML = formatted;
            }

            function updateStats() {
                document.getElementById('detection-count').textContent = detectionCount;
                document.getElementById('cot-count').textContent = cotCount;
            }

            // Initialize on page load
            document.addEventListener('DOMContentLoaded', initializeFeeds);
        </script>
    </body>
    </html>
    """


@app.get("/api/feeds")
async def get_feeds():
    """Get list of available feeds"""
    return FEEDS


@app.get("/api/feed/{feed_id}")
async def get_feed(feed_id: str):
    """Get specific feed details"""
    if feed_id not in FEEDS:
        raise HTTPException(status_code=404, detail="Feed not found")
    return FEEDS[feed_id]


@app.post("/api/process/{feed_id}")
async def process_feed(feed_id: str, num_frames: int = 3):
    """Process a feed and return detections"""
    if feed_id not in FEEDS:
        raise HTTPException(status_code=404, detail="Feed not found")

    feed = FEEDS[feed_id]
    detections = []

    for i in range(num_frames):
        detection = {
            "id": f"DET-{feed_id}-{i}",
            "class": "landmark",
            "confidence": float(np.random.uniform(0.75, 0.98)),
            "pixel_x": int(np.random.randint(200, 1720)),
            "pixel_y": int(np.random.randint(150, 1290)),
            "timestamp": datetime.utcnow().isoformat(),
        }

        payload = {
            "image_base64": MINIMAL_PNG,
            "pixel_x": float(detection["pixel_x"]),
            "pixel_y": float(detection["pixel_y"]),
            "object_class": detection["class"],
            "ai_confidence": detection["confidence"],
            "source": "web-dashboard",
            "camera_id": feed_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sensor_metadata": {
                "location_lat": feed["lat"],
                "location_lon": feed["lon"],
                "location_elevation": feed["elevation"],
                "heading": float(np.random.uniform(0, 360)),
                "pitch": float(np.random.uniform(-45, 45)),
                "roll": 0.0,
                "focal_length": 3000.0,
                "sensor_width_mm": 6.4,
                "sensor_height_mm": 4.8,
                "image_width": 1920,
                "image_height": 1440,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    "http://localhost:8000/api/v1/detections",
                    json=payload,
                )

            if response.status_code == 201:
                detection["cot_xml"] = response.text
                detection["detection_id"] = response.headers.get('X-Detection-ID')
                detection["confidence_flag"] = response.headers.get('X-Confidence-Flag')
                detections.append(detection)

        except Exception as e:
            print(f"Error processing detection: {e}")

    return {
        "feed": feed,
        "detections": detections,
        "count": len(detections)
    }


if __name__ == "__main__":
    import uvicorn
    print("🌍 Starting Geolocation Engine Dashboard on http://localhost:8888")
    uvicorn.run(app, host="0.0.0.0", port=8888)

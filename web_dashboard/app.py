#!/usr/bin/env python3
"""
Geolocation Engine 2 - Web Dashboard
Beautiful UI for visualizing feeds → detections → CoT XML
"""
from fastapi import FastAPI, WebSocket, HTTPException, Body
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
import base64
import numpy as np
from datetime import datetime
from pathlib import Path
import httpx
from worker import WorkerManager

# Import AI adapters
try:
    from adapters.huggingface import HuggingFaceDetector
except (ImportError, ValueError):
    HuggingFaceDetector = None
try:
    from adapters.roboflow import RoboflowDetector
except (ImportError, ValueError):
    RoboflowDetector = None

app = FastAPI(title="Geolocation Engine Dashboard")

# Initialize worker manager
worker_manager = WorkerManager(geolocation_url="http://localhost:8000")

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


# Request models
class SimulatorRequest(BaseModel):
    latitude: float
    longitude: float
    elevation: float
    heading: float = 0.0


# Minimal valid PNG for demo
MINIMAL_PNG = base64.b64encode(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
).decode()

FEEDS = {
    # ===== REAL AI DETECTION FEEDS =====
    "roboflow-coco": {
        "name": "🤖 Roboflow COCO (Real AI)",
        "lat": 40.7128,
        "lon": -74.0060,
        "elevation": 10.0,
        "description": "Real-time AI object detection (80 classes: people, vehicles, animals, etc.)",
        "icon": "🤖",
        "category": "Real AI",
        "requires_api_key": "ROBOFLOW_API_KEY"
    },
    "roboflow-logos": {
        "name": "🏷️ Roboflow Logos (Real AI)",
        "lat": 40.7128,
        "lon": -74.0060,
        "elevation": 10.0,
        "description": "Real-time logo and brand detection",
        "icon": "🏷️",
        "category": "Real AI",
        "requires_api_key": "ROBOFLOW_API_KEY"
    },
    "huggingface-detr": {
        "name": "🤗 HuggingFace DETR (Real AI)",
        "lat": 40.7128,
        "lon": -74.0060,
        "elevation": 10.0,
        "description": "High-accuracy object detection from HuggingFace (30,000 free inferences/month)",
        "icon": "🤗",
        "category": "Real AI",
        "requires_api_key": "HF_API_KEY"
    },
    "huggingface-yolos": {
        "name": "⚡ HuggingFace YOLOS (Fast AI)",
        "lat": 40.7128,
        "lon": -74.0060,
        "elevation": 10.0,
        "description": "Fast real-time detection from HuggingFace",
        "icon": "⚡",
        "category": "Real AI",
        "requires_api_key": "HF_API_KEY"
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
                grid-template-columns: 1fr 1fr 1fr 1fr;
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
                max-height: 500px;
                overflow-y: auto;
                line-height: 1.5;
                white-space: pre-wrap;
                word-wrap: break-word;
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

            .json-key {
                color: #9cdcfe;
                font-weight: 600;
            }

            .json-string {
                color: #ce9178;
            }

            .json-number {
                color: #b5cea8;
            }

            .json-boolean {
                color: #569cd6;
            }

            .json-null {
                color: #569cd6;
                font-style: italic;
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

            .input-group {
                margin-bottom: 15px;
            }

            .input-group label {
                display: block;
                font-weight: 600;
                margin-bottom: 6px;
                color: #333;
                font-size: 0.9em;
            }

            .input-group input {
                width: 100%;
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 0.95em;
                box-sizing: border-box;
            }

            .input-group input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }

            .presets {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 8px;
                margin-bottom: 15px;
            }

            .preset-btn {
                padding: 8px 12px;
                background: #f0f4ff;
                border: 2px solid #e0e6ff;
                border-radius: 6px;
                cursor: pointer;
                font-size: 0.85em;
                font-weight: 500;
                color: #667eea;
                transition: all 0.2s;
            }

            .preset-btn:hover {
                background: #e0e6ff;
                border-color: #667eea;
                transform: translateY(-1px);
            }

            @media (max-width: 1400px) {
                .dashboard {
                    grid-template-columns: 1fr 1fr;
                }
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

                        <div style="display: flex; gap: 10px; margin-top: auto;">
                            <button class="button" onclick="startFeed()" style="flex: 1;">
                                ▶️ Start Live Feed
                            </button>
                            <button class="button" onclick="stopFeed()" style="flex: 1; background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);">
                                ⏹️ Stop
                            </button>
                        </div>

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
                            <canvas id="video-canvas" style="display: none; max-width: 100%;"></canvas>
                        </div>
                        <div style="font-size: 0.9em; color: #666; margin-top: 15px;">
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                                <div style="background: #f5f7fa; padding: 10px; border-radius: 6px;">
                                    <strong style="display: block; color: #333; margin-bottom: 5px;">Frames:</strong>
                                    <span id="frame-count" style="font-size: 1.3em; color: #667eea; font-weight: bold;">0</span>
                                </div>
                                <div style="background: #f5f7fa; padding: 10px; border-radius: 6px;">
                                    <strong style="display: block; color: #333; margin-bottom: 5px;">Rate:</strong>
                                    <span id="frame-rate" style="font-size: 1.3em; color: #667eea; font-weight: bold;">0/s</span>
                                </div>
                            </div>
                            <strong>Status:</strong> <span id="stream-status">Idle</span><br>
                            <strong>Resolution:</strong> <span id="frame-size">1920×1440</span><br>
                            <strong>Updated:</strong> <span id="last-update">Never</span>
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

                <!-- Camera Simulator Panel -->
                <div class="panel">
                    <div class="panel-header">
                        <span>🎥</span>
                        <span>Camera Simulator</span>
                    </div>
                    <div class="panel-body">
                        <div style="margin-bottom: 15px;">
                            <label style="font-weight: 600; color: #333; font-size: 0.9em; display: block; margin-bottom: 8px;">Quick Presets:</label>
                            <div class="presets">
                                <button class="preset-btn" onclick="setPreset({lat: 40.7580, lon: -73.9855, elev: 10, name: 'Times Square'})">📍 Times Square</button>
                                <button class="preset-btn" onclick="setPreset({lat: 48.8584, lon: 2.2945, elev: 100, name: 'Eiffel Tower'})">🗼 Eiffel Tower</button>
                                <button class="preset-btn" onclick="setPreset({lat: 35.6750, lon: 139.7396, elev: 150, name: 'Tokyo Tower'})">🗾 Tokyo Tower</button>
                                <button class="preset-btn" onclick="setPreset({lat: 22.9519, lon: -43.2105, elev: 700, name: 'Christ Redeemer'})">✝️ Christ Redeemer</button>
                            </div>
                        </div>

                        <div class="input-group">
                            <label for="sim-lat">📏 Latitude:</label>
                            <input type="number" id="sim-lat" placeholder="40.7128" step="0.0001" />
                        </div>

                        <div class="input-group">
                            <label for="sim-lon">↔️ Longitude:</label>
                            <input type="number" id="sim-lon" placeholder="-74.0060" step="0.0001" />
                        </div>

                        <div class="input-group">
                            <label for="sim-elev">📐 Elevation (m):</label>
                            <input type="number" id="sim-elev" placeholder="10" step="1" />
                        </div>

                        <div class="input-group">
                            <label for="sim-heading">🧭 Heading (°):</label>
                            <input type="number" id="sim-heading" placeholder="0" step="1" min="0" max="360" />
                        </div>

                        <button class="button" onclick="submitSimulation()" style="width: 100%; margin-top: auto;">
                            ▶️ Simulate Detection
                        </button>

                        <div style="margin-top: 15px; font-size: 0.85em; color: #666; background: #f5f7fa; padding: 10px; border-radius: 6px; border-left: 3px solid #667eea;">
                            <strong style="color: #333;">Tip:</strong> Uses simulated camera at the specified location. Submit to test geolocation pipeline.
                        </div>
                    </div>
                </div>
            </div>

            <!-- Full-Width Detection Object Panel -->
            <div class="panel">
                <div class="panel-header">
                    <span>🔍</span>
                    <span>Raw Detection Object (JSON)</span>
                </div>
                <div class="panel-body">
                    <div class="cot-xml" id="detection-object-output">
                        <div class="empty-state">
                            <div class="empty-state-icon">📭</div>
                            <div>No detection object received yet</div>
                            <small>Start a feed to see raw detection data</small>
                        </div>
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

            let currentAdapterId = null;
            let eventSource = null;
            let frameCount = 0;
            let frameTimestamps = [];

            function updateFrameRate() {
                const now = Date.now();
                frameTimestamps = frameTimestamps.filter(t => now - t < 1000);
                const rate = frameTimestamps.length;
                document.getElementById('frame-rate').textContent = rate + '/s';
            }

            function displayVideoFrame(detection) {
                frameCount++;
                frameTimestamps.push(Date.now());
                updateFrameRate();

                // Update frame count
                document.getElementById('frame-count').textContent = frameCount;

                // Create visual representation
                const canvas = document.getElementById('video-canvas');
                const ctx = canvas.getContext('2d');

                canvas.width = 320;
                canvas.height = 240;

                // Background: gradient representing video
                const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
                gradient.addColorStop(0, '#667eea');
                gradient.addColorStop(1, '#764ba2');
                ctx.fillStyle = gradient;
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                // Draw a subtle grid
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
                ctx.lineWidth = 1;
                for (let i = 0; i < canvas.width; i += 40) {
                    ctx.beginPath();
                    ctx.moveTo(i, 0);
                    ctx.lineTo(i, canvas.height);
                    ctx.stroke();
                }
                for (let i = 0; i < canvas.height; i += 30) {
                    ctx.beginPath();
                    ctx.moveTo(0, i);
                    ctx.lineTo(canvas.width, i);
                    ctx.stroke();
                }

                // Draw detection point
                ctx.fillStyle = '#10b981';
                ctx.beginPath();
                ctx.arc(
                    (detection.pixel_x / 1920) * canvas.width,
                    (detection.pixel_y / 1440) * canvas.height,
                    6,
                    0,
                    Math.PI * 2
                );
                ctx.fill();

                // Draw confidence glow
                ctx.strokeStyle = detection.confidence > 0.9 ? '#10b981' :
                                detection.confidence > 0.75 ? '#f59e0b' : '#ef4444';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(
                    (detection.pixel_x / 1920) * canvas.width,
                    (detection.pixel_y / 1440) * canvas.height,
                    12,
                    0,
                    Math.PI * 2
                );
                ctx.stroke();

                // Display as image
                document.getElementById('video-content').innerHTML = '';
                const container = document.getElementById('video-content');
                container.appendChild(canvas);
                canvas.style.display = 'block';
                canvas.style.maxWidth = '100%';

                // Show detection info overlay
                const info = document.createElement('div');
                info.style.cssText = 'position: absolute; bottom: 10px; left: 10px; background: rgba(0,0,0,0.7); color: #fff; padding: 8px 12px; border-radius: 6px; font-size: 0.85em;';
                info.innerHTML = `🎬 Frame ${frameCount} • ${detection.confidence_flag || '?'} ${(detection.confidence * 100).toFixed(0)}%`;
                container.appendChild(info);
            }

            async function startFeed() {
                if (!currentFeed) {
                    alert('Please select a feed first');
                    return;
                }

                currentAdapterId = document.getElementById('feed-select').value;
                frameCount = 0;

                document.getElementById('stream-status').textContent = 'Starting...';
                document.getElementById('video-content').innerHTML = '🎬<br><small>Connecting...</small>';
                document.getElementById('frame-count').textContent = '0';
                document.getElementById('frame-rate').textContent = '0/s';

                try {
                    // Start the adapter on the backend
                    const response = await fetch(`/api/adapter/${currentAdapterId}/start`, { method: 'POST' });
                    const result = await response.json();

                    if (response.ok) {
                        document.getElementById('stream-status').textContent = 'Active ✓';
                        document.getElementById('video-content').innerHTML = '🎥<br><small>LIVE FEED</small>';

                        // Connect to event stream
                        connectToEventStream();
                    } else {
                        alert('Error starting adapter: ' + result.detail);
                        document.getElementById('stream-status').textContent = 'Error';
                    }
                } catch (error) {
                    console.error('Error:', error);
                    alert('Error: ' + error.message);
                    document.getElementById('stream-status').textContent = 'Error';
                }
            }

            function connectToEventStream() {
                // Close existing connection if any
                if (eventSource) eventSource.close();

                eventSource = new EventSource('/api/detections/stream');

                eventSource.onmessage = (event) => {
                    if (event.data === '') return; // Heartbeat

                    try {
                        const detection = JSON.parse(event.data);

                        document.getElementById('last-update').textContent = new Date(detection.timestamp).toLocaleTimeString();

                        if (detection.status === 'success') {
                            addDetection({
                                class: detection.ai_confidence > 0.9 ? 'landmark' : 'landmark',
                                confidence: detection.ai_confidence,
                                id: detection.detection_id || 'DET-' + Date.now(),
                                timestamp: detection.timestamp,
                                confidence_flag: detection.confidence_flag,
                                cot_xml: detection.cot_xml,
                                adapter_id: detection.adapter_id,
                                adapter_name: detection.adapter_name
                            });
                        }
                    } catch (e) {
                        console.log('Event parse error:', e, 'data:', event.data);
                    }
                };

                eventSource.onerror = (error) => {
                    console.error('EventSource error:', error);
                    document.getElementById('stream-status').textContent = 'Disconnected';
                };
            }

            async function stopFeed() {
                if (currentAdapterId && eventSource) {
                    eventSource.close();
                    eventSource = null;

                    try {
                        await fetch(`/api/adapter/${currentAdapterId}/stop`, { method: 'POST' });
                        document.getElementById('stream-status').textContent = 'Stopped';
                    } catch (error) {
                        console.error('Error stopping feed:', error);
                    }
                }
            }

            function addDetection(detection) {
                detectionCount++;
                updateStats();

                // Display video frame with detection
                displayVideoFrame(detection);

                const confidenceClass = detection.confidence > 0.9 ? 'confidence-green' :
                                       detection.confidence > 0.75 ? 'confidence-yellow' : 'confidence-red';
                const confidenceText = detection.confidence_flag || (detection.confidence > 0.9 ? 'GREEN' :
                                      detection.confidence > 0.75 ? 'YELLOW' : 'RED');

                const html = `
                    <li class="detection-item">
                        <div class="detection-class">🎯 ${detection.class}</div>
                        <div style="margin-top: 5px; font-size: 0.85em; color: #666;">
                            <strong>Source:</strong> ${detection.adapter_name || 'Unknown'}<br>
                            <strong>ID:</strong> ${detection.id.substring(0, 12)}...<br>
                            <strong>Time:</strong> ${new Date(detection.timestamp).toLocaleTimeString()}
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

                // Display raw detection object
                displayDetectionObject(detection);

                // Show CoT if available
                if (detection.cot_xml) {
                    displayCoT(detection.cot_xml);
                }

                // Keep only last 10
                while (list.children.length > 10) {
                    list.removeChild(list.lastChild);
                }
            }

            function syntaxHighlightJSON(json, key = '') {
                json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
                    var cls = 'number';
                    if (/^"/.test(match)) {
                        if (/:$/.test(match)) {
                            cls = 'key';
                        } else {
                            cls = 'string';
                        }
                    } else if (/true|false/.test(match)) {
                        cls = 'boolean';
                    } else if (/null/.test(match)) {
                        cls = 'null';
                    }
                    return '<span class="json-' + cls + '">' + match + '</span>';
                });
            }

            function displayDetectionObject(detection) {
                // Create a clean object for display (exclude large base64 image data)
                const displayObj = {
                    ...detection,
                    image_base64: detection.image_base64 ? '[base64 image data - ' + detection.image_base64.length + ' bytes]' : undefined
                };

                const formattedJSON = JSON.stringify(displayObj, null, 2);
                const highlighted = syntaxHighlightJSON(formattedJSON);

                const outputDiv = document.getElementById('detection-object-output');
                outputDiv.innerHTML = '<pre style="margin: 0;">' + highlighted + '</pre>';
            }

            function displayCoT(xml) {
                cotCount++;
                updateStats();

                const formatted = xml.split('\\n').map(line => {
                    let html = line
                        .replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;');

                    // Syntax highlighting
                    html = html.replace(/(&lt;\\?[\w\\s=".:\/\\-]*\\?&gt;)/g, '<span class="cot-tag">$1</span>');
                    html = html.replace(/(&lt;\\/?\w+)/g, '<span class="cot-tag">$1</span>');
                    html = html.replace(/(\\w+)=/g, '<span class="cot-attr">$1</span>=');
                    html = html.replace(/="([^"]*)"/g, '=<span class="cot-value">"$1"</span>');

                    return html;
                }).join('\\n');

                document.getElementById('cot-output').innerHTML = formatted;
            }


            function updateStats() {
                document.getElementById('detection-count').textContent = detectionCount;
                document.getElementById('cot-count').textContent = cotCount;
            }

            function setPreset(preset) {
                document.getElementById('sim-lat').value = preset.lat;
                document.getElementById('sim-lon').value = preset.lon;
                document.getElementById('sim-elev').value = preset.elev;
                document.getElementById('sim-heading').value = 0;
            }

            async function submitSimulation() {
                const lat = parseFloat(document.getElementById('sim-lat').value);
                const lon = parseFloat(document.getElementById('sim-lon').value);
                const elev = parseFloat(document.getElementById('sim-elev').value);
                const heading = parseFloat(document.getElementById('sim-heading').value) || 0;

                if (isNaN(lat) || isNaN(lon) || isNaN(elev)) {
                    alert('Please fill in all location fields');
                    return;
                }

                if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
                    alert('Invalid coordinates (lat: -90 to 90, lon: -180 to 180)');
                    return;
                }

                try {
                    const response = await fetch('/api/simulator/submit', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            latitude: lat,
                            longitude: lon,
                            elevation: elev,
                            heading: heading
                        })
                    });

                    const result = await response.json();

                    if (response.ok) {
                        alert('✅ Simulated detection submitted!\\nCheck detections panel for results.');
                        // Connect to stream if not already connected
                        if (!eventSource || eventSource.readyState !== EventSource.OPEN) {
                            connectToEventStream();
                        }
                    } else {
                        alert('Error: ' + (result.detail || 'Unknown error'));
                    }
                } catch (error) {
                    console.error('Error:', error);
                    alert('Error: ' + error.message);
                }
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


@app.post("/api/adapter/{adapter_id}/start")
async def start_adapter(adapter_id: str):
    """Start a live adapter feed"""
    try:
        worker = await worker_manager.start_adapter(adapter_id)
        return {
            "status": "started",
            "adapter_id": adapter_id,
            "adapter_name": worker.adapter_config["name"],
            "message": f"Processing {worker.adapter_config['name']} feed..."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/adapter/{adapter_id}/stop")
async def stop_adapter(adapter_id: str):
    """Stop a live adapter feed"""
    try:
        await worker_manager.stop_adapter(adapter_id)
        return {
            "status": "stopped",
            "adapter_id": adapter_id,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/adapter/{adapter_id}/status")
async def adapter_status(adapter_id: str):
    """Get status of an adapter"""
    status = worker_manager.get_worker_status(adapter_id)
    return status


@app.get("/api/adapters/status")
async def all_adapters_status():
    """Get status of all adapters"""
    statuses = {}
    for adapter_id in worker_manager.workers.keys():
        statuses[adapter_id] = worker_manager.get_worker_status(adapter_id)
    return statuses


async def detection_event_generator():
    """Server-Sent Events stream of detections"""
    while True:
        try:
            # Wait for detection with timeout
            detection = await asyncio.wait_for(
                worker_manager.detection_queue.get(), timeout=1.0
            )
            yield f"data: {json.dumps(detection)}\n\n"
        except asyncio.TimeoutError:
            # Keep connection alive with heartbeat
            yield ": heartbeat\n\n"


@app.get("/api/detections/stream")
async def detections_stream():
    """Stream detections from active adapters"""
    return StreamingResponse(
        detection_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/simulator/submit")
async def simulator_submit(data: SimulatorRequest):
    """Submit simulated camera telemetry with real HuggingFace AI detections"""
    latitude = data.latitude
    longitude = data.longitude
    elevation = data.elevation
    heading = data.heading

    # Get real AI detections from HuggingFace
    detections = []
    if not HuggingFaceDetector:
        raise HTTPException(
            status_code=503,
            detail="HuggingFace adapter not available. Set HF_API_KEY environment variable."
        )

    try:
        detector = HuggingFaceDetector(model="facebook/detr-resnet-50", confidence_threshold=0.5)
        detections = await detector.detect_and_convert_pixels(MINIMAL_PNG)

        if not detections:
            raise HTTPException(
                status_code=400,
                detail="No detections found in image. Try again or check HuggingFace API status."
            )

    except ValueError as e:
        raise HTTPException(status_code=503, detail=f"HuggingFace API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running AI detection: {str(e)}")

    # Send each detection to geolocation engine
    processed = []
    for detection in detections:
        payload = {
            "image_base64": MINIMAL_PNG,
            "pixel_x": detection["pixel_x"],
            "pixel_y": detection["pixel_y"],
            "object_class": detection["object_class"],
            "ai_confidence": detection["ai_confidence"],
            "source": "web-simulator",
            "camera_id": "simulator",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sensor_metadata": {
                "location_lat": latitude,
                "location_lon": longitude,
                "location_elevation": elevation,
                "heading": float(heading),
                "pitch": float(np.random.uniform(-30, 30)),
                "roll": 0.0,
                "focal_length": 3000.0,
                "sensor_width_mm": 6.4,
                "sensor_height_mm": 4.8,
                "image_width": 1920,
                "image_height": 1440,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "http://localhost:8000/api/v1/detections",
                    json=payload,
                )

            if response.status_code == 201:
                processed.append({
                    "object_class": detection["object_class"],
                    "ai_confidence": detection["ai_confidence"],
                    "pixel_x": detection["pixel_x"],
                    "pixel_y": detection["pixel_y"],
                    "detection_id": response.headers.get('X-Detection-ID'),
                    "confidence_flag": response.headers.get('X-Confidence-Flag')
                })
            else:
                # Log error but continue processing other detections
                print(f"Warning: Detection failed with status {response.status_code}")

        except Exception as e:
            print(f"Error processing detection: {e}")

    if not processed:
        raise HTTPException(status_code=500, detail="Failed to process any detections")

    return {
        "status": "success",
        "message": f"Processed {len(processed)} real AI detections from HuggingFace",
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "elevation": elevation,
            "heading": heading
        },
        "detections_processed": processed,
        "total": len(processed)
    }


if __name__ == "__main__":
    import uvicorn
    print("🌍 Starting Geolocation Engine Dashboard on http://localhost:8888")
    uvicorn.run(app, host="0.0.0.0", port=8888)

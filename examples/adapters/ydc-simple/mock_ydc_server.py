#!/usr/bin/env python3
"""
Mock YDC Server - Simulates YDC WebSocket for testing the adapter

Sends fake detections every 2 seconds to simulate real YDC.
"""
import asyncio
import json
import websockets
from typing import Set


class MockYDCServer:
    def __init__(self, host: str = "localhost", port: int = 5173):
        self.host = host
        self.port = port
        self.clients: Set = set()
        self.detection_counter = 0

    async def register_client(self, websocket):
        """Register a new client"""
        self.clients.add(websocket)
        print(f"✅ Adapter connected! ({len(self.clients)} client(s))")

    async def unregister_client(self, websocket):
        """Unregister a client"""
        self.clients.discard(websocket)
        print(f"❌ Adapter disconnected! ({len(self.clients)} client(s))")

    async def broadcast_detection(self, detection: dict):
        """Send detection to all connected adapters"""
        if not self.clients:
            return

        message = json.dumps(detection)
        print(f"📤 Broadcasting: {detection['class']} ({detection['confidence']:.0%}) at pixel ({detection['x']}, {detection['y']})")

        for websocket in self.clients.copy():
            try:
                await websocket.send(message)
            except websockets.exceptions.ConnectionClosed:
                await self.unregister_client(websocket)

    async def generate_detections(self):
        """Generate fake detections every 2 seconds"""
        detections = [
            {"x": 400, "y": 300, "width": 80, "height": 60, "class": "vehicle", "confidence": 0.95},
            {"x": 200, "y": 150, "width": 50, "height": 50, "class": "person", "confidence": 0.87},
            {"x": 600, "y": 400, "width": 100, "height": 120, "class": "vehicle", "confidence": 0.92},
            {"x": 100, "y": 100, "width": 40, "height": 40, "class": "person", "confidence": 0.78},
        ]

        while True:
            detection = detections[self.detection_counter % len(detections)]
            await self.broadcast_detection(detection)
            self.detection_counter += 1
            await asyncio.sleep(2)

    async def handle_client(self, websocket, path):
        """Handle client connection"""
        await self.register_client(websocket)
        try:
            # Just keep the connection open and send detections
            await websocket.wait_closed()
        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            await self.unregister_client(websocket)

    async def start(self):
        """Start the mock YDC server"""
        print(f"🚀 Mock YDC Server starting on ws://{self.host}:{self.port}/api/detections")
        print("   Waiting for adapter to connect...")

        # Start detection generator in background
        asyncio.create_task(self.generate_detections())

        # Start WebSocket server
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # Run forever


if __name__ == "__main__":
    server = MockYDCServer()
    asyncio.run(server.start())

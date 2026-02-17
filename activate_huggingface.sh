#!/bin/bash

# Quick activation script for HuggingFace real AI detections
# Usage: bash activate_huggingface.sh hf_your_token_here

if [ -z "$1" ]; then
    echo "❌ Please provide your HuggingFace token"
    echo ""
    echo "Usage:"
    echo "  bash activate_huggingface.sh hf_your_token_here"
    echo ""
    echo "Get token at: https://huggingface.co/settings/tokens"
    exit 1
fi

TOKEN="$1"

echo "🚀 Activating HuggingFace Real AI Detection"
echo ""

# Validate token format
if [[ ! $TOKEN =~ ^hf_ ]]; then
    echo "❌ Token doesn't start with 'hf_'"
    echo "   Token provided: $TOKEN"
    exit 1
fi

echo "✓ Token format looks good"
echo ""

# Set environment variable
export HF_API_KEY="$TOKEN"
echo "✓ HF_API_KEY set in environment"
echo ""

# Test token
echo "Testing authentication..."
python3 << EOF
import httpx
import os

token = "$TOKEN"
response = httpx.get(
    "https://huggingface.co/api/whoami",
    headers={"Authorization": f"Bearer {token}"},
    timeout=10
)

if response.status_code == 200:
    user = response.json()
    username = user.get("name", "unknown")
    print(f"✅ Authentication successful!")
    print(f"✅ Logged in as: {username}")
    exit(0)
else:
    print(f"❌ Authentication failed: {response.status_code}")
    try:
        print(f"   {response.json()}")
    except:
        pass
    exit(1)
EOF

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Token authentication failed"
    echo "Please verify:"
    echo "  1. Token is complete (no truncation)"
    echo "  2. Token type is 'Read'"
    echo "  3. Token was recently created"
    exit 1
fi

echo ""
echo "✅ All checks passed!"
echo ""
echo "Starting system with real HuggingFace detections..."
echo ""

cd /workspaces/geolocation-engine2
bash run_complete_system.sh

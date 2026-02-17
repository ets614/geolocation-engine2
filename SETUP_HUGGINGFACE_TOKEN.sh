#!/bin/bash

# HuggingFace Token Setup Script
# Gets your real HF token working for Geolocation Engine

echo "🤗 HuggingFace Token Setup"
echo "=========================="
echo ""

# Step 1: Check if token already set
if [ -n "$HF_API_KEY" ]; then
    echo "✓ HF_API_KEY already set in environment"
    echo "  Token: ${HF_API_KEY:0:20}... (truncated for security)"
    echo ""
    echo "Testing token..."
    python3 << 'PYTHON_TEST'
import httpx
import os

token = os.getenv("HF_API_KEY")
response = httpx.get(
    "https://huggingface.co/api/whoami",
    headers={"Authorization": f"Bearer {token}"},
    timeout=5
)

if response.status_code == 200:
    user = response.json().get("name", "unknown")
    print(f"✓ Token is VALID! Authenticated as: {user}")
    exit(0)
else:
    print(f"✗ Token INVALID: {response.json()}")
    exit(1)
PYTHON_TEST

    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ All set! Token is working."
        exit 0
    else
        echo ""
        echo "⚠️ Token exists but is invalid. Please get a new one."
    fi
else
    echo "✗ HF_API_KEY not set in environment"
fi

echo ""
echo "Steps to get your HuggingFace token:"
echo "======================================"
echo ""
echo "1️⃣  Go to: https://huggingface.co/settings/tokens"
echo ""
echo "2️⃣  Click 'New token'"
echo ""
echo "3️⃣  Fill in:"
echo "    - Name: Geolocation Engine"
echo "    - Type: Read (NOT write)"
echo "    - Expiration: No expiration (recommended)"
echo ""
echo "4️⃣  Click 'Create token'"
echo ""
echo "5️⃣  Copy the token (starts with 'hf_')"
echo ""
echo "=================================="
echo "Once you have your token, run:"
echo ""
echo "export HF_API_KEY='hf_your_token_here'"
echo ""
echo "Then verify with:"
echo "bash SETUP_HUGGINGFACE_TOKEN.sh"
echo ""

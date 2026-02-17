#!/usr/bin/env python3
"""
Quick test: Is your HuggingFace token valid?
Usage: python3 test_huggingface_token.py [your_token_here]
"""
import sys
import httpx
import os

def test_token(token=None):
    """Test if HuggingFace token is valid"""

    # Get token from arg, env, or prompt
    if not token:
        token = os.getenv("HF_API_KEY")

    if not token:
        print("❌ No token provided!")
        print()
        print("Usage:")
        print("  python3 test_huggingface_token.py hf_your_token_here")
        print("  OR")
        print("  export HF_API_KEY='hf_your_token_here'")
        print("  python3 test_huggingface_token.py")
        return False

    # Show what we're testing
    print(f"Testing token: {token[:20]}...{token[-5:]}")
    print()

    try:
        # Test 1: Verify token format
        if not token.startswith("hf_"):
            print("❌ Token doesn't start with 'hf_'")
            print(f"   Token starts with: {token[:10]}")
            return False

        print(f"✓ Token format looks good (starts with hf_)")
        print(f"✓ Token length: {len(token)} characters")

        # Test 2: Check if auth works
        print()
        print("Testing authentication...")
        response = httpx.get(
            "https://huggingface.co/api/whoami",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )

        if response.status_code == 200:
            user_info = response.json()
            username = user_info.get("name", "unknown")
            print(f"✅ Authentication successful!")
            print(f"   Logged in as: {username}")
            return True
        else:
            print(f"❌ Authentication failed!")
            print(f"   Status: {response.status_code}")
            try:
                error = response.json()
                print(f"   Error: {error.get('error', str(error))}")
            except:
                print(f"   Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Error testing token: {e}")
        return False

if __name__ == "__main__":
    token = sys.argv[1] if len(sys.argv) > 1 else None
    success = test_token(token)
    sys.exit(0 if success else 1)

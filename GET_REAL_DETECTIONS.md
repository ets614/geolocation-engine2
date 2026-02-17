# 🚀 Getting Real HuggingFace Detections Working

Your system is **almost ready**. You just need to set your HuggingFace token in the environment.

---

## Quick Start (2 minutes)

### Step 1: Get Your Token
1. Go to: **https://huggingface.co/settings/tokens**
2. If you don't have an account, click "Sign up" (use GitHub/Google for speed)
3. Click **"New token"** (blue button)
4. Fill in:
   - **Name:** `Geolocation Engine`
   - **Type:** **Read** (not Write)
   - **Expiration:** No expiration
5. Click **"Create token"**
6. **Copy the full token** (starts with `hf_`)

⚠️ **Important:** Copy the ENTIRE token, don't truncate it. It should be ~40+ characters.

---

### Step 2: Set Environment Variable

```bash
# Replace with YOUR actual token
export HF_API_KEY="hf_your_actual_token_here"
```

**Example:**
```bash
export HF_API_KEY="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"
```

---

### Step 3: Verify Token Works

```bash
# Test your token
bash SETUP_HUGGINGFACE_TOKEN.sh
```

You should see:
```
✓ HuggingFace API Status: 200
✓ Authenticated as: your_username
```

---

### Step 4: Start System with Real Detections

```bash
# With token set, start the system
bash run_complete_system.sh
```

---

## What Happens Now vs After

### BEFORE (Current - Demo Mode)
```
Dashboard shows:
🎯 person     ← Generated randomly
Pixel: (523, 412) ← Random pixel
GREEN 92%     ← Random confidence
```

### AFTER (With Real HuggingFace)
```
Dashboard shows:
🎯 person     ← Real detection from image!
🎯 car        ← Real detection!
🎯 dog        ← Real detection!
Pixel: (523, 412) ← Actual object position
GREEN 94%     ← Real confidence from HF model
```

---

## Troubleshooting

### "Invalid username or password"
- **Cause:** Token not set or invalid
- **Fix:**
  ```bash
  # Check if token is set
  echo $HF_API_KEY

  # If empty, set it again
  export HF_API_KEY="hf_..."

  # Verify
  bash SETUP_HUGGINGFACE_TOKEN.sh
  ```

### Token not persisting between terminal sessions
- **Cause:** Setting with `export` only works in current session
- **Fix - Option A (Current session):**
  ```bash
  export HF_API_KEY="hf_..."
  bash run_complete_system.sh
  ```
- **Fix - Option B (Persistent):**
  ```bash
  # Add to ~/.bashrc or ~/.zshrc
  echo 'export HF_API_KEY="hf_..."' >> ~/.bashrc
  source ~/.bashrc
  ```

### "Rate limit exceeded"
- **Cause:** Hit 30,000 inferences/month free limit
- **Fix:** Wait until next month or upgrade at https://huggingface.co/settings/billing

### Very slow responses (>5 seconds)
- **Cause:** Free tier uses shared CPU
- **Expected:** 500-1000ms is normal for HuggingFace free tier
- **Fix:** Upgrade to Pro tier for GPU access

---

## How to Verify It's Working

1. **Check logs in dashboard terminal:**
   ```
   ✅ Got 3 real detections from HuggingFace
   ```
   (Instead of: `ℹ️ Demo mode: 2 realistic detections`)

2. **Check dashboard in browser:**
   - Open http://localhost:8888
   - Select "🤗 HuggingFace DETR (Real AI)"
   - Click "Start"
   - **Watch live real object detections** appear with GPS coordinates!

3. **Check CoT XML:**
   - Real detections will show actual HuggingFace results
   - You'll see detected object types: person, car, dog, etc.
   - Confidence scores from actual model

---

## Common Token Issues

| Issue | Token Looks Like | Solution |
|-------|------------------|----------|
| Token too short | `hf_abc123` | Copy the FULL token from HF settings |
| Token has spaces | `hf_abc 123` | Copy without extra whitespace |
| Wrong token type | Created from API keys page | Create from Settings → Access Tokens |
| Expired | Set months ago | Create new token at https://huggingface.co/settings/tokens |

---

## Next: After Getting Real Detections

Once you have real HuggingFace detections working:

1. **Try different models:**
   ```
   In dashboard dropdown:
   - 🤗 HuggingFace DETR (slower, more accurate)
   - ⚡ HuggingFace YOLOS (faster)
   ```

2. **Integrate with TAK/ATAK:**
   - Copy CoT XML from dashboard
   - Send to TAK server
   - See detections on military map

3. **Scale up:**
   - Add more camera feeds
   - Upgrade to paid tier for more inferences
   - Connect to real video streams

---

## Need Help?

- **HuggingFace Docs:** https://huggingface.co/docs/hub/api-inference
- **Available Models:** https://huggingface.co/models?task=object-detection
- **Geolocation Engine Docs:** See `HUGGINGFACE_INTEGRATION.md` and `REAL_AI_QUICKSTART.md`

---

**Let's go! 🚀**

```bash
# 1. Set your token (replace with YOUR actual token)
export HF_API_KEY="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"

# 2. Start system
bash run_complete_system.sh

# 3. Open browser
# http://localhost:8888

# 4. Select "🤗 HuggingFace DETR" and click "Start"

# 5. Watch real AI detections appear! 🎉
```

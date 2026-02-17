# 🚀 Real AI Detection - Quick Start (5 minutes)

Get **real AI detections** running in your Geolocation Engine dashboard.

---

## Option 1: Roboflow (Simplest)

### 1️⃣ Sign Up (1 min)
```
→ https://roboflow.com
→ Click "Sign up for free"
→ Use Google/GitHub login
→ Confirm email
```

### 2️⃣ Get API Key (2 min)
```
→ Settings → API Keys
→ Copy "Private API Key" (looks like: rf_XXXXX)
→ Don't lose it!
```

### 3️⃣ Set Environment Variable (1 min)
```bash
export ROBOFLOW_API_KEY="rf_your_actual_key_here"
```

### 4️⃣ Run System
```bash
bash run_complete_system.sh
```

### 5️⃣ Use Dashboard
```
→ Open http://localhost:8888
→ Select "🤖 Roboflow COCO (Real AI)" from dropdown
→ Click "Start"
→ Watch real detections appear! 🎉
```

**Free Tier:** 100 inferences/month = ~3 per day (perfect for testing)

---

## Option 2: HuggingFace (More Inferences)

### 1️⃣ Sign Up (1 min)
```
→ https://huggingface.co
→ Click "Sign up"
→ Use Google/GitHub login
→ Confirm email
```

### 2️⃣ Get API Token (2 min)
```
→ Click profile icon → Settings
→ Access Tokens → New token
→ Name: "Geolocation Engine"
→ Type: "Read"
→ Copy token (looks like: hf_ABCDefGHIjk...)
```

### 3️⃣ Set Environment Variable (1 min)
```bash
export HF_API_KEY="hf_your_actual_token_here"
```

### 4️⃣ Run System
```bash
bash run_complete_system.sh
```

### 5️⃣ Use Dashboard
```
→ Open http://localhost:8888
→ Select "🤗 HuggingFace DETR (30k free)" from dropdown
→ Click "Start"
→ Watch real detections appear! 🎉
```

**Free Tier:** 30,000 inferences/month = ~1000 per day (much more!)

---

## Which Should I Choose?

### Pick Roboflow If:
- ✅ You want the absolute simplest setup
- ✅ You just want to see a demo
- ✅ You don't need many inferences

### Pick HuggingFace If:
- ✅ You want 300x more free inferences (30k vs 100)
- ✅ You want to experiment with different models
- ✅ You plan longer testing sessions

**My Recommendation:** Start with **Roboflow** for speed, switch to **HuggingFace** if you need more testing time.

---

## Verification: Is It Working?

### In Dashboard, you should see:

**Before (simulated detections):**
```
🎯 Landmark
Pixel: (1505, 775) ← Random
GREEN 87% ← Random confidence
```

**After (real AI detections):**
```
🎯 Person  ← Real AI detected this!
🎯 Car
🎯 Dog
Pixel: (523, 412) ← Actual object position
GREEN 94% ← Real confidence from model
```

If you see **real object types** (Person, Car, Dog, etc.) instead of just "Landmark", it's working! ✅

---

## What Each Adapter Detects

### Roboflow COCO
Detects 80 object types:
- People, animals, vehicles, furniture, food, nature, etc.

### HuggingFace DETR
Detects 80 object types (same as COCO):
- Person, car, dog, cat, truck, bicycle, etc.

### HuggingFace YOLOS (Fast)
Same detections but faster:
- Good for real-time processing

---

## API Comparison

```
Roboflow (100/month free)
├─ COCO: General object detection
└─ OpenLogo: Brand/landmark detection

HuggingFace (30,000/month free)
├─ DETR: High accuracy, slower
├─ YOLOS-tiny: Very fast, decent accuracy
└─ YOLOS-base: Balanced
```

---

## Troubleshooting

### "Invalid API key" error
**Solution:**
- Verify you copied the **full** key
- Check no spaces: `echo "$ROBOFLOW_API_KEY" | wc -c`
- Try setting again: `export ROBOFLOW_API_KEY="rf_..."`

### No new detections appearing
**Solution:**
- Refresh browser (F5)
- Check browser console (F12 → Console tab)
- Verify API is running: `curl http://localhost:8000/api/health`
- Check logs: `tail -f /tmp/geolocation-api.log`

### "Rate limit exceeded" error
**Solution:**
- You've used all free inferences this month
- Wait until next month OR
- Upgrade to paid tier at Roboflow/HuggingFace

### Dashboard won't start
**Solution:**
```bash
# Kill old processes
pkill -f "uvicorn"
pkill -f "python app.py"

# Try again
bash run_complete_system.sh
```

---

## What's Happening Behind the Scenes

```
1. You select "🤖 Roboflow COCO" in dashboard

2. Dashboard sends frame to your adapter:
   POST /api/adapter/roboflow-coco/frame

3. Your adapter sends image to Roboflow cloud API:
   POST https://detect.roboflow.com/coco

4. Roboflow's AI model detects objects:
   Response: [
     {"class": "person", "x": 500, "y": 300, "confidence": 0.92},
     ...
   ]

5. Your adapter converts to pixel coordinates

6. Geolocation engine calculates GPS from pixels:
   "If person is at pixel (500, 300) in image from camera at 40.7580°, -73.9855°,
    they must be at GPS 40.759°, -73.984°"

7. Generates CoT XML:
   <point lat="40.759" lon="-73.984" />

8. Dashboard displays everything in real-time ✅
```

---

## Advanced: Multiple Adapters

You can run multiple adapters simultaneously!

```bash
# Terminal running dashboard shows:
🤖 Roboflow COCO         ← Running
🤗 HuggingFace DETR      ← Running (at same time!)
🗽 Times Square (simulated) ← Also running
🌍 Eiffel Tower (simulated)  ← Also running
```

Just start different feeds from dashboard.

---

## Next Steps After Getting It Working

1. **Test accuracy**
   - Compare detections with actual objects in video
   - Check if GPS coordinates make sense

2. **Try different models**
   - Roboflow: Try "openlogo" for landmarks
   - HuggingFace: Try different YOLOS models

3. **Integrate with TAK**
   - Copy CoT XML from dashboard
   - Paste into TAK/ATAK server
   - See detections on map!

4. **Scale up**
   - Upgrade to paid tier for more inferences
   - Add more camera feeds
   - Connect to real video streams

---

## File Reference

```
New files created:
├── ROBOFLOW_INTEGRATION.md ........... Detailed Roboflow guide
├── HUGGINGFACE_INTEGRATION.md ....... Detailed HuggingFace guide
├── HOSTED_AI_SERVICES.md ............ All hosted services comparison
├── REAL_AI_QUICKSTART.md ............ This file!
└── web_dashboard/adapters/
    ├── roboflow.py ................... Roboflow API client
    └── huggingface.py ................ HuggingFace API client
```

---

## Let's Go! 🚀

**Choose one:**

### Option A: Roboflow (Simpler)
```bash
# 1. Sign up: https://roboflow.com
# 2. Copy API key from Settings
# 3. Run:
export ROBOFLOW_API_KEY="rf_..."
bash run_complete_system.sh
```

### Option B: HuggingFace (More Inferences)
```bash
# 1. Sign up: https://huggingface.co
# 2. Copy token from Settings → Access Tokens
# 3. Run:
export HF_API_KEY="hf_..."
bash run_complete_system.sh
```

Then open: **http://localhost:8888** 🎉

---

**Questions?**
- Roboflow: See `ROBOFLOW_INTEGRATION.md`
- HuggingFace: See `HUGGINGFACE_INTEGRATION.md`
- All options: See `HOSTED_AI_SERVICES.md`

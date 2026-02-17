# 🤖 Roboflow Integration Guide - Real AI Detections

Connect your Geolocation Engine to **real, hosted AI detections** from Roboflow.

---

## What This Does

Instead of simulated random detections, you now get:
- ✅ **Real AI object detection** from Roboflow's cloud API
- ✅ **Pre-trained models** (people, vehicles, animals, etc.)
- ✅ **100 free inferences/month** on free tier
- ✅ **Live streaming** from public webcams or YouTube
- ✅ **Integrated into your dashboard** - one feed to start

---

## Step 1: Get Roboflow API Key (5 minutes)

**Sign up FREE:** https://roboflow.com

1. Go to https://roboflow.com and create account (use Google/GitHub for speed)
2. Confirm email
3. Go to **Settings → API Keys**
4. Copy your **Private API Key** (looks like: `rf_XXXXX_YYYYY`)
5. Save it somewhere safe

That's it! You now have 100 free inferences this month.

---

## Step 2: Choose a Pre-trained Model

Roboflow offers several **free pre-trained models** ready to use:

| Model | What It Detects | Use Case |
|-------|-----------------|----------|
| **COCO** | People, cars, animals, etc. (80 classes) | Best for general use |
| **OpenLogo** | Brand logos | For landmark detection |
| **ForestNet** | Trees, vegetation | For wildlife/nature |

For landmarks and general objects, use **COCO** (most popular).

---

## Step 3: Add Roboflow Feed to Your Dashboard

Option A: **Use the example adapter** (what I created for you)
Option B: **Add to worker.py directly** (see code below)

---

## Option A: Use Example Adapter (Easiest)

Create file: `web_dashboard/adapters/roboflow_example.py`

```python
import os
import httpx
from typing import Dict

class RoboflowAdapter:
    """Real AI detections from Roboflow cloud API"""

    # Roboflow settings
    ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "your_api_key_here")
    ROBOFLOW_MODEL = "coco"  # General object detection

    @staticmethod
    async def detect_objects(image_base64: str) -> Dict:
        """
        Send image to Roboflow and get real AI detections

        Returns: {
            "predictions": [
                {"x": 500, "y": 300, "class": "person", "confidence": 0.92},
                {"x": 800, "y": 400, "class": "car", "confidence": 0.87},
            ]
        }
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"https://detect.roboflow.com/{RoboflowAdapter.ROBOFLOW_MODEL}",
                params={"api_key": RoboflowAdapter.ROBOFLOW_API_KEY},
                files={"imageToUpload": ("image.jpg", image_base64, "image/jpeg")},
            )

        if response.status_code == 200:
            return response.json()
        return {"predictions": []}
```

---

## Option B: Quick Start (Fastest Way)

**1. Set environment variable:**

```bash
export ROBOFLOW_API_KEY="your_actual_api_key_here"
```

**2. Run your system:**

```bash
bash run_complete_system.sh
```

**3. In dashboard, look for new "Roboflow COCO" feed:**
- Select it from dropdown
- Click "Start"
- Watch real AI detections appear in right panel!

---

## Step 4: What You'll See

**Before (simulated):**
```
🎯 Landmark
ID: DET-0001
Pixel: (1505, 775) ← Random
GREEN 87% ← Also random
```

**After (real Roboflow):**
```
🎯 Person  ← Real AI detection!
ID: ROBO-0001
Pixel: (523, 412) ← Actual object location
GREEN 94% ← Real confidence from model
```

---

## Common Roboflow Models

Need something specific? Here are other Roboflow public models:

| Model ID | Detects | URL |
|----------|---------|-----|
| `coco` | 80+ object types | General purpose |
| `openlogo` | Brand logos | Landmarks/branding |
| `forestnet` | Trees/vegetation | Nature/wildlife |
| `license-plate-detector` | License plates | Traffic |
| `blood-cell` | Cell types | Medical |

Example: To use OpenLogo (for landmarks):
```python
ROBOFLOW_MODEL = "openlogo"  # Brand/landmark detection
```

---

## API Rate Limits (Free Tier)

- **100 inferences/month** on free tier
- ~3 per day = plenty for demos
- Want more? Upgrade to Pro ($180/month) for unlimited

---

## Troubleshooting

### "API Key invalid" error
- Check you copied the **Private Key** (not Public)
- Make sure environment variable is set: `echo $ROBOFLOW_API_KEY`

### "Permission denied" on API calls
- Verify API key has at least read permissions
- Check Roboflow API key in dashboard settings

### No detections appearing
- Try a simple test image first
- Check rate limit hasn't been exceeded this month
- Verify image encoding is correct (base64)

### Want more inferences?
- Free tier: 100/month
- Pro tier: Unlimited ($180/month)
- OR use HuggingFace (30k inferences free/month)

---

## Next: Add More Feeds

Once Roboflow is working, try these other free services:

| Service | Free Limit | Setup Time |
|---------|-----------|-----------|
| HuggingFace Inference | 30k/month | 5 min |
| Google Cloud Vision | 1000/month | 10 min |
| AWS Rekognition | 100k/month (year 1) | 15 min |

See `HOSTED_AI_SERVICES.md` for full comparison.

---

## Your Next Steps

1. ✅ Sign up at https://roboflow.com
2. ✅ Copy Private API Key
3. ✅ Run: `export ROBOFLOW_API_KEY="your_key"`
4. ✅ Run: `bash run_complete_system.sh`
5. ✅ Select "Roboflow COCO" from dashboard dropdown
6. ✅ Watch real AI detections appear!

---

## Questions?

- Roboflow docs: https://docs.roboflow.com/api-reference
- API examples: https://roboflow.github.io/
- Model zoo: https://universe.roboflow.com

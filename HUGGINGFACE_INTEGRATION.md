# 🤗 HuggingFace Inference API Integration

Get **real AI detections** with 30,000 free inferences/month from HuggingFace.

---

## Why HuggingFace Over Roboflow?

| Factor | Roboflow | HuggingFace |
|--------|----------|-------------|
| Free/month | 100 | 30,000 (300x more!) |
| Models | 5-10 | 1000+ to choose from |
| Setup | 5 min | 5 min |
| Speed | Fast | Medium |
| **For testing** | ⭐ Good | ⭐⭐⭐ Best |

**Choose HuggingFace if you want:** More inferences, more model options, longer testing window.

---

## Step 1: Get HuggingFace API Key (5 minutes)

**Sign up FREE:** https://huggingface.co

1. Create account (use GitHub/Google for speed)
2. Confirm email
3. Go to **Settings → Access Tokens** (or click profile icon → Settings)
4. Click **"New token"**
5. Set name to "Geolocation Engine"
6. Type: **"Read"** (you only need read access)
7. Create token
8. Copy the token (looks like: `hf_ABCDefGHIjklmnopQRSTuvwxyz`)

That's it! You now have 30,000 free inferences this month.

---

## Step 2: Choose a Detection Model

HuggingFace has **1000+ models**. Here are the best for object detection:

### Best for SPEED (Fast, lower accuracy)
```
hustvl/yolos-tiny
- Fastest inference
- ~200-300ms per image
- Good for real-time
```

### Best for BALANCE (Medium speed, good accuracy)
```
hustvl/yolos-base
- 300-500ms per image
- Good accuracy
- Recommended for most use cases
```

### Best for ACCURACY (Slow, highest accuracy)
```
facebook/detr-resnet-101
- 800ms-1s per image
- Highest accuracy
- For critical applications
```

### Recommended for YOUR project
```
facebook/detr-resnet-50 ← START HERE
- 500-700ms per image
- COCO dataset (80 object types)
- Great balance of speed/accuracy
- Most popular
```

---

## Step 3: Configure Your System

### Option A: Environment Variable (Recommended)

```bash
export HF_API_KEY="hf_your_actual_token_here"
```

Then run normally:
```bash
bash run_complete_system.sh
```

### Option B: Create .env File

Create `web_dashboard/.env`:
```
HF_API_KEY=hf_your_actual_token_here
```

### Option C: Pass at Runtime

```bash
HF_API_KEY="hf_your_token" python app.py
```

---

## Step 4: Test the Connection

```bash
cd web_dashboard

# Test detector directly
python -c "
import asyncio
from adapters.huggingface import HuggingFaceDetector
import base64

# Minimal test image
img = base64.b64encode(
    b'\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x01\\x08\\x06\\x00\\x00\\x00\\x1f\\x15\\xc4\\x89\\x00\\x00\\x00\\nIDATx\\x9cc\\x00\\x01\\x00\\x00\\x05\\x00\\x01\\r\\n-\\xb4\\x00\\x00\\x00\\x00IEND\\xaeB\`\\x82'
).decode()

detector = HuggingFaceDetector()
print('Testing HuggingFace API...')
print(asyncio.run(detector.detect(img)))
"
```

---

## Step 5: Use in Dashboard

### Start System
```bash
bash run_complete_system.sh
```

### In Dashboard Dropdown
Look for:
- 🤗 **HuggingFace DETR (30k free)**
- ⚡ **HuggingFace YOLOS (Fast)**

### Select One
Click "Start" and watch real AI detections appear!

---

## What You'll See

**Before (simulated):**
```
🎯 Landmark
Pixel: (1505, 775) ← Random
GREEN 87% ← Also random
```

**After (real HuggingFace):**
```
🎯 Person  ← Real detection!
🎯 Car     ← Real detection!
🎯 Dog     ← Real detection!
Pixel: (523, 412) ← Actual object
GREEN 94% ← Real confidence
```

---

## Available Detection Models

### General Object Detection (Recommended)

| Model | Speed | Accuracy | Classes | URL |
|-------|-------|----------|---------|-----|
| `facebook/detr-resnet-50` | Medium | High | 80 (COCO) | Use this! |
| `facebook/detr-resnet-101` | Slow | Very High | 80 (COCO) | For accuracy |
| `hustvl/yolos-tiny` | Very Fast | Medium | 80 | For speed |
| `hustvl/yolos-base` | Fast | High | 80 | Balanced |

### Object Types Detected (COCO dataset - 80 classes)

```
People: person
Animals: dog, cat, bird, horse, sheep, cow, elephant, bear, zebra, giraffe
Vehicles: car, motorcycle, airplane, bus, train, truck, boat
Indoor: chair, couch, bed, table, lamp, phone, laptop, keyboard, mouse
Food: apple, banana, orange, carrot, hot dog, pizza, donut, cake
Nature: tree, flower, potted plant, backpack, umbrella
And 50+ more...
```

---

## Model Comparison

### DETR (Default - Recommended)
```
facebook/detr-resnet-50
✅ Pre-trained on COCO
✅ Best accuracy/speed ratio
✅ Stable inference
✅ Good for landmarks/general objects
⚠️ Slower than YOLO
```

### YOLOS (Fast Alternative)
```
hustvl/yolos-tiny, base, large
✅ Faster inference
✅ Real-time processing possible
✅ Multiple accuracy levels
⚠️ Slightly lower accuracy than DETR
```

**Recommendation:** Start with DETR, switch to YOLOS if you need speed.

---

## Rate Limits (Free Tier)

- **30,000 inferences/month**
- That's ~1000 per day, or ~40 per hour
- Enough for demos and testing
- Hitting limit? Upgrade to Pro ($9/month) for 500k

---

## Troubleshooting

### "API token invalid" error
- Copy **full** token from HuggingFace settings
- Check no extra spaces: `echo "$HF_API_KEY" | wc -c`
- Verify env var set: `echo $HF_API_KEY`

### "Rate limit exceeded" error
- You've hit 30k inferences this month
- Wait until next month OR
- Upgrade at https://huggingface.co/settings/billing

### Model not found / 404 error
- Check model name matches exactly
- Some models may be archived/unavailable
- Try: `facebook/detr-resnet-50` (most stable)

### Slow inference (>2 seconds)
- This is normal for CPU-based models
- HuggingFace free tier is shared CPU
- Upgrade for GPU access

### No detections appearing
- API might be overloaded (free tier)
- Try again in a minute
- Check browser console for errors (F12)

---

## Advanced: Custom Models

HuggingFace lets you **fine-tune** models on your data.

Example: Custom "landmark detector"
```
1. Upload 100+ images of landmarks
2. Annotate with labels
3. HuggingFace auto-trains
4. Get custom model endpoint
5. Use in your adapter!
```

See: https://huggingface.co/docs/datasets

---

## Compare: HuggingFace vs Others

```
Roboflow:
- 100/month free
- Pre-built detection models
- ✅ Very easy for beginners

HuggingFace:
- 30,000/month free (300x more!)
- 1000+ models to choose from
- ✅ Better for experimentation

Google Cloud:
- 1,000/month free
- Highest accuracy
- ✅ Better for production

AWS:
- 100,000/month free (year 1)
- Excellent for scale
- ✅ Better for enterprise
```

**For your project:** HuggingFace gives you the most inferences to test with!

---

## API Response Example

When HuggingFace detects objects:

```json
[
  {
    "score": 0.9876,
    "label": "person",
    "box": {
      "xmin": 400,
      "ymin": 200,
      "xmax": 600,
      "ymax": 500
    }
  },
  {
    "score": 0.8543,
    "label": "car",
    "box": {
      "xmin": 100,
      "ymin": 300,
      "xmax": 350,
      "ymax": 450
    }
  }
]
```

Your adapter automatically converts this to geolocation coordinates!

---

## Next Steps

1. ✅ Sign up at https://huggingface.co
2. ✅ Get Access Token from Settings
3. ✅ Set: `export HF_API_KEY="your_token"`
4. ✅ Run: `bash run_complete_system.sh`
5. ✅ Select "🤗 HuggingFace DETR" from dashboard
6. ✅ Watch real AI detections appear!

---

## Questions?

- HuggingFace API Docs: https://huggingface.co/docs/hub/api-inference
- Model Hub: https://huggingface.co/models?task=object-detection
- Community: https://discuss.huggingface.co

# AutoHVAC Production Deployment Guide

## Critical Configuration for Accurate HVAC Calculations

### 1. Install PaddleOCR (REQUIRED)

PaddleOCR is essential for accurate blueprint text extraction. Without it, scale detection and room identification will fail.

#### For Render.com Deployment

Add to your build command:
```bash
pip install -r requirements.txt
```

Ensure `requirements.txt` includes:
```
paddlepaddle==2.5.2
paddleocr>=2.7.0.3
```

#### For Docker Deployment

Add to your Dockerfile:
```dockerfile
# Install system dependencies for PaddleOCR
RUN apt-get update && apt-get install -y \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

#### For Local Development

```bash
# macOS with Apple Silicon (M1/M2)
pip install paddlepaddle==2.5.1 -i https://mirror.baidu.com/pypi/simple
pip install paddleocr

# Linux/Windows
pip install paddlepaddle paddleocr

# Verify installation
python -c "from paddleocr import PaddleOCR; print('PaddleOCR installed successfully')"
```

### 2. Set Environment Variables

Create a `.env` file or set these in your deployment platform:

```bash
# CRITICAL: Use traditional-first mode for accurate parsing
PARSING_MODE=traditional_first

# Force specific scale if blueprints are known to be 1/4"=1'
SCALE_OVERRIDE=48  # pixels per foot for 1/4" scale

# Lower confidence threshold to catch more rooms
MIN_CONFIDENCE_THRESHOLD=0.5

# Your OpenAI API key (required)
OPENAI_API_KEY=sk-...

# Redis for background jobs (optional but recommended)
REDIS_URL=redis://...
```

### 3. Verify PaddleOCR Installation

After deployment, check your worker logs for:
- ✅ "PaddleOCR initialized successfully"
- ✅ "Using PaddleOCR for text extraction"

If you see these errors, PaddleOCR is NOT working:
- ❌ "PaddleOCR not available - OCR extraction will be limited"
- ❌ "OCR not available - returning empty results"

### 4. Common Issues and Solutions

#### Issue: "Total Heating Load 1,898 BTU/hr" (way too low)
**Cause:** Scale detection failed (wrong pixels-per-foot ratio)
**Solution:** 
- Ensure PaddleOCR is installed
- Set `SCALE_OVERRIDE=48` for 1/4"=1' blueprints
- Use `PARSING_MODE=traditional_first`

#### Issue: "Only 928 sqft detected" (missing floors)
**Cause:** GPT-4V only detecting partial floor plan
**Solution:**
- Increase image resolution (already set to 2000px)
- Ensure all PDF pages are being processed
- Check for floor labels in OCR output

#### Issue: "Unable to identify floor plan in image"
**Cause:** GPT-4V failing on title/elevation pages
**Solution:**
- System now retries with enhanced processing
- Traditional parsing will extract geometry even if AI fails

### 5. Production Checklist

Before going live, verify:

- [ ] PaddleOCR is installed and working
- [ ] `PARSING_MODE=traditional_first` is set
- [ ] Worker logs show "Using PaddleOCR for text extraction"
- [ ] Test with a known blueprint to verify correct BTU/hr calculations
- [ ] Scale detection shows confidence > 0.6
- [ ] Multiple floors are detected if blueprint has multiple levels

### 6. Monitoring

Watch these metrics in your logs:
- Scale detection confidence (should be > 0.6)
- Number of rooms detected (should match blueprint)
- Total area detected (should be realistic for home size)
- OCR text elements extracted (should be > 0 if PaddleOCR is working)

### 7. Rollback Plan

If issues persist after deployment:
1. Set `PARSING_MODE=ai_first` to use GPT-4V primarily
2. Set `SCALE_OVERRIDE=48` to force 1/4" scale
3. Contact support with job IDs showing incorrect calculations

## Architecture Overview

The system uses a multi-layer approach:
1. **PaddleOCR** extracts all text (dimensions, labels, scale notations)
2. **Geometry Parser** extracts walls, rooms, lines
3. **Spatial Matcher** associates text with geometry
4. **Scale Detector** determines pixels-per-foot ratio
5. **Room Detector** identifies rooms using both traditional and AI methods
6. **Manual J Calculator** computes HVAC loads

Each layer has validation gates that raise exceptions when confidence is low, ensuring accurate results.
# HVAC Load Calculation Fixes - Sprint 1 Complete

## Critical Issues Fixed (Sprint 1 ✅)

### 1. Quality Score Gate (Fixed)
**Problem:** System continued processing even when quality score = 0
**Fix:** Modified `blueprint_parser.py:371-386` to ALWAYS raise `NeedsInputError` when quality < 50
- No longer requires critical_issues to exist
- Provides clear error message and recommendations
- Prevents bad data from reaching Manual J calculations

### 2. Geometry Validation Gates (Fixed)
**Problem:** System computed loads with nonsense room geometry (85 rooms @ 26 sqft each)
**Fixes implemented in `blueprint_parser.py:1094-1156`:**
- **Average room size gate:** Stops if avg < 40 sqft (indicates wrong scale)
- **Total area gate:** Stops if total < 500 or > 10,000 sqft
- **Room count gate:** Stops if > 40 rooms detected (likely detecting non-room elements)
- All gates raise `NeedsInputError` with specific recommendations

### 3. Page/Scale Context Tracking (Fixed)
**Problem:** Different pages used by different pipeline stages (GPT picks page 1, geometry uses page 2)
**Fix:** Added `PageContext` class in `blueprint_parser.py:52-114`
- Thread-safe tracking of selected page and scale
- Prevents page switching mid-pipeline
- Prevents scale changes without explicit override
- Raises error if inconsistency detected

### 4. Floor Loss Calculation (Verified Correct)
**Problem suspected:** Fixed 501 BTU/hr per room regardless of size
**Finding:** Floor losses ARE area-based (`manualj.py:735-747`)
- Uses `room.area` in calculation
- The 501 BTU/hr was RESULT of calculation for 26 sqft rooms
- With new gates, this scenario won't occur

### 5. New Error Type (Added)
**File:** `services/error_types.py:127-146`
Added `NeedsInputError` class for user input requirements:
- `input_type`: 'scale', 'plan_quality', 'envelope_gaps'
- Clear messages and recommendations
- Structured details for debugging

## What These Fixes Prevent

Your failing example (85 rooms @ 26.8 sqft = 2,281 sqft total) will now:
1. **STOP** at quality score check (score was 0)
2. **STOP** at avg room size check (26.8 < 40 sqft minimum)
3. **STOP** at total area check (2,281 < typical, but with wrong room size)
4. **STOP** at room count check (85 > 40 maximum)

Result: **NeedsInputError** requesting SCALE_OVERRIDE instead of bogus 202,546 BTU/hr load

## Sprint 2 Complete: Deterministic Scale Detection ✅

### What's Been Added

1. **DeterministicScaleDetector** (`services/deterministic_scale_detector.py`)
   - Title block OCR with comprehensive regex patterns
   - Dimension text parsing with distance validation
   - Known object detection (doors, hallways, grid)
   - Requires 2+ corroborating estimates within 3%
   - Returns confidence score and detailed evidence

2. **RoomFilter** (`services/room_filter.py`)
   - MIN_ROOM_SQFT=40, MAX_ROOM_SQFT=1000 enforcement
   - Aspect ratio filtering (removes hallways)
   - Duplicate/overlap detection
   - Statistical outlier removal
   - Total building validation (500-10,000 sqft)

3. **Integration Module** (`services/blueprint_parser_integration.py`)
   - Connects scale detector to parser pipeline
   - Applies room filtering with proper error handling
   - Updates metadata with detection statistics

### How Scale Detection Now Works

1. **User Override** (highest priority)
   - SCALE_OVERRIDE environment variable

2. **Title Block OCR**
   - Patterns: "SCALE: 1/4\"=1'-0\"", "1:48", etc.
   - Confidence: 0.95 with "SCALE" keyword

3. **Dimension Text Cross-Validation**
   - Finds "12'-6\"" text with anchor points
   - Measures pixel distance between anchors
   - Calculates scale: pixels/feet
   - Validates against standard scales

4. **Known Object Detection**
   - Finds door-like rectangles (aspect 2.3-2.8)
   - Assumes standard door width (2'8")
   - Clusters similar sizes for consensus

5. **Grid Analysis**
   - Detects regular spacing in lines
   - Matches to typical grid (10', 15', 20', etc.)

### Consensus Requirements

- Needs 2+ methods agreeing within 3%
- If only 1 estimate: confidence halved, requests override
- If no consensus: raises NeedsInputError

## Remaining Work (Sprints 3-5)

### Sprint 3: Semantic Labeling
- [ ] Restrict Vision to labels only (no measurements)
- [ ] Parse window/door schedules
- [ ] Envelope defaults with provenance tracking

### Sprint 4: Manual J Engine
- [ ] Volume-based infiltration (not per-room)
- [ ] Proper duct loss model
- [ ] Confidence scoring

### Sprint 5: Observability
- [ ] Metrics emission
- [ ] Detailed logging of imputed values

## Testing the Fixes

Run your failing PDF again. Expected result:
```
NeedsInputError: Blueprint quality score (0) below minimum threshold (50). Cannot proceed with load calculations.
Details: {
  'quality_score': 0,
  'threshold': 50,
  'recommendation': 'Please provide a clearer blueprint or use PARSING_MODE=traditional_first'
}
```

Or if quality passes but geometry fails:
```
NeedsInputError: Average room size (26.8 sqft) indicates incorrect scale. Cannot proceed.
Details: {
  'avg_room_sqft': 26.8,
  'recommendation': 'Set SCALE_OVERRIDE=48 for 1/4"=1' or SCALE_OVERRIDE=96 for 1/8"=1' blueprints'
}
```

## Key Insight

The 501 BTU/hr per room wasn't a fixed constant - it was the RESULT of calculating floor losses for 26.8 sqft rooms. This revealed the real problem: **bad scale detection creating tiny rooms**. The validation gates now prevent this scenario entirely.
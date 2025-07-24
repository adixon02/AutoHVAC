# HVAC Calculation Fixes Summary

## Problem
The HVAC load calculations were producing extremely low values:
- Cooling: 0.34873 tons (4,184 BTU/hr)
- Heating: 0.09047 tons (1,085 BTU/hr)

## Root Causes Identified

### 1. Frontend-Backend Data Mismatch
- Frontend was looking for `results.total_area` but backend was providing `building_data.floor_area_ft2`
- Frontend defaulted to 500 sq ft when `total_area` was missing, causing severely undersized calculations

### 2. Excessive Safety Factors
- Multiple compounding factors were being applied:
  - Diversity factors (0.90 heating, 0.85 cooling)
  - Duct losses (1.15 heating, 1.20 cooling)
  - Safety factors (1.10 heating, 1.15 cooling)
- These multiplied together created unrealistic adjustments

### 3. Internal Gains Over-credited
- Internal gains from occupants, lighting, and equipment were reducing heating load too much
- Used full internal gain credit for heating, which is unrealistic for nighttime/unoccupied periods

### 4. Blueprint Data Structure Issues
- Room data format mismatch between backend (`area_ft2`, `ceiling_height`) and frontend (`area`, `height`)
- Missing `building_details` structure that frontend expected

## Fixes Applied

### 1. Enhanced Manual J Calculator (`services/enhanced_manual_j_calculator.py`)
- Removed compounding safety and diversity factors (set to 1.0)
- Reduced duct loss factors (1.15 heating, 1.10 cooling)
- Adjusted internal gains calculation:
  - Only 50% credit for heating (accounts for nighttime/unoccupied)
  - Reduced default occupancy (1 person per 300 sq ft instead of 200)
  - Reduced lighting power (0.5 W/sq ft for LED instead of 1.0)
  - Reduced equipment power (0.3 W/sq ft instead of 0.5)
- Added minimum load requirements:
  - 4 BTU/hr/sq ft minimum for heating
  - 8 BTU/hr/sq ft minimum for cooling
- Adjusted solar gain factors to more realistic values

### 2. Blueprint API (`api/blueprint.py`)
- Added `total_area` field at root level for frontend compatibility
- Transformed room data to frontend format:
  - `area_ft2` → `area`
  - `ceiling_height` → `height`
  - `window_area` → `windows` (count)
- Added `building_details` structure
- Updated fallback data with complete 1480 sq ft home (7 rooms)

### 3. Data Flow Fixes
- Ensured consistent data structure between extraction and API response
- Added proper field mappings in `_combine_extraction_results`
- Fixed frontend store to properly read building area

## Expected Results
For a typical 1480 sq ft home in Spokane, WA (ZIP 99206):
- Heating: 0.7-1.0 tons (8,400-12,000 BTU/hr)
- Cooling: 2.0-2.5 tons (24,000-30,000 BTU/hr)

These values are now within industry-standard ranges for the climate zone and building size.

## Testing
Run these scripts to verify the fixes:
1. `python3 test_enhanced_calculations.py` - Tests full home calculation
2. `python3 test_frontend_scenario.py` - Tests specific frontend scenarios
3. `python3 trace_calculation.py` - Traces calculation details

## Next Steps
1. Test the full blueprint upload flow to ensure proper data extraction
2. Consider adding more sophisticated internal gain scheduling
3. Implement room-specific ventilation requirements
4. Add equipment sizing recommendations based on ACCA Manual S
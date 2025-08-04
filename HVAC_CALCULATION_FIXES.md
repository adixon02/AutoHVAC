# HVAC Load Calculation Discrepancy Analysis & Fixes

## Executive Summary

Our HVAC load calculations are underestimating heating loads by **46%** (33,276 vs 61,393 BTU/hr) while cooling loads are relatively close (only 8% low). This analysis identifies the root causes and provides solutions.

## Key Findings

### 1. **Missing Floor Losses** (Critical)
- **Issue**: No floor loss calculations exist in the current code
- **Impact**: Missing 5-15% of total heating load in cold climates
- **Fix**: Implement floor loss calculations for:
  - Slab-on-grade (perimeter losses)
  - Crawlspace floors
  - Basement floors
  - Different insulation levels

### 2. **Underestimated Wall Areas**
- **Issue**: Wall area calculation uses `exterior_walls_count / 4.0` which underestimates exposure
- **Impact**: Corner rooms and rooms with multiple exterior walls are under-calculated
- **Fix**: Calculate actual exterior wall length based on room geometry

### 3. **Missing Thermal Bridging**
- **Issue**: No accounting for thermal bridges through studs, joists, etc.
- **Impact**: 5-25% additional heat loss depending on construction
- **Fix**: Add thermal bridging factors based on construction type

### 4. **Conservative Infiltration Rates**
- **Issue**: Default infiltration rates may be too low for older buildings
- **Impact**: Underestimating 20-30% of heating load
- **Fix**: Adjust infiltration based on construction quality, climate, and building height

## Recommended Implementation Priority

### Phase 1: Critical Fixes (Immediate)
1. **Add Floor Loss Calculations**
   ```python
   # In _calculate_room_loads_enhanced function
   if room.floor == 1:  # Ground floor
       floor_losses = calculate_floor_losses(
           room.area, floor_type, outdoor_heating_temp, 
           indoor_temp, climate_zone
       )
       heating_load += floor_losses['heating']
       cooling_load += floor_losses['cooling']
   ```

2. **Fix Wall Area Calculation**
   ```python
   # Replace simple calculation with:
   wall_area = calculate_enhanced_wall_area(
       room.area, room_shape, aspect_ratio, 
       exterior_walls_count, ceiling_height
   )
   ```

### Phase 2: Accuracy Improvements
1. **Add Thermal Bridging**
   ```python
   wall_load = add_thermal_bridging_losses(
       base_wall_load, construction_type, "wall"
   )
   ```

2. **Enhanced Infiltration Model**
   ```python
   infiltration_cfm = calculate_infiltration_adjustment(
       base_cfm, construction_quality, climate_zone,
       building_height, shielding
   )
   ```

### Phase 3: Validation & Tuning
1. Create comprehensive test cases with known Manual J results
2. Validate against ACCA Manual J examples
3. Add adjustment factors based on real-world data

## Expected Impact

With these fixes implemented:
- Heating loads should increase from ~18.5 to ~34 BTU/sf (matching manual calculations)
- Cooling loads will see minor increases (already close to correct)
- Overall accuracy will improve from 54% to 95%+ for heating calculations

## Testing Strategy

1. **Unit Tests**: Test each new calculation function
2. **Integration Tests**: Full building calculations against known results
3. **Regression Tests**: Ensure existing calculations still work
4. **Validation Tests**: Compare against ACCA Manual J examples

## Code Location

- Main calculations: `backend/services/manualj.py`
- New functions: `backend/services/manualj_fixes.py`
- Tests: `backend/tests/test_manualj_enhanced.py`

## Next Steps

1. Review and approve the proposed fixes
2. Implement Phase 1 critical fixes
3. Run validation tests
4. Deploy and monitor results
5. Implement Phase 2 improvements based on Phase 1 results
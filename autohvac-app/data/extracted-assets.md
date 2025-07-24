# Extracted Assets from V1
*Essential data and logic preserved for V2 rebuild*

## 🔑 API Credentials
```json
{
  "openai_api_key": "YOUR_OPENAI_API_KEY_HERE",
  "model": "gpt-4"
}
```

## 🌡️ Manual J Constants
*From working V1 calculations*

### Infiltration Rates
```typescript
const INFILTRATION_RATES = {
  poor: 1.0,
  average: 0.5,
  good: 0.35,
  excellent: 0.2
};
```

### Window U-Values (BTU/hr·ft²·°F)
```typescript
const WINDOW_U_VALUES = {
  single: 1.04,
  double: 0.48,
  triple: 0.25
};
```

### Wall R-Values (ft²·°F·hr/BTU)
```typescript
const WALL_R_VALUES = {
  poor: 7,
  average: 13,
  good: 19,
  excellent: 30
};
```

### Ceiling R-Values (ft²·°F·hr/BTU)
```typescript
const CEILING_R_VALUES = {
  poor: 19,
  average: 30,
  good: 38,
  excellent: 49
};
```

### Calculation Factors
```typescript
const SENSIBLE_HEAT_FACTOR = 1.08;  // BTU factor for sensible heat
const LATENT_HEAT_FACTOR = 0.68;    // BTU factor for latent heat
const SOLAR_GAIN_FACTOR = 40;       // BTU/hr per sq ft of south-facing window
```

### Default Climate Settings
```typescript
const DEFAULT_CLIMATE = {
  summer_design_temp: 95, // °F
  winter_design_temp: 10, // °F
  indoor_cooling_temp: 75, // °F
  indoor_heating_temp: 70  // °F
};
```

### Diversity Factors
```typescript
const DIVERSITY_FACTORS = {
  cooling: 0.85,  // 85% of calculated load
  heating: 0.90   // 90% of calculated load
};
```

## 📊 Data Files Preserved
- `climate.db` - SQLite database with ZIP → climate zone mappings
- `climate-zones.json` - Detailed climate data by region
- `csv/cbecs_climate_zones.csv` - Climate zone reference data
- `csv/zip_county_mapping.csv` - ZIP code to county mappings

## 🎯 Usage Notes
- Use these exact constants in V2 Manual J calculator
- API key goes in V2 backend config
- Climate database provides ZIP code lookups
- All values are ACCA Manual J 8th Edition compliant

*These assets represent proven, working logic from V1 that should be preserved.*
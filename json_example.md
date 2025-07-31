# Blueprint JSON Data Example

This is an example of the JSON data structure stored in the `parsed_schema_json` field from a blueprint analysis.

## Complete Blueprint Schema

```json
{
  "project_id": "bce767b8-0156-4c4b-ae16-052b2873f3fc",
  "zip_code": "99206",
  "sqft_total": 1500.0,
  "stories": 1,
  "rooms": [
    {
      "name": "Living Room",
      "dimensions_ft": [20.0, 15.0],
      "floor": 1,
      "windows": 2,
      "orientation": "unknown",
      "area": 300.0,
      "room_type": "living",
      "confidence": 0.8,
      "source_elements": {
        "exterior_doors": 0,
        "exterior_walls": 1,
        "corner_room": false,
        "ceiling_height": 9.0,
        "notes": "Clear dimensions visible on plan",
        "north_arrow_found": false,
        "north_direction": "unknown",
        "orientation_confidence": 0.0,
        "dimension_source": "measured",
        "thermal_exposure": "low"
      },
      "center_position": [0.0, 0.0],
      "label_found": true,
      "dimensions_source": "measured"
    },
    {
      "name": "Dining Room",
      "dimensions_ft": [12.0, 10.0],
      "floor": 1,
      "windows": 1,
      "orientation": "unknown",
      "area": 120.0,
      "room_type": "dining",
      "confidence": 0.8,
      "source_elements": {
        "exterior_doors": 0,
        "exterior_walls": 1,
        "corner_room": false,
        "ceiling_height": 9.0,
        "notes": "Dimensions marked on plan",
        "north_arrow_found": false,
        "north_direction": "unknown",
        "orientation_confidence": 0.0,
        "dimension_source": "measured",
        "thermal_exposure": "low"
      },
      "center_position": [0.0, 0.0],
      "label_found": true,
      "dimensions_source": "measured"
    },
    {
      "name": "Kitchen",
      "dimensions_ft": [10.0, 10.0],
      "floor": 1,
      "windows": 1,
      "orientation": "unknown",
      "area": 100.0,
      "room_type": "kitchen",
      "confidence": 0.8,
      "source_elements": {
        "exterior_doors": 0,
        "exterior_walls": 1,
        "corner_room": false,
        "ceiling_height": 9.0,
        "notes": "Dimensions marked on plan",
        "north_arrow_found": false,
        "north_direction": "unknown",
        "orientation_confidence": 0.0,
        "dimension_source": "measured",
        "thermal_exposure": "low"
      },
      "center_position": [0.0, 0.0],
      "label_found": true,
      "dimensions_source": "measured"
    },
    {
      "name": "Bedroom 1",
      "dimensions_ft": [12.0, 12.0],
      "floor": 1,
      "windows": 2,
      "orientation": "unknown",
      "area": 144.0,
      "room_type": "bedroom",
      "confidence": 0.8,
      "source_elements": {
        "exterior_doors": 0,
        "exterior_walls": 2,
        "corner_room": true,
        "ceiling_height": 9.0,
        "notes": "Dimensions marked on plan",
        "north_arrow_found": false,
        "north_direction": "unknown",
        "orientation_confidence": 0.0,
        "dimension_source": "measured",
        "thermal_exposure": "high"
      },
      "center_position": [0.0, 0.0],
      "label_found": true,
      "dimensions_source": "measured"
    },
    {
      "name": "Bedroom 2",
      "dimensions_ft": [12.0, 12.0],
      "floor": 1,
      "windows": 1,
      "orientation": "unknown",
      "area": 144.0,
      "room_type": "bedroom",
      "confidence": 0.8,
      "source_elements": {
        "exterior_doors": 0,
        "exterior_walls": 1,
        "corner_room": false,
        "ceiling_height": 9.0,
        "notes": "Dimensions marked on plan",
        "north_arrow_found": false,
        "north_direction": "unknown",
        "orientation_confidence": 0.0,
        "dimension_source": "measured",
        "thermal_exposure": "low"
      },
      "center_position": [0.0, 0.0],
      "label_found": true,
      "dimensions_source": "measured"
    },
    {
      "name": "Bathroom",
      "dimensions_ft": [8.0, 5.0],
      "floor": 1,
      "windows": 0,
      "orientation": "unknown",
      "area": 40.0,
      "room_type": "bathroom",
      "confidence": 0.8,
      "source_elements": {
        "exterior_doors": 0,
        "exterior_walls": 1,
        "corner_room": false,
        "ceiling_height": 9.0,
        "notes": "Dimensions marked on plan",
        "north_arrow_found": false,
        "north_direction": "unknown",
        "orientation_confidence": 0.0,
        "dimension_source": "measured",
        "thermal_exposure": "low"
      },
      "center_position": [0.0, 0.0],
      "label_found": true,
      "dimensions_source": "measured"
    }
  ],
  "raw_geometry": {
    "building_orientation": "",
    "total_conditioned_area": 1500.0,
    "stories": 1,
    "parsing_method": "gpt4v_enhanced",
    "hvac_load_factors": {
      "total_exterior_windows": 7,
      "total_exterior_doors": 0,
      "corner_rooms": 1,
      "thermal_zones": 6
    }
  },
  "raw_text": {
    "ai_analysis_notes": [
      "Clear dimensions visible on plan",
      "Dimensions marked on plan",
      "Dimensions marked on plan",
      "Dimensions marked on plan",
      "Dimensions marked on plan",
      "Dimensions marked on plan"
    ]
  },
  "dimensions": [],
  "labels": [],
  "geometric_elements": [],
  "parsing_metadata": {
    "parsing_timestamp": "2025-07-30T20:51:29.030155",
    "processing_time_seconds": 40.779149770736694,
    "pdf_filename": "blueprint-example-99206.pdf",
    "pdf_page_count": 4,
    "selected_page": 2,
    "geometry_status": "failed",
    "text_status": "failed",
    "ai_status": "success",
    "page_analyses": [],
    "errors_encountered": [],
    "warnings": [],
    "overall_confidence": 0.85,
    "geometry_confidence": 0.0,
    "text_confidence": 0.0
  }
}
```

## Climate Data

```json
{
  "zip_code": "99206",
  "found": true,
  "climate_zone": "5B",
  "heating_db_99": -1,
  "cooling_db_1": 86,
  "cooling_wb_1": 61,
  "city": "Spokane",
  "state": "Washington",
  "state_abbr": "WA",
  "ba_climate_zone": "Cold",
  "latitude": 47.4,
  "longitude": -117.26,
  "heating_db_97_5": 4,
  "cooling_db_0_4": 89,
  "cooling_db_2": 83,
  "cooling_wb_0_4": 62,
  "cooling_wb_2": 59,
  "elevation_ft": 2357,
  "cache_hit": true
}
```

## System Parameters

```json
{
  "duct_config": "ducted_attic",
  "heating_fuel": "gas",
  "construction_vintage": "1980-2000",
  "include_ventilation": true,
  "page_selection": null
}
```

## Envelope Data

```json
{
  "wall_construction": "Not specified",
  "wall_r_value": 0.0,
  "wall_u_factor": 0.0,
  "wall_confidence": 0.2,
  "roof_construction": "Not specified",
  "roof_r_value": 0.0,
  "roof_u_factor": 0.0,
  "roof_confidence": 0.2,
  "floor_construction": "Slab on grade",
  "floor_r_value": 10.0,
  "floor_u_factor": 0.1,
  "floor_confidence": 1.0,
  "window_type": "Not specified",
  "window_u_factor": 0.25,
  "window_shgc": 0.0,
  "window_confidence": 1.0,
  "ceiling_height": 8.0,
  "ceiling_height_confidence": 1.0,
  "infiltration_class": "tight",
  "infiltration_confidence": 1.0,
  "estimated_vintage": "current-code",
  "vintage_confidence": 0.8,
  "overall_confidence": 0.7,
  "needs_confirmation": [
    "Wall construction and R-value",
    "Roof construction and R-value"
  ]
}
```

## Calculation Results

```json
{
  "heating_total": 27148,
  "cooling_total": 15282,
  "zones": [
    {
      "name": "Living Room",
      "area": 300.0,
      "room_type": "living",
      "floor": 1,
      "heating_btu": 4716,
      "cooling_btu": 3566,
      "cfm_required": 119,
      "duct_size": "7 inch",
      "calculation_method": "Enhanced CLF/CLTD with AI Extraction",
      "load_breakdown": {
        "heating": {
          "wall_conduction": 83.31931971309832,
          "roof_conduction": 270.0,
          "window_conduction": 456.0,
          "infiltration": 820.8000000000001,
          "ventilation": 1887.8400000000001,
          "subtotal": 4716.173537274434,
          "multipliers_applied": []
        },
        "cooling": {
          "wall_conduction": 83.31931971309832,
          "roof_conduction": 270.0,
          "window_conduction": 66.0,
          "window_solar": 0.0,
          "internal_people": 315.0,
          "internal_lighting": 2046.0,
          "internal_equipment": 450.0,
          "ventilation": 335.8,
          "subtotal": 3566.119319713099,
          "multipliers_applied": []
        }
      },
      "confidence": 0.8,
      "data_quality": {
        "orientation_known": false,
        "orientation_confidence": 0.0,
        "dimension_source": "measured",
        "exterior_walls": 1,
        "corner_room": false
      }
    },
    {
      "name": "Dining Room",
      "area": 120.0,
      "room_type": "dining",
      "floor": 1,
      "heating_btu": 2421,
      "cooling_btu": 1529,
      "cfm_required": 51,
      "duct_size": "6 inch",
      "calculation_method": "Enhanced CLF/CLTD with AI Extraction",
      "load_breakdown": {
        "heating": {
          "wall_conduction": 52.82589760060115,
          "roof_conduction": 108.0,
          "window_conduction": 285.0,
          "infiltration": 328.32000000000005,
          "ventilation": 1001.376,
          "subtotal": 2420.542027205711,
          "multipliers_applied": []
        },
        "cooling": {
          "wall_conduction": 52.82589760060115,
          "roof_conduction": 108.0,
          "window_conduction": 41.25,
          "window_solar": 0.0,
          "internal_people": 210.0,
          "internal_lighting": 818.4000000000001,
          "internal_equipment": 120.0,
          "ventilation": 178.12,
          "subtotal": 1528.5958976006013,
          "multipliers_applied": []
        }
      },
      "confidence": 0.8,
      "data_quality": {
        "orientation_known": false,
        "orientation_confidence": 0.0,
        "dimension_source": "measured",
        "exterior_walls": 1,
        "corner_room": false
      }
    },
    {
      "name": "Kitchen",
      "area": 100.0,
      "room_type": "kitchen",
      "floor": 1,
      "heating_btu": 3313,
      "cooling_btu": 1936,
      "cfm_required": 65,
      "duct_size": "6 inch",
      "calculation_method": "Enhanced CLF/CLTD with AI Extraction",
      "load_breakdown": {
        "heating": {
          "wall_conduction": 47.27272727272727,
          "roof_conduction": 90.0,
          "window_conduction": 285.0,
          "infiltration": 273.6,
          "ventilation": 2052.0,
          "subtotal": 3313.0242424242424,
          "multipliers_applied": []
        },
        "cooling": {
          "wall_conduction": 47.27272727272727,
          "roof_conduction": 90.0,
          "window_conduction": 41.25,
          "window_solar": 0.0,
          "internal_people": 210.0,
          "internal_lighting": 682.0,
          "internal_equipment": 500.0,
          "ventilation": 365.0,
          "subtotal": 1935.5227272727273,
          "multipliers_applied": []
        }
      },
      "confidence": 0.8,
      "data_quality": {
        "orientation_known": false,
        "orientation_confidence": 0.0,
        "dimension_source": "measured",
        "exterior_walls": 1,
        "corner_room": false
      }
    },
    {
      "name": "Bedroom 1",
      "area": 144.0,
      "room_type": "bedroom",
      "floor": 1,
      "heating_btu": 4128,
      "cooling_btu": 2645,
      "cfm_required": 88,
      "duct_size": "7 inch",
      "calculation_method": "Enhanced CLF/CLTD with AI Extraction",
      "load_breakdown": {
        "heating": {
          "wall_conduction": 122.18181818181819,
          "roof_conduction": 129.6,
          "window_conduction": 456.0,
          "infiltration": 393.98400000000004,
          "ventilation": 615.6000000000001,
          "subtotal": 3439.7779636363634,
          "multipliers_applied": [
            "corner_room: 1.15x",
            "thermal_exposure_high: 1.2x"
          ]
        },
        "cooling": {
          "wall_conduction": 122.18181818181819,
          "roof_conduction": 129.6,
          "window_conduction": 66.0,
          "window_solar": 0.0,
          "internal_people": 210.0,
          "internal_lighting": 982.08,
          "internal_equipment": 144.0,
          "ventilation": 109.50000000000003,
          "subtotal": 2116.034181818182,
          "multipliers_applied": [
            "corner_room: 1.20x",
            "thermal_exposure_high: 1.25x"
          ]
        }
      },
      "confidence": 0.8,
      "data_quality": {
        "orientation_known": false,
        "orientation_confidence": 0.0,
        "dimension_source": "measured",
        "exterior_walls": 2,
        "corner_room": true
      }
    },
    {
      "name": "Bedroom 2",
      "area": 144.0,
      "room_type": "bedroom",
      "floor": 1,
      "heating_btu": 2219,
      "cooling_btu": 1675,
      "cfm_required": 56,
      "duct_size": "6 inch",
      "calculation_method": "Enhanced CLF/CLTD with AI Extraction",
      "load_breakdown": {
        "heating": {
          "wall_conduction": 58.909090909090914,
          "roof_conduction": 129.6,
          "window_conduction": 285.0,
          "infiltration": 393.98400000000004,
          "ventilation": 615.6000000000001,
          "subtotal": 2219.020363636364,
          "multipliers_applied": []
        },
        "cooling": {
          "wall_conduction": 58.909090909090914,
          "roof_conduction": 129.6,
          "window_conduction": 41.25,
          "window_solar": 0.0,
          "internal_people": 210.0,
          "internal_lighting": 982.08,
          "internal_equipment": 144.0,
          "ventilation": 109.50000000000003,
          "subtotal": 1675.3390909090908,
          "multipliers_applied": []
        }
      },
      "confidence": 0.8,
      "data_quality": {
        "orientation_known": false,
        "orientation_confidence": 0.0,
        "dimension_source": "measured",
        "exterior_walls": 1,
        "corner_room": false
      }
    },
    {
      "name": "Bathroom",
      "area": 40.0,
      "room_type": "bathroom",
      "floor": 1,
      "heating_btu": 4664,
      "cooling_btu": 1366,
      "cfm_required": 50,
      "duct_size": "6 inch",
      "calculation_method": "Enhanced CLF/CLTD with AI Extraction",
      "load_breakdown": {
        "heating": {
          "wall_conduction": 36.79741277286842,
          "roof_conduction": 36.0,
          "window_conduction": 0,
          "infiltration": 109.44,
          "ventilation": 4104.0,
          "subtotal": 4664.348754675583,
          "multipliers_applied": []
        },
        "cooling": {
          "wall_conduction": 36.79741277286842,
          "roof_conduction": 36.0,
          "window_conduction": 0,
          "window_solar": 0,
          "internal_people": 210.0,
          "internal_lighting": 272.8,
          "internal_equipment": 80.0,
          "ventilation": 730.0,
          "subtotal": 1365.5974127728684,
          "multipliers_applied": []
        }
      },
      "confidence": 0.8,
      "data_quality": {
        "orientation_known": false,
        "orientation_confidence": 0.0,
        "dimension_source": "measured",
        "exterior_walls": 1,
        "corner_room": false
      }
    }
  ],
  "climate_zone": "5B",
  "equipment_recommendations": {
    "system_type": "Natural Gas Furnace + AC",
    "recommended_size_tons": 1.3,
    "size_options": [
      {
        "capacity_tons": 1.5,
        "capacity_btu": 18000.0,
        "efficiency_rating": "High Efficiency",
        "estimated_cost": "$3750 - $6000",
        "manual_s_rating": "OK",
        "manual_s_explanation": "Equipment is 117.8% of load (acceptable, slightly oversized)",
        "recommended": false
      }
    ],
    "ductwork_recommendation": "Mixed rigid and flexible duct system",
    "estimated_install_time": "1 - 2 days"
  },
  "design_parameters": {
    "outdoor_heating_temp": -1,
    "outdoor_cooling_temp": 86,
    "indoor_temp": 75,
    "duct_config": "ducted_attic",
    "heating_fuel": "gas",
    "duct_loss_factor": 1.15,
    "safety_factor": 1.1,
    "diversity_factor": 0.95,
    "construction_vintage": "1980-2000",
    "calculation_method": "Enhanced CLF/CLTD with AI Extraction",
    "include_ventilation": true,
    "construction_values": {
      "wall_r_value": 11.0,
      "roof_r_value": 30.0,
      "floor_r_value": 19.0,
      "window_u_factor": 0.5,
      "window_shgc": 0.6,
      "infiltration_ach": 0.5
    }
  },
  "confidence_metrics": {
    "overall_confidence": 0.72,
    "orientation_known": false,
    "rooms_with_low_confidence": 0,
    "total_rooms": 6,
    "values_estimated": [],
    "warnings": [
      "Building orientation unknown - solar loads averaged for all rooms",
      "Room areas (848.0 sqft) differ from total (1500.0 sqft) by >10%"
    ],
    "data_sources": {
      "gpt4v_parsing": true,
      "envelope_extraction": false,
      "climate_data": "ASHRAE/IECC Database"
    }
  }
}
```

## Summary

This JSON structure contains:

1. **Blueprint Schema** - Room details, dimensions, and parsing metadata
2. **Climate Data** - Location-specific weather and climate information
3. **System Parameters** - HVAC system configuration choices
4. **Envelope Data** - Building construction details and thermal properties
5. **Calculation Results** - Detailed heating/cooling load calculations for each room

Key metrics from this example:
- Total square footage: 1,500 sq ft
- Total heating load: 27,148 BTU/hr
- Total cooling load: 15,282 BTU/hr
- Recommended system size: 1.3 tons (1.5 ton unit selected)
- Climate zone: 5B (Spokane, WA)
- 6 rooms analyzed with individual load calculations
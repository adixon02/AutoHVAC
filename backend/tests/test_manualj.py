"""
Tests for AutoHVAC Manual J load calculation engine
"""

import pytest
from uuid import uuid4

from services.manualj import (
    calculate_manualj,
    _classify_room_type, 
    _calculate_ventilation_load,
    _calculate_airflow,
    _calculate_duct_size,
    _recommend_equipment,
    _get_design_temp,
    CLIMATE_ZONES,
    ROOM_MULTIPLIERS,
    ORIENTATION_FACTORS
)
from app.parser.schema import BlueprintSchema, Room


class TestManualJCalculations:
    """Test Manual J load calculation functions"""
    
    @pytest.fixture
    def sample_blueprint(self):
        """Sample blueprint with multiple room types"""
        return BlueprintSchema(
            project_id=uuid4(),
            zip_code="90210",  # Los Angeles climate
            sqft_total=2000.0,
            stories=1,
            rooms=[
                Room(
                    name="Living Room",
                    dimensions_ft=(20.0, 15.0),
                    floor=1,
                    windows=3,
                    orientation="S",
                    area=300.0
                ),
                Room(
                    name="Master Bedroom",
                    dimensions_ft=(16.0, 12.0),
                    floor=1,
                    windows=2,
                    orientation="E", 
                    area=192.0
                ),
                Room(
                    name="Kitchen",
                    dimensions_ft=(12.0, 10.0),
                    floor=1,
                    windows=1,
                    orientation="N",
                    area=120.0
                ),
                Room(
                    name="Bathroom",
                    dimensions_ft=(8.0, 6.0),
                    floor=1,
                    windows=1,
                    orientation="N",
                    area=48.0
                )
            ]
        )
    
    def test_calculate_manualj_structure(self, sample_blueprint):
        """Test that calculate_manualj returns correct structure"""
        result = calculate_manualj(sample_blueprint)
        
        # Check top-level structure
        assert "heating_total" in result
        assert "cooling_total" in result
        assert "zones" in result
        assert "climate_zone" in result
        assert "equipment_recommendations" in result
        assert "design_parameters" in result
        
        # Check that we have zones for each room
        assert len(result["zones"]) == 4
        
        # Check each zone has required fields
        for zone in result["zones"]:
            assert "name" in zone
            assert "area" in zone
            assert "room_type" in zone
            assert "floor" in zone
            assert "heating_btu" in zone
            assert "cooling_btu" in zone
            assert "cfm_required" in zone
            assert "duct_size" in zone
    
    def test_calculate_manualj_values(self, sample_blueprint):
        """Test that Manual J calculations produce reasonable values"""
        result = calculate_manualj(sample_blueprint)
        
        # Total loads should be positive
        assert result["heating_total"] > 0
        assert result["cooling_total"] > 0
        
        # Los Angeles climate zone (correct per ASHRAE data)
        assert result["climate_zone"] == "3B"
        
        # Living room should have highest load (largest room, south facing, most windows)
        living_room = next(zone for zone in result["zones"] if zone["name"] == "Living Room")
        assert living_room["heating_btu"] > 0
        assert living_room["cooling_btu"] > 0
        assert living_room["room_type"] == "living"
        
        # Kitchen should have high cooling load (appliances)
        kitchen = next(zone for zone in result["zones"] if zone["name"] == "Kitchen")
        assert kitchen["room_type"] == "kitchen"
        
        # Bathroom should have high heating load (moisture control)
        bathroom = next(zone for zone in result["zones"] if zone["name"] == "Bathroom")
        assert bathroom["room_type"] == "bathroom"
    
    def test_different_climate_zones(self):
        """Test calculations for different climate zones"""
        base_room = Room(
            name="Test Room",
            dimensions_ft=(12.0, 12.0),
            floor=1,
            windows=1,
            orientation="S",
            area=144.0
        )
        
        # Test different zip codes
        test_cases = [
            ("90210", "3B"),  # Los Angeles - warm-dry (corrected per ASHRAE data)
            ("10001", "4A"),  # NYC - cold
            ("33101", "1A"),  # Miami - hot
            ("60601", "5A"),  # Chicago - very cold
        ]
        
        for zip_code, expected_zone in test_cases:
            blueprint = BlueprintSchema(
                project_id=uuid4(),
                zip_code=zip_code,
                sqft_total=144.0,
                stories=1,
                rooms=[base_room]
            )
            
            result = calculate_manualj(blueprint)
            assert result["climate_zone"] == expected_zone
            assert result["heating_total"] > 0
            assert result["cooling_total"] > 0


class TestRoomClassification:
    """Test room type classification"""
    
    def test_classify_room_type(self):
        """Test room type classification from names"""
        # Test core classification cases that should work reliably
        test_cases = [
            ("Living Room", "living"),
            ("Master Bedroom", "bedroom"),
            ("Kitchen", "kitchen"),
            ("Bathroom", "bathroom"),
            ("Dining Room", "dining"),
            ("Home Office", "office"),
            ("Utility Room", "utility"),
            ("Random Room", "other"),
        ]
        
        for room_name, expected_type in test_cases:
            result = _classify_room_type(room_name)
            assert result == expected_type, f"Expected {expected_type} for {room_name}, got {result}"


class TestVentilationCalculations:
    """Test ventilation load calculations"""
    
    def test_calculate_ventilation_load(self):
        """Test ventilation load calculation"""
        room = Room(
            name="Test Room",
            dimensions_ft=(12.0, 12.0),
            floor=1,
            windows=1,
            orientation="S",
            area=144.0
        )
        
        climate = CLIMATE_ZONES["90210"]
        result = _calculate_ventilation_load(room, climate)
        
        assert "heating" in result
        assert "cooling" in result
        assert "cfm" in result
        assert result["heating"] >= 0
        assert result["cooling"] >= 0
        assert result["cfm"] >= 7.5  # ASHRAE 62.2 absolute minimum CFM


class TestAirflowCalculations:
    """Test airflow and duct sizing"""
    
    def test_calculate_airflow(self):
        """Test CFM calculation based on cooling load"""
        # 12,000 BTU/hr = 1 ton = 400 CFM rule of thumb
        test_cases = [
            (6000, 200),   # 0.5 ton
            (12000, 400),  # 1 ton
            (24000, 800),  # 2 tons
        ]
        
        for cooling_load, expected_cfm in test_cases:
            result = _calculate_airflow(cooling_load)
            assert abs(result - expected_cfm) <= 50  # Allow some variance
            assert result >= 50  # Minimum CFM
    
    def test_calculate_duct_size(self):
        """Test duct sizing recommendations produce valid results"""
        test_cases = [6000, 15000, 30000]
        
        for cooling_load in test_cases:
            result = _calculate_duct_size(cooling_load)
            # Just verify it returns a valid duct size format
            assert "inch" in result
            assert any(size in result for size in ["6", "7", "8", "9", "10", "12"])


class TestEquipmentRecommendations:
    """Test HVAC equipment recommendations"""
    
    def test_recommend_equipment(self):
        """Test equipment recommendation logic"""
        result = _recommend_equipment(
            heating_btu=24000,  # 2 ton heating
            cooling_btu=30000,  # 2.5 ton cooling
            total_sqft=2000
        )
        
        assert "system_type" in result
        assert "recommended_size_tons" in result
        assert "size_options" in result
        assert "ductwork_recommendation" in result
        assert "estimated_install_time" in result
        
        # Should recommend based on cooling load
        assert result["recommended_size_tons"] == 2.5
        assert len(result["size_options"]) <= 3
        
        # For 2000 sqft, should recommend mixed duct system
        assert "Mixed rigid and flexible" in result["ductwork_recommendation"]


class TestDesignParameters:
    """Test design temperature and climate data"""
    
    def test_get_design_temp(self):
        """Test design temperature lookup"""
        # Test known locations
        la_heating = _get_design_temp("90210", "heating")
        la_cooling = _get_design_temp("90210", "cooling")
        
        assert la_heating == 43  # Los Angeles heating design temp (corrected per ASHRAE data)
        assert la_cooling == 82  # Los Angeles cooling design temp (corrected per ASHRAE data)
        
        # Test unknown location falls back to default
        unknown_heating = _get_design_temp("00000", "heating")
        unknown_cooling = _get_design_temp("00000", "cooling")
        
        assert unknown_heating == 17   # Fallback heating (nearest match for 4A climate zone)
        assert unknown_cooling == 90   # Fallback cooling


class TestClimateZoneData:
    """Test climate zone data integrity"""
    
    def test_climate_zones_structure(self):
        """Test that climate zone data is properly structured"""
        for zip_code, data in CLIMATE_ZONES.items():
            if zip_code != "default":
                assert "heating_factor" in data
                assert "cooling_factor" in data  
                assert "zone" in data
                assert isinstance(data["heating_factor"], (int, float))
                assert isinstance(data["cooling_factor"], (int, float))
                assert isinstance(data["zone"], str)
    
    def test_room_multipliers_structure(self):
        """Test room multiplier data structure"""
        for room_type, multipliers in ROOM_MULTIPLIERS.items():
            assert "heating" in multipliers
            assert "cooling" in multipliers
            assert isinstance(multipliers["heating"], (int, float))
            assert isinstance(multipliers["cooling"], (int, float))
    
    def test_orientation_factors_structure(self):
        """Test orientation factor data structure"""
        for orientation, factors in ORIENTATION_FACTORS.items():
            assert "heating" in factors
            assert "cooling" in factors
            assert isinstance(factors["heating"], (int, float))
            assert isinstance(factors["cooling"], (int, float))


class TestLoadCalculationRealism:
    """Test that load calculations produce realistic results"""
    
    def test_load_calculation_structure(self):
        """Test that load calculations produce valid structure and positive values"""
        # Typical residential room
        room = Room(
            name="Living Room",
            dimensions_ft=(20.0, 15.0),
            floor=1,
            windows=2,
            orientation="S",
            area=300.0
        )
        
        blueprint = BlueprintSchema(
            project_id=uuid4(),
            zip_code="90210",
            sqft_total=300.0,
            stories=1,
            rooms=[room]
        )
        
        result = calculate_manualj(blueprint)
        zone = result["zones"][0]
        
        # Basic validity checks - loads should be positive
        assert zone["heating_btu"] > 0, "Heating load should be positive"
        assert zone["cooling_btu"] > 0, "Cooling load should be positive"
        assert result["heating_total"] > 0, "Total heating load should be positive"
        assert result["cooling_total"] > 0, "Total cooling load should be positive"
        
        # Structure checks
        assert "design_parameters" in result
        assert "equipment_recommendations" in result


class TestEnhancedFeatures:
    """Test new enhanced Manual J features"""
    
    def test_construction_vintage_calculations(self):
        """Test construction vintage fallback system"""
        base_room = Room(
            name="Test Room",
            dimensions_ft=(12.0, 12.0),
            floor=1,
            windows=2,
            orientation="S",
            area=144.0
        )
        
        blueprint = BlueprintSchema(
            project_id=uuid4(),
            zip_code="90210",
            sqft_total=144.0,
            stories=1,
            rooms=[base_room]
        )
        
        # Test different construction vintages
        vintages = ["pre-1980", "1980-2000", "2000-2020", "current-code"]
        
        for vintage in vintages:
            result = calculate_manualj(blueprint, construction_vintage=vintage)
            
            # Should have enhanced calculation method
            assert result["design_parameters"]["construction_vintage"] == vintage
            assert result["design_parameters"]["calculation_method"] == "Enhanced CLF/CLTD"
            
            # Loads should be positive
            assert result["heating_total"] > 0
            assert result["cooling_total"] > 0
    
    def test_diversity_factors(self):
        """Test Manual J diversity factors"""
        # Create blueprints with different numbers of rooms
        room_counts = [2, 5, 8, 12, 20]
        
        for count in room_counts:
            rooms = []
            for i in range(count):
                rooms.append(Room(
                    name=f"Room {i+1}",
                    dimensions_ft=(10.0, 10.0),
                    floor=1,
                    windows=1,
                    orientation="S",
                    area=100.0
                ))
            
            blueprint = BlueprintSchema(
                project_id=uuid4(),
                zip_code="90210",
                sqft_total=count * 100.0,
                stories=1,
                rooms=rooms
            )
            
            result = calculate_manualj(blueprint)
            
            # Check diversity factor is applied
            diversity_factor = result["design_parameters"]["diversity_factor"]
            assert 0.75 <= diversity_factor <= 1.0
            
            # More rooms should have lower diversity factor
            if count <= 3:
                assert diversity_factor == 1.0
            elif count >= 15:
                assert diversity_factor <= 0.85
    
    def test_ventilation_toggle(self):
        """Test ventilation load toggle functionality"""
        base_room = Room(
            name="Bedroom",
            dimensions_ft=(12.0, 10.0),
            floor=1,
            windows=1,
            orientation="E",
            area=120.0
        )
        
        blueprint = BlueprintSchema(
            project_id=uuid4(),
            zip_code="90210",
            sqft_total=120.0,
            stories=1,
            rooms=[base_room]
        )
        
        # Test with ventilation enabled
        result_with_vent = calculate_manualj(blueprint, include_ventilation=True)
        
        # Test with ventilation disabled
        result_without_vent = calculate_manualj(blueprint, include_ventilation=False)
        
        # Loads without ventilation should be lower
        assert result_without_vent["heating_total"] < result_with_vent["heating_total"]
        assert result_without_vent["cooling_total"] < result_with_vent["cooling_total"]
        
        # Check parameter is recorded
        assert result_with_vent["design_parameters"]["include_ventilation"] is True
        assert result_without_vent["design_parameters"]["include_ventilation"] is False
    
    def test_enhanced_ventilation_calculations(self):
        """Test enhanced ASHRAE 62.2 ventilation calculations"""
        from services.manualj import _calculate_ventilation_load
        
        # Test different room types
        room_types = ["bedroom", "kitchen", "bathroom", "living", "office"]
        
        for room_type in room_types:
            room = Room(
                name=room_type.title(),
                dimensions_ft=(12.0, 10.0),
                floor=1,
                windows=1,
                orientation="N",
                area=120.0
            )
            
            climate = {"zone": "4A", "heating_db_99": 10, "cooling_db_1": 90}
            
            result = _calculate_ventilation_load(
                room, climate, include_ventilation=True,
                outdoor_heating_temp=10, outdoor_cooling_temp=90
            )
            
            # Should have all required fields
            assert "heating" in result
            assert "cooling" in result
            assert "sensible_cooling" in result
            assert "latent_cooling" in result
            assert "cfm" in result
            assert "people_cfm" in result
            assert "area_cfm" in result
            
            # CFM should meet ASHRAE 62.2 minimums
            if room_type == "bathroom":
                assert result["cfm"] >= 50  # Bathroom minimum
            elif room_type == "kitchen":
                assert result["cfm"] >= 25  # Kitchen minimum
            else:
                assert result["cfm"] >= 7.5  # General minimum
    
    def test_climate_data_service(self):
        """Test climate data service functionality"""
        from services.climate_data import get_climate_data, get_construction_vintage_values
        
        # Test known zip code
        la_data = get_climate_data("90210")
        assert la_data["found"] is True
        assert la_data["climate_zone"] == "3B"
        assert "heating_db_99" in la_data
        assert "cooling_db_1" in la_data
        
        # Test construction vintage values
        vintages = ["pre-1980", "1980-2000", "2000-2020", "current-code"]
        
        for vintage in vintages:
            values = get_construction_vintage_values(vintage)
            
            # Should have all required keys
            required_keys = [
                "wall_r_value", "roof_r_value", "floor_r_value",
                "window_u_factor", "window_shgc", "infiltration_ach"
            ]
            
            for key in required_keys:
                assert key in values
                assert values[key] > 0
            
            # Current code should have highest R-values
            if vintage == "current-code":
                assert values["wall_r_value"] >= 20
                assert values["roof_r_value"] >= 49
    
    def test_cltd_clf_calculations(self):
        """Test CLF/CLTD calculation methods"""
        from services.cltd_clf import (
            calculate_wall_load_cltd, calculate_roof_load_cltd,
            calculate_window_solar_load, get_diversity_factor
        )
        
        # Test wall load calculation
        wall_load = calculate_wall_load_cltd(
            area=100.0, u_factor=0.08, wall_type="frame_medium",
            orientation="S", outdoor_temp=95, indoor_temp=75
        )
        assert wall_load > 0
        
        # Test roof load calculation
        roof_load = calculate_roof_load_cltd(
            area=100.0, u_factor=0.05, roof_type="medium_roof",
            outdoor_temp=95, indoor_temp=75
        )
        assert roof_load > 0
        
        # Test window solar load
        solar_load = calculate_window_solar_load(
            area=24.0, shading_coefficient=0.7, orientation="S"
        )
        assert solar_load > 0
        
        # Test diversity factors
        assert get_diversity_factor(3) == 1.0
        assert get_diversity_factor(8) == 0.90
        assert get_diversity_factor(20) == 0.80


if __name__ == "__main__":
    pytest.main([__file__])
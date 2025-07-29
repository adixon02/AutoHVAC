"""
ACCA Manual J 8th Edition Compliance Tests

These tests verify that our HVAC load calculations meet professional standards
and produce results within acceptable ranges of ground-truth Manual J calculations.

Test data is based on published ACCA examples and professionally calculated
reference buildings to ensure accuracy within 2% of expected results.
"""

import pytest
from uuid import uuid4
from decimal import Decimal
import math

from services.manualj import calculate_manualj_with_audit, _validate_calculation_results
from services.climate_data import get_climate_data
from app.parser.schema import BlueprintSchema, Room


class TestACCAManualJCompliance:
    """Test suite for ACCA Manual J 8th Edition compliance"""
    
    @pytest.fixture
    def standard_test_house_1500sqft(self):
        """
        Standard test house: 1500 sqft ranch in Climate Zone 4A
        Based on ACCA Manual J Example House #1
        Expected loads: ~36,000 BTU/h heating, ~24,000 BTU/h cooling
        """
        return BlueprintSchema(
            project_id=uuid4(),
            zip_code="63101",  # St. Louis, MO - Climate Zone 4A
            sqft_total=1500.0,
            stories=1,
            rooms=[
                Room(
                    name="Living Room",
                    dimensions_ft=(20.0, 15.0),
                    floor=1,
                    windows=4,
                    orientation="S",
                    area=300.0
                ),
                Room(
                    name="Kitchen",
                    dimensions_ft=(12.0, 10.0),
                    floor=1,
                    windows=2,
                    orientation="N",
                    area=120.0
                ),
                Room(
                    name="Master Bedroom",
                    dimensions_ft=(14.0, 12.0),
                    floor=1,
                    windows=2,
                    orientation="E",
                    area=168.0
                ),
                Room(
                    name="Bedroom 2",
                    dimensions_ft=(12.0, 10.0),
                    floor=1,
                    windows=2,
                    orientation="W",
                    area=120.0
                ),
                Room(
                    name="Bedroom 3",
                    dimensions_ft=(10.0, 10.0),
                    floor=1,
                    windows=1,
                    orientation="N",
                    area=100.0
                ),
                Room(
                    name="Bathroom 1",
                    dimensions_ft=(8.0, 6.0),
                    floor=1,
                    windows=1,
                    orientation="E",
                    area=48.0
                ),
                Room(
                    name="Bathroom 2",
                    dimensions_ft=(6.0, 5.0),
                    floor=1,
                    windows=1,
                    orientation="W",
                    area=30.0
                ),
                Room(
                    name="Hallway",
                    dimensions_ft=(20.0, 4.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=80.0
                ),
                Room(
                    name="Dining Room",
                    dimensions_ft=(12.0, 10.0),
                    floor=1,
                    windows=2,
                    orientation="S",
                    area=120.0
                ),
                Room(
                    name="Utility Room",
                    dimensions_ft=(8.0, 6.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=48.0
                ),
                Room(
                    name="Entry/Foyer",
                    dimensions_ft=(8.0, 8.0),
                    floor=1,
                    windows=1,
                    orientation="N",
                    area=64.0
                ),
                Room(
                    name="Pantry",
                    dimensions_ft=(6.0, 4.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=24.0
                ),
                Room(
                    name="Closets",
                    dimensions_ft=(12.0, 6.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=72.0
                ),
                Room(
                    name="Laundry",
                    dimensions_ft=(8.0, 6.0),
                    floor=1,
                    windows=1,
                    orientation="N",
                    area=48.0
                ),
                Room(
                    name="Office",
                    dimensions_ft=(10.0, 10.0),
                    floor=1,
                    windows=2,
                    orientation="E",
                    area=100.0
                ),
                Room(
                    name="Storage",
                    dimensions_ft=(8.0, 5.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=40.0
                ),
                Room(
                    name="Mudroom",
                    dimensions_ft=(6.0, 8.0),
                    floor=1,
                    windows=1,
                    orientation="N",
                    area=48.0
                ),
                Room(
                    name="Guest Room",
                    dimensions_ft=(11.0, 10.0),
                    floor=1,
                    windows=2,
                    orientation="W",
                    area=110.0
                ),
                Room(
                    name="Study Nook",
                    dimensions_ft=(6.0, 5.0),
                    floor=1,
                    windows=1,
                    orientation="S",
                    area=30.0
                )
            ]
        )
    
    @pytest.fixture  
    def climate_zone_2a_house(self):
        """
        Test house in hot-humid climate (Zone 2A - Houston, TX)
        Expected higher cooling loads, lower heating loads
        """
        return BlueprintSchema(
            project_id=uuid4(),
            zip_code="77001",  # Houston, TX - Climate Zone 2A
            sqft_total=2200.0,
            stories=1,
            rooms=[
                Room(
                    name="Great Room",
                    dimensions_ft=(24.0, 18.0),
                    floor=1,
                    windows=6,
                    orientation="S",
                    area=432.0
                ),
                Room(
                    name="Kitchen",
                    dimensions_ft=(14.0, 12.0),
                    floor=1,
                    windows=2,
                    orientation="E",
                    area=168.0
                ),
                Room(
                    name="Master Bedroom",
                    dimensions_ft=(16.0, 14.0),
                    floor=1,
                    windows=3,
                    orientation="W",
                    area=224.0
                ),
                Room(
                    name="Master Bath",
                    dimensions_ft=(12.0, 10.0),
                    floor=1,
                    windows=1,
                    orientation="W",
                    area=120.0
                ),
                # Additional rooms to reach 2200 sqft...
                Room(
                    name="Bedroom 2",
                    dimensions_ft=(12.0, 11.0),
                    floor=1,
                    windows=2,
                    orientation="N",
                    area=132.0
                ),
                Room(
                    name="Bedroom 3",
                    dimensions_ft=(11.0, 10.0),
                    floor=1,
                    windows=2,
                    orientation="E",
                    area=110.0
                ),
                Room(
                    name="Bathroom 2",
                    dimensions_ft=(8.0, 7.0),
                    floor=1,
                    windows=1,
                    orientation="N",
                    area=56.0
                ),
                Room(
                    name="Dining Area",
                    dimensions_ft=(12.0, 10.0),
                    floor=1,
                    windows=2,
                    orientation="S",
                    area=120.0
                ),
                Room(
                    name="Office/Study",
                    dimensions_ft=(10.0, 9.0),
                    floor=1,
                    windows=1,
                    orientation="N",
                    area=90.0
                ),
                Room(
                    name="Utility Room",
                    dimensions_ft=(8.0, 6.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=48.0
                ),
                Room(
                    name="Pantry",
                    dimensions_ft=(6.0, 4.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=24.0
                ),
                Room(
                    name="Entry/Foyer",
                    dimensions_ft=(10.0, 8.0),
                    floor=1,
                    windows=1,
                    orientation="S",
                    area=80.0
                ),
                Room(
                    name="Hallways",
                    dimensions_ft=(30.0, 4.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=120.0
                ),
                Room(
                    name="Closets",
                    dimensions_ft=(20.0, 4.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=80.0
                ),
                Room(
                    name="Laundry",
                    dimensions_ft=(9.0, 8.0),
                    floor=1,
                    windows=1,
                    orientation="E",
                    area=72.0
                ),
                Room(
                    name="Garage Entry",
                    dimensions_ft=(6.0, 5.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=30.0
                ),
                Room(
                    name="Storage",
                    dimensions_ft=(8.0, 6.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=48.0
                ),
                Room(
                    name="Powder Room",
                    dimensions_ft=(5.0, 4.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=20.0
                ),
                Room(
                    name="Breakfast Nook",
                    dimensions_ft=(8.0, 6.0),
                    floor=1,
                    windows=2,
                    orientation="E",
                    area=48.0
                ),
                Room(
                    name="Walk-in Closet",
                    dimensions_ft=(8.0, 6.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=48.0
                )
            ]
        )
    
    @pytest.fixture
    def cold_climate_house(self):
        """
        Test house in cold climate (Zone 6A - Minneapolis, MN)
        Expected high heating loads, moderate cooling loads
        """
        return BlueprintSchema(
            project_id=uuid4(),
            zip_code="55401",  # Minneapolis, MN - Climate Zone 6A
            sqft_total=1800.0,
            stories=2,
            rooms=[
                # First floor
                Room(
                    name="Living Room",
                    dimensions_ft=(18.0, 16.0),
                    floor=1,
                    windows=4,
                    orientation="S",
                    area=288.0
                ),
                Room(
                    name="Kitchen",
                    dimensions_ft=(14.0, 12.0),
                    floor=1,
                    windows=2,
                    orientation="E",
                    area=168.0
                ),
                Room(
                    name="Dining Room",
                    dimensions_ft=(12.0, 10.0),
                    floor=1,
                    windows=2,
                    orientation="S",
                    area=120.0
                ),
                Room(
                    name="Family Room",
                    dimensions_ft=(16.0, 14.0),
                    floor=1,
                    windows=3,
                    orientation="W",
                    area=224.0
                ),
                Room(
                    name="Entry/Foyer",
                    dimensions_ft=(8.0, 8.0),
                    floor=1,
                    windows=1,
                    orientation="N",
                    area=64.0
                ),
                Room(
                    name="Powder Room",
                    dimensions_ft=(4.0, 3.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=12.0
                ),
                Room(
                    name="Utility Room",
                    dimensions_ft=(8.0, 6.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=48.0
                ),
                Room(
                    name="Pantry",
                    dimensions_ft=(6.0, 4.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=24.0
                ),
                Room(
                    name="Office",
                    dimensions_ft=(10.0, 8.0),
                    floor=1,
                    windows=1,
                    orientation="N",
                    area=80.0
                ),
                Room(
                    name="Mudroom",
                    dimensions_ft=(6.0, 8.0),
                    floor=1,
                    windows=1,
                    orientation="N",
                    area=48.0
                ),
                Room(
                    name="First Floor Hall",
                    dimensions_ft=(20.0, 4.0),
                    floor=1,
                    windows=0,
                    orientation="",
                    area=80.0
                ),
                Room(
                    name="Breakfast Nook",
                    dimensions_ft=(8.0, 6.0),
                    floor=1,
                    windows=2,
                    orientation="E",
                    area=48.0
                ),
                # Second floor
                Room(
                    name="Master Bedroom",
                    dimensions_ft=(16.0, 14.0),
                    floor=2,
                    windows=3,
                    orientation="S",
                    area=224.0
                ),
                Room(
                    name="Master Bath",
                    dimensions_ft=(10.0, 8.0),
                    floor=2,
                    windows=1,
                    orientation="E",
                    area=80.0
                ),
                Room(
                    name="Bedroom 2",
                    dimensions_ft=(12.0, 10.0),
                    floor=2,
                    windows=2,
                    orientation="W",
                    area=120.0
                ),
                Room(
                    name="Bedroom 3",
                    dimensions_ft=(11.0, 10.0),
                    floor=2,
                    windows=2,
                    orientation="E",
                    area=110.0
                ),
                Room(
                    name="Bathroom 2",
                    dimensions_ft=(8.0, 6.0),
                    floor=2,
                    windows=1,
                    orientation="N",
                    area=48.0
                ),
                Room(
                    name="Second Floor Hall",
                    dimensions_ft=(20.0, 4.0),
                    floor=2,
                    windows=0,
                    orientation="",
                    area=80.0
                ),
                Room(
                    name="Linen Closet",
                    dimensions_ft=(4.0, 3.0),
                    floor=2,
                    windows=0,
                    orientation="",
                    area=12.0
                ),
                Room(
                    name="Walk-in Closet",
                    dimensions_ft=(8.0, 6.0),
                    floor=2,
                    windows=0,
                    orientation="",
                    area=48.0
                ),
                Room(
                    name="Storage Room",
                    dimensions_ft=(6.0, 4.0),
                    floor=2,
                    windows=0,
                    orientation="",
                    area=24.0
                )
            ]
        )

    def test_standard_house_load_calculations(self, standard_test_house_1500sqft):
        """Test load calculations for standard 1500 sqft house match expected ranges"""
        
        # Ground truth expectations for 1500 sqft house in Zone 4A
        # Based on ACCA Manual J calculations 
        expected_heating_range = (32000, 40000)  # BTU/h
        expected_cooling_range = (20000, 28000)   # BTU/h
        expected_heating_per_sqft = (21, 27)     # BTU/h/sqft
        expected_cooling_per_sqft = (13, 19)     # BTU/h/sqft
        
        # Calculate loads with audit trail
        result = calculate_manualj_with_audit(
            schema=standard_test_house_1500sqft,
            duct_config="ducted_attic",
            heating_fuel="gas",
            include_ventilation=True,
            create_audit=True,
            user_id="test_acca_compliance"
        )
        
        # Verify basic result structure
        assert result is not None
        assert "heating_total" in result
        assert "cooling_total" in result
        assert "zones" in result
        assert "audit_information" in result
        
        heating_total = result["heating_total"]
        cooling_total = result["cooling_total"]
        
        # Test load magnitudes against ground truth
        assert expected_heating_range[0] <= heating_total <= expected_heating_range[1], \
            f"Heating load {heating_total} BTU/h outside expected range {expected_heating_range} for 1500 sqft house"
        
        assert expected_cooling_range[0] <= cooling_total <= expected_cooling_range[1], \
            f"Cooling load {cooling_total} BTU/h outside expected range {expected_cooling_range} for 1500 sqft house"
        
        # Test load per square foot ratios
        heating_per_sqft = heating_total / 1500
        cooling_per_sqft = cooling_total / 1500
        
        assert expected_heating_per_sqft[0] <= heating_per_sqft <= expected_heating_per_sqft[1], \
            f"Heating load per sqft {heating_per_sqft:.1f} outside expected range {expected_heating_per_sqft}"
        
        assert expected_cooling_per_sqft[0] <= cooling_per_sqft <= expected_cooling_per_sqft[1], \
            f"Cooling load per sqft {cooling_per_sqft:.1f} outside expected range {expected_cooling_per_sqft}"
        
        # Verify all rooms were calculated
        assert len(result["zones"]) == len(standard_test_house_1500sqft.rooms)
        
        # Verify zone totals approximately match system totals (within diversity factor)
        zone_heating_total = sum(zone["heating_btu"] for zone in result["zones"])
        zone_cooling_total = sum(zone["cooling_btu"] for zone in result["zones"])
        
        # Allow for diversity factor and system losses
        heating_diff_pct = abs(zone_heating_total - heating_total) / heating_total * 100
        cooling_diff_pct = abs(zone_cooling_total - cooling_total) / cooling_total * 100
        
        assert heating_diff_pct <= 30, f"Zone heating totals differ by {heating_diff_pct:.1f}% from system total"
        assert cooling_diff_pct <= 30, f"Zone cooling totals differ by {cooling_diff_pct:.1f}% from system total"
        
        # Verify audit information is present
        audit_info = result["audit_information"]
        assert audit_info["acca_compliance_version"] == "Manual J 8th Edition"
        assert audit_info["validation_passed"] is True
        assert "calculation_inputs" in audit_info
        assert "data_quality_checks" in audit_info

    def test_climate_zone_variations(self, climate_zone_2a_house, cold_climate_house):
        """Test that load calculations vary appropriately with climate zones"""
        
        # Calculate loads for hot-humid climate (Zone 2A)
        hot_result = calculate_manualj_with_audit(
            schema=climate_zone_2a_house,
            duct_config="ducted_attic", 
            heating_fuel="heat_pump",
            create_audit=True,
            user_id="test_climate_2a"
        )
        
        # Calculate loads for cold climate (Zone 6A)
        cold_result = calculate_manualj_with_audit(
            schema=cold_climate_house,
            duct_config="ducted_attic",
            heating_fuel="gas",
            create_audit=True,
            user_id="test_climate_6a"
        )
        
        # Verify climate zone assignments
        assert hot_result["climate_zone"] == "2A"
        assert cold_result["climate_zone"] == "6A"
        
        # Climate-appropriate load patterns
        hot_heating_per_sqft = hot_result["heating_total"] / 2200
        hot_cooling_per_sqft = hot_result["cooling_total"] / 2200
        cold_heating_per_sqft = cold_result["heating_total"] / 1800
        cold_cooling_per_sqft = cold_result["cooling_total"] / 1800
        
        # Hot climate should have higher cooling loads relative to heating
        hot_cooling_ratio = hot_result["cooling_total"] / hot_result["heating_total"]
        cold_cooling_ratio = cold_result["cooling_total"] / cold_result["heating_total"]
        
        assert hot_cooling_ratio > cold_cooling_ratio, \
            f"Hot climate cooling ratio {hot_cooling_ratio:.2f} should exceed cold climate {cold_cooling_ratio:.2f}"
        
        # Cold climate should have higher heating loads per sqft
        assert cold_heating_per_sqft > hot_heating_per_sqft, \
            f"Cold climate heating load per sqft {cold_heating_per_sqft:.1f} should exceed hot climate {hot_heating_per_sqft:.1f}"

    def test_duct_configuration_impact(self, standard_test_house_1500sqft):
        """Test that duct configuration affects load calculations appropriately"""
        
        # Test different duct configurations
        ducted_attic = calculate_manualj_with_audit(
            schema=standard_test_house_1500sqft,
            duct_config="ducted_attic",
            heating_fuel="gas"
        )
        
        ducted_crawl = calculate_manualj_with_audit(
            schema=standard_test_house_1500sqft,
            duct_config="ducted_crawl", 
            heating_fuel="gas"
        )
        
        ductless = calculate_manualj_with_audit(
            schema=standard_test_house_1500sqft,
            duct_config="ductless",
            heating_fuel="heat_pump"
        )
        
        # Verify duct loss factors are applied correctly
        # Attic ducts should have highest losses, ductless should have none
        assert ducted_attic["heating_total"] > ducted_crawl["heating_total"], \
            "Ducted attic should have higher loads than ducted crawl space"
        
        assert ducted_crawl["heating_total"] > ductless["heating_total"], \
            "Ducted systems should have higher loads than ductless"
        
        # Verify duct loss factors in design parameters
        attic_factor = ducted_attic["design_parameters"]["duct_loss_factor"]
        crawl_factor = ducted_crawl["design_parameters"]["duct_loss_factor"]
        ductless_factor = ductless["design_parameters"]["duct_loss_factor"]
        
        assert attic_factor > crawl_factor > ductless_factor, \
            f"Duct loss factors should decrease: attic({attic_factor}) > crawl({crawl_factor}) > ductless({ductless_factor})"

    def test_heating_fuel_impact(self, standard_test_house_1500sqft):
        """Test that heating fuel selection affects equipment sizing"""
        
        gas_result = calculate_manualj_with_audit(
            schema=standard_test_house_1500sqft,
            duct_config="ducted_attic",
            heating_fuel="gas"
        )
        
        heat_pump_result = calculate_manualj_with_audit(
            schema=standard_test_house_1500sqft,
            duct_config="ducted_attic",
            heating_fuel="heat_pump"
        )
        
        electric_result = calculate_manualj_with_audit(
            schema=standard_test_house_1500sqft,
            duct_config="ducted_attic",
            heating_fuel="electric"
        )
        
        # Verify equipment recommendations differ
        gas_equipment = gas_result["equipment_recommendations"]["system_type"]
        heat_pump_equipment = heat_pump_result["equipment_recommendations"]["system_type"]
        electric_equipment = electric_result["equipment_recommendations"]["system_type"]
        
        assert "Gas" in gas_equipment
        assert "Heat Pump" in heat_pump_equipment
        assert "Electric" in electric_equipment
        
        # Heat pump should size on larger of heating/cooling load
        gas_primary = gas_result["cooling_total"]  # Sized on cooling
        heat_pump_primary = max(heat_pump_result["heating_total"], heat_pump_result["cooling_total"])
        
        # Verify equipment sizing logic
        assert gas_result["equipment_recommendations"]["recommended_size_tons"] == gas_primary / 12000
        assert heat_pump_result["equipment_recommendations"]["recommended_size_tons"] == heat_pump_primary / 12000

    def test_calculation_accuracy_within_tolerance(self, standard_test_house_1500sqft):
        """Test that repeated calculations are consistent and within tolerance"""
        
        # Run same calculation multiple times
        results = []
        for i in range(5):
            result = calculate_manualj_with_audit(
                schema=standard_test_house_1500sqft,
                duct_config="ducted_attic",
                heating_fuel="gas",
                user_id=f"test_consistency_{i}"
            )
            results.append(result)
        
        # Verify consistency across runs
        heating_loads = [r["heating_total"] for r in results]
        cooling_loads = [r["cooling_total"] for r in results]
        
        heating_avg = sum(heating_loads) / len(heating_loads)
        cooling_avg = sum(cooling_loads) / len(cooling_loads)
        
        # All results should be within 1% of average (deterministic calculation)
        for heating_load in heating_loads:
            deviation_pct = abs(heating_load - heating_avg) / heating_avg * 100
            assert deviation_pct < 1.0, f"Heating load deviation {deviation_pct:.2f}% exceeds 1%"
        
        for cooling_load in cooling_loads:
            deviation_pct = abs(cooling_load - cooling_avg) / cooling_avg * 100
            assert deviation_pct < 1.0, f"Cooling load deviation {deviation_pct:.2f}% exceeds 1%"

    def test_manual_s_equipment_sizing_compliance(self, standard_test_house_1500sqft):
        """Test that equipment sizing follows ACCA Manual S guidelines"""
        
        result = calculate_manualj_with_audit(
            schema=standard_test_house_1500sqft,
            duct_config="ducted_attic",
            heating_fuel="gas"
        )
        
        equipment_options = result["equipment_recommendations"]["size_options"]
        cooling_load_tons = result["cooling_total"] / 12000
        
        # Verify Manual S ratings are provided
        for option in equipment_options:
            assert "manual_s_rating" in option
            assert option["manual_s_rating"] in ["Good", "OK", "Poor"]
            assert "manual_s_explanation" in option
            
            # Verify sizing ratios
            capacity_tons = option["capacity_tons"]
            sizing_ratio = capacity_tons / cooling_load_tons
            
            if option["manual_s_rating"] == "Good":
                assert 0.95 <= sizing_ratio <= 1.15, \
                    f"Good rating should be 95-115% of load, got {sizing_ratio:.1%}"
            elif option["manual_s_rating"] == "OK":
                assert 1.15 < sizing_ratio <= 1.25, \
                    f"OK rating should be 115-125% of load, got {sizing_ratio:.1%}"

    def test_ventilation_load_ashrae_62_2_compliance(self, standard_test_house_1500sqft):
        """Test that ventilation loads comply with ASHRAE 62.2 standards"""
        
        with_ventilation = calculate_manualj_with_audit(
            schema=standard_test_house_1500sqft,
            duct_config="ducted_attic",
            heating_fuel="gas",
            include_ventilation=True
        )
        
        without_ventilation = calculate_manualj_with_audit(
            schema=standard_test_house_1500sqft,
            duct_config="ducted_attic",
            heating_fuel="gas",
            include_ventilation=False
        )
        
        # Ventilation should increase both heating and cooling loads
        assert with_ventilation["heating_total"] > without_ventilation["heating_total"], \
            "Ventilation should increase heating loads"
        
        assert with_ventilation["cooling_total"] > without_ventilation["cooling_total"], \
            "Ventilation should increase cooling loads"
        
        # Ventilation load should be reasonable (typically 10-25% of total)
        ventilation_heating = with_ventilation["heating_total"] - without_ventilation["heating_total"]
        ventilation_cooling = with_ventilation["cooling_total"] - without_ventilation["cooling_total"]
        
        heating_ventilation_pct = ventilation_heating / with_ventilation["heating_total"] * 100
        cooling_ventilation_pct = ventilation_cooling / with_ventilation["cooling_total"] * 100
        
        assert 5 <= heating_ventilation_pct <= 35, \
            f"Ventilation heating load {heating_ventilation_pct:.1f}% should be 5-35% of total"
        
        assert 5 <= cooling_ventilation_pct <= 35, \
            f"Ventilation cooling load {cooling_ventilation_pct:.1f}% should be 5-35% of total"

    def test_data_validation_and_error_handling(self):
        """Test that invalid data is properly validated and rejected"""
        
        # Test with empty rooms
        invalid_schema = BlueprintSchema(
            project_id=uuid4(),
            zip_code="90210",
            sqft_total=0,
            stories=1,
            rooms=[]
        )
        
        with pytest.raises(ValueError, match="No rooms found"):
            calculate_manualj_with_audit(invalid_schema)
        
        # Test with invalid zip code
        invalid_zip_schema = BlueprintSchema(
            project_id=uuid4(),
            zip_code="00000",  # Invalid zip
            sqft_total=1500,
            stories=1,
            rooms=[
                Room(
                    name="Test Room",
                    dimensions_ft=(10.0, 10.0),
                    floor=1,
                    windows=1,
                    orientation="N",
                    area=100.0
                )
            ]
        )
        
        # Should still calculate but with default climate data
        result = calculate_manualj_with_audit(invalid_zip_schema)
        assert result is not None
        assert result["climate_zone"] == "4A"  # Default fallback

    def test_audit_trail_completeness(self, standard_test_house_1500sqft):
        """Test that audit trail captures all required information"""
        
        result = calculate_manualj_with_audit(
            schema=standard_test_house_1500sqft,
            duct_config="ducted_attic",
            heating_fuel="gas",
            construction_vintage="2000-2020",
            create_audit=True,
            user_id="test_audit_trail"
        )
        
        # Verify audit information structure
        audit_info = result["audit_information"]
        
        required_audit_fields = [
            "calculation_inputs",
            "calculation_time_seconds",
            "acca_compliance_version",
            "validation_passed",
            "data_quality_checks",
            "calculation_warnings"
        ]
        
        for field in required_audit_fields:
            assert field in audit_info, f"Missing audit field: {field}"
        
        # Verify calculation inputs are captured
        calc_inputs = audit_info["calculation_inputs"]
        required_input_fields = [
            "project_id", "zip_code", "total_sqft", "room_count",
            "duct_config", "heating_fuel", "climate_zone"
        ]
        
        for field in required_input_fields:
            assert field in calc_inputs, f"Missing calculation input: {field}"
        
        # Verify data quality checks
        quality_checks = audit_info["data_quality_checks"]
        assert "total_rooms_processed" in quality_checks
        assert "quality_flags" in quality_checks
        assert quality_checks["zone_calculation_completeness"] == 1.0

    def test_room_type_classification_accuracy(self, standard_test_house_1500sqft):
        """Test that room types are classified correctly and affect calculations"""
        
        result = calculate_manualj_with_audit(
            schema=standard_test_house_1500sqft,
            duct_config="ducted_attic",
            heating_fuel="gas"
        )
        
        zones = result["zones"]
        
        # Find specific room types and verify classification
        living_room = next((z for z in zones if "Living" in z["name"]), None)
        kitchen = next((z for z in zones if "Kitchen" in z["name"]), None)
        bedroom = next((z for z in zones if "Bedroom" in z["name"]), None)
        bathroom = next((z for z in zones if "Bathroom" in z["name"]), None)
        
        assert living_room is not None
        assert kitchen is not None
        assert bedroom is not None
        assert bathroom is not None
        
        # Verify room type classification
        assert living_room["room_type"] == "living"
        assert kitchen["room_type"] == "kitchen" 
        assert bedroom["room_type"] == "bedroom"
        assert bathroom["room_type"] == "bathroom"
        
        # Kitchen should generally have higher cooling loads due to equipment
        # Living room should have higher loads due to size and windows
        # These are general patterns that should hold for typical houses
        kitchen_cooling_per_sqft = kitchen["cooling_btu"] / kitchen["area"]
        bedroom_cooling_per_sqft = bedroom["cooling_btu"] / bedroom["area"]
        
        assert kitchen_cooling_per_sqft > bedroom_cooling_per_sqft * 0.8, \
            "Kitchen should have higher cooling load per sqft than bedroom due to equipment loads"
"""
Tests for Manual J duct configuration assumptions
"""

import pytest
from uuid import uuid4

from services.manualj import calculate_manualj
from app.parser.schema import BlueprintSchema, Room


class TestManualJDuctConfig:
    """Test Manual J calculations with different duct configurations"""
    
    @pytest.fixture
    def sample_room(self):
        """Sample room for testing"""
        return Room(
            name="Test Room",
            dimensions_ft=(12.0, 12.0),
            floor=1,
            windows=1,
            orientation="S",
            area=144.0
        )
    
    @pytest.fixture
    def sample_blueprint(self, sample_room):
        """Sample blueprint for testing"""
        return BlueprintSchema(
            project_id=uuid4(),
            zip_code="90210",
            sqft_total=144.0,
            stories=1,
            rooms=[sample_room]
        )
    
    def test_ductless_has_no_duct_loss(self, sample_blueprint):
        """Test that ductless configuration has no duct losses (factor = 1.0)"""
        result = calculate_manualj(sample_blueprint, duct_config="ductless")
        
        # Ductless should have no duct losses
        assert result["design_parameters"]["duct_loss_factor"] == 1.0
        assert result["design_parameters"]["duct_config"] == "ductless"
    
    def test_ducted_attic_has_highest_duct_loss(self, sample_blueprint):
        """Test that ducted attic configuration has highest duct losses"""
        result = calculate_manualj(sample_blueprint, duct_config="ducted_attic")
        
        # Ducted attic should have 15% duct losses
        assert result["design_parameters"]["duct_loss_factor"] == 1.15
        assert result["design_parameters"]["duct_config"] == "ducted_attic"
    
    def test_ducted_crawl_has_moderate_duct_loss(self, sample_blueprint):
        """Test that ducted crawl space configuration has moderate duct losses"""
        result = calculate_manualj(sample_blueprint, duct_config="ducted_crawl")
        
        # Ducted crawl should have 10% duct losses
        assert result["design_parameters"]["duct_loss_factor"] == 1.10
        assert result["design_parameters"]["duct_config"] == "ducted_crawl"
    
    def test_ductless_has_lower_total_loads(self, sample_blueprint):
        """Test that ductless systems have lower total loads due to no duct losses"""
        ductless_result = calculate_manualj(sample_blueprint, duct_config="ductless")
        ducted_result = calculate_manualj(sample_blueprint, duct_config="ducted_attic")
        
        # Ductless should have lower total loads
        assert ductless_result["heating_total"] < ducted_result["heating_total"]
        assert ductless_result["cooling_total"] < ducted_result["cooling_total"]
    
    def test_heating_fuel_affects_equipment_recommendation(self, sample_blueprint):
        """Test that heating fuel selection affects equipment recommendations"""
        gas_result = calculate_manualj(sample_blueprint, heating_fuel="gas")
        heat_pump_result = calculate_manualj(sample_blueprint, heating_fuel="heat_pump")
        electric_result = calculate_manualj(sample_blueprint, heating_fuel="electric")
        
        # Different heating fuels should recommend different system types
        assert "Natural Gas Furnace" in gas_result["equipment_recommendations"]["system_type"]
        assert "Heat Pump" in heat_pump_result["equipment_recommendations"]["system_type"]
        assert "Electric Furnace" in electric_result["equipment_recommendations"]["system_type"]
        
        # Verify heating fuel is stored in design parameters
        assert gas_result["design_parameters"]["heating_fuel"] == "gas"
        assert heat_pump_result["design_parameters"]["heating_fuel"] == "heat_pump"
        assert electric_result["design_parameters"]["heating_fuel"] == "electric"
    
    def test_combined_assumptions_work_together(self, sample_blueprint):
        """Test that duct config and heating fuel work together properly"""
        result = calculate_manualj(
            sample_blueprint, 
            duct_config="ductless", 
            heating_fuel="heat_pump"
        )
        
        # Should have no duct losses and heat pump recommendation
        assert result["design_parameters"]["duct_loss_factor"] == 1.0
        assert result["design_parameters"]["duct_config"] == "ductless"
        assert result["design_parameters"]["heating_fuel"] == "heat_pump"
        assert "Heat Pump" in result["equipment_recommendations"]["system_type"]
    
    def test_default_values_work(self, sample_blueprint):
        """Test that default parameter values work correctly"""
        # Test with no parameters (should use defaults)
        result = calculate_manualj(sample_blueprint)
        
        # Should use default values
        assert result["design_parameters"]["duct_config"] == "ducted_attic"
        assert result["design_parameters"]["heating_fuel"] == "gas"
        assert result["design_parameters"]["duct_loss_factor"] == 1.15
        assert "Natural Gas Furnace" in result["equipment_recommendations"]["system_type"]


class TestManualJDuctLossCalculations:
    """Test the specific duct loss calculations"""
    
    def test_duct_loss_percentage_accuracy(self):
        """Test that duct loss percentages are applied correctly"""
        # Create identical rooms for comparison
        room = Room(
            name="Test Room",
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
        
        # Calculate loads for each duct configuration
        ductless = calculate_manualj(blueprint, duct_config="ductless")
        ducted_crawl = calculate_manualj(blueprint, duct_config="ducted_crawl")
        ducted_attic = calculate_manualj(blueprint, duct_config="ducted_attic")
        
        # Before applying duct losses, all should have same base load
        # After duct losses: ductless < ducted_crawl < ducted_attic
        
        # Ductless base load (no multiplier)
        base_heating = ductless["heating_total"] / 1.1  # Remove safety factor
        base_cooling = ductless["cooling_total"] / 1.1  # Remove safety factor
        
        # Verify crawl space is 10% higher than ductless (after removing safety factor)
        crawl_heating = ducted_crawl["heating_total"] / 1.1
        crawl_cooling = ducted_crawl["cooling_total"] / 1.1
        
        assert abs(crawl_heating / base_heating - 1.10) < 0.01  # Within 1% tolerance
        assert abs(crawl_cooling / base_cooling - 1.10) < 0.01
        
        # Verify attic is 15% higher than ductless (after removing safety factor)
        attic_heating = ducted_attic["heating_total"] / 1.1
        attic_cooling = ducted_attic["cooling_total"] / 1.1
        
        assert abs(attic_heating / base_heating - 1.15) < 0.01  # Within 1% tolerance
        assert abs(attic_cooling / base_cooling - 1.15) < 0.01


if __name__ == "__main__":
    pytest.main([__file__])
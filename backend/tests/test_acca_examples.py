"""
Parametrized regression tests based on ACCA Manual J examples
Ensures calculation accuracy against known Manual J test cases
"""

import pytest
from uuid import uuid4

from services.manualj import calculate_manualj
from services.climate_data import get_construction_vintage_values
from app.parser.schema import BlueprintSchema, Room


class TestACCAExamples:
    """Test Manual J calculations against ACCA example problems"""
    
    @pytest.mark.parametrize("test_case", [
        {
            "name": "ACCA Example 1 - Small Ranch Home",
            "zip_code": "60601",  # Chicago - Cold climate
            "construction_vintage": "1980-2000",
            "rooms": [
                {"name": "Living Room", "area": 320, "windows": 3, "orientation": "S", "floor": 1},
                {"name": "Kitchen", "area": 150, "windows": 2, "orientation": "E", "floor": 1},
                {"name": "Master Bedroom", "area": 200, "windows": 2, "orientation": "N", "floor": 1},
                {"name": "Bedroom 2", "area": 120, "windows": 1, "orientation": "N", "floor": 1},
                {"name": "Bathroom", "area": 60, "windows": 1, "orientation": "W", "floor": 1},
            ],
            "expected_heating_range": (45000, 55000),  # BTU/hr
            "expected_cooling_range": (22000, 28000),  # BTU/hr
            "tolerance": 0.15  # ±15% tolerance
        },
        {
            "name": "ACCA Example 2 - Medium Colonial Home",
            "zip_code": "90210",  # Los Angeles - Mild climate
            "construction_vintage": "2000-2020", 
            "rooms": [
                {"name": "Living Room", "area": 400, "windows": 4, "orientation": "S", "floor": 1},
                {"name": "Dining Room", "area": 180, "windows": 2, "orientation": "E", "floor": 1},
                {"name": "Kitchen", "area": 200, "windows": 2, "orientation": "N", "floor": 1},
                {"name": "Family Room", "area": 350, "windows": 3, "orientation": "W", "floor": 1},
                {"name": "Master Bedroom", "area": 250, "windows": 3, "orientation": "S", "floor": 2},
                {"name": "Bedroom 2", "area": 150, "windows": 2, "orientation": "E", "floor": 2},
                {"name": "Bedroom 3", "area": 140, "windows": 2, "orientation": "W", "floor": 2},
                {"name": "Master Bath", "area": 80, "windows": 1, "orientation": "N", "floor": 2},
                {"name": "Hall Bath", "area": 50, "windows": 1, "orientation": "E", "floor": 2},
            ],
            "expected_heating_range": (25000, 35000),  # BTU/hr (mild climate, enhanced calculation)
            "expected_cooling_range": (30000, 42000),  # BTU/hr (enhanced CLF/CLTD method)
            "tolerance": 0.15
        },
        {
            "name": "ACCA Example 3 - Hot Climate Home", 
            "zip_code": "33101",  # Miami - Hot-humid climate
            "construction_vintage": "current-code",
            "rooms": [
                {"name": "Great Room", "area": 450, "windows": 5, "orientation": "S", "floor": 1},
                {"name": "Kitchen", "area": 180, "windows": 2, "orientation": "E", "floor": 1},
                {"name": "Master Suite", "area": 300, "windows": 3, "orientation": "W", "floor": 1},
                {"name": "Bedroom 2", "area": 160, "windows": 2, "orientation": "N", "floor": 1},
                {"name": "Bedroom 3", "area": 140, "windows": 2, "orientation": "E", "floor": 1},
                {"name": "Master Bath", "area": 90, "windows": 1, "orientation": "W", "floor": 1},
                {"name": "Guest Bath", "area": 60, "windows": 1, "orientation": "N", "floor": 1},
            ],
            "expected_heating_range": (13000, 20000),  # BTU/hr (hot climate, enhanced calculation)
            "expected_cooling_range": (26000, 34000),  # BTU/hr (enhanced CLF/CLTD with current code efficiency)
            "tolerance": 0.15
        }
    ])
    def test_acca_example_cases(self, test_case):
        """Test against ACCA Manual J example problems"""
        
        # Create rooms from test case data
        rooms = []
        total_area = 0
        
        for room_data in test_case["rooms"]:
            area = room_data["area"]
            total_area += area
            
            # Estimate dimensions (assume square-ish rooms)
            width = (area * 0.8) ** 0.5  # Slight rectangular assumption
            length = area / width
            
            room = Room(
                name=room_data["name"],
                dimensions_ft=(width, length),
                floor=room_data["floor"],
                windows=room_data["windows"],
                orientation=room_data["orientation"],
                area=area
            )
            rooms.append(room)
        
        # Create blueprint schema
        blueprint = BlueprintSchema(
            project_id=uuid4(),
            zip_code=test_case["zip_code"],
            sqft_total=total_area,
            stories=max(r["floor"] for r in test_case["rooms"]),
            rooms=rooms
        )
        
        # Run calculation
        result = calculate_manualj(
            blueprint,
            construction_vintage=test_case["construction_vintage"],
            create_audit=False  # Skip audit for tests
        )
        
        # Check results are within expected ranges
        heating_total = result["heating_total"]
        cooling_total = result["cooling_total"]
        
        heating_min, heating_max = test_case["expected_heating_range"]
        cooling_min, cooling_max = test_case["expected_cooling_range"]
        
        tolerance = test_case["tolerance"]
        
        # Apply tolerance to ranges
        heating_min_tol = heating_min * (1 - tolerance)
        heating_max_tol = heating_max * (1 + tolerance)
        cooling_min_tol = cooling_min * (1 - tolerance)
        cooling_max_tol = cooling_max * (1 + tolerance)
        
        assert heating_min_tol <= heating_total <= heating_max_tol, \
            f"{test_case['name']}: Heating load {heating_total} BTU/hr outside expected range {heating_min_tol:.0f}-{heating_max_tol:.0f}"
        
        assert cooling_min_tol <= cooling_total <= cooling_max_tol, \
            f"{test_case['name']}: Cooling load {cooling_total} BTU/hr outside expected range {cooling_min_tol:.0f}-{cooling_max_tol:.0f}"
        
        # Verify calculation used enhanced method
        assert result["design_parameters"]["calculation_method"] == "Enhanced CLF/CLTD"
        
        # Verify reasonable load per square foot
        heating_per_sqft = heating_total / total_area
        cooling_per_sqft = cooling_total / total_area
        
        assert 10 <= heating_per_sqft <= 80, f"Heating load per sqft ({heating_per_sqft:.1f}) outside reasonable range"
        assert 10 <= cooling_per_sqft <= 50, f"Cooling load per sqft ({cooling_per_sqft:.1f}) outside reasonable range"


class TestManualJAccuracy:
    """Test calculation accuracy for specific scenarios"""
    
    def test_climate_zone_impact(self):
        """Test that different climate zones produce appropriate load differences"""
        
        # Standard test room
        room = Room(
            name="Test Room",
            dimensions_ft=(12.0, 12.0),
            floor=1,
            windows=2,
            orientation="S",
            area=144.0
        )
        
        blueprint_base = {
            "sqft_total": 144.0,
            "stories": 1,
            "rooms": [room]
        }
        
        # Test different climate zones
        climate_tests = [
            ("33101", "Hot-Humid"),    # Miami - high cooling, low heating
            ("90210", "Warm-Dry"),     # LA - moderate loads
            ("60601", "Cold-Humid"),   # Chicago - high heating, moderate cooling
        ]
        
        results = {}
        
        for zip_code, climate_name in climate_tests:
            blueprint = BlueprintSchema(
                project_id=uuid4(),
                zip_code=zip_code,
                **blueprint_base
            )
            
            result = calculate_manualj(blueprint, construction_vintage="1980-2000", create_audit=False)
            results[climate_name] = {
                "heating": result["heating_total"],
                "cooling": result["cooling_total"],
                "climate_zone": result["climate_zone"]
            }
        
        # Verify climate-appropriate trends
        # Hot-Humid should have lowest heating, highest cooling
        assert results["Hot-Humid"]["heating"] < results["Cold-Humid"]["heating"]
        assert results["Hot-Humid"]["cooling"] > results["Cold-Humid"]["cooling"]
        
        # Warm-Dry should be in between
        assert results["Warm-Dry"]["heating"] < results["Cold-Humid"]["heating"]
        assert results["Warm-Dry"]["heating"] > results["Hot-Humid"]["heating"]
    
    def test_construction_vintage_impact(self):
        """Test that construction vintage affects loads appropriately"""
        
        room = Room(
            name="Test Room",
            dimensions_ft=(20.0, 15.0),
            floor=1,
            windows=3,
            orientation="S",
            area=300.0
        )
        
        blueprint = BlueprintSchema(
            project_id=uuid4(),
            zip_code="60601",  # Chicago - cold climate shows differences better
            sqft_total=300.0,
            stories=1,
            rooms=[room]
        )
        
        vintages = ["pre-1980", "1980-2000", "2000-2020", "current-code"]
        results = {}
        
        for vintage in vintages:
            result = calculate_manualj(blueprint, construction_vintage=vintage, create_audit=False)
            results[vintage] = {
                "heating": result["heating_total"],
                "cooling": result["cooling_total"]
            }
        
        # Verify newer construction has lower loads (better insulation)
        assert results["pre-1980"]["heating"] > results["current-code"]["heating"]
        assert results["pre-1980"]["cooling"] > results["current-code"]["cooling"]
        
        # Verify progressive improvement
        heating_loads = [results[v]["heating"] for v in vintages]
        assert heating_loads == sorted(heating_loads, reverse=True), "Heating loads should decrease with newer construction"
    
    def test_room_orientation_impact(self):
        """Test that room orientation affects cooling loads appropriately"""
        
        orientations = ["N", "E", "S", "W"]
        results = {}
        
        for orientation in orientations:
            room = Room(
                name=f"{orientation} Room",
                dimensions_ft=(15.0, 12.0),
                floor=1,
                windows=2,
                orientation=orientation,
                area=180.0
            )
            
            blueprint = BlueprintSchema(
                project_id=uuid4(),
                zip_code="90210",  # Mild climate
                sqft_total=180.0,
                stories=1,
                rooms=[room]
            )
            
            result = calculate_manualj(blueprint, construction_vintage="1980-2000", create_audit=False)
            results[orientation] = {
                "heating": result["heating_total"],
                "cooling": result["cooling_total"]
            }
        
        # South and West should have higher cooling loads (more solar gain)
        assert results["S"]["cooling"] > results["N"]["cooling"]
        assert results["W"]["cooling"] > results["N"]["cooling"]
        
        # North should have highest heating load (least solar gain)
        assert results["N"]["heating"] >= results["S"]["heating"]
    
    def test_diversity_factor_application(self):
        """Test that diversity factors are applied correctly for different home sizes"""
        
        # Test with different numbers of rooms
        room_counts = [3, 8, 15]
        results = {}
        
        for count in room_counts:
            rooms = []
            for i in range(count):
                room = Room(
                    name=f"Room {i+1}",
                    dimensions_ft=(12.0, 10.0),
                    floor=1,
                    windows=1,
                    orientation="S",
                    area=120.0
                )
                rooms.append(room)
            
            blueprint = BlueprintSchema(
                project_id=uuid4(),
                zip_code="90210",
                sqft_total=count * 120.0,
                stories=1,
                rooms=rooms
            )
            
            result = calculate_manualj(blueprint, construction_vintage="1980-2000", create_audit=False)
            diversity_factor = result["design_parameters"]["diversity_factor"]
            cooling_per_room = result["cooling_total"] / count
            
            results[count] = {
                "diversity_factor": diversity_factor,
                "cooling_per_room": cooling_per_room,
                "total_cooling": result["cooling_total"]
            }
        
        # Verify diversity factors decrease with more rooms
        assert results[3]["diversity_factor"] >= results[8]["diversity_factor"]
        assert results[8]["diversity_factor"] >= results[15]["diversity_factor"]
        
        # Verify appropriate diversity factor values
        assert results[3]["diversity_factor"] == 1.0  # Small homes get no diversity
        assert results[15]["diversity_factor"] <= 0.90  # Large homes get significant diversity


class TestCalculationConsistency:
    """Test calculation consistency and regression prevention"""
    
    def test_calculation_repeatability(self):
        """Test that identical inputs produce identical outputs"""
        
        room = Room(
            name="Test Room",
            dimensions_ft=(15.0, 12.0),
            floor=1,
            windows=2,
            orientation="S",
            area=180.0
        )
        
        blueprint = BlueprintSchema(
            project_id=uuid4(),
            zip_code="90210",
            sqft_total=180.0,
            stories=1,
            rooms=[room]
        )
        
        # Run calculation multiple times
        results = []
        for _ in range(3):
            result = calculate_manualj(blueprint, construction_vintage="1980-2000", create_audit=False)
            results.append({
                "heating": result["heating_total"],
                "cooling": result["cooling_total"]
            })
        
        # All results should be identical
        assert all(r["heating"] == results[0]["heating"] for r in results)
        assert all(r["cooling"] == results[0]["cooling"] for r in results)
    
    def test_load_calculation_minimums(self):
        """Test that load calculations never go below reasonable minimums"""
        
        # Very small room with minimal heat sources
        room = Room(
            name="Small Room",
            dimensions_ft=(6.0, 6.0),
            floor=1,
            windows=0,
            orientation="",  # Interior room
            area=36.0
        )
        
        blueprint = BlueprintSchema(
            project_id=uuid4(),
            zip_code="90210",
            sqft_total=36.0,
            stories=1,
            rooms=[room]
        )
        
        result = calculate_manualj(blueprint, construction_vintage="current-code", create_audit=False)
        
        # Even tiny rooms should have some load
        assert result["heating_total"] > 500  # Minimum heating load
        assert result["cooling_total"] > 500  # Minimum cooling load
        
        # Verify reasonable load per square foot
        heating_per_sqft = result["heating_total"] / 36.0
        cooling_per_sqft = result["cooling_total"] / 36.0
        
        assert heating_per_sqft >= 15  # Minimum reasonable heating
        assert cooling_per_sqft >= 12  # Minimum reasonable cooling


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
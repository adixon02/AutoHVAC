"""
Test climate data endpoint
"""
import pytest
from fastapi.testclient import TestClient


def test_get_climate_data_valid_zip(client: TestClient):
    """Test getting climate data for valid ZIP code"""
    zip_code = "12345"
    
    response = client.get(f"/api/v2/climate/{zip_code}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["zip_code"] == zip_code
    assert "climate_zone" in data
    assert "heating_design_temp" in data
    assert "cooling_design_temp" in data
    assert data["data_source"] == "Mock Data Service"


def test_get_climate_data_invalid_zip_format(client: TestClient):
    """Test invalid ZIP code format returns 400"""
    invalid_zips = ["123", "12345a", "abcde", ""]
    
    for zip_code in invalid_zips:
        response = client.get(f"/api/v2/climate/{zip_code}")
        assert response.status_code == 400
        assert "Invalid ZIP code format" in response.json()["detail"]


def test_get_climate_data_regional_differences(client: TestClient):
    """Test different regions return different climate data"""
    northern_zip = "01234"  # Starts with 0 (Northern)
    southern_zip = "60123"  # Starts with 6 (Southern)
    
    north_response = client.get(f"/api/v2/climate/{northern_zip}")
    south_response = client.get(f"/api/v2/climate/{southern_zip}")
    
    assert north_response.status_code == 200
    assert south_response.status_code == 200
    
    north_data = north_response.json()
    south_data = south_response.json()
    
    # Northern regions should have lower heating design temps
    assert north_data["heating_design_temp"] < south_data["heating_design_temp"]
    # Different climate zones
    assert north_data["climate_zone"] != south_data["climate_zone"]


def test_climate_data_response_format(client: TestClient):
    """Test climate data response has correct format and types"""
    response = client.get("/api/v2/climate/12345")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check data types
    assert isinstance(data["zip_code"], str)
    assert isinstance(data["climate_zone"], str)
    assert isinstance(data["heating_design_temp"], (int, float))
    assert isinstance(data["cooling_design_temp"], (int, float))
    assert isinstance(data["data_source"], str)
    assert isinstance(data["message"], str)


def test_climate_data_includes_request_id(client: TestClient):
    """Test climate data response includes request ID header"""
    response = client.get("/api/v2/climate/12345")
    
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
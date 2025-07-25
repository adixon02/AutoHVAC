"""
Test health check endpoint
"""
import pytest
from fastapi.testclient import TestClient


def test_health_check_success(client: TestClient):
    """Test health check returns 200 with correct format"""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))


def test_health_check_response_time(client: TestClient):
    """Test health check responds quickly (< 100ms)"""
    import time
    
    start = time.time()
    response = client.get("/health")
    duration = (time.time() - start) * 1000  # Convert to ms
    
    assert response.status_code == 200
    assert duration < 100  # Should respond in under 100ms


def test_health_check_no_auth_required(client: TestClient):
    """Test health check works without authentication"""
    response = client.get("/health")
    assert response.status_code == 200
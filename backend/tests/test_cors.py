import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_cors_headers_on_options_request():
    """Test that CORS headers are present on OPTIONS requests"""
    response = client.options(
        "/api/v1/job/test-job-id",
        headers={"Origin": "http://localhost:3000"}
    )
    
    # Should return 200 OK for OPTIONS request
    assert response.status_code == 200
    
    # Check CORS headers are present
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "Access-Control-Allow-Methods" in response.headers
    assert "Access-Control-Allow-Headers" in response.headers
    assert "Access-Control-Allow-Credentials" in response.headers


def test_cors_headers_on_error_response():
    """Test that CORS headers are present on error responses"""
    response = client.get(
        "/api/v1/job/nonexistent-job-id",
        headers={"Origin": "http://localhost:3000"}
    )
    
    # Should return 404 for nonexistent job
    assert response.status_code == 404
    
    # Check CORS headers are present even on error responses
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "Access-Control-Allow-Credentials" in response.headers
    
    # Check structured error response
    data = response.json()
    assert "error" in data
    assert "type" in data["error"]
    assert "message" in data["error"]
    assert data["error"]["type"] == "JobNotFound"


def test_cors_headers_rejected_for_wrong_origin():
    """Test that CORS headers are not added for unauthorized origins"""
    response = client.get(
        "/api/v1/job/nonexistent-job-id",
        headers={"Origin": "http://malicious-site.com"}
    )
    
    # Should still return 404
    assert response.status_code == 404
    
    # Should NOT have CORS headers for unauthorized origin
    assert response.headers.get("Access-Control-Allow-Origin") != "http://malicious-site.com"


def test_cors_test_endpoint():
    """Test dedicated CORS test endpoint with OPTIONS request"""
    # Test the health endpoint as a CORS test
    response = client.options(
        "/healthz",
        headers={"Origin": "http://localhost:3000"}
    )
    
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"


def test_structured_error_format():
    """Test that errors follow the structured format"""
    response = client.get(
        "/api/v1/job/invalid-job-id",
        headers={"Origin": "http://localhost:3000"}
    )
    
    assert response.status_code == 404
    data = response.json()
    
    # Check structured error format
    assert "error" in data
    assert isinstance(data["error"], dict)
    assert "type" in data["error"]
    assert "message" in data["error"]
    assert isinstance(data["error"]["type"], str)
    assert isinstance(data["error"]["message"], str)
    
    # Should not have old "detail" field
    assert "detail" not in data
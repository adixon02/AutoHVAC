import pytest
import requests

def test_get_status_dev():
    """Test that job status endpoint returns proper response structure"""
    
    # Test with a non-existent job ID to verify error handling
    response = requests.get(
        "http://localhost:8000/api/v1/job/test-job-id-that-does-not-exist",
        headers={"Origin": "http://localhost:3000"}
    )
    
    # Should return 404 for non-existent job
    assert response.status_code == 404
    
    # Check that response has CORS headers
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    
    # Check structured error response format
    data = response.json()
    assert "error" in data
    assert "type" in data["error"]
    assert "message" in data["error"]
    
    # Should be JobNotFound error type
    assert data["error"]["type"] == "JobNotFound"
    
    # Should not have the old "detail" field
    assert "detail" not in data


def test_job_status_endpoint_structure():
    """Test that job status endpoint follows expected response structure"""
    
    # Test endpoint accessibility
    response = client.get(
        "/api/v1/job/any-job-id",
        headers={"Origin": "http://localhost:3000"}
    )
    
    # Should return either 404 (job not found) or 500 (if database issues)
    # Both are acceptable for this test since we're testing structure
    assert response.status_code in [404, 500]
    
    # Should have CORS headers regardless of status code
    assert "Access-Control-Allow-Origin" in response.headers
    
    # Should return JSON
    assert response.headers["content-type"] == "application/json"
    
    # Should have structured error format
    data = response.json()
    assert "error" in data
    assert isinstance(data["error"], dict)
    assert "type" in data["error"]
    assert "message" in data["error"]


def test_job_status_cors_preflight():
    """Test CORS preflight handling for job status endpoint"""
    
    response = client.options(
        "/api/v1/job/test-job-id",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type"
        }
    )
    
    # Should handle OPTIONS request
    assert response.status_code == 200
    
    # Should have CORS headers
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "Access-Control-Allow-Methods" in response.headers
    assert "Access-Control-Allow-Headers" in response.headers
    assert "Access-Control-Allow-Credentials" in response.headers
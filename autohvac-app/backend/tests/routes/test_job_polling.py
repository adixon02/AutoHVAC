"""
Test job polling endpoint
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from app.services.job_storage import job_storage
from app.models.requests import JobStatusEnum


def test_get_job_status_not_found(client: TestClient):
    """Test getting status for non-existent job returns 404"""  
    fake_job_id = "non-existent-job-id"
    
    response = client.get(f"/api/v2/job/{fake_job_id}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_get_job_status_queued(client: TestClient):
    """Test getting status for queued job"""
    # Create a test job
    job_id = job_storage.create_job("test.pdf", 1024)
    
    response = client.get(f"/api/v2/job/{job_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["job_id"] == job_id
    assert data["status"] == "queued"
    assert "created_at" in data
    assert "updated_at" in data
    assert data["progress_percent"] == 0
    assert data["message"] == "Job queued for processing"


def test_get_job_status_processing(client: TestClient):
    """Test getting status for processing job"""
    # Create and update job to processing
    job_id = job_storage.create_job("test.pdf", 1024)
    job_storage.update_job_status(
        job_id=job_id,
        status=JobStatusEnum.PROCESSING,
        progress=50,
        message="Processing in progress"
    )
    
    response = client.get(f"/api/v2/job/{job_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["job_id"] == job_id
    assert data["status"] == "processing"
    assert data["progress_percent"] == 50
    assert data["message"] == "Processing in progress"


def test_get_job_status_completed(client: TestClient):
    """Test getting status for completed job with results"""
    # Create and complete job
    job_id = job_storage.create_job("test.pdf", 1024)
    
    result_data = {
        "rooms": [{"name": "Living Room", "area_sqft": 200}],
        "total_load": 15000
    }
    
    job_storage.update_job_status(
        job_id=job_id,
        status=JobStatusEnum.COMPLETED,
        progress=100,
        message="Processing completed successfully",
        result=result_data
    )
    
    response = client.get(f"/api/v2/job/{job_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["job_id"] == job_id
    assert data["status"] == "completed"
    assert data["progress_percent"] == 100
    assert data["result"] == result_data
    assert "processing_time_seconds" in data


def test_get_job_status_failed(client: TestClient):
    """Test getting status for failed job with error"""
    # Create and fail job
    job_id = job_storage.create_job("test.pdf", 1024)
    job_storage.update_job_status(
        job_id=job_id,
        status=JobStatusEnum.FAILED,
        message="Processing failed",
        error="PDF parsing error"
    )
    
    response = client.get(f"/api/v2/job/{job_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["job_id"] == job_id
    assert data["status"] == "failed"
    assert data["error"] == "PDF parsing error"
    assert "processing_time_seconds" in data


def test_job_status_includes_request_id(client: TestClient):
    """Test job status response includes request ID header"""
    job_id = job_storage.create_job("test.pdf", 1024) 
    
    response = client.get(f"/api/v2/job/{job_id}")
    
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
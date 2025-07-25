"""
Test job storage service
"""
import pytest
from datetime import datetime

from app.services.job_storage import JobStorageService
from app.models.requests import JobStatusEnum


@pytest.fixture
def job_service():
    """Fresh job storage service for each test"""
    service = JobStorageService()
    service.memory_storage.clear()
    return service


def test_create_job(job_service):
    """Test creating a new job"""
    job_id = job_service.create_job("test.pdf", 1024)
    
    assert job_id is not None
    assert isinstance(job_id, str)
    
    # Verify job was stored
    job_data = job_service.get_job(job_id)
    assert job_data is not None
    assert job_data["job_id"] == job_id
    assert job_data["filename"] == "test.pdf"
    assert job_data["file_size"] == 1024
    assert job_data["status"] == JobStatusEnum.QUEUED.value


def test_get_nonexistent_job(job_service):
    """Test getting a job that doesn't exist"""
    result = job_service.get_job("nonexistent-id")
    assert result is None


def test_update_job_status(job_service):
    """Test updating job status and metadata"""
    job_id = job_service.create_job("test.pdf", 1024)
    
    # Update to processing
    success = job_service.update_job_status(
        job_id=job_id,
        status=JobStatusEnum.PROCESSING,
        progress=50,
        message="Processing file"
    )
    
    assert success is True
    
    job_data = job_service.get_job(job_id)
    assert job_data["status"] == JobStatusEnum.PROCESSING.value
    assert job_data["progress_percent"] == 50
    assert job_data["message"] == "Processing file"


def test_update_job_to_completed_with_result(job_service):
    """Test updating job to completed with result data"""
    job_id = job_service.create_job("test.pdf", 1024)
    
    result_data = {"rooms": [{"name": "Living Room", "area": 200}]}
    
    success = job_service.update_job_status(
        job_id=job_id,
        status=JobStatusEnum.COMPLETED,
        progress=100,
        message="Processing completed",
        result=result_data
    )
    
    assert success is True
    
    job_data = job_service.get_job(job_id)
    assert job_data["status"] == JobStatusEnum.COMPLETED.value
    assert job_data["result"] == result_data


def test_update_job_to_failed_with_error(job_service):
    """Test updating job to failed with error message"""
    job_id = job_service.create_job("test.pdf", 1024)
    
    success = job_service.update_job_status(
        job_id=job_id,
        status=JobStatusEnum.FAILED,
        message="Processing failed",
        error="PDF parsing error"
    )
    
    assert success is True
    
    job_data = job_service.get_job(job_id)
    assert job_data["status"] == JobStatusEnum.FAILED.value
    assert job_data["error"] == "PDF parsing error"


def test_update_nonexistent_job(job_service):
    """Test updating a job that doesn't exist returns False"""
    success = job_service.update_job_status(
        job_id="nonexistent-id",
        status=JobStatusEnum.PROCESSING
    )
    
    assert success is False


def test_job_timestamps(job_service):
    """Test job creation and update timestamps"""
    job_id = job_service.create_job("test.pdf", 1024)
    
    job_data = job_service.get_job(job_id)
    created_at = job_data["created_at"]
    updated_at = job_data["updated_at"]
    
    # Initially created_at and updated_at should be the same
    assert created_at == updated_at
    
    # Update job status
    job_service.update_job_status(job_id, JobStatusEnum.PROCESSING)
    
    updated_job_data = job_service.get_job(job_id)
    new_updated_at = updated_job_data["updated_at"]
    
    # created_at should remain the same, updated_at should change
    assert updated_job_data["created_at"] == created_at
    assert new_updated_at != updated_at
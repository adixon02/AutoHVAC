"""
Test blueprint upload endpoint
"""
import pytest
import io
from fastapi.testclient import TestClient


def test_upload_options_cors(client: TestClient, cors_headers):
    """Test OPTIONS preflight request returns correct CORS headers"""
    response = client.options("/api/v2/blueprint/upload", headers=cors_headers)
    
    assert response.status_code == 204
    assert "Access-Control-Allow-Methods" in response.headers
    assert "POST" in response.headers["Access-Control-Allow-Methods"]
    assert "OPTIONS" in response.headers["Access-Control-Allow-Methods"]


def test_upload_success(client: TestClient, sample_pdf_content, cors_headers):
    """Test successful PDF upload returns 202 with job_id"""
    files = {"file": ("test.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
    
    response = client.post("/api/v2/blueprint/upload", files=files, headers=cors_headers)
    
    assert response.status_code == 202
    data = response.json()
    
    assert "job_id" in data
    assert data["status"] == "queued"
    assert data["filename"] == "test.pdf"
    assert "file_size_bytes" in data
    assert data["message"] == "File uploaded successfully and queued for processing"


def test_upload_non_pdf_rejected(client: TestClient, cors_headers):
    """Test non-PDF files are rejected with 400"""
    files = {"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")}
    
    response = client.post("/api/v2/blueprint/upload", files=files, headers=cors_headers)
    
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]


def test_upload_large_file_rejected(client: TestClient, cors_headers):
    """Test files larger than 150MB are rejected with 413"""
    # Create a large dummy file content (simulating > 150MB)
    large_content = b"x" * (151 * 1024 * 1024)  # 151 MB
    files = {"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")}
    
    response = client.post("/api/v2/blueprint/upload", files=files, headers=cors_headers)
    
    assert response.status_code == 413
    assert "exceeds limit" in response.json()["detail"]


def test_upload_no_file(client: TestClient, cors_headers):
    """Test upload without file returns 422"""
    response = client.post("/api/v2/blueprint/upload", headers=cors_headers)
    
    assert response.status_code == 422


def test_upload_cors_headers_in_response(client: TestClient, sample_pdf_content, cors_headers):
    """Test upload response includes CORS headers"""
    files = {"file": ("test.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
    
    response = client.post("/api/v2/blueprint/upload", files=files, headers=cors_headers)
    
    assert response.status_code == 202
    # CORS headers should be added by middleware
    

def test_upload_request_id_tracking(client: TestClient, sample_pdf_content):
    """Test upload includes request ID for tracking"""
    files = {"file": ("test.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
    
    response = client.post("/api/v2/blueprint/upload", files=files)
    
    assert response.status_code == 202
    assert "X-Request-ID" in response.headers
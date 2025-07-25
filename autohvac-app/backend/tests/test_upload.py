"""
Comprehensive tests for hardened blueprint upload system
Tests CORS, file limits, async processing, and job polling
"""
import pytest
import tempfile
import os
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
import asyncio

# Import the app
from app.main import app

client = TestClient(app)

class TestCORSAndPreflight:
    """Test CORS configuration and preflight requests"""
    
    def test_cors_preflight_allowed_origin(self):
        """Test CORS preflight with allowed origin"""
        response = client.options(
            "/api/v2/blueprint/upload",
            headers={
                "Origin": "https://auto-hvac.vercel.app",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type"
            }
        )
        
        assert response.status_code == 204
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "https://auto-hvac.vercel.app"
        assert "access-control-allow-methods" in response.headers
        assert "POST" in response.headers["access-control-allow-methods"]
    
    def test_cors_preflight_vercel_preview(self):
        """Test CORS preflight with Vercel preview URL"""
        preview_url = "https://auto-hvac-git-feature-user.vercel.app"
        
        response = client.options(
            "/api/v2/blueprint/upload",
            headers={
                "Origin": preview_url,
                "Access-Control-Request-Method": "POST"
            }
        )
        
        assert response.status_code == 204
        assert response.headers["access-control-allow-origin"] == preview_url
    
    def test_cors_preflight_localhost(self):
        """Test CORS preflight with localhost"""
        response = client.options(
            "/api/v2/blueprint/upload",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        assert response.status_code == 204
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    
    def test_cors_preflight_denied_origin(self):
        """Test CORS preflight with denied origin"""
        response = client.options(
            "/api/v2/blueprint/upload",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        # Should still return 204 but without allow-origin header
        assert response.status_code == 204
        assert "access-control-allow-origin" not in response.headers

class TestFileUpload:
    """Test file upload functionality and limits"""
    
    def create_test_pdf(self, size_mb: float) -> tempfile.NamedTemporaryFile:
        """Create a temporary PDF file of specified size"""
        temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        
        # Write PDF header
        temp_file.write(b"%PDF-1.4\n")
        
        # Fill with dummy content to reach desired size
        target_size = int(size_mb * 1024 * 1024)
        current_size = temp_file.tell()
        
        chunk = b"0" * 1024  # 1KB chunks
        while current_size < target_size:
            remaining = target_size - current_size
            write_size = min(len(chunk), remaining)
            temp_file.write(chunk[:write_size])
            current_size += write_size
        
        # Write PDF footer
        temp_file.write(b"\n%%EOF")
        temp_file.close()
        
        return temp_file
    
    def test_upload_small_file_success(self):
        """Test successful upload of small PDF file"""
        # Create 1MB test file
        test_file = self.create_test_pdf(1.0)
        
        try:
            with open(test_file.name, "rb") as f:
                response = client.post(
                    "/api/v2/blueprint/upload",
                    files={"file": ("test.pdf", f, "application/pdf")},
                    data={
                        "zip_code": "90210",
                        "project_name": "Test Project",
                        "building_type": "Office",
                        "construction_type": "Steel Frame"
                    },
                    headers={"Origin": "https://auto-hvac.vercel.app"}
                )
            
            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "queued"
            assert data["file_size_mb"] == 1.0
            assert "response_time_seconds" in data
            
            # Verify CORS headers
            assert response.headers["access-control-allow-origin"] == "https://auto-hvac.vercel.app"
            
        finally:
            os.unlink(test_file.name)
    
    def test_upload_large_file_within_limit(self):
        """Test upload of large file within 150MB limit"""
        # Create 100MB test file
        test_file = self.create_test_pdf(100.0)
        
        try:
            with open(test_file.name, "rb") as f:
                response = client.post(
                    "/api/v2/blueprint/upload",
                    files={"file": ("large.pdf", f, "application/pdf")},
                    data={
                        "zip_code": "99206",
                        "project_name": "Large Test",
                        "building_type": "Residential", 
                        "construction_type": "Wood Frame"
                    },
                    headers={"Origin": "http://localhost:3000"}
                )
            
            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data
            assert data["file_size_mb"] == 100.0
            
        finally:
            os.unlink(test_file.name)
    
    def test_upload_file_exceeds_limit(self):
        """Test upload of file exceeding 150MB limit returns 413"""
        # Create 160MB test file
        test_file = self.create_test_pdf(160.0)
        
        try:
            with open(test_file.name, "rb") as f:
                response = client.post(
                    "/api/v2/blueprint/upload",
                    files={"file": ("huge.pdf", f, "application/pdf")},
                    data={
                        "zip_code": "90210",
                        "project_name": "Huge Test",
                        "building_type": "Office",
                        "construction_type": "Steel Frame"
                    },
                    headers={"Origin": "https://auto-hvac.vercel.app"}
                )
            
            assert response.status_code == 413
            data = response.json()
            assert "too large" in data["detail"].lower()
            assert "150" in data["detail"] or "150.0" in data["detail"]
            
            # Verify CORS headers even on error
            assert response.headers["access-control-allow-origin"] == "https://auto-hvac.vercel.app"
            
        finally:
            os.unlink(test_file.name)
    
    def test_upload_non_pdf_file(self):
        """Test upload of non-PDF file returns 400"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"This is not a PDF")
            temp_file.close()
            
            try:
                with open(temp_file.name, "rb") as f:
                    response = client.post(
                        "/api/v2/blueprint/upload",
                        files={"file": ("test.txt", f, "text/plain")},
                        data={
                            "zip_code": "90210",
                            "project_name": "Invalid Test",
                            "building_type": "Office",
                            "construction_type": "Steel Frame"
                        },
                        headers={"Origin": "https://auto-hvac.vercel.app"}
                    )
                
                assert response.status_code == 400
                data = response.json()
                assert "pdf" in data["detail"].lower()
                
            finally:
                os.unlink(temp_file.name)
    
    def test_upload_trailing_slash(self):
        """Test upload endpoint works with trailing slash"""
        test_file = self.create_test_pdf(1.0)
        
        try:
            with open(test_file.name, "rb") as f:
                response = client.post(
                    "/api/v2/blueprint/upload/",  # Note trailing slash
                    files={"file": ("test.pdf", f, "application/pdf")},
                    data={
                        "zip_code": "90210",
                        "project_name": "Trailing Slash Test",
                        "building_type": "Office",
                        "construction_type": "Steel Frame"
                    }
                )
            
            assert response.status_code == 202
            
        finally:
            os.unlink(test_file.name)

class TestJobPolling:
    """Test job status and result polling"""
    
    def test_job_status_not_found(self):
        """Test job status for non-existent job returns 404"""
        response = client.get("/api/v2/blueprint/status/nonexistent-job-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_job_status_queued(self):
        """Test job status for queued job"""
        # First upload a file to create a job
        test_file = self.create_test_pdf(1.0)
        
        try:
            with open(test_file.name, "rb") as f:
                upload_response = client.post(
                    "/api/v2/blueprint/upload",
                    files={"file": ("test.pdf", f, "application/pdf")},
                    data={
                        "zip_code": "90210",
                        "project_name": "Status Test",
                        "building_type": "Office", 
                        "construction_type": "Steel Frame"
                    }
                )
            
            assert upload_response.status_code == 202
            job_id = upload_response.json()["job_id"]
            
            # Check job status
            status_response = client.get(f"/api/v2/blueprint/status/{job_id}")
            
            assert status_response.status_code == 200
            data = status_response.json()
            assert data["job_id"] == job_id
            assert data["status"] in ["queued", "processing", "completed"]
            assert "progress" in data
            assert "message" in data
            assert "created_at" in data
            
        finally:
            os.unlink(test_file.name)
    
    def test_job_alternative_endpoint(self):
        """Test alternative job endpoint /api/v2/job/{job_id}"""
        test_file = self.create_test_pdf(1.0)
        
        try:
            with open(test_file.name, "rb") as f:
                upload_response = client.post(
                    "/api/v2/blueprint/upload",
                    files={"file": ("test.pdf", f, "application/pdf")},
                    data={
                        "zip_code": "90210",
                        "project_name": "Alt Endpoint Test",
                        "building_type": "Office",
                        "construction_type": "Steel Frame"
                    }
                )
            
            job_id = upload_response.json()["job_id"]
            
            # Test alternative endpoint
            response = client.get(f"/api/v2/blueprint/job/{job_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == job_id
            
        finally:
            os.unlink(test_file.name)

class TestHealthAndMisc:
    """Test health check and miscellaneous endpoints"""
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"
        assert data["max_file_size_mb"] == 150
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "AutoHVAC API V2" in data["message"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
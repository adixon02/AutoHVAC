"""
Test configuration and fixtures
"""
import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


@pytest.fixture
def client():
    """Test client for API requests"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def temp_upload_dir():
    """Temporary directory for file uploads during tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_temp_dir = settings.temp_dir  
        settings.temp_dir = temp_dir
        yield temp_dir
        settings.temp_dir = original_temp_dir


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing"""
    # Minimal PDF content that can be used for testing
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000097 00000 n 
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
149
%%EOF"""


@pytest.fixture
def sample_pdf_file(sample_pdf_content, temp_upload_dir):
    """Sample PDF file for upload tests"""
    file_path = Path(temp_upload_dir) / "test.pdf"
    with open(file_path, "wb") as f:
        f.write(sample_pdf_content)
    return file_path


@pytest.fixture
def cors_headers():
    """CORS headers for testing"""
    return {
        "Origin": "https://auto-hvac.vercel.app",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type"
    }


@pytest.fixture(autouse=True)
def reset_job_storage():
    """Reset job storage before each test"""
    from app.services.job_storage import job_storage
    job_storage.memory_storage.clear()
    yield
    job_storage.memory_storage.clear()
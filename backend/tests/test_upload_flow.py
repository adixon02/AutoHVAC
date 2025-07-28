"""
Test upload-to-completion flow with large PDFs
"""

import pytest
import asyncio
import time
import io
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app
from database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models.db_models import Base, User

# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_db():
    """Create a test database session"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        # Pre-create a verified test user
        test_user = User(
            email="test@example.com",
            email_verified=True,
            free_report_used=False
        )
        session.add(test_user)
        await session.commit()
    
    yield async_session_maker
    
    await engine.dispose()

@pytest.fixture
async def client(test_db):
    """Create test client with database override"""
    async def get_test_db():
        async with test_db() as session:
            yield session
    
    app.dependency_overrides[get_async_session] = get_test_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

def create_large_pdf(size_mb=50):
    """Create a dummy PDF of specified size in MB"""
    pdf_header = b"%PDF-1.4\n"
    pdf_footer = b"\n%%EOF"
    # Calculate how much dummy content we need
    target_size = size_mb * 1024 * 1024
    current_size = len(pdf_header) + len(pdf_footer)
    
    # Create dummy PDF content (simulating pages)
    dummy_content = b"1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    dummy_content += b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    dummy_content += b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\n"
    
    # Fill remaining space with comments (PDF allows comments)
    remaining = target_size - current_size - len(dummy_content)
    if remaining > 0:
        # Add comments in chunks to avoid memory issues
        comment_chunk = b"% " + b"0" * 78 + b"\n"  # 80 bytes per line
        chunks_needed = remaining // len(comment_chunk)
        dummy_content += comment_chunk * chunks_needed
    
    return pdf_header + dummy_content + pdf_footer

async def poll_until_complete(client, job_id, timeout=60):
    """Poll job status until complete or timeout"""
    start_time = time.time()
    last_progress = 0
    
    while time.time() - start_time < timeout:
        response = await client.get(f"/api/v1/job/{job_id}")
        data = response.json()
        status = data["status"]
        progress = data.get("progress_percent", 0)
        
        # Log progress updates
        if progress > last_progress:
            print(f"Progress: {progress}% - {data.get('current_stage', 'unknown')}")
            last_progress = progress
        
        if status in ["completed", "failed"]:
            return status, data
        
        # Verify we get 202 for processing jobs
        if status in ["pending", "processing"]:
            assert response.status_code == 202, f"Expected 202 for {status}, got {response.status_code}"
        
        await asyncio.sleep(2)
    
    return "timeout", {"error": f"Job did not complete within {timeout}s"}

@pytest.mark.asyncio
async def test_upload_to_completion_flow(client):
    """Test complete upload flow from file upload to job completion"""
    # Create a regular PDF (not 50MB for faster tests)
    pdf_content = create_large_pdf(1)  # 1MB for faster testing
    pdf_file = io.BytesIO(pdf_content)
    
    # Prepare upload data
    files = {
        "file": ("test.pdf", pdf_file, "application/pdf")
    }
    data = {
        "email": "test@example.com",
        "project_label": "Test Upload Flow",
        "duct_config": "ducted_attic",
        "heating_fuel": "gas"
    }
    
    # Upload the file
    print("Uploading file...")
    response = await client.post("/api/v1/blueprint/upload", data=data, files=files)
    assert response.status_code == 200, f"Upload failed: {response.text}"
    
    result = response.json()
    assert "jobId" in result, "Response missing jobId"
    job_id = result["jobId"]
    print(f"Got job ID: {job_id}")
    
    # Poll until complete
    print("Polling for completion...")
    final_status, final_data = await poll_until_complete(client, job_id, timeout=30)
    
    # Verify completion
    assert final_status == "completed", f"Job ended with status: {final_status}, error: {final_data.get('error')}"
    assert final_data.get("progress_percent") == 100, "Job should be at 100% when completed"
    print("✅ Job completed successfully!")

@pytest.mark.asyncio
async def test_large_pdf_upload(client):
    """Test uploading a large PDF file"""
    # Create 50MB PDF
    print("Creating 50MB test PDF...")
    large_pdf = create_large_pdf(50)
    
    files = {
        "file": ("large.pdf", io.BytesIO(large_pdf), "application/pdf")
    }
    data = {
        "email": "test@example.com",
        "project_label": "Large PDF Test",
        "duct_config": "ducted_attic",
        "heating_fuel": "gas"
    }
    
    # Test upload
    print("Uploading 50MB file...")
    response = await client.post("/api/v1/blueprint/upload", data=data, files=files)
    assert response.status_code == 200, f"Large upload failed: {response.text}"
    
    job_id = response.json()["jobId"]
    print(f"Large PDF job ID: {job_id}")
    
    # Just verify it started processing
    await asyncio.sleep(2)
    status_response = await client.get(f"/api/v1/job/{job_id}")
    assert status_response.status_code in [200, 202], "Job status check failed"
    
    status_data = status_response.json()
    assert status_data["status"] in ["pending", "processing", "completed"], "Invalid job status"
    assert status_data.get("progress_percent", 0) >= 1, "Progress should have started"
    print(f"✅ Large PDF processing started: {status_data['status']} at {status_data.get('progress_percent', 0)}%")

@pytest.mark.asyncio
async def test_progress_tracking(client):
    """Test that progress updates during processing"""
    # Upload a file
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF"
    files = {"file": ("progress_test.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {
        "email": "test@example.com",
        "project_label": "Progress Test",
        "duct_config": "ducted_attic",
        "heating_fuel": "gas"
    }
    
    response = await client.post("/api/v1/blueprint/upload", data=data, files=files)
    job_id = response.json()["jobId"]
    
    # Track progress changes
    progress_values = []
    stages_seen = []
    
    for _ in range(10):  # Poll up to 10 times
        response = await client.get(f"/api/v1/job/{job_id}")
        data = response.json()
        
        progress = data.get("progress_percent", 0)
        stage = data.get("current_stage", "")
        
        if progress not in progress_values:
            progress_values.append(progress)
        if stage and stage not in stages_seen:
            stages_seen.append(stage)
        
        if data["status"] in ["completed", "failed"]:
            break
        
        await asyncio.sleep(1)
    
    # Verify we saw progress updates
    print(f"Progress values seen: {progress_values}")
    print(f"Stages seen: {stages_seen}")
    
    assert len(progress_values) > 1, "Should see multiple progress values"
    assert 1 in progress_values, "Should start at 1% after upload"
    assert any(p > 1 for p in progress_values), "Progress should increase beyond 1%"
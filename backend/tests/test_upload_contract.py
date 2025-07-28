"""
Test upload endpoint contract to ensure consistent API response format.
This prevents frontend navigation errors caused by key mismatches.
"""

import pytest
import uuid
from httpx import AsyncClient
from fastapi.testclient import TestClient
import io

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

@pytest.mark.asyncio
async def test_upload_response_contract(client):
    """Test that upload endpoint returns correct camelCase keys"""
    # Create a dummy PDF file
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n9\n%%EOF"
    pdf_file = io.BytesIO(pdf_content)
    
    # Prepare form data
    files = {
        "file": ("test.pdf", pdf_file, "application/pdf")
    }
    data = {
        "email": "test@example.com",
        "project_label": "Test Project",
        "duct_config": "ducted_attic",
        "heating_fuel": "gas"
    }
    
    # Make upload request
    response = await client.post("/api/v1/blueprint/upload", data=data, files=files)
    
    # Assert response is successful
    assert response.status_code == 200, f"Upload failed: {response.text}"
    
    # Parse response JSON
    result = response.json()
    
    # Assert exact keys are present (camelCase)
    expected_keys = {"jobId", "status", "projectLabel"}
    actual_keys = set(result.keys())
    assert actual_keys == expected_keys, f"Expected keys {expected_keys}, got {actual_keys}"
    
    # Assert jobId is a valid UUID
    job_id = result["jobId"]
    try:
        uuid.UUID(job_id)
    except ValueError:
        pytest.fail(f"jobId '{job_id}' is not a valid UUID")
    
    # Assert other fields have expected values
    assert result["status"] == "pending"
    assert result["projectLabel"] == "Test Project"
    
    # Test immediate job status lookup
    status_response = await client.get(f"/api/v1/job/{job_id}")
    assert status_response.status_code == 200, f"Job status lookup failed: {status_response.text}"
    
    status_data = status_response.json()
    assert status_data["job_id"] == job_id
    assert status_data["status"] in ["pending", "processing", "completed", "failed"]

@pytest.mark.asyncio
async def test_upload_without_jobid_fails(client):
    """Test that missing jobId in response would be caught"""
    # This test documents the expected behavior if the contract is broken
    # It's mainly for documentation purposes since our model enforces the contract
    
    # The response model ensures this can't happen, but we test the shape anyway
    pdf_content = b"%PDF-1.4"
    files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {
        "email": "test@example.com",
        "project_label": "Test",
        "duct_config": "ducted_attic",
        "heating_fuel": "gas"
    }
    
    response = await client.post("/api/v1/blueprint/upload", data=data, files=files)
    
    if response.status_code == 200:
        result = response.json()
        # This should always pass because of our response model
        assert "jobId" in result, "Response missing required 'jobId' field"
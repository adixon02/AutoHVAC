"""
Integration tests for AutoHVAC full pipeline
Tests the complete flow from PDF parsing to Manual J calculations
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tasks.parse_blueprint import process_blueprint
from services.store import job_store
from app.parser.schema import BlueprintSchema, Room
from models.db_models import Project, JobStatus


class TestFullPipeline:
    """Test the complete blueprint processing pipeline"""
    
    @pytest.fixture
    def sample_pdf_bytes(self):
        """Generate sample PDF content bytes"""
        # This would typically be real PDF bytes, but for testing we use mock data
        return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n9\n%%EOF"
    
    @pytest.fixture
    def mock_blueprint_result(self):
        """Mock blueprint result from AI cleanup"""
        return BlueprintSchema(
            project_id=uuid4(),
            zip_code="90210",
            sqft_total=2000.0,
            stories=1,
            rooms=[
                Room(
                    name="Living Room",
                    dimensions_ft=(20.0, 15.0),
                    floor=1,
                    windows=3,
                    orientation="S",
                    area=300.0
                ),
                Room(
                    name="Master Bedroom",
                    dimensions_ft=(16.0, 12.0),
                    floor=1,
                    windows=2,
                    orientation="E",
                    area=192.0
                ),
                Room(
                    name="Kitchen",
                    dimensions_ft=(12.0, 10.0),
                    floor=1,
                    windows=1,
                    orientation="N",
                    area=120.0
                )
            ]
        )
    
    def test_process_blueprint_success(self, sample_pdf_bytes, mock_blueprint_result):
        """Test successful blueprint processing end-to-end"""
        job_id = "test-job-123"
        filename = "test_blueprint.pdf"
        email = "test@example.com"
        zip_code = "90210"
        
        # Mock the AI cleanup to return predictable results
        with patch('app.parser.ai_cleanup.cleanup', new_callable=AsyncMock) as mock_cleanup:
            mock_cleanup.return_value = mock_blueprint_result
            
            # Mock the geometry and text parsers to return valid data
            with patch('app.parser.geometry_parser.GeometryParser') as MockGeometryParser:
                with patch('app.parser.text_parser.TextParser') as MockTextParser:
                    # Setup geometry parser mock
                    mock_geo_parser = Mock()
                    mock_geo_result = Mock()
                    mock_geo_result.lines = []
                    mock_geo_result.rectangles = []
                    mock_geo_result.polylines = []
                    mock_geo_result.page_width = 792.0
                    mock_geo_result.page_height = 612.0
                    mock_geo_result.scale_factor = 48.0
                    mock_geo_parser.parse.return_value = mock_geo_result
                    MockGeometryParser.return_value = mock_geo_parser
                    
                    # Setup text parser mock
                    mock_text_parser = Mock()
                    mock_text_result = Mock()
                    mock_text_result.words = []
                    mock_text_result.room_labels = []
                    mock_text_result.dimensions = []
                    mock_text_result.notes = []
                    mock_text_parser.parse.return_value = mock_text_result
                    MockTextParser.return_value = mock_text_parser
                    
                    # Initialize job store entry
                    job_store.update_job(job_id, {
                        "status": "pending",
                        "stage": "queued",
                        "progress": 0
                    })
                    
                    # Run the processing task
                    process_blueprint(job_id, sample_pdf_bytes, filename, email, zip_code)
                    
                    # Verify final job state
                    final_job = job_store.get_job(job_id)
                    
                    assert final_job["status"] == "completed"
                    assert final_job["stage"] == "complete"
                    assert final_job["progress"] == 100
                    assert "result" in final_job
                    
                    result = final_job["result"]
                    assert result["job_id"] == job_id
                    assert result["filename"] == filename
                    assert result["email"] == email
                    assert "blueprint" in result
                    assert "hvac_analysis" in result
                    assert "raw_data" in result
                    assert "processing_stats" in result
                    
                    # Verify blueprint data
                    blueprint = result["blueprint"]
                    assert blueprint["zip_code"] == "90210"
                    assert blueprint["sqft_total"] == 2000.0
                    assert blueprint["stories"] == 1
                    assert len(blueprint["rooms"]) == 3
                    
                    # Verify HVAC analysis
                    hvac = result["hvac_analysis"]
                    assert "heating_total" in hvac
                    assert "cooling_total" in hvac
                    assert "zones" in hvac
                    assert "equipment_recommendations" in hvac
                    assert len(hvac["zones"]) == 3
    
    def test_process_blueprint_ai_failure(self, sample_pdf_bytes):
        """Test blueprint processing handles AI cleanup failures"""
        job_id = "test-job-ai-fail"
        filename = "test_blueprint.pdf"
        
        # Mock AI cleanup to raise an error
        with patch('app.parser.ai_cleanup.cleanup', new_callable=AsyncMock) as mock_cleanup:
            mock_cleanup.side_effect = Exception("AI processing failed")
            
            # Mock parsers to return valid data
            with patch('app.parser.geometry_parser.GeometryParser') as MockGeometryParser:
                with patch('app.parser.text_parser.TextParser') as MockTextParser:
                    mock_geo_parser = Mock()
                    mock_geo_result = Mock()
                    mock_geo_result.lines = []
                    mock_geo_result.rectangles = []
                    mock_geo_result.polylines = []
                    mock_geo_parser.parse.return_value = mock_geo_result
                    MockGeometryParser.return_value = mock_geo_parser
                    
                    mock_text_parser = Mock()
                    mock_text_result = Mock()
                    mock_text_result.words = []
                    mock_text_result.room_labels = []
                    mock_text_result.dimensions = []
                    mock_text_result.notes = []
                    mock_text_parser.parse.return_value = mock_text_result
                    MockTextParser.return_value = mock_text_parser
                    
                    # Initialize job
                    job_store.update_job(job_id, {
                        "status": "pending",
                        "stage": "queued",
                        "progress": 0
                    })
                    
                    # Run processing - should handle the error gracefully
                    process_blueprint(job_id, sample_pdf_bytes, filename)
                    
                    # Verify error handling
                    final_job = job_store.get_job(job_id)
                    
                    assert final_job["status"] == "failed"
                    assert "error" in final_job
                    assert "AI processing failed" in final_job["error"]
    
    def test_process_blueprint_pdf_parsing_failure(self, sample_pdf_bytes):
        """Test blueprint processing handles PDF parsing failures"""
        job_id = "test-job-pdf-fail"
        filename = "invalid_blueprint.pdf"
        
        # Mock geometry parser to raise an error
        with patch('app.parser.geometry_parser.GeometryParser') as MockGeometryParser:
            mock_geo_parser = Mock()
            mock_geo_parser.parse.side_effect = Exception("PDF parsing failed")
            MockGeometryParser.return_value = mock_geo_parser
            
            # Initialize job
            job_store.update_job(job_id, {
                "status": "pending",
                "stage": "queued", 
                "progress": 0
            })
            
            # Run processing
            process_blueprint(job_id, sample_pdf_bytes, filename)
            
            # Verify error handling
            final_job = job_store.get_job(job_id)
            
            assert final_job["status"] == "failed"
            assert "error" in final_job
            assert "PDF parsing failed" in final_job["error"]
    
    def test_job_progress_tracking(self, sample_pdf_bytes, mock_blueprint_result):
        """Test that job progress is properly tracked through pipeline stages"""
        job_id = "test-job-progress"
        filename = "test_blueprint.pdf"
        
        progress_history = []
        
        # Mock job_store to capture progress updates
        original_update = job_store.update_job
        def capture_progress(job_id, update_data):
            if "progress" in update_data:
                progress_history.append({
                    "stage": update_data.get("stage", "unknown"),
                    "progress": update_data["progress"]
                })
            return original_update(job_id, update_data)
        
        with patch.object(job_store, 'update_job', side_effect=capture_progress):
            with patch('app.parser.ai_cleanup.cleanup', new_callable=AsyncMock) as mock_cleanup:
                mock_cleanup.return_value = mock_blueprint_result
                
                with patch('app.parser.geometry_parser.GeometryParser') as MockGeometryParser:
                    with patch('app.parser.text_parser.TextParser') as MockTextParser:
                        # Setup mocks
                        mock_geo_parser = Mock()
                        mock_geo_result = Mock()
                        mock_geo_result.lines = []
                        mock_geo_result.rectangles = []
                        mock_geo_result.polylines = []
                        mock_geo_result.page_width = 792.0
                        mock_geo_result.page_height = 612.0
                        mock_geo_result.scale_factor = 48.0
                        mock_geo_parser.parse.return_value = mock_geo_result
                        MockGeometryParser.return_value = mock_geo_parser
                        
                        mock_text_parser = Mock()
                        mock_text_result = Mock()
                        mock_text_result.words = []
                        mock_text_result.room_labels = []
                        mock_text_result.dimensions = []
                        mock_text_result.notes = []
                        mock_text_parser.parse.return_value = mock_text_result
                        MockTextParser.return_value = mock_text_parser
                        
                        # Initialize and run
                        job_store.update_job(job_id, {
                            "status": "pending",
                            "stage": "queued",
                            "progress": 0
                        })
                        
                        process_blueprint(job_id, sample_pdf_bytes, filename)
        
        # Verify progress was tracked through expected stages
        expected_stages = [
            "initializing",
            "extracting_geometry", 
            "extracting_text",
            "ai_processing",
            "calculating_loads",
            "finalizing"
        ]
        
        recorded_stages = [entry["stage"] for entry in progress_history if entry["stage"] in expected_stages]
        
        # Should have hit most of the major stages
        assert len(recorded_stages) >= 4
        assert "initializing" in recorded_stages
        assert "finalizing" in recorded_stages
        
        # Progress should generally increase
        progress_values = [entry["progress"] for entry in progress_history]
        assert progress_values[0] <= progress_values[-1]  # Should end higher than start


class TestJobStoreIntegration:
    """Test integration with job storage system"""
    
    def test_job_lifecycle(self):
        """Test complete job lifecycle from creation to completion"""
        job_id = "lifecycle-test-job"
        
        # Job starts non-existent
        initial_job = job_store.get_job(job_id)
        assert initial_job == {}
        
        # Job gets created
        job_store.update_job(job_id, {
            "status": "pending",
            "stage": "queued",
            "progress": 0
        })
        
        pending_job = job_store.get_job(job_id)
        assert pending_job["status"] == "pending"
        assert pending_job["stage"] == "queued"
        assert pending_job["progress"] == 0
        
        # Job progresses through stages
        job_store.update_job(job_id, {
            "status": "processing",
            "stage": "extracting_geometry",
            "progress": 20
        })
        
        processing_job = job_store.get_job(job_id)
        assert processing_job["status"] == "processing" 
        assert processing_job["stage"] == "extracting_geometry"
        assert processing_job["progress"] == 20
        
        # Job completes
        final_result = {
            "job_id": job_id,
            "blueprint": {"rooms": []},
            "hvac_analysis": {"heating_total": 10000}
        }
        
        job_store.update_job(job_id, {
            "status": "completed",
            "stage": "complete",
            "progress": 100,
            "result": final_result
        })
        
        completed_job = job_store.get_job(job_id)
        assert completed_job["status"] == "completed"
        assert completed_job["progress"] == 100
        assert "result" in completed_job
        assert completed_job["result"]["job_id"] == job_id


class TestErrorHandling:
    """Test error handling in various failure scenarios"""
    
    def test_malformed_pdf_handling(self):
        """Test handling of malformed PDF files"""
        job_id = "malformed-pdf-test"
        malformed_pdf = b"Not a real PDF file"
        filename = "malformed.pdf"
        
        # This should be handled gracefully by the parsers
        job_store.update_job(job_id, {
            "status": "pending",
            "stage": "queued",
            "progress": 0
        })
        
        process_blueprint(job_id, malformed_pdf, filename)
        
        final_job = job_store.get_job(job_id)
        assert final_job["status"] == "failed"
        assert "error" in final_job
    
    def test_empty_pdf_handling(self):
        """Test handling of empty PDF files"""
        job_id = "empty-pdf-test"
        empty_pdf = b""
        filename = "empty.pdf"
        
        job_store.update_job(job_id, {
            "status": "pending",
            "stage": "queued",
            "progress": 0
        })
        
        process_blueprint(job_id, empty_pdf, filename)
        
        final_job = job_store.get_job(job_id)
        assert final_job["status"] == "failed"
        assert "error" in final_job


class TestDatabaseSchema:
    """Test database schema consistency"""
    
    def test_project_model_with_progress_fields(self):
        """Test that Project model can be instantiated with progress tracking fields"""
        # Test that we can create a Project instance with all required fields
        project = Project(
            user_email="test@example.com",
            project_label="Test Project",
            filename="test.pdf",
            file_size=1024,
            status=JobStatus.PENDING,
            progress_percent=0,
            current_stage="initializing",
            duct_config="ducted_attic",
            heating_fuel="gas",
            assumptions_collected=True
        )
        
        # Verify fields are set correctly
        assert project.progress_percent == 0
        assert project.current_stage == "initializing"
        assert project.status == JobStatus.PENDING
        assert project.user_email == "test@example.com"
        assert project.project_label == "Test Project"
        assert project.filename == "test.pdf"
        assert project.file_size == 1024
        assert project.duct_config == "ducted_attic"
        assert project.heating_fuel == "gas"
        assert project.assumptions_collected is True
        
        # Verify that required fields have proper defaults
        project_with_defaults = Project(
            user_email="test2@example.com",
            project_label="Test Project 2", 
            filename="test2.pdf"
        )
        
        assert project_with_defaults.progress_percent == 0
        assert project_with_defaults.current_stage == "initializing"
        assert project_with_defaults.status == JobStatus.PENDING
        assert project_with_defaults.assumptions_collected is False


if __name__ == "__main__":
    pytest.main([__file__])
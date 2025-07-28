"""
Test concurrent progress updates and job status polling
Verifies that background job processing doesn't conflict with API requests
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from services.simple_job_processor import process_job_sync
from services.job_service import job_service
from routes.job import router as job_router
from fastapi import FastAPI
import threading


class TestConcurrentProgress:
    """Test concurrent access to job progress updates"""

    @pytest.fixture
    def sample_pdf_path(self):
        """Create a temporary PDF file for testing"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            # Write minimal PDF content
            f.write(b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 1 /Root 1 0 R >>\nstartxref\n9\n%%EOF')
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except:
            pass

    @pytest.fixture
    def test_app(self):
        """Create FastAPI test app"""
        app = FastAPI()
        app.include_router(job_router, prefix="/job")
        return app

    @pytest.mark.asyncio
    async def test_concurrent_job_status_polling_no_interface_error(self, sample_pdf_path, test_app):
        """
        Test that 20 concurrent job status polls don't cause InterfaceError
        while background job processor is running
        """
        project_id = "concurrent-test-job"
        
        # Mock successful AI processing to avoid OpenAI calls
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch('services.simple_job_processor.GeometryParser') as mock_geo:
                with patch('services.simple_job_processor.TextParser') as mock_text:
                    with patch('services.simple_job_processor.cleanup', new_callable=AsyncMock) as mock_cleanup:
                        with patch('services.simple_job_processor.extract_envelope_data', new_callable=AsyncMock) as mock_envelope:
                            with patch('fitz.open') as mock_fitz:
                                
                                # Mock successful responses
                                mock_doc = MagicMock()
                                mock_doc.__len__ = MagicMock(return_value=1)
                                mock_doc.get_text = MagicMock(return_value="Living Room 12x15")
                                mock_fitz.return_value = mock_doc
                                
                                mock_geo.return_value.parse = MagicMock(return_value=MagicMock())
                                mock_text.return_value.parse = MagicMock(return_value=MagicMock())
                                
                                mock_blueprint = MagicMock()
                                mock_blueprint.dict = MagicMock(return_value={"rooms": [{"name": "Living Room"}]})
                                mock_cleanup.return_value = mock_blueprint
                                
                                mock_envelope.return_value = MagicMock(__dict__={"wall_r_value": 13.0})
                                
                                # Mock rate limiter
                                with patch('services.rate_limiter.rate_limiter') as mock_rate_limiter:
                                    mock_rate_limiter.decrement_active_jobs = AsyncMock()
                                    
                                    # Mock job service methods
                                    with patch('services.job_service.job_service') as mock_job_service:
                                        
                                        # Mock project data progression
                                        project_states = [
                                            # Initial state
                                            MagicMock(
                                                assumptions_collected=True,
                                                duct_config="ducted_attic", 
                                                heating_fuel="gas",
                                                parsed_schema_json=None,
                                                status="PROCESSING",
                                                progress_percent=5,
                                                current_stage="opened_pdf",
                                                error=None
                                            ),
                                            # Mid processing
                                            MagicMock(
                                                assumptions_collected=True,
                                                duct_config="ducted_attic", 
                                                heating_fuel="gas", 
                                                parsed_schema_json=None,
                                                status="PROCESSING",
                                                progress_percent=75,
                                                current_stage="extracting_text",
                                                error=None
                                            ),
                                            # Completed
                                            MagicMock(
                                                assumptions_collected=True,
                                                duct_config="ducted_attic",
                                                heating_fuel="gas",
                                                parsed_schema_json={"rooms": [{"name": "Living Room"}]},
                                                status="COMPLETED",
                                                progress_percent=100,
                                                current_stage="completed",
                                                error=None
                                            )
                                        ]
                                        
                                        call_count = 0
                                        def mock_get_project(pid):
                                            nonlocal call_count
                                            if call_count < 5:
                                                result = project_states[0]
                                            elif call_count < 15: 
                                                result = project_states[1]
                                            else:
                                                result = project_states[2]
                                            call_count += 1
                                            return result
                                        
                                        mock_job_service.get_project = AsyncMock(side_effect=mock_get_project)
                                        mock_job_service.update_project = AsyncMock(return_value=True)
                                        mock_job_service.set_project_completed = AsyncMock(return_value=True)
                                        mock_job_service.wait_for_assumptions = AsyncMock(return_value=True)
                                        
                                        # Start background job processor
                                        job_task = asyncio.create_task(
                                            process_job_sync(project_id, sample_pdf_path, "test.pdf", "test@example.com")
                                        )
                                        
                                        # Wait a bit for job to start
                                        await asyncio.sleep(0.1)
                                        
                                        # Create 20 concurrent job status requests
                                        async def poll_job_status():
                                            """Simulate API request polling job status"""
                                            try:
                                                # This simulates the actual API endpoint behavior
                                                project = await job_service.get_project(project_id)
                                                if not project:
                                                    return {"error": "Job not found"}
                                                
                                                return {
                                                    "job_id": project_id,
                                                    "status": project.status,
                                                    "progress_percent": project.progress_percent,
                                                    "current_stage": project.current_stage,
                                                    "error": project.error
                                                }
                                            except Exception as e:
                                                # This should NOT be an InterfaceError
                                                return {"error": str(e), "error_type": type(e).__name__}
                                        
                                        # Launch 20 concurrent polls
                                        poll_tasks = [
                                            asyncio.create_task(poll_job_status()) 
                                            for _ in range(20)
                                        ]
                                        
                                        # Wait for all polls to complete
                                        poll_results = await asyncio.gather(*poll_tasks, return_exceptions=True)
                                        
                                        # Wait for job to complete
                                        await asyncio.wait_for(job_task, timeout=10.0)
                                        
                                        # Verify no InterfaceError occurred
                                        interface_errors = []
                                        for i, result in enumerate(poll_results):
                                            if isinstance(result, Exception):
                                                interface_errors.append(f"Poll {i}: {type(result).__name__}: {result}")
                                            elif isinstance(result, dict) and "InterfaceError" in str(result.get("error_type", "")):
                                                interface_errors.append(f"Poll {i}: {result}")
                                        
                                        assert not interface_errors, f"InterfaceError detected in concurrent polls: {interface_errors}"
                                        
                                        # Verify job completed successfully (no unhandled exceptions)
                                        assert job_task.done()
                                        assert not job_task.cancelled()
                                        
                                        # Get final job status to verify completion
                                        final_project = await job_service.get_project(project_id)
                                        assert final_project.status == "COMPLETED", f"Job should complete successfully, got: {final_project.status}"

    @pytest.mark.asyncio
    async def test_rapid_progress_updates_no_deadlock(self):
        """Test that rapid progress updates don't cause deadlocks"""
        project_id = "rapid-progress-test"
        
        with patch('services.job_service.job_service') as mock_job_service:
            mock_job_service.update_project = AsyncMock(return_value=True)
            
            # Simulate rapid progress updates from background thread
            async def rapid_updates():
                from services.simple_job_processor import update_progress
                
                for i in range(0, 101, 5):  # 0%, 5%, 10%, ... 100%
                    await update_progress(project_id, i, f"stage_{i}")
                    await asyncio.sleep(0.01)  # 10ms between updates
            
            # Run rapid updates
            await asyncio.wait_for(rapid_updates(), timeout=5.0)
            
            # Verify all updates succeeded (no exceptions raised)
            assert mock_job_service.update_project.call_count == 21  # 0 to 100 by 5s = 21 calls

    @pytest.mark.asyncio 
    async def test_retry_logic_handles_transient_errors(self):
        """Test that progress update retry logic handles transient database errors"""
        project_id = "retry-test"
        
        with patch('services.job_service.job_service') as mock_job_service:
            # First call fails, second call succeeds
            mock_job_service.update_project = AsyncMock(
                side_effect=[Exception("Transient DB error"), True]
            )
            
            from services.simple_job_processor import update_progress
            
            # Should succeed after retry
            await update_progress(project_id, 50, "test_stage")
            
            # Verify retry happened
            assert mock_job_service.update_project.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_logic_fails_after_max_attempts(self):
        """Test that progress updates fail after max retry attempts"""
        project_id = "retry-fail-test"
        
        with patch('services.job_service.job_service') as mock_job_service:
            # Both attempts fail
            mock_job_service.update_project = AsyncMock(
                side_effect=Exception("Persistent DB error")
            )
            
            from services.simple_job_processor import update_progress
            
            # Should raise exception after 2 attempts
            with pytest.raises(Exception, match="Persistent DB error"):
                await update_progress(project_id, 50, "test_stage")
            
            # Verify 2 attempts were made
            assert mock_job_service.update_project.call_count == 2

    @pytest.mark.asyncio
    async def test_session_isolation_between_operations(self):
        """Test that different job operations use isolated database sessions"""
        project_id = "session-isolation-test"
        
        # Track session creation calls
        session_creations = []
        
        original_get_async_session = None
        
        async def mock_session_generator():
            session_id = len(session_creations)
            session_creations.append(session_id)
            
            # Create a mock session
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            yield mock_session
        
        with patch('database.get_async_session', side_effect=mock_session_generator):
            with patch('services.job_service.job_service') as mock_job_service:
                mock_job_service.update_project = AsyncMock(return_value=True)
                mock_job_service.get_project = AsyncMock(return_value=MagicMock(
                    status="PROCESSING",
                    progress_percent=0,
                    current_stage="started"
                ))
                
                from services.simple_job_processor import update_progress
                
                # Perform multiple operations
                await update_progress(project_id, 25, "stage1")
                await update_progress(project_id, 50, "stage2") 
                await update_progress(project_id, 75, "stage3")
                
                # Each operation should use a fresh session
                assert len(session_creations) >= 3, "Each progress update should create a fresh session"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
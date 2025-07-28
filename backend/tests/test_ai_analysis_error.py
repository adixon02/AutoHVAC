"""
Integration tests for AI analysis error handling in job processor
Tests various failure modes to ensure jobs properly fail instead of hanging
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import patch, AsyncMock, MagicMock
from services.simple_job_processor import (
    run_ai_analysis, 
    MissingAIKeyError, 
    AIAnalysisTimeoutError, 
    PDFTooLargeError,
    process_job_sync
)
from services.job_service import job_service
from app.parser.ai_cleanup import AICleanupError
from services.envelope_extractor import EnvelopeExtractorError
from database import AsyncSessionLocal


class TestAIAnalysisErrorHandling:
    """Test suite for AI analysis error handling"""

    @pytest.fixture
    async def mock_session(self):
        """Mock database session"""
        session = AsyncMock()
        return session

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

    @pytest.mark.asyncio
    async def test_missing_openai_key_fast_fail(self, mock_session, sample_pdf_path):
        """Test that missing OpenAI API key causes immediate failure"""
        
        with patch.dict(os.environ, {}, clear=True):  # Clear all env vars
            with pytest.raises(MissingAIKeyError) as exc_info:
                await run_ai_analysis("test-job-123", sample_pdf_path, mock_session)
            
            assert "OPENAI_API_KEY environment variable is missing or blank" in str(exc_info.value)
            
            # Verify job was marked as failed
            job_service.set_project_failed.assert_called_once()
            call_args = job_service.set_project_failed.call_args
            assert call_args[0][0] == "test-job-123"  # project_id
            assert "MissingAIKeyError" in call_args[0][1]  # error message

    @pytest.mark.asyncio 
    async def test_blank_openai_key_fast_fail(self, mock_session, sample_pdf_path):
        """Test that blank OpenAI API key causes immediate failure"""
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "   "}, clear=True):
            with pytest.raises(MissingAIKeyError):
                await run_ai_analysis("test-job-124", sample_pdf_path, mock_session)

    @pytest.mark.asyncio
    async def test_pdf_too_large_error(self, mock_session, sample_pdf_path):
        """Test that PDFs with too many pages are rejected"""
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch('fitz.open') as mock_fitz:
                # Mock PDF with 100 pages (exceeds MAX_PAGES = 50)
                mock_doc = MagicMock()
                mock_doc.__len__ = MagicMock(return_value=100)
                mock_fitz.return_value = mock_doc
                
                with pytest.raises(PDFTooLargeError) as exc_info:
                    await run_ai_analysis("test-job-125", sample_pdf_path, mock_session)
                
                assert "100 pages" in str(exc_info.value)
                assert "split large blueprints" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_geometry_parser_timeout(self, mock_session, sample_pdf_path):
        """Test that geometry parser timeout is handled"""
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch('fitz.open') as mock_fitz:
                # Mock valid PDF
                mock_doc = MagicMock()
                mock_doc.__len__ = MagicMock(return_value=1)
                mock_fitz.return_value = mock_doc
                
                with patch('services.simple_job_processor.GeometryParser') as mock_parser:
                    # Mock parser that takes too long
                    mock_instance = mock_parser.return_value
                    mock_instance.parse = MagicMock(side_effect=lambda x: asyncio.sleep(200))
                    
                    with patch('asyncio.to_thread', side_effect=asyncio.TimeoutError):
                        with pytest.raises(AIAnalysisTimeoutError) as exc_info:
                            await run_ai_analysis("test-job-126", sample_pdf_path, mock_session)
                        
                        assert "Geometry extraction timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ai_cleanup_timeout(self, mock_session, sample_pdf_path):
        """Test that AI cleanup timeout is handled"""
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch('fitz.open') as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.__len__ = MagicMock(return_value=1)
                mock_fitz.return_value = mock_doc
                
                with patch('services.simple_job_processor.GeometryParser'):
                    with patch('services.simple_job_processor.TextParser'):
                        with patch('services.simple_job_processor.cleanup', new_callable=AsyncMock) as mock_cleanup:
                            # Mock cleanup that times out
                            mock_cleanup.side_effect = asyncio.TimeoutError()
                            
                            with pytest.raises(AIAnalysisTimeoutError) as exc_info:
                                await run_ai_analysis("test-job-127", sample_pdf_path, mock_session)
                            
                            assert "AI cleanup timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_openai_api_error_handling(self, mock_session, sample_pdf_path):
        """Test that OpenAI API errors are properly handled"""
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch('fitz.open') as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.__len__ = MagicMock(return_value=1)
                mock_doc.get_text = MagicMock(return_value="sample text")
                mock_fitz.return_value = mock_doc
                
                with patch('services.simple_job_processor.GeometryParser'):
                    with patch('services.simple_job_processor.TextParser'):
                        with patch('services.simple_job_processor.cleanup', new_callable=AsyncMock) as mock_cleanup:
                            # Mock OpenAI API error
                            mock_cleanup.side_effect = AICleanupError("OpenAI API call failed: Rate limit exceeded")
                            
                            with pytest.raises(AICleanupError) as exc_info:
                                await run_ai_analysis("test-job-128", sample_pdf_path, mock_session)
                            
                            assert "OpenAI API call failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_envelope_extraction_error(self, mock_session, sample_pdf_path):
        """Test that envelope extraction errors are handled"""
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch('fitz.open') as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.__len__ = MagicMock(return_value=1)
                mock_doc.get_text = MagicMock(return_value="sample text")
                mock_fitz.return_value = mock_doc
                
                with patch('services.simple_job_processor.GeometryParser'):
                    with patch('services.simple_job_processor.TextParser'):
                        with patch('services.simple_job_processor.cleanup', new_callable=AsyncMock):
                            with patch('services.simple_job_processor.extract_envelope_data', new_callable=AsyncMock) as mock_envelope:
                                # Mock envelope extraction error
                                mock_envelope.side_effect = EnvelopeExtractorError("OpenAI quota exceeded")
                                
                                with pytest.raises(EnvelopeExtractorError) as exc_info:
                                    await run_ai_analysis("test-job-129", sample_pdf_path, mock_session)
                                
                                assert "OpenAI quota exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_happy_path_success(self, mock_session, sample_pdf_path):
        """Test successful AI analysis completion"""
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch('fitz.open') as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.__len__ = MagicMock(return_value=1)
                mock_doc.get_text = MagicMock(return_value="Living Room 12x15")
                mock_fitz.return_value = mock_doc
                
                with patch('services.simple_job_processor.GeometryParser') as mock_geo:
                    with patch('services.simple_job_processor.TextParser') as mock_text:
                        with patch('services.simple_job_processor.cleanup', new_callable=AsyncMock) as mock_cleanup:
                            with patch('services.simple_job_processor.extract_envelope_data', new_callable=AsyncMock) as mock_envelope:
                                
                                # Mock successful responses
                                mock_geo.return_value.parse = MagicMock(return_value=MagicMock())
                                mock_text.return_value.parse = MagicMock(return_value=MagicMock())
                                
                                mock_blueprint = MagicMock()
                                mock_blueprint.dict = MagicMock(return_value={"rooms": [{"name": "Living Room"}]})
                                mock_cleanup.return_value = mock_blueprint
                                
                                mock_envelope.return_value = MagicMock(__dict__={"wall_r_value": 13.0})
                                
                                # Should complete without raising exception
                                await run_ai_analysis("test-job-130", sample_pdf_path, mock_session)
                                
                                # Verify progress updates were called
                                assert job_service.update_project.call_count >= 5  # Multiple progress updates

    @pytest.mark.asyncio 
    async def test_full_job_processing_with_ai_error(self, sample_pdf_path):
        """Integration test: Full job processing with AI error should mark job as failed"""
        
        project_id = "integration-test-job"
        
        with patch.dict(os.environ, {}, clear=True):  # No OpenAI key
            with patch('services.simple_job_processor.AsyncSessionLocal') as mock_session_factory:
                mock_session = AsyncMock()
                mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)
                
                with patch('services.job_service.job_service') as mock_job_service:
                    mock_project = MagicMock()
                    mock_project.assumptions_collected = True
                    mock_project.duct_config = "ducted_attic"
                    mock_project.heating_fuel = "gas"
                    mock_project.parsed_schema_json = None
                    mock_job_service.get_project.return_value = mock_project
                    mock_job_service.wait_for_assumptions.return_value = True
                    
                    with patch('services.rate_limiter.rate_limiter'):
                        # This should fail due to missing OpenAI key
                        await process_job_sync(project_id, sample_pdf_path, "test.pdf", "test@example.com")
                        
                        # Verify job was marked as failed
                        mock_job_service.set_project_failed.assert_called()
                        call_args = mock_job_service.set_project_failed.call_args
                        assert "MissingAIKeyError" in call_args[0][1]


class TestProgressAlignment:
    """Test that progress percentages align with UI expectations"""
    
    @pytest.mark.asyncio
    async def test_progress_buckets_sequence(self, mock_session):
        """Test that progress updates follow the correct sequence: 65→70→75→80→85→90"""
        
        progress_updates = []
        
        def capture_progress(project_id, percent, stage, session):
            progress_updates.append((percent, stage))
            return AsyncMock()
        
        with patch('services.simple_job_processor.update_progress', side_effect=capture_progress):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
                with patch('os.path.exists', return_value=True):
                    with patch('fitz.open') as mock_fitz:
                        mock_doc = MagicMock()
                        mock_doc.__len__ = MagicMock(return_value=1)
                        mock_doc.get_text = MagicMock(return_value="test")
                        mock_fitz.return_value = mock_doc
                        
                        with patch('services.simple_job_processor.GeometryParser'):
                            with patch('services.simple_job_processor.TextParser'):
                                with patch('services.simple_job_processor.cleanup', new_callable=AsyncMock):
                                    with patch('services.simple_job_processor.extract_envelope_data', new_callable=AsyncMock):
                                        with patch('services.job_service.job_service.update_project', new_callable=AsyncMock):
                                            
                                            await run_ai_analysis("test-job", "/fake/path", mock_session)
                                            
                                            # Verify progress sequence
                                            expected_sequence = [65, 70, 75, 80, 85, 90]
                                            actual_sequence = [update[0] for update in progress_updates]
                                            
                                            assert actual_sequence == expected_sequence
                                            
                                            # Verify stage names
                                            expected_stages = [
                                                "ai_analysis", "extracting_geometry", "extracting_text", 
                                                "ai_processing", "envelope_analysis", "storing_analysis"
                                            ]
                                            actual_stages = [update[1] for update in progress_updates]
                                            assert actual_stages == expected_stages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
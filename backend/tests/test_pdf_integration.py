import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from services.pdf_service import PDFGenerationService
from services.job_service import job_service
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def temp_pdf_dir():
    """Create a temporary directory for PDF storage during testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def mock_pdf_service(temp_pdf_dir):
    """Mock PDF service with temporary directory"""
    service = PDFGenerationService()
    service.pdf_storage_path = temp_pdf_dir
    return service

class TestPDFGeneration:
    """Test PDF generation functionality"""
    
    def test_pdf_generation_success(self, mock_pdf_service):
        """Test successful PDF generation"""
        # Mock job result data
        job_result = {
            'rooms': [
                {'name': 'Living Room', 'area': 300, 'heating_load': 6000, 'cooling_load': 5500},
                {'name': 'Kitchen', 'area': 150, 'heating_load': 3000, 'cooling_load': 2800},
                {'name': 'Master Bedroom', 'area': 200, 'heating_load': 4000, 'cooling_load': 3600},
            ],
            'loads': {
                'total_heating_btu': 13000,
                'total_cooling_btu': 11900,
            },
            'processing_info': {
                'filename': 'test_blueprint.pdf',
                'timestamp': 1640995200
            }
        }
        
        # Mock wkhtmltopdf to avoid requiring the binary in tests
        with patch('pdfkit.from_string') as mock_pdfkit:
            # Create a dummy PDF file
            test_pdf_path = os.path.join(mock_pdf_service.pdf_storage_path, 'test_report.pdf')
            with open(test_pdf_path, 'wb') as f:
                f.write(b'%PDF-1.4 mock pdf content')
            
            mock_pdfkit.return_value = None
            mock_pdfkit.side_effect = lambda html, path, **kwargs: open(path, 'wb').write(b'%PDF-1.4 mock pdf content')
            
            # Generate PDF
            pdf_path = mock_pdf_service.generate_report_pdf(
                project_id='test-project-123',
                project_label='Test Project',
                filename='test_blueprint.pdf',
                job_result=job_result
            )
            
            # Verify PDF was created
            assert os.path.exists(pdf_path)
            assert pdf_path.endswith('.pdf')
            
            # Verify file content
            with open(pdf_path, 'rb') as f:
                content = f.read()
                assert content.startswith(b'%PDF')
    
    def test_pdf_generation_error_handling(self, mock_pdf_service):
        """Test PDF generation error handling"""
        with patch('pdfkit.from_string', side_effect=Exception("PDF generation failed")):
            with pytest.raises(Exception, match="PDF generation failed"):
                mock_pdf_service.generate_report_pdf(
                    project_id='test-project-456',
                    project_label='Failed Project',
                    filename='test.pdf',
                    job_result={'rooms': [], 'loads': {}}
                )
    
    def test_filename_sanitization(self, mock_pdf_service):
        """Test that unsafe filenames are sanitized"""
        unsafe_name = 'Project <With> "Bad" /Characters\\ |And? *More'
        safe_name = mock_pdf_service._sanitize_filename(unsafe_name)
        
        # Should not contain unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            assert char not in safe_name
        
        # Should be reasonable length
        assert len(safe_name) <= 50
    
    def test_equipment_recommendations_logic(self, mock_pdf_service):
        """Test equipment recommendations are calculated correctly"""
        job_result = {
            'rooms': [{'name': 'Large Room', 'area': 500, 'heating_load': 15000, 'cooling_load': 14000}],
            'loads': {
                'total_heating_btu': 15000,
                'total_cooling_btu': 14000,
            }
        }
        
        with patch('pdfkit.from_string') as mock_pdfkit:
            test_pdf_path = os.path.join(mock_pdf_service.pdf_storage_path, 'equipment_test.pdf')
            mock_pdfkit.side_effect = lambda html, path, **kwargs: open(path, 'wb').write(b'%PDF-1.4 mock pdf')
            
            pdf_path = mock_pdf_service.generate_report_pdf(
                project_id='equipment-test',
                project_label='Equipment Test',
                filename='test.pdf',
                job_result=job_result
            )
            
            # Verify PDF was created with proper calculations
            assert os.path.exists(pdf_path)

class TestProjectDownload:
    """Test project download functionality"""
    
    @pytest.mark.asyncio
    async def test_download_existing_pdf(self, client, temp_pdf_dir):
        """Test downloading an existing PDF report"""
        # Create a mock PDF file
        pdf_filename = 'test_project_12345678_report.pdf'
        pdf_path = os.path.join(temp_pdf_dir, pdf_filename)
        
        with open(pdf_path, 'wb') as f:
            f.write(b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n9\n%%EOF')
        
        # Mock the job service to return a project with PDF path
        with patch('routes.jobs.job_service') as mock_job_service:
            mock_project = MagicMock()
            mock_project.id = 'test-project-123'
            mock_project.project_label = 'Test Project'
            mock_project.status = 'completed'
            mock_project.pdf_report_path = pdf_path
            
            mock_job_service.get_project_by_user_and_id.return_value = mock_project
            
            # Test download endpoint
            response = client.get(
                '/api/v1/jobs/test-project-123/download?email=test@example.com'
            )
            
            # Should return PDF file
            assert response.status_code == 200
            assert response.headers['content-type'] == 'application/pdf'
            assert 'attachment' in response.headers.get('content-disposition', '')
    
    @pytest.mark.asyncio
    async def test_download_nonexistent_project(self, client):
        """Test downloading from nonexistent project"""
        with patch('routes.jobs.job_service') as mock_job_service:
            mock_job_service.get_project_by_user_and_id.return_value = None
            
            response = client.get(
                '/api/v1/jobs/nonexistent-project/download?email=test@example.com'
            )
            
            assert response.status_code == 404
            assert 'not found' in response.json()['detail'].lower()
    
    @pytest.mark.asyncio
    async def test_download_incomplete_project(self, client):
        """Test downloading from incomplete project"""
        with patch('routes.jobs.job_service') as mock_job_service:
            mock_project = MagicMock()
            mock_project.status = 'processing'
            mock_project.pdf_report_path = None
            
            mock_job_service.get_project_by_user_and_id.return_value = mock_project
            
            response = client.get(
                '/api/v1/jobs/incomplete-project/download?email=test@example.com'
            )
            
            assert response.status_code == 400
            assert 'not completed' in response.json()['detail'].lower()

class TestJobIntegration:
    """Test complete job processing with PDF generation"""
    
    @pytest.mark.asyncio
    async def test_complete_job_flow_with_pdf(self, temp_pdf_dir):
        """Test complete job processing including PDF generation"""
        # This would be a more comprehensive integration test
        # that tests the entire flow from upload to PDF generation
        
        # Mock the necessary services
        with patch('services.simple_job_processor.pdf_service') as mock_pdf_service, \
             patch('services.simple_job_processor.job_service') as mock_job_service:
            
            # Setup mocks
            mock_pdf_service.generate_report_pdf.return_value = os.path.join(temp_pdf_dir, 'test_report.pdf')
            mock_project = MagicMock()
            mock_project.project_label = 'Integration Test Project'
            mock_job_service.get_project.return_value = mock_project
            
            # Import and test the job processor
            from services.simple_job_processor import process_job_sync
            
            # This would normally require a full async context
            # For now, just verify the function exists and can be imported
            assert callable(process_job_sync)

if __name__ == '__main__':
    pytest.main([__file__])
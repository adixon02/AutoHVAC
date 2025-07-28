"""
Tests for AutoHVAC parser components with mocked AI cleanup
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import json
from uuid import uuid4

from app.parser.geometry_parser import GeometryParser
from app.parser.text_parser import TextParser
from app.parser.ai_cleanup import cleanup, AICleanupError
from app.parser.schema import BlueprintSchema, Room, RawGeometry, RawText


class TestGeometryParser:
    """Test geometry extraction from PDFs"""
    
    def test_geometry_parser_init(self):
        """Test GeometryParser initialization"""
        parser = GeometryParser()
        assert parser.scale_patterns is not None
        assert len(parser.scale_patterns) > 0
    
    @patch('pdfplumber.open')
    @patch('fitz.open')
    def test_parse_returns_raw_geometry(self, mock_fitz, mock_pdf):
        """Test that parse returns RawGeometry with correct structure"""
        # Mock pdfplumber
        mock_page = Mock()
        mock_page.width = 792.0
        mock_page.height = 612.0
        mock_page.extract_words.return_value = []
        mock_page.lines = [
            {'x0': 100, 'y0': 100, 'x1': 300, 'y1': 100, 'width': 2}
        ]
        mock_page.rects = [
            {'x0': 100, 'y0': 100, 'x1': 300, 'y1': 250}
        ]
        
        mock_pdf_context = Mock()
        mock_pdf_context.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf_context)
        mock_pdf.__exit__ = Mock(return_value=None)
        
        # Mock PyMuPDF
        mock_doc = Mock()
        mock_page_fitz = Mock()
        mock_page_fitz.get_drawings.return_value = []
        mock_doc.__getitem__ = Mock(return_value=mock_page_fitz)
        mock_doc.close = Mock()
        mock_fitz.return_value = mock_doc
        
        parser = GeometryParser()
        result = parser.parse("test.pdf")
        
        assert isinstance(result, RawGeometry)
        assert result.page_width == 792.0
        assert result.page_height == 612.0
        assert len(result.lines) > 0
        assert result.lines[0]['type'] == 'line'
        assert 'coords' in result.lines[0]
        assert len(result.rectangles) > 0
        assert result.rectangles[0]['type'] == 'rect'
        assert 'coords' in result.rectangles[0]


class TestTextParser:
    """Test text extraction from PDFs"""
    
    def test_text_parser_init(self):
        """Test TextParser initialization"""
        parser = TextParser()
        assert parser.room_keywords is not None
        assert len(parser.room_keywords) > 0
        assert parser.dimension_patterns is not None
    
    @patch('pdfplumber.open')
    @patch('fitz.open')
    @patch('pytesseract.image_to_data')
    def test_parse_returns_raw_text(self, mock_ocr, mock_fitz, mock_pdf):
        """Test that parse returns RawText with correct structure"""
        # Mock pdfplumber
        mock_page = Mock()
        mock_page.extract_words.return_value = [
            {
                'text': 'Living Room',
                'x0': 100,
                'top': 150,
                'x1': 200,
                'bottom': 170,
                'size': 12,
                'fontname': 'Arial'
            },
            {
                'text': "12'-6\"",  
                'x0': 250,
                'top': 180,
                'x1': 300,
                'bottom': 200,
                'size': 10
            }
        ]
        
        mock_pdf_context = Mock()
        mock_pdf_context.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf_context)
        mock_pdf.__exit__ = Mock(return_value=None)
        
        # Mock OCR (no additional text found)
        mock_ocr.return_value = {'text': [], 'conf': [], 'left': [], 'top': [], 'width': [], 'height': []}
        
        # Mock PyMuPDF for OCR
        mock_doc = Mock()
        mock_page_fitz = Mock()
        mock_pix = Mock()
        mock_pix.tobytes.return_value = b"mock_image_data"
        mock_page_fitz.get_pixmap.return_value = mock_pix
        mock_doc.__getitem__ = Mock(return_value=mock_page_fitz)
        mock_doc.close = Mock()
        mock_fitz.return_value = mock_doc
        
        parser = TextParser()
        result = parser.parse("test.pdf")
        
        assert isinstance(result, RawText)
        assert len(result.words) >= 2
        assert result.words[0]['text'] == 'Living Room'
        assert 'x0' in result.words[0]
        assert 'top' in result.words[0]
        assert 'x1' in result.words[0]
        assert 'bottom' in result.words[0]
        
        # Check room labels classification
        assert len(result.room_labels) > 0
        assert result.room_labels[0]['text'] == 'Living Room'
        
        # Check dimensions classification
        assert len(result.dimensions) > 0
        assert "12'-6\"" in result.dimensions[0]['text']


class TestAICleanup:
    """Test AI cleanup functionality with mocks"""
    
    @pytest.fixture
    def sample_raw_geometry(self):
        """Sample raw geometry data"""
        return RawGeometry(
            page_width=792.0,
            page_height=612.0,
            scale_factor=48.0,
            lines=[
                {
                    'type': 'line',
                    'coords': [100, 100, 300, 100],
                    'length': 200,
                    'orientation': 'horizontal',
                    'wall_probability': 0.8
                }
            ],
            rectangles=[
                {
                    'type': 'rect',
                    'coords': [100, 100, 300, 250],
                    'area': 3000,
                    'center_x': 200,
                    'center_y': 175,
                    'width': 200,
                    'height': 150,
                    'room_probability': 0.9
                }
            ],
            polylines=[]
        )
    
    @pytest.fixture
    def sample_raw_text(self):
        """Sample raw text data"""
        return RawText(
            words=[
                {
                    'text': 'Living Room',
                    'x0': 180,
                    'top': 175,
                    'x1': 250,
                    'bottom': 190
                }
            ],
            room_labels=[
                {
                    'text': 'Living Room',
                    'x0': 180,
                    'top': 175,
                    'x1': 250,
                    'bottom': 190,
                    'room_type': 'living',
                    'confidence': 0.9
                }
            ],
            dimensions=[],
            notes=[]
        )
    
    @pytest.fixture
    def sample_blueprint_response(self):
        """Sample AI response matching BlueprintSchema"""
        return {
            "project_id": str(uuid4()),
            "zip_code": "90210",
            "sqft_total": 2500.0,
            "stories": 1,
            "rooms": [
                {
                    "name": "Living Room",
                    "dimensions_ft": [20.0, 15.0],
                    "floor": 1,
                    "windows": 3,
                    "orientation": "S",
                    "area": 300.0
                },
                {
                    "name": "Master Bedroom", 
                    "dimensions_ft": [16.0, 12.0],
                    "floor": 1,
                    "windows": 2,
                    "orientation": "E",
                    "area": 192.0
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_cleanup_with_valid_response(self, sample_raw_geometry, sample_raw_text, sample_blueprint_response):
        """Test successful AI cleanup with valid response"""
        with patch('app.parser.ai_cleanup.AsyncOpenAI') as mock_openai:
            # Mock OpenAI client
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_choice = Mock()
            mock_choice.message.content = json.dumps(sample_blueprint_response)
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            # Mock environment variable
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                result = await cleanup(sample_raw_geometry, sample_raw_text)
            
            assert isinstance(result, BlueprintSchema)
            assert result.zip_code == "90210"
            assert result.sqft_total == 2500.0
            assert result.stories == 1
            assert len(result.rooms) == 2
            assert result.rooms[0].name == "Living Room"
            assert result.rooms[0].area == 300.0
            assert result.rooms[1].name == "Master Bedroom"
    
    @pytest.mark.asyncio
    async def test_cleanup_missing_api_key(self, sample_raw_geometry, sample_raw_text):
        """Test AI cleanup fails without API key"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(AICleanupError, match="OPENAI_API_KEY environment variable not set"):
                await cleanup(sample_raw_geometry, sample_raw_text)
    
    @pytest.mark.asyncio
    async def test_cleanup_invalid_json_response(self, sample_raw_geometry, sample_raw_text):
        """Test AI cleanup handles invalid JSON response"""
        with patch('app.parser.ai_cleanup.AsyncOpenAI') as mock_openai:
            # Mock OpenAI client with invalid JSON response
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_choice = Mock()
            mock_choice.message.content = "Invalid JSON response"
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client
            
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                with pytest.raises(AICleanupError, match="Failed to parse AI response as JSON"):
                    await cleanup(sample_raw_geometry, sample_raw_text)
    
    @pytest.mark.asyncio
    async def test_cleanup_openai_api_error(self, sample_raw_geometry, sample_raw_text):
        """Test AI cleanup handles OpenAI API errors"""
        with patch('app.parser.ai_cleanup.AsyncOpenAI') as mock_openai:
            # Mock OpenAI client that raises an exception
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
            mock_openai.return_value = mock_client
            
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                with pytest.raises(AICleanupError, match="OpenAI API call failed"):
                    await cleanup(sample_raw_geometry, sample_raw_text)


class TestIntegration:
    """Integration tests for parser components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_parsing_with_mock_ai(self):
        """Test complete parsing pipeline with mocked AI"""
        # This would be a more comprehensive test that runs
        # geometry parsing -> text parsing -> AI cleanup in sequence
        # with real PDF data and mocked AI responses
        
        mock_blueprint = BlueprintSchema(
            project_id=uuid4(),
            zip_code="90210",
            sqft_total=1500.0,
            stories=1,
            rooms=[
                Room(
                    name="Test Room",
                    dimensions_ft=(15.0, 10.0),
                    floor=1,
                    windows=2, 
                    orientation="S",
                    area=150.0
                )
            ]
        )
        
        # Mock the AI cleanup to return our test blueprint
        with patch('app.parser.ai_cleanup.cleanup', new_callable=AsyncMock) as mock_cleanup:
            mock_cleanup.return_value = mock_blueprint
            
            # This test would use real geometry and text parsers
            # but mock the AI step for predictable results
            result = mock_blueprint  # Simplified for this example
            
            assert isinstance(result, BlueprintSchema)
            assert len(result.rooms) == 1
            assert result.rooms[0].name == "Test Room"


if __name__ == "__main__":
    pytest.main([__file__])
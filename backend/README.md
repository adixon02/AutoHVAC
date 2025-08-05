# AutoHVAC Backend

## Quick Start

### Prerequisites
- Python 3.8+
- Redis (optional, for background job processing)
- OpenAI API key (required for AI blueprint parsing)
- Pillow (included in requirements.txt)
- PaddleOCR (optional, for enhanced text extraction)

### Setup & Run

1. **Install dependencies:**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```
   
   **Important Production Settings:**
   ```bash
   # For production deployments, set these for optimal accuracy:
   PARSING_MODE=traditional_first  # Use geometry/text extraction first, AI for enhancement
   MIN_CONFIDENCE_THRESHOLD=0.5    # Lower threshold for validation gates
   SCALE_OVERRIDE=48               # Force 1/4"=1' scale if known (48 px/ft)
   ```

3. **Run the server:**
   
   Option A - Using the shell script:
   ```bash
   ./run_dev.sh
   ```
   
   Option B - Using Python directly:
   ```bash
   python run_server.py
   ```
   
   Option C - Using uvicorn directly:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Verify it's running:**
   - Server: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/healthz

## AI-First Blueprint Processing

AutoHVAC uses GPT-4 Vision (GPT-4V) as the primary method for parsing blueprints:

- **No complexity limits**: Handles blueprints with 40k+ vector elements
- **Automatic compression**: Smart image optimization for GPT-4V API limits
- **Graceful fallback**: Uses traditional parsing if AI is unavailable

### Configuration

```bash
# Enable/disable AI parsing (default: true)
AI_PARSING_ENABLED=true

# Element limit for legacy parser only (default: 20000)
LEGACY_ELEMENT_LIMIT=20000

# File size warning threshold in MB (default: 20)
FILE_SIZE_WARNING_MB=20
```

## API Endpoints

- `POST /api/v1/blueprint/upload` - Upload blueprint for processing (up to 50MB)
- `GET /api/v1/job/{job_id}` - Get job status
- `GET /healthz` - Health check endpoint

## Testing

### Test AI-First Configuration
```bash
python3 test_ai_first_config.py
```

### Test PDF Validation
```bash
# Test with a complex blueprint
python3 test_pdf_validation.py tests/sample_blueprints/blueprint-example-99206.pdf
```

### Test Upload Scenarios
```bash
python3 test_upload_simulation.py
```

## Troubleshooting

### ImportError: No module named 'app'
Make sure you're running from the backend directory:
```bash
cd /Users/austindixon/Documents/AutoHVAC/backend
```

### Connection refused on port 8000
Check if another process is using port 8000:
```bash
lsof -i :8000
```

### Redis connection error
The app works without Redis but won't process jobs asynchronously. To use Redis:
```bash
brew install redis
brew services start redis
```

### Complex blueprint validation errors
If you see "Blueprint is too complex to process":
1. Ensure `AI_PARSING_ENABLED=true` (default)
2. Check that `OPENAI_API_KEY` is set
3. AI parsing handles complex blueprints without element limits

### Large file uploads
Files between 20-50MB will show a warning but are allowed:
- "Large blueprint detected. AI processing may take 2-3 minutes."
- Maximum file size: 50MB

### PaddleOCR Installation (Optional but Recommended)
For enhanced text extraction from blueprints:
```bash
# Install PaddleOCR for better OCR accuracy
pip install paddlepaddle paddleocr

# Note: On macOS with Apple Silicon (M1/M2), you may need:
pip install paddlepaddle==2.5.1 -i https://mirror.baidu.com/pypi/simple

# Verify installation:
python -c "from paddleocr import PaddleOCR; print('PaddleOCR installed successfully')"
```

If PaddleOCR is not available, the system will fall back to basic text extraction.
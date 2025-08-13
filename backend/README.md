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

## System Architecture & Call Chain

### Software Logic Map

This section documents the complete call chain and data flow through the AutoHVAC system.

#### Entry Point: Worker Startup
`/Users/austindixon/Documents/AutoHVAC/backend/start_worker.sh`
- Changes to Render project directory: `/opt/render/project/src/backend`
- Launches Celery worker with `tasks.calculate_hvac_loads` module
- Worker configuration:
  - Concurrency: 2 workers
  - Memory limit: 1.5GB per child
  - Max tasks per child: 50
  - Time limits: 30 minutes hard, 29 minutes soft
  - Optimizations: No gossip, mingle, or heartbeat (production settings)

#### Main Processing Pipeline

##### 1. Celery Task Orchestration
**File:** `tasks/calculate_hvac_loads.py::calculate_hvac_loads()`
- Celery app configuration: Redis broker/backend from `REDIS_URL` env var
- Task safeguards: `acks_late=True`, `reject_on_worker_lost=True`
- Resource limits: 50MB PDF max, 100 pages max, 10-minute total timeout

**Call sequence:**

1. **S3 Storage** (`services/s3_storage.py`)
   - Check file existence in S3 bucket
   - Download PDF from S3 to temp file via `download_to_temp_file()`
   - Store results back to S3: `jobs/{project_id}/` structure
   
2. **Climate Data** (`services/climate_data.py`)
   - Fetch ASHRAE climate data for zip code

3. **Blueprint Parser** (`services/blueprint_parser.py::parse_blueprint_to_json()`)
   - Main entry point for PDF to JSON conversion
   - Returns `BlueprintSchema` object with rooms, metadata, and validation
   - **PDF Analysis** (`services/pdf_page_analyzer.py`)
     - Analyze all pages, score them, select best floor plan
   
   - **Geometry-First Processing** (NEW):
     - **Vector Extraction** (`services/vector_extractor.py`)
       - Extract vector paths, text, dimensions directly from PDF
       - No OCR needed for vector content
     - **RANSAC Scale Detection** (`services/scale_detector.py`)
       - Edge-dimension pairing with RANSAC algorithm
       - 95% confidence threshold for Gate A validation
       - KD-tree clustering for robust scale detection
     - **North Arrow Detection** (`services/north_arrow_detector.py`)
       - Detect orientation from vector glyphs and text
       - Apply rotation corrections
   
   - **AI Classification Path** (`services/blueprint_ai_parser.py`)
     - Convert PDF → Images (`pdf2image`)
     - **GPT-4o Vision** (`services/gpt4v_blueprint_analyzer.py`)
       - Single attempt, 60s timeout (no retries)
       - Classification only via `services/gpt_classifier.py`
       - Tight schema, no numerical extraction
   
   - **Validation Gates** (`services/validation_gates.py`)
     - Gate A: Scale detection (95% confidence required) - STOPS PROCESSING if fails
     - Gate B: Pre-Manual-J validation - STOPS PROCESSING if fails
     - Gates now raise NeedsInputError when validation fails
   
   - **Room Processing**:
     - **Geometry Extraction** (`services/geometry_extractor.py`)
       - Deterministic room polygon extraction
     - **Room Graph Validation** (`services/room_graph_validator.py`)
       - Validate polygons with Shapely
       - Build adjacency graph with NetworkX
       - Check overlaps, gaps, connectivity
   
   - **Fallback Paths** (DISABLED - raises error instead):
     - ~~Text Parser (`services/text_parser.py`)~~ - Disabled
     - ~~OCR Extractor (`services/ocr_extractor.py`)~~ - Disabled
     - System now raises NeedsInputError instead of creating estimated rooms

4. **Envelope Extraction** (`services/envelope_extractor.py`)
   - Extract R-values, insulation data
   - Uses GPT-4 text model (not vision)

5. **Manual J Calculations** (`services/manualj.py::calculate_manualj_with_audit()`)
   - **Pre-Processing**:
     - Filter unconditioned spaces BEFORE calculations
     - Correct floor assembly assignment (slab losses on floor 1 ONLY)
     - Multi-story support: Properly counts unique floor numbers
   
   - **Orientation Priority** (in order):
     1. User-provided from upload modal (highest confidence 0.95)
     2. Detected north arrow from blueprint (if available)
     3. Climate-based smart default (when user selects "Not sure")
   
   - **Load Calculators:**
     - `services/cltd_clf.py` - Cooling Load Temperature Difference
     - `services/infiltration.py` - Air infiltration loads
     - `services/multi_story_calculator.py` - Multi-floor aggregation
     - `services/thermal_mass.py` - Thermal mass calculations
   
   - **Equipment Sizing** - Generate HVAC recommendations

6. **Audit & Storage**
   - `services/artifact_manager.py` - Versioned artifact saving (NEW)
   - `services/audit_tracker.py` - Create audit trail
   - `services/job_service.py` - Update database status via `sync_update_project()`
   - Progress tracking: Real-time updates via `update_progress_sync()`
   - Save results to S3 (`analysis.json`, `hvac_results.json`, `metadata.json`)

7. **Notifications**
   - `core/email.py` - Send completion email

#### Key Service Dependencies

**Database Layer:**
- `database.py` - PostgreSQL sessions
- `models/` - SQLAlchemy models

**Validation & Quality:**
- `services/blueprint_validator.py` - Data validation
- `services/data_quality_validator.py` - Quality scoring
- `services/confidence_scorer.py` - Confidence assessment
- `services/validation_gates.py` - Two-gate validation system
- `services/room_graph_validator.py` - Room polygon and adjacency validation

**Error Handling:**
- `services/error_types.py` - Error categorization
- `app/parser/exceptions.py` - Custom exceptions

**Geometry Processing:**
- `services/vector_extractor.py` - Direct PDF vector/text extraction
- `services/scale_detector.py` - RANSAC-based scale detection (passes to Manual J)
- `services/north_arrow_detector.py` - Orientation detection (passes to Manual J)
- `services/geometry_extractor.py` - Room polygon extraction
- `services/pipeline_context.py` - Maintains scale/orientation across pipeline

**Utilities:**
- `services/pdf_thread_manager.py` - Thread-safe PDF operations
- `utils/json_utils.py` - JSON serialization helpers
- `services/artifact_manager.py` - Versioned artifact saving for debugging

#### Data Flow
```
PDF Upload → FastAPI Router → S3 Storage → Celery Task Queue
    ↓
Vector Extraction → RANSAC Scale Detection → Validation Gate A (MUST PASS)
    ↓                                              ↓ (fails)
    ↓                                          NeedsInputError
Geometry Processing → Room Graph Validation → GPT-4o Classification (optional)
    ↓                                              ↓ (fails)
    ↓                                          NeedsInputError (no fallback)
BlueprintSchema JSON → Validation Gate B (MUST PASS) → Manual J Calculations
    ↓                        ↓ (fails)                    ↓
    ↓                    NeedsInputError         (includes scale & orientation)
HVAC Load Results → Database + S3 + Artifacts
    ↓
Email Notification → User Report
```

#### AI Service Usage
- **GPT-4o Vision** (gpt-4o-2024-11-20): Classification only, single attempt with 60s timeout
- **GPT-4/GPT-4-mini**: Text analysis only (envelope data extraction)
- **Vector Extraction**: Direct PDF vector/text extraction (primary method)
- **OCR Fallback**: PaddleOCR or Tesseract for rasterized content only

#### Processing Stages & Progress Tracking
1. **Initialization**: 5% progress - File validation, S3 check
2. **Blueprint Parsing**: 20-50% progress 
   - PDF to JSON conversion (AI timeout: 300s)
   - Stored as `parsed_schema_json` in database
3. **Envelope Analysis**: 65% progress (optional, non-critical)
4. **HVAC Calculations**: 80% progress
5. **Result Compilation**: 95% progress
6. **Completion**: 100% progress

Total processing timeout: 600 seconds (10 minutes)
Worker time limits: 1800s hard, 1740s soft (30/29 minutes)

#### Critical Performance Requirements
- Blueprint processing: <30 seconds target
- Multi-story processing: Must handle ALL floors
- Target accuracy: 74,000 BTU/hr for 2-story test home
- Max PDF size: 50MB
- Max PDF pages: 100

#### File Storage Structure (S3)
```
jobs/{project_id}/
├── blueprint.pdf         # Original uploaded file
├── analysis.json        # Blueprint parsing results
├── hvac_results.json    # Manual J calculation results
└── metadata.json        # Processing metadata and audit
```
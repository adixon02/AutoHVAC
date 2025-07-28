# AutoHVAC

Elite PDF-to-HVAC engine that transforms architectural blueprints into complete HVAC designs with AI-powered analysis and ACCA Manual J load calculations.

## Project Structure

```
AutoHVAC/
├── frontend/                          # Next.js SaaS Frontend
│   ├── components/                    # React components
│   │   ├── Hero.tsx                   # Landing page hero section
│   │   ├── FeatureSteps.tsx           # 4-step process walkthrough
│   │   ├── Testimonials.tsx           # Customer testimonial slider
│   │   ├── MultiStepUpload.tsx        # Multi-step upload with progress tracking
│   │   ├── AssumptionModal.tsx        # Building envelope assumptions collection
│   │   ├── NavBar.tsx                 # Navigation bar component
│   │   ├── ProjectCard.tsx            # Project display card
│   │   └── UploadModal.tsx.old        # Legacy upload modal (reference)
│   ├── pages/                         # Next.js pages
│   │   ├── _app.tsx                   # App wrapper with global styles
│   │   ├── index.tsx                  # Main landing page
│   │   ├── dashboard.tsx              # User dashboard
│   │   ├── analyzing/                 # Processing status pages
│   │   │   └── [jobId].tsx            # Job analysis progress
│   │   ├── api/                       # API proxy routes
│   │   │   ├── job/[jobId].ts         # Job status polling
│   │   │   └── jobs/[jobId]/          # Extended job API endpoints
│   │   │       └── assumptions.ts     # User assumption collection endpoint
│   │   └── payment/                   # Stripe payment pages
│   │       ├── success.tsx            # Payment success
│   │       └── cancel.tsx             # Payment cancelled
│   ├── constants/                     # Frontend constants
│   │   └── api.ts                     # API configuration and endpoints
│   ├── lib/                           # Utility libraries
│   │   └── fetcher.ts                 # API client with error handling
│   ├── types/                         # TypeScript type definitions
│   │   └── api.ts                     # Shared API type definitions
│   ├── styles/
│   │   └── globals.css                # Tailwind + custom styles
│   ├── package.json                   # Dependencies + scripts
│   ├── tailwind.config.js             # Tailwind configuration
│   ├── tsconfig.json                  # TypeScript configuration
│   ├── next.config.js                 # Next.js configuration
│   ├── postcss.config.js              # PostCSS configuration
│   ├── .env.local                     # Frontend environment variables
│   └── Dockerfile.dev                 # Development Docker image
│
├── backend/                           # FastAPI Backend
│   ├── app/                           # Main application
│   │   ├── main.py                    # FastAPI app with CORS + routes
│   │   ├── config.py                  # Application configuration
│   │   ├── middleware/                # Custom middleware
│   │   │   ├── __init__.py
│   │   │   └── error_handler.py       # Global error handling
│   │   └── parser/                    # Elite PDF parsing engine
│   │       ├── __init__.py            # Parser module exports
│   │       ├── geometry_parser.py     # pdfplumber + PyMuPDF geometry extraction
│   │       ├── text_parser.py         # OCR + text extraction with Tesseract
│   │       ├── ai_cleanup.py          # OpenAI GPT-4 data structuring
│   │       └── schema.py              # Pydantic models (Room, BlueprintSchema)
│   ├── routes/                        # API endpoints
│   │   ├── __init__.py
│   │   ├── blueprint.py               # Blueprint upload + job management
│   │   ├── job.py                     # Job status polling
│   │   ├── jobs.py                    # Job listing and management
│   │   ├── auth.py                    # Authentication endpoints
│   │   └── billing.py                 # Stripe subscription + webhooks
│   ├── services/                      # Business logic services
│   │   ├── __init__.py
│   │   ├── manualj.py                 # ACCA Manual J load calculations
│   │   ├── job_service.py             # Job management service
│   │   ├── user_service.py            # User management with email verification
│   │   ├── rate_limiter.py            # Rate limiting service
│   │   ├── pdf_service.py             # PDF generation service
│   │   ├── simple_job_processor.py    # Simplified job processing for development
│   │   ├── audit_tracker.py           # Comprehensive audit logging system
│   │   ├── climate_data.py            # ASHRAE climate zone and temperature data
│   │   ├── envelope_extractor.py      # Building envelope analysis
│   │   ├── cltd_clf.py               # Cooling Load Temperature Difference calculations
│   │   ├── store.py                   # Data storage service
│   │   └── user_store.py              # User data management
│   ├── data/                          # Climate and regional data
│   │   ├── ashrae_design_temps.csv    # ASHRAE design temperature database
│   │   ├── county_climate_zones.csv   # County-based climate zone mapping
│   │   └── zip_county_mapping.csv     # ZIP code to county relationships
│   ├── scripts/                       # Development and utility scripts
│   │   ├── test_pipeline.py           # Complete pipeline testing script
│   │   └── local_server.py            # Standalone local development server
│   ├── tasks/                         # Celery background tasks
│   │   ├── __init__.py
│   │   └── parse_blueprint.py         # 5-stage processing orchestration
│   ├── models/                        # Data models
│   │   ├── __init__.py
│   │   ├── db_models.py               # SQLModel database models
│   │   ├── schemas.py                 # API request/response schemas
│   │   └── enums.py                   # System enumerations and constants
│   ├── core/                          # Core configuration
│   │   ├── __init__.py
│   │   ├── email.py                   # Email service integration
│   │   └── stripe_config.py           # Stripe API configuration
│   ├── tests/                         # Comprehensive test suite
│   │   ├── __init__.py
│   │   ├── sample_blueprints/         # Test PDF files
│   │   │   └── blueprint-example-99206.pdf
│   │   ├── test_parser.py             # Parser tests with mocked AI
│   │   ├── test_manualj.py            # Manual J calculation tests
│   │   ├── test_integration.py        # Full pipeline integration tests
│   │   ├── test_pdf_integration.py    # PDF service tests
│   │   ├── test_acca_examples.py      # ACCA Manual J validation tests
│   │   ├── test_cors.py               # CORS configuration tests
│   │   ├── test_job_status.py         # Job status polling tests
│   │   ├── test_manualj_duct_config.py # Duct sizing configuration tests
│   │   └── legacy/                    # Legacy test files
│   │       └── test_manualj_legacy.py # Previous Manual J implementation tests
│   ├── html_templates/                # HTML templates for PDF generation
│   │   └── report.html                # HVAC report template
│   ├── alembic/                       # Database migrations
│   │   ├── versions/                  # Migration files
│   │   ├── env.py                     # Alembic environment
│   │   └── script.py.mako             # Migration template
│   ├── database.py                    # Database connection and session management
│   ├── requirements.txt               # Python dependencies (optimized)
│   ├── alembic.ini                    # Alembic configuration
│   ├── Dockerfile.dev                 # Development Docker image
│   ├── run_dev.sh                     # Development server startup script
│   ├── run_server.py                  # Production server entry point
│   └── start_backend.sh               # Backend startup script
│
├── .github/workflows/                 # CI/CD Pipeline
│   └── ci.yaml                        # GitHub Actions workflow
│       ├── frontend-test              # Node.js linting + type check + build
│       ├── backend-test               # Python linting + type check + pytest
│       └── api-smoke-test             # Live API endpoint testing
│
├── docker-compose.yml                 # Local Development Stack
│   ├── frontend                       # Next.js dev server
│   ├── backend                        # FastAPI with hot reload
│   ├── worker                         # Celery worker
│   ├── redis                          # Task queue + caching
│   ├── postgres                       # Database
│   └── minio                          # S3-compatible file storage
│
├── render.yaml                        # Production Deployment
│   ├── autohvac-frontend              # Next.js web service
│   ├── autohvac-backend               # FastAPI web service
│   ├── autohvac-worker                # Celery worker service
│   ├── autohvac-redis                 # Redis service
│   └── autohvac-postgres              # PostgreSQL database
│
├── README.md                          # This file
├── .env                              # Environment variables (not committed)
├── .gitignore                        # Enhanced Git ignore rules (prevents logs, builds, dev files)
├── design-brief.md                   # Project design brief
├── docker-compose.override.yml       # Local development overrides
└── pipeline_output_*.json            # Sample pipeline output files
```

### Key File Descriptions

#### **Core Parser Engine (`backend/app/parser/`)**
- **`geometry_parser.py`**: Advanced PDF geometry extraction using pdfplumber for basic shapes and PyMuPDF for complex paths, scale detection, and wall probability scoring
  - Returns standardized format: `List[{"type": "line"|"rect", "coords": [...]}]`
  - Includes orientation detection, wall classification, and parallel line grouping
- **`text_parser.py`**: Multi-layer text extraction with pdfplumber for clean text and Tesseract OCR for handwritten labels, with confidence scoring
  - Returns: `List[{"text": str, "x0": float, "top": float, "x1": float, "bottom": float}]`
  - Classifies text into room labels, dimensions, and notes
- **`ai_cleanup.py`**: OpenAI GPT-4 integration with expert HVAC system prompts to convert raw extraction data into structured room schemas
  - Async function: `cleanup(raw_geo, raw_text) -> BlueprintSchema`
  - Uses GPT-4 with structured JSON response format
- **`schema.py`**: Pydantic data models defining Room and BlueprintSchema with validation and type safety
  - `Room`: name, dimensions_ft, floor, windows, orientation, area
  - `BlueprintSchema`: project_id, zip_code, sqft_total, stories, rooms

#### **HVAC Analysis (`backend/services/manualj.py`)**
- Complete ACCA Manual J load calculation implementation
- Climate zone factors, room type multipliers, orientation adjustments
- Equipment sizing recommendations with cost estimates and duct sizing

#### **Task Orchestration (`backend/tasks/parse_blueprint.py`)**
- 5-stage processing pipeline: geometry → text → AI cleanup → Manual J → finalization
- Progress tracking, comprehensive error handling, async OpenAI integration
- Temporary file management and result compilation
- Stages: `extracting_geometry` (20%) → `extracting_text` (40%) → `ai_processing` (60%) → `calculating_loads` (80%) → `complete` (100%)

#### **Development Services (`backend/services/`)**
- **`simple_job_processor.py`**: Simplified development job processor
  - In-memory job processing without Celery/Redis
  - Mock HVAC analysis results for testing
  - Threaded background processing for development
  - Progress tracking: 1% → 5% → 25% → 60% → 90% → 100%

#### **Test Suite (`backend/tests/`)**
- **`test_parser.py`**: Comprehensive parser component tests
  - GeometryParser tests with mocked PDF operations
  - TextParser tests with OCR fallback verification
  - AI cleanup tests with mocked OpenAI responses
- **`test_manualj.py`**: Manual J calculation validation
  - Room classification tests
  - Climate zone calculations
  - Equipment sizing recommendations
  - Realistic BTU/sqft range validation
- **`test_integration.py`**: Full pipeline integration tests
  - End-to-end processing with mocked AI
  - Job lifecycle and progress tracking
  - Error handling scenarios
  - Performance and data integrity checks
- **`sample_blueprints/`**: Test PDF files for development and testing
  - Sample blueprint PDFs for pipeline validation

#### **Modern SaaS Frontend (`frontend/`)**
- **`components/Hero.tsx`**: Benefit-focused landing with interactive mockup
- **`components/FeatureSteps.tsx`**: 4-step process walkthrough with animations
- **`components/Testimonials.tsx`**: Customer testimonial slider with social proof
- **`components/MultiStepUpload.tsx`**: Enhanced multi-step upload process with progress tracking and assumption collection
- **`components/AssumptionModal.tsx`**: Interactive modal for collecting building envelope assumptions (insulation, windows, construction materials)
- **`components/UploadModal.tsx.old`**: Legacy upload modal retained for reference during transition
- **`constants/api.ts`**: Centralized API configuration and endpoint definitions
  - Environment-based API URL configuration
  - Request timeout settings and smoke test endpoints
- **`types/api.ts`**: Shared TypeScript type definitions for API communication
  - Request/response interfaces for upload and job status
  - Payment and health check response types
  - Building envelope assumption data structures

#### **Development Tools (`backend/scripts/`)**
- **`local_server.py`**: Standalone local development server
  - Runs AutoHVAC backend without Docker, Redis, or PostgreSQL
  - In-memory job storage for testing and development
  - Complete PDF processing pipeline with AI fallback
  - Simplified deployment for local testing
- **`test_pipeline.py`**: Complete pipeline testing and validation script
  - End-to-end testing from PDF upload to Manual J calculations
  - Comprehensive output with parsing metadata and data gap analysis
  - Fallback parsing when OpenAI API is unavailable
  - Enhanced room data with building envelope assumptions

#### **Infrastructure**
- **`docker-compose.yml`**: Complete local development stack with all services
- **`render.yaml`**: Production deployment configuration with auto-scaling
- **`.github/workflows/ci.yaml`**: Comprehensive CI/CD with linting, testing, and deployment

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker & Docker Compose
- OpenAI API key
- Stripe account (for billing)

### Environment Variables

Create `.env` file in project root:

```bash
# OpenAI (Required)
OPENAI_API_KEY=sk-...

# Stripe (Required for billing)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...

# Optional (for production)
DATABASE_URL=postgresql://user:pass@host:5432/db
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### Local Development

#### Option 1: Full Docker Stack (Recommended)

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd AutoHVAC
   ```

2. **Start all services**
   ```bash
   docker-compose up --build
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - MinIO Console: http://localhost:9001

## Running Background Workers

### Development (Simple Processor)
The development setup uses threaded background processing:
- Jobs process in background threads without Redis/Celery
- Progress tracking from 1% to 100% with detailed stages
- Check logs for thread lifecycle: "🧵 THREAD: Started", "🚀 THREAD: Job processor started"
- Temporary files streamed to `/tmp/` for memory efficiency with large PDFs

### Production (Celery)
For production with high concurrency and reliability:
```bash
# Start Celery worker with optimal settings
celery -A tasks.parse_blueprint worker --loglevel=info --concurrency=4 -Ofair
```
- `--concurrency=4`: Process 4 jobs in parallel
- `-Ofair`: Distribute tasks fairly among workers
- Requires Redis for task queue and result backend

#### Option 2: Lightweight Local Server (No Docker Required)

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd AutoHVAC
   ```

2. **Start the local development server**
   ```bash
   # Terminal 1: Start local backend server
   python backend/scripts/local_server.py
   
   # Terminal 2: Start frontend
   cd frontend
   npm install && npm run dev
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Manual Setup (Alternative)

#### Backend Services
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Backend API
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 3: Celery Worker
cd backend
celery -A tasks.parse_blueprint worker --loglevel=info

# Terminal 4: Frontend
cd frontend
npm install && npm run dev
```

## Elite PDF Processing Pipeline

### 1. Geometry Extraction
- **pdfplumber**: Extracts lines, rectangles, page dimensions
- **PyMuPDF (fitz)**: Advanced path analysis, curves, scale detection
- **Output**: Raw geometry with wall/room probability scoring

### 2. Text Extraction
- **pdfplumber**: Clean text extraction with positioning
- **Tesseract OCR**: Fallback for handwritten/unclear text
- **Output**: Room labels, dimensions, notes with confidence scores

### 3. AI-Powered Cleanup
- **OpenAI GPT-4**: Converts raw data into structured rooms
- **System Prompt**: Expert HVAC design AI with architectural knowledge
- **Function**: `async cleanup(raw_geo, raw_text) -> BlueprintSchema`
- **Output**: Validated `BlueprintSchema` with room properties

### 4. ACCA Manual J Calculations
- **Climate Zones**: Location-based heating/cooling factors
- **Room Types**: Kitchen, bedroom, bathroom-specific multipliers
- **Orientation**: Solar gain adjustments (N/S/E/W)
- **Windows**: Heat gain/loss calculations
- **Equipment Sizing**: Ton recommendations with cost estimates
- **Function**: `calculate_manualj(schema: BlueprintSchema) -> Dict`

## API Endpoints

### Blueprint Processing
- `POST /api/v1/blueprint/upload` - Upload PDF blueprint
  - Requires: `email` (string), `file` (PDF)
  - Returns: `{job_id, status}`
  - Billing: First job free, subsequent jobs require subscription

- `GET /api/v1/job/{job_id}` - Get processing status
  - Returns: `{status, stage, progress, result?, error?}`
  - Stages: `extracting_geometry` → `extracting_text` → `ai_processing` → `calculating_loads` → `complete`

### Billing (Stripe Integration)
- `POST /api/v1/subscribe` - Create subscription checkout
- `POST /api/v1/webhook` - Stripe webhook handler

### System
- `GET /health` - Health check
- `GET /` - API status

## Response Format

### Successful Processing Result
```json
{
  "job_id": "uuid",
  "filename": "blueprint.pdf",
  "processed_at": 1703123456.789,
  "blueprint": {
    "project_id": "uuid",
    "zip_code": "90210",
    "sqft_total": 2500.0,
    "stories": 2,
    "rooms": [
      {
        "name": "Living Room",
        "dimensions_ft": [20.0, 15.0],
        "floor": 1,
        "windows": 3,
        "orientation": "S",
        "area": 300.0
      }
    ]
  },
  "hvac_analysis": {
    "heating_total": 45000,
    "cooling_total": 36000,
    "climate_zone": "3A",
    "zones": [
      {
        "name": "Living Room",
        "heating_btu": 8500,
        "cooling_btu": 7200,
        "cfm_required": 240,
        "duct_size": "8 inch"
      }
    ],
    "equipment_recommendations": {
      "system_type": "Heat Pump",
      "recommended_size_tons": 3.0,
      "size_options": [...],
      "estimated_install_time": "2-3 days"
    }
  }
}
```

## Testing the Pipeline

### Complete Pipeline Test

Test the entire parsing pipeline from PDF to Manual J calculations:

```bash
# Run the complete pipeline test
python backend/scripts/test_pipeline.py

# Output includes:
# - Geometry extraction summary
# - Text parsing results
# - AI cleanup with fallback
# - Manual J load calculations
# - Enhanced output with metadata
```

The pipeline test will:
1. Parse a sample blueprint PDF
2. Extract geometry and text data
3. Use AI cleanup (with fallback if OpenAI unavailable)
4. Calculate HVAC loads using Manual J
5. Generate comprehensive results with data gap analysis

## Development Workflow

### Testing
```bash
# Frontend
cd frontend
npm run lint && npm run type-check && npm run build

# Backend
cd backend
black --check . && isort --check-only . && flake8 . && mypy . && pytest

# Run specific test suites
pytest tests/test_parser.py -v      # Parser component tests
pytest tests/test_manualj.py -v     # Manual J calculation tests  
pytest tests/test_integration.py -v # Full pipeline tests

# Run with coverage
pytest --cov=app --cov=services --cov=tasks tests/
```

### CI/CD Pipeline
- **Linting**: Black, isort, flake8, ESLint
- **Type Checking**: mypy, TypeScript
- **Testing**: pytest, API smoke tests
- **Deployment**: Automatic on merge to main

## Production Deployment

### Render (Recommended)
1. Connect GitHub repository to Render
2. Render auto-detects `render.yaml` configuration
3. Set environment variables in Render dashboard
4. Deploy automatically triggers on push to main

**Important**: Render must stay on CPython ≤3.12 until all binary deps ship cp313 wheels.

### Required Environment Variables (Production)
```bash
OPENAI_API_KEY=sk-...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...
```

## Architecture

### Technology Stack
- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS
- **Backend**: FastAPI + Pydantic + Celery
- **AI**: OpenAI GPT-4 Turbo
- **PDF Processing**: pdfplumber + PyMuPDF + Tesseract OCR
- **Queue**: Redis
- **Database**: PostgreSQL
- **Storage**: MinIO (S3-compatible)
- **Deployment**: Render
- **Billing**: Stripe

### Data Flow
1. User uploads PDF blueprint via modern SaaS frontend
2. FastAPI validates file and user billing status
3. Celery worker processes PDF through 4-stage pipeline
4. Results stored in job store with real-time status updates
5. Frontend polls for completion and displays comprehensive HVAC analysis

### Key Features
- **Elite Parsing**: Advanced geometry + text extraction with AI cleanup
- **Professional UI**: Modern SaaS design targeting HVAC contractors
- **Interactive User Experience**: Multi-step upload with building envelope assumption collection
- **Advanced HVAC Analysis**: Comprehensive ACCA Manual J implementation with climate zone precision
- **Comprehensive Climate Data**: ASHRAE design temperatures and county-based climate mapping
- **Professional Reporting**: PDF generation with detailed HVAC analysis and recommendations
- **Billing Integration**: Stripe subscription with "first job free"
- **Real-time Status**: Progress tracking through processing stages
- **Production Ready**: Docker, CI/CD, monitoring, error handling, audit logging
- **HVAC Expertise**: ACCA Manual J compliance with equipment recommendations
- **Optimized Codebase**: Cleaned dependencies, organized structure, comprehensive .gitignore

## Recent Updates

### Enhanced HVAC Analysis & User Experience (Latest)
- **Advanced Manual J Implementation**: Added comprehensive ACCA Manual J load calculations with climate zone data, ASHRAE design temperatures, and county-based climate mapping
- **Interactive User Assumptions**: New `AssumptionModal.tsx` component allows users to provide building envelope details (insulation R-values, window types, construction materials) for accurate load calculations
- **Multi-Step Upload Process**: Enhanced `MultiStepUpload.tsx` with progress tracking and assumption collection workflow
- **Comprehensive Climate Data**: Added CSV datasets for ASHRAE design temperatures, county climate zones, and zip code mappings for precise regional calculations
- **Advanced HVAC Services**: New services including `climate_data.py`, `envelope_extractor.py`, `cltd_clf.py` for sophisticated thermal load analysis
- **Audit Tracking System**: Implemented `audit_tracker.py` for comprehensive logging and monitoring of processing pipeline
- **Enhanced Testing Suite**: Extended test coverage with ACCA examples, duct configuration tests, and legacy Manual J validation
- **PDF Generation**: Advanced PDF report generation with HTML templates for professional HVAC reports
- **User Data Management**: Enhanced user services with secure data storage and management capabilities

### Codebase Optimization (Previous)
- **Removed unused dependencies**: Eliminated `boto3` and `wkhtmltopdf` from requirements.txt
- **Cleaned legacy components**: Retained `UploadModal.tsx.old` for reference during multi-step implementation
- **Organized project structure**: Moved development scripts to `backend/scripts/` folder
- **Enhanced .gitignore**: Comprehensive rules to prevent log files and build artifacts
- **Improved file organization**: Better separation of concerns and cleaner project layout
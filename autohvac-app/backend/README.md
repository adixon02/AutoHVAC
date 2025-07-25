# AutoHVAC API V2 - Clean Architecture

🏗️ **Professional HVAC load calculations and system recommendations with a clean, modular FastAPI implementation.**

## 🎯 Features

- ✅ **Strict versioned routing** (`/api/v2/...`)
- ✅ **Robust CORS** with wildcard subdomain support
- ✅ **Streaming file uploads** (≤1MB chunks, max 150MB)
- ✅ **Background job processing** with Redis/Celery
- ✅ **Job status polling** (`/api/v2/job/{job_id}`)
- ✅ **Health check** (`/health`) for load balancers
- ✅ **Comprehensive logging** and error handling
- ✅ **Full test suite** with 90%+ coverage
- ✅ **CI/CD pipeline** with GitHub Actions
- ✅ **Docker support** for local development

## 🚀 Quick Start

### Local Development with Docker

```bash
# Clone and navigate
git clone <repo-url>
cd autohvac-app/backend

# Start all services (web, worker, redis)
docker-compose up --build

# API available at http://localhost:8000
# Health check: http://localhost:8000/health
```

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (required)
docker run -d -p 6379:6379 redis:7-alpine

# Start web server
uvicorn app.main:app --reload --port 8000

# Start worker (separate terminal)
celery -A app.tasks.worker worker --loglevel=info
```

## 📡 API Endpoints

### Core Endpoints
- `GET /health` - Health check
- `GET /` - API info

### Blueprint Processing
- `POST /api/v2/blueprint/upload` - Upload PDF (returns job_id)
- `GET /api/v2/job/{job_id}` - Poll job status/results

### Climate Data
- `GET /api/v2/climate/{zip_code}` - Get climate zone and design temps

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/routes/test_blueprint_upload.py -v

# Run integration tests only
pytest -m integration
```

## 📋 Development Workflow

### Code Quality
```bash
# Lint code
flake8 app tests

# Type check
mypy app

# Sort imports
isort app tests

# Security scan
bandit -r app
safety check
```

### Test Upload Flow
```bash
# Test CORS preflight
curl -I -X OPTIONS -H "Origin: https://auto-hvac.vercel.app" \
     http://localhost:8000/api/v2/blueprint/upload

# Upload a file
curl -X POST -F "file=@test.pdf" \
     http://localhost:8000/api/v2/blueprint/upload

# Poll job status (use job_id from upload response)
curl http://localhost:8000/api/v2/job/{job_id}
```

## 🏗️ Architecture

```
app/
├── main.py              # FastAPI app with CORS & middleware
├── core/                # Configuration, logging, errors
│   ├── config.py        # Pydantic settings
│   ├── logging.py       # Structured logging
│   └── errors.py        # Custom exceptions
├── routes/              # API endpoints
│   ├── blueprint.py     # File upload endpoint
│   ├── job.py          # Job polling endpoint
│   ├── health.py       # Health check
│   └── climate.py      # Climate data
├── models/              # Pydantic schemas
│   ├── requests.py     # Request models
│   └── responses.py    # Response models
├── services/            # Business logic
│   ├── job_storage.py  # Redis job storage
│   └── file_handler.py # File upload handling
└── tasks/               # Background processing
    ├── blueprint_processing.py  # PDF processing
    └── worker.py               # Celery configuration
```

## 🚀 Deployment

### Render.com (Production)

The project includes `render.yaml` with separate web and worker services:

- **Web service**: Handles HTTP requests only
- **Worker service**: Processes background jobs
- **Redis service**: Job storage and message broker

### Environment Variables

```bash
# Core settings
APP_NAME="AutoHVAC API V2"
APP_VERSION="2.0.0"
LOG_LEVEL="INFO"

# File upload limits
MAX_FILE_SIZE_MB=150
UPLOAD_CHUNK_SIZE_MB=1

# CORS origins
ALLOWED_ORIGINS="https://auto-hvac.vercel.app,http://localhost:3000"

# Redis connection
REDIS_URL="redis://localhost:6379/0"
```

## 📊 Monitoring

### Health Check
```bash
curl https://autohvac.onrender.com/health
# Expected: {"status": "healthy", "version": "2.0.0", ...}
```

### Logs
- Structured JSON logging with request IDs
- Error tracking with full stack traces
- Performance metrics (request duration)

## 🔒 Security

- File size limits (150MB max)
- File type validation (PDF only)
- CORS protection with origin validation
- Input sanitization and validation
- Security scanning with Bandit

## 🤝 Contributing

1. **Create feature branch**: `git checkout -b feature/amazing-feature`
2. **Run tests**: `pytest`
3. **Lint code**: `flake8 app tests`
4. **Type check**: `mypy app`
5. **Create PR** to `main` branch

## 📈 Performance

- **Upload response**: < 2 seconds for files up to 150MB
- **Health check**: < 50ms response time
- **Job processing**: Parallel background execution
- **Memory efficient**: Streaming file uploads

---

**Built with FastAPI, Redis, Celery, and ❤️**
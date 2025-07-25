# AutoHVAC Backend Deployment Guide

## Architecture Overview

The AutoHVAC backend is now split into three services for better scalability and reliability:

1. **Web API Service** (`autohvac-api`) - Handles HTTP requests, never exits during file uploads
2. **Background Worker Service** (`autohvac-worker`) - Processes blueprint files using Celery
3. **Redis Service** (`autohvac-redis`) - Message broker and result backend

## Key Features

- **Graceful Shutdown**: Main API process waits for active uploads to complete before shutting down
- **Health Check**: `/health` endpoint returns 200 immediately for load balancer checks
- **Background Processing**: File processing happens in separate worker processes
- **Fault Tolerance**: Falls back to synchronous processing if Celery is unavailable
- **PDF Validation**: Validates PDF files before processing to prevent "No /Root object" errors

## Deployment on Render

The `render.yaml` file defines all three services:

```yaml
services:
  - type: web          # API service
  - type: worker       # Background worker
  - type: redis        # Message broker
```

### Environment Variables

The following environment variables are automatically configured:

- `REDIS_URL` - Redis connection string
- `CELERY_BROKER_URL` - Celery message broker
- `CELERY_RESULT_BACKEND` - Celery result storage
- `ALLOWED_ORIGINS` - CORS allowed origins

## Local Development

### Option 1: Full Stack (API + Worker + Redis)
```bash
python dev_start.py
```

### Option 2: Individual Services
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start API
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3: Start Worker
python start_worker.py
```

## Testing

### Health Check
```bash
curl http://localhost:8000/health
```

### Celery Connection
```bash
python test_celery.py
```

### Full Deployment Verification
```bash
python verify_deployment.py https://your-render-url.com
```

## API Endpoints

### Core Endpoints
- `GET /health` - Immediate health check (< 100ms response)
- `GET /` - API information
- `POST /api/v2/blueprint/upload` - Upload blueprint for processing
- `GET /api/v2/blueprint/status/{job_id}` - Check processing status
- `GET /api/v2/blueprint/results/{job_id}` - Get processing results

### Blueprint Processing Flow

1. **Upload**: Client uploads PDF to `/api/v2/blueprint/upload`
2. **Validation**: Server validates PDF format and size
3. **Job Creation**: Unique job ID created, file saved to disk
4. **Background Processing**: Celery task started for PDF processing
5. **Status Polling**: Client polls `/api/v2/blueprint/status/{job_id}`
6. **Results**: When complete, results available at `/api/v2/blueprint/results/{job_id}`

## Error Handling

### PDF Validation Errors
- Invalid PDF files are rejected with 400 status
- Files are cleaned up if validation fails

### Processing Failures
- Falls back to mock data if processing fails
- Graceful degradation ensures API always responds

### Celery Failures
- Falls back to synchronous processing
- Upload tracking ensures graceful shutdown

## Monitoring

### Health Checks
- Web service: `GET /health` (configured in render.yaml)
- Worker service: Monitored by Render automatically
- Redis service: Monitored by Render automatically

### Logs
- API logs: Available in Render dashboard for `autohvac-api`
- Worker logs: Available in Render dashboard for `autohvac-worker`
- Redis logs: Available in Render dashboard for `autohvac-redis`

## Scaling

### Vertical Scaling
- Upgrade Render plans for more CPU/memory
- Increase Celery worker concurrency

### Horizontal Scaling
- Multiple worker instances can be deployed
- Redis handles coordination between workers
- API is stateless (except for in-memory job storage)

## Troubleshooting

### Common Issues

1. **"No /Root object" PDF Error**
   - Now handled by PDF validation before processing
   - Invalid files rejected with clear error message

2. **Worker Not Processing Tasks**
   - Check Redis connection
   - Verify worker service is running in Render dashboard
   - Check worker logs for errors

3. **API Timeouts During Upload**
   - File processing now happens in background
   - Upload endpoint returns immediately after validation

4. **Graceful Shutdown Issues**
   - Check logs for active upload tracking
   - Verify shutdown timeout settings

### Debug Commands

```bash
# Check Redis connection
redis-cli ping

# List Celery tasks
celery -A celery_app inspect active

# Monitor Celery workers
celery -A celery_app inspect stats

# Test health check
curl -w "%{time_total}" http://localhost:8000/health
```

## Security Considerations

- PDF validation prevents malicious file processing
- File size limits prevent DoS attacks
- CORS properly configured for allowed origins
- Redis isolated per environment
- Worker processes isolated from API

## Performance

- Health checks respond in < 100ms
- File uploads process immediately in background
- Worker processes handle heavy computational tasks
- Redis provides fast message passing and result storage
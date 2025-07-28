# AutoHVAC Backend

## Quick Start

### Prerequisites
- Python 3.8+
- Redis (optional, for background job processing)
- OpenAI API key (for blueprint parsing)

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

## API Endpoints

- `POST /api/v1/blueprint/upload` - Upload blueprint for processing
- `GET /api/v1/job/{job_id}` - Get job status
- `GET /healthz` - Health check endpoint

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
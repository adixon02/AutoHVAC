# Backend Fix Deployment Validation

## Issues Fixed

### 1. ✅ API 422 Error - Missing zip_code Field
**Problem**: Frontend form didn't collect zip_code, but backend required it
**Solution**: 
- Added ZIP code collection step to MultiStepUpload.tsx 
- Added form validation for 5-digit ZIP codes
- Updated form submission to include zip_code parameter

### 2. ✅ Celery Worker Import Issues
**Problem**: render.yaml referenced wrong module `tasks.parse_blueprint` 
**Solution**:
- Updated render.yaml to use correct module: `tasks.calculate_hvac_loads`
- Increased worker time limits to 1800s for complex processing

### 3. ✅ AsyncClient 'proxies' Error in AI Processing  
**Problem**: OpenAI library version incompatibility with httpx proxies parameter
**Solution**:
- Updated OpenAI library to >= 1.35.0 for compatibility
- Added comprehensive error handling for httpx/connection errors
- Added specific error messages for proxy-related issues

### 4. ✅ OCR and PDF Dependencies
**Problem**: Missing tesseract-ocr and PDF processing system packages
**Solution**:
- Updated Dockerfile.dev and render.yaml with system packages:
  - tesseract-ocr tesseract-ocr-eng
  - libpoppler-utils poppler-utils  
  - libgl1-mesa-glx libglib2.0-0
- Added error handling for missing OCR dependencies
- Fixed PyMuPDF null pointer comparisons

## Deployment Validation Steps

### Pre-Deployment Checklist

1. **Environment Variables**
   ```bash
   # Ensure these are set in render.yaml environment
   OPENAI_API_KEY=your_openai_key
   REDIS_URL=redis://localhost:6379/0  
   DATABASE_URL=postgresql://...
   PYTHONUNBUFFERED=1
   ```

2. **Dependencies Check**
   ```bash
   # Verify requirements.txt versions
   openai>=1.35.0,<2.0
   pymupdf>=1.24.0,<1.26.0
   pytesseract==0.3.13
   ```

### Post-Deployment Validation

#### 1. API Upload Endpoint Test
```bash
# Test upload with all required fields including zip_code
curl -X POST https://your-backend.onrender.com/api/v1/blueprint/upload \
  -F "file=@test.pdf" \
  -F "email=test@example.com" \
  -F "project_label=Test Project" \
  -F "zip_code=90210" \
  -F "duct_config=ducted_attic" \
  -F "heating_fuel=gas"

# Expected: 200 response with job_id
# Should NOT return 422 error about missing zip_code
```

#### 2. Celery Worker Startup Test
```bash
# Check worker logs for import errors
# Should see successful startup like:
# [2024-XX-XX XX:XX:XX,XXX: INFO/MainProcess] Connected to redis://...
# [2024-XX-XX XX:XX:XX,XXX: INFO/MainProcess] mingle: searching for neighbors
# [2024-XX-XX XX:XX:XX,XXX: INFO/MainProcess] Ready to accept tasks

# Should NOT see:
# ModuleNotFoundError: No module named 'tasks.parse_blueprint'
```

#### 3. AI Processing Test
```bash
# Monitor job processing through the pipeline
# Check for successful AI cleanup without proxy errors

# Successful logs should show:
# "AI processing completed: X rooms, Y sqft"
# 
# Should NOT see:
# "AsyncClient.__init__() got an unexpected keyword argument 'proxies'"
# "HTTP client configuration error - please update OpenAI library"
```

#### 4. OCR and PDF Processing Test
```bash
# Check system packages are installed
tesseract --version
# Should return version info, not "command not found"

# Upload a PDF and check processing logs
# Should see:
# "Text extraction completed: {...}"
# "Geometry extraction completed: {...}"
#
# Should NOT see:
# "tesseract is not installed or it's not in your PATH"
# "'<' not supported between instances of 'NoneType' and 'float'"
```

#### 5. Full Pipeline Test
```bash
# Test complete upload-to-completion flow
1. Upload a PDF blueprint with all required fields
2. Monitor job progress through stages:
   - initializing (5%)
   - extracting_geometry (20%) 
   - extracting_text (35%)
   - ai_processing (50%)
   - envelope_analysis (65%)
   - calculating_loads (80%)
   - finalizing (95%)
   - completed (100%)

3. Verify final result contains:
   - HVAC load calculations
   - Room-by-room analysis
   - Equipment recommendations
   - No error messages in job status
```

### Error Monitoring

#### Check These Logs for Issues:

1. **Frontend Console Errors**
   - No 422 errors on form submission
   - ZIP code validation working properly

2. **Backend API Logs**  
   - All upload requests succeed with 200 status
   - No missing field validation errors

3. **Celery Worker Logs**
   - Workers start without import errors
   - Tasks complete successfully without timeouts
   - All pipeline stages execute without exceptions

4. **Job Status Database**
   - Jobs progress through all stages
   - Final status is "completed" not "failed"
   - Error messages are clear when failures occur

### Rollback Plan

If issues persist after deployment:

1. **Immediate Actions**
   - Rollback render.yaml to previous working version
   - Monitor error rates and job completion

2. **Debug Steps**
   - Check environment variables are set correctly
   - Verify system packages installed in build logs
   - Test dependencies in container environment

3. **Gradual Re-deployment**
   - Deploy fixes one component at a time
   - Test each fix in isolation before combining

## Success Criteria

✅ API returns 200 for valid uploads including zip_code  
✅ Celery worker starts with no module import errors  
✅ Jobs progress through all pipeline stages successfully  
✅ OCR and PDF parsing work without dependency errors  
✅ All errors are logged clearly and reported to job status  
✅ Full upload-to-result pipeline completes in under 5 minutes  

## Contact

If deployment validation fails, check:
1. Build logs for system package installation
2. Runtime logs for dependency errors  
3. Job status for specific pipeline stage failures
4. Environment variable configuration
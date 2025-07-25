# AutoHVAC Deployment Guide

## Overview
Your code has been successfully committed and pushed to GitHub. Now you need to deploy:
1. **Backend** to Render (3 services: API, Worker, Redis)
2. **Frontend** to Vercel

## ✅ Completed
- [x] Code committed to Git
- [x] Changes pushed to GitHub: `88ba2f1`
- [x] Backend configured with graceful shutdown and Celery
- [x] Render configuration updated with 3-service architecture

## 🚀 Next Steps

### 1. Deploy Backend to Render

Since we've updated the `render.yaml` with the new architecture, you need to:

#### Option A: Automatic Deployment (if connected to GitHub)
1. Go to [Render Dashboard](https://dashboard.render.com)
2. If your repository is connected, the deployment should start automatically
3. You'll see 3 new services being created:
   - `autohvac-api` (Web Service)
   - `autohvac-worker` (Background Worker)  
   - `autohvac-redis` (Redis)

#### Option B: Manual Service Creation
If not automatically detected, create services manually:

1. **Create Redis Service**
   - Go to Render Dashboard → New → Redis
   - Name: `autohvac-redis`
   - Plan: Free
   - Max Memory Policy: `allkeys-lru`

2. **Create Web Service (API)**
   - Go to Render Dashboard → New → Web Service
   - Connect your GitHub repo
   - Name: `autohvac-api`
   - Root Directory: `autohvac-app/backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 300`
   - Environment Variables:
     ```
     REDIS_URL=[Link to autohvac-redis]
     CELERY_BROKER_URL=[Link to autohvac-redis]
     CELERY_RESULT_BACKEND=[Link to autohvac-redis]
     ALLOWED_ORIGINS=https://auto-hvac.vercel.app,http://localhost:3000
     ```

3. **Create Worker Service**
   - Go to Render Dashboard → New → Background Worker
   - Connect same GitHub repo
   - Name: `autohvac-worker`
   - Root Directory: `autohvac-app/backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python start_worker.py`
   - Same environment variables as above

### 2. Deploy Frontend to Vercel

#### Method 1: Vercel CLI (Local)
```bash
cd autohvac-app/frontend

# Login to Vercel (if not already)
npx vercel login

# Deploy to production
npx vercel --prod
```

#### Method 2: Vercel Dashboard (Recommended)
1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "New Project"
3. Import your GitHub repository
4. Set these configurations:
   - **Root Directory**: `autohvac-app/frontend`
   - **Framework Preset**: Next.js
   - **Build Command**: `npm run build`
   - **Output Directory**: (leave default)
   - **Environment Variables**:
     ```
     NEXT_PUBLIC_API_URL=https://autohvac-api.onrender.com
     ```

### 3. Update CORS Configuration

After getting your Vercel URL, update the Render API service:
1. Go to Render Dashboard → autohvac-api → Environment
2. Update `ALLOWED_ORIGINS` to include your Vercel domain:
   ```
   ALLOWED_ORIGINS=https://your-vercel-app.vercel.app,http://localhost:3000
   ```

### 4. Verify Deployment

Run the verification script against your deployed services:

```bash
cd autohvac-app/backend

# Test the Render API
python verify_deployment.py https://autohvac-api.onrender.com

# Test end-to-end with frontend
# Visit your Vercel URL and test blueprint upload
```

## 🔍 Monitoring & Troubleshooting

### Health Checks
- **API Health**: `https://autohvac-api.onrender.com/health`
- **Worker Status**: Check Render dashboard for `autohvac-worker` logs
- **Redis Status**: Check Render dashboard for `autohvac-redis` metrics

### Common Issues

1. **Services not starting**
   - Check logs in Render dashboard
   - Verify environment variables are set correctly
   - Ensure Redis service is linked properly

2. **Worker not processing tasks**
   - Check `autohvac-worker` logs
   - Verify Redis connection
   - Test with: `python test_celery.py`

3. **CORS errors on frontend**
   - Update `ALLOWED_ORIGINS` environment variable
   - Include your exact Vercel domain

4. **PDF processing fails**
   - Check worker logs for specific errors
   - Test PDF validation with various files
   - Falls back to mock data on failure

### Performance Monitoring

The new architecture provides:
- **API Response Time**: < 100ms for health checks
- **Upload Processing**: Background via Celery workers
- **Graceful Shutdown**: API waits for active uploads
- **Fault Tolerance**: Falls back to sync processing if Celery fails

## 📋 Deployment Checklist

- [ ] Render Redis service created and running
- [ ] Render API service created and running  
- [ ] Render Worker service created and running
- [ ] Environment variables configured
- [ ] Frontend deployed to Vercel
- [ ] CORS origins updated with Vercel URL
- [ ] Health check responding (< 100ms)
- [ ] Blueprint upload test successful
- [ ] Worker processing test successful

## 🎯 URLs to Test

After deployment, you should have:
- **API**: `https://autohvac-api.onrender.com`
- **Health**: `https://autohvac-api.onrender.com/health`  
- **Frontend**: `https://your-app.vercel.app`
- **Climate API**: `https://autohvac-api.onrender.com/api/v2/climate/99206`

## 📚 Documentation

- **Backend Architecture**: `/autohvac-app/backend/DEPLOYMENT.md`
- **API Documentation**: Available at API root URL
- **Development Setup**: Use `python dev_start.py` for local development

---

**Next Steps After Deployment:**
1. Test the complete user flow from frontend to backend
2. Monitor logs for any deployment issues
3. Test with real PDF files to verify processing
4. Set up any monitoring/alerting as needed
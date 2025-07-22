# AutoHVAC Deployment Guide

## Quick Deploy Options

### 1. **Recommended: Vercel + Railway**

#### Frontend (Vercel)
1. Push your code to GitHub
2. Go to [vercel.com](https://vercel.com) and import your repo
3. Set environment variable: `NEXT_PUBLIC_API_URL` = your Railway backend URL
4. Deploy automatically!

#### Backend (Railway)
1. Go to [railway.app](https://railway.app)
2. Create new project from GitHub repo
3. Select the `backend/` folder
4. Railway will auto-deploy using the Dockerfile
5. Copy the generated URL for your frontend

### 2. **Alternative: All-in-One Railway**

Deploy both frontend and backend on Railway:
1. Create two services in one Railway project
2. Frontend: Next.js service
3. Backend: Python service
4. Set up internal networking

### 3. **Other Options**

- **Netlify + Render**
- **AWS (EC2/Elastic Beanstalk + S3)**
- **Google Cloud Platform**
- **Digital Ocean App Platform**

## Step-by-Step Deployment

### A. Deploy Backend First

#### Railway Deployment:
1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your AutoHVAC repository
4. Choose "backend" folder as root directory
5. Railway will detect the Dockerfile and deploy
6. Copy the generated URL (e.g., `https://autohvac-backend-production.railway.app`)

#### Environment Variables (in Railway dashboard):
```
PORT=8000
ALLOWED_ORIGINS=https://your-frontend-url.vercel.app
```

### B. Deploy Frontend

#### Vercel Deployment:
1. Go to [vercel.com](https://vercel.com)
2. Click "New Project" → Import from GitHub
3. Select your AutoHVAC repository
4. Set Root Directory to `autohvac-app`
5. Add Environment Variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
   ```
6. Deploy!

### C. Update CORS Settings

After deployment, update your backend's CORS settings:
1. Go to Railway dashboard
2. Update environment variable:
   ```
   ALLOWED_ORIGINS=https://your-actual-vercel-url.vercel.app
   ```
3. Redeploy backend

## Testing Your Deployment

1. Visit your Vercel URL
2. Test the manual input flow first
3. Test blueprint upload (requires both services running)
4. Check the Network tab in browser dev tools for API calls

## Troubleshooting

### Common Issues:

**CORS Errors:**
- Check that your frontend URL is in backend's `ALLOWED_ORIGINS`
- Ensure environment variables are set correctly

**Backend Not Found:**
- Verify `NEXT_PUBLIC_API_URL` points to correct Railway URL
- Check that backend service is running (Railway dashboard)

**File Upload Fails:**
- Check Railway logs for backend errors
- Ensure file size limits are appropriate

**Build Failures:**
- Check build logs in platform dashboard
- Verify all dependencies are in requirements.txt/package.json

### Debugging Commands:

**Check backend health:**
```bash
curl https://your-backend-url.railway.app/health
```

**View Railway logs:**
Go to Railway dashboard → Your service → Logs

**View Vercel logs:**
Go to Vercel dashboard → Your project → Functions tab

## Production Checklist

- [ ] Backend deployed and health check passes
- [ ] Frontend deployed and loads correctly
- [ ] Environment variables configured
- [ ] CORS settings updated
- [ ] File upload tested
- [ ] Blueprint processing tested
- [ ] Error handling works
- [ ] Performance is acceptable

## Free Tier Limits

**Vercel:**
- 100GB bandwidth/month
- 10GB storage
- Serverless functions

**Railway:**
- $5 free credit/month
- Enough for light testing
- Upgrade for production use

## Cost Estimates

**Monthly costs for production:**
- Vercel Pro: $20/month (if you exceed free tier)
- Railway: $5-20/month (depending on usage)
- **Total: ~$25-40/month** for a production-ready setup

## Next Steps

1. Set up custom domain
2. Add authentication
3. Set up monitoring
4. Configure backups
5. Add SSL certificates (handled automatically by platforms)
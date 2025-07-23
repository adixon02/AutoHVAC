# Vercel Environment Variables Setup

To make the blueprint upload work on your Vercel deployment, you need to add the following environment variable:

## Steps:

1. Go to your Vercel dashboard
2. Select your AutoHVAC project
3. Go to Settings → Environment Variables
4. Add the following variable:

   **Variable Name:** `NEXT_PUBLIC_API_URL`
   **Value:** `https://autohvac-backend.onrender.com`
   **Environment:** Production (and optionally Preview)

5. Click "Save"
6. Redeploy your application (Vercel should do this automatically)

## Important Notes:

- The backend URL assumes your Render service is named `autohvac-backend`
- If your Render URL is different, update accordingly
- The `NEXT_PUBLIC_` prefix is required for the variable to be accessible in the browser
- Make sure there are no trailing slashes in the URL

## Testing:

After deployment, open the browser console and look for these debug messages:
- 🚀 Uploading to: https://autohvac-backend.onrender.com/api/blueprint/upload
- ✅ Upload successful, job ID: [some-uuid]
- 🔄 Showing analyzing screen for: [filename]

If you see errors, check:
1. The Render backend is running (check Render dashboard)
2. The URL is correct
3. No CORS errors in console
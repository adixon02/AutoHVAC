# AutoHVAC MVP Testing Instructions

## Setup

1. **Install Frontend Dependencies**
```bash
cd frontend
npm install
```

2. **Configure Environment Variables**

Create `.env.local` in the frontend directory:
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# NextAuth Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key-here

# Email Configuration (for magic links)
EMAIL_SERVER_HOST=smtp.gmail.com
EMAIL_SERVER_PORT=587
EMAIL_SERVER_USER=your-email@gmail.com
EMAIL_SERVER_PASSWORD=your-app-password
EMAIL_FROM=noreply@autohvac.com
```

3. **Start Services**
```bash
# Terminal 1: Backend
cd backend
python run_server.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

## Test Flow

### 1. First Upload (Free)

1. Go to http://localhost:3000
2. Click "Start Free Analysis"
3. Complete the multi-step upload:
   - Step 1: Enter project name and upload PDF
   - Step 2: Select duct configuration
   - Step 3: Select heating system
   - Step 4: Enter ZIP code
   - Step 5: Review selections
   - Step 6: Enter email (captures at the end!)
4. Click "Start Analysis"
5. You should see the analyzing page with progress

### 2. After Analysis Complete

1. When analysis is complete, you'll see:
   - "Create Account & View Report" button (if not logged in)
   - A prompt to create an account with the email you provided
2. Click "Create Account & View Report"
3. You'll be redirected to sign in page
4. Enter the same email
5. Check your email for magic link
6. Click the link to sign in
7. You'll be redirected to dashboard

### 3. Second Upload (Paywall)

1. From dashboard, click "New Analysis"
2. You should be redirected to /upgrade page (NOT a modal)
3. The upgrade page shows:
   - Full pricing details
   - Benefits list
   - Testimonials
   - FAQs
4. Click "Upgrade to Pro" to see Stripe checkout (test mode)

### 4. Testing Stripe

Use test card: 4242 4242 4242 4242
- Any future expiry date
- Any 3-digit CVC
- Any billing ZIP

### 5. Reset for Re-testing

To reset a user's free upload:
```bash
cd backend
python scripts/reset_free_upload.py test@example.com
```

## What to Verify

✅ **Email Collection Last**: Email is only requested in final step
✅ **Free First Upload**: Works without any authentication
✅ **Full Page Paywall**: Second upload redirects to /upgrade (not modal)
✅ **Magic Link Auth**: Simple email-only authentication
✅ **Usage Indicator**: Dashboard shows free/paid status clearly
✅ **No Dead Ends**: All error states guide to upgrade

## Common Issues

1. **Email not sending**: Check EMAIL_SERVER credentials in .env.local
2. **Stripe not working**: Ensure STRIPE_MODE=test in backend .env
3. **402 error as 500**: Backend should return proper 402 status
4. **Dashboard redirect loop**: Clear cookies and try again

## MVP Scope Reminders

- ❌ No share links
- ❌ No teams/organizations  
- ❌ No advanced analytics
- ✅ Single user per email
- ✅ One free upload
- ✅ Simple magic link auth
- ✅ Full page paywall
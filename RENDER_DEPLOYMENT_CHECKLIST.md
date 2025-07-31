# Render Deployment Checklist for "First Report Free" Feature

## Pre-Deployment Steps

### 1. Environment Variables to Verify/Add on Render

#### Backend Service
- [ ] `SENDGRID_API_KEY` - Required for sending report completion emails
- [ ] `STRIPE_SECRET_KEY` - Required for payment processing
- [ ] `STRIPE_PRICE_ID` - Your subscription price ID from Stripe
- [ ] `STRIPE_WEBHOOK_SECRET` - For handling Stripe webhooks
- [ ] `FRONTEND_URL` - Should be your Render frontend URL (e.g., https://autohvac-frontend.onrender.com)
- [ ] `DATABASE_URL` - Should be automatically set by Render
- [ ] `AWS_ACCESS_KEY_ID` - For S3 storage
- [ ] `AWS_SECRET_ACCESS_KEY` - For S3 storage

#### Frontend Service
- [ ] `NEXT_PUBLIC_API_URL` - Should point to your Render backend URL

### 2. Database Migration
After deployment, the new migration needs to run:
```bash
# This should happen automatically if you have a build command like:
# python -m alembic upgrade head
```

The migration adds these fields to the `projects` table:
- `client_ip` (VARCHAR 45)
- `user_agent` (VARCHAR 512)
- `referrer` (VARCHAR 512)

### 3. Stripe Configuration
- [ ] Ensure Stripe webhook endpoint is configured to point to: `https://your-backend-url.onrender.com/billing/webhook`
- [ ] Webhook should listen for these events:
  - `checkout.session.completed`
  - `invoice.paid`
  - `customer.subscription.deleted`
  - `invoice.payment_failed`
  - `customer.subscription.updated`

## Deployment Steps

1. **Backend Deployment**
   - Render will automatically detect the push to main
   - Watch the deploy logs for any errors
   - Verify the migration runs successfully

2. **Frontend Deployment**
   - Will also auto-deploy from the push
   - No specific changes needed for frontend

## Post-Deployment Verification

### 1. Test the Free Report Flow
- [ ] Visit your production site
- [ ] Upload a blueprint with a NEW email address
- [ ] Verify it succeeds without email verification
- [ ] Check that user is created with `free_report_used = true`

### 2. Test the Payment Gate
- [ ] Use the SAME email to upload another blueprint
- [ ] Verify you get the payment required modal
- [ ] Check that the Stripe checkout URL works

### 3. Test Email Notifications
- [ ] Complete a report processing
- [ ] Verify email is sent with:
  - Report link
  - Upgrade CTAs
  - "This was your FREE report!" message

### 4. Test Analytics Tracking
- [ ] Check database for new projects
- [ ] Verify `client_ip`, `user_agent`, and `referrer` are populated

### 5. Monitor Logs
- [ ] Check Render logs for any errors
- [ ] Monitor Sentry (if configured) for exceptions

## Rollback Plan

If issues arise:

1. **Quick Rollback**
   - Use Render's "Rollback" feature to previous deployment

2. **Database Rollback** (if needed)
   ```bash
   python -m alembic downgrade -1
   ```

3. **Feature Flag** (if implemented)
   - Set `FREE_REPORT_ENABLED=false` to disable the feature

## Expected Behavior

### Success Metrics
- First-time users can upload without friction
- Clear payment gate for second upload
- Increased email engagement with CTAs
- Analytics data being collected

### Known Limitations
- Email validation is basic (can be enhanced later)
- Analytics are for first upload only (can expand later)
- No browser fingerprinting yet (IP only)

## Support Contacts
- Frontend issues: Check browser console for 402 responses
- Backend issues: Check Render logs
- Payment issues: Check Stripe dashboard
- Email issues: Check SendGrid dashboard

## Notes
- The feature is designed to be backward compatible
- Existing users with subscriptions are unaffected
- All payment processing goes through Stripe's secure checkout
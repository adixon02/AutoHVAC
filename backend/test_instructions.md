# Testing the Free Report Flow Implementation

## Prerequisites
1. Make sure the backend is running on the correct port (check with `ps aux | grep uvicorn`)
2. Make sure the frontend is running on http://localhost:3000
3. Apply database migrations if needed: `python3 -m alembic upgrade head`

## Manual Testing Steps

### 1. Test First Upload (No Email Verification Required)
1. Open http://localhost:3000 in your browser
2. Navigate to the upload page
3. Use a NEW email address (e.g., `testuser_[timestamp]@example.com`)
4. Upload any PDF blueprint
5. **Expected Result**: Upload should succeed without requiring email verification
6. Check the database to verify:
   - User was created with `free_report_used = True`
   - Project was created successfully

### 2. Test Second Upload (Payment Required)
1. Use the SAME email from step 1
2. Try to upload another blueprint
3. **Expected Result**: 
   - Should receive a 402 Payment Required response
   - Should see a modal/message with:
     - "You've used your free analysis. Upgrade to Pro for unlimited reports."
     - List of upgrade benefits
     - Stripe checkout button

### 3. Test Email Validation
Try uploading with these invalid emails:
- `notanemail`
- `test@test.com` (blocked spam pattern)
- `asdf@asdf.com` (blocked spam pattern)
- `@example.com`
- `test test@example.com`

**Expected Result**: Should get "Invalid email format" error

### 4. Test Report Completion Email
1. Complete a successful upload with a valid email
2. Wait for the report to process
3. **Expected Result**: 
   - Email should be sent with:
     - "This was your FREE report!" message
     - Strong upgrade CTAs
     - Customer testimonials
     - Link to view report

### 5. Test Job Status API
After a report completes, check the job status endpoint:
```
GET /job/{job_id}
```

**Expected Result**: Response should include `upgrade_prompt` object with:
```json
{
  "upgrade_prompt": {
    "show": true,
    "title": "Love AutoHVAC? Go Pro!",
    "benefits": [...],
    "cta_text": "Upgrade Now",
    "limited_time_offer": "20% OFF - Limited Time"
  }
}
```

## Debugging Tips

1. **Check backend logs** for any errors
2. **Check browser console** for API errors
3. **Verify environment variables**:
   - `SENDGRID_API_KEY` (for emails)
   - `STRIPE_SECRET_KEY` (for payments)
   - `FRONTEND_URL` (for email links)

4. **Database checks**:
   ```sql
   -- Check user status
   SELECT email, free_report_used, email_verified, active_subscription 
   FROM users 
   WHERE email = 'your_test_email@example.com';
   
   -- Check project analytics
   SELECT user_email, client_ip, user_agent, referrer 
   FROM projects 
   WHERE user_email = 'your_test_email@example.com';
   ```

## Common Issues

1. **"Method not allowed" errors**: Wrong API endpoint or port
2. **Database errors**: Run migrations with `python3 -m alembic upgrade head`
3. **Email not sending**: Check SendGrid configuration
4. **Payment errors**: Check Stripe configuration

## Success Criteria

✅ First upload works without email verification
✅ Second upload requires payment
✅ Invalid emails are rejected
✅ Analytics are tracked (IP, user agent, referrer)
✅ Completion email sent with upgrade CTAs
✅ Job status includes upgrade prompts
✅ Frontend shows payment modal on second upload
# Stripe Paywall Testing Guide

This guide explains how to test the Stripe paywall flow for blueprint uploads.

## Overview

Each user gets one free blueprint upload. After using their free upload, they must subscribe via Stripe to continue uploading blueprints.

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# Stripe Configuration
# For testing (default):
STRIPE_MODE=test
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_test_...

# For production (when ready):
# STRIPE_MODE=live
# STRIPE_SECRET_KEY_LIVE=sk_live_...
# STRIPE_PUBLISHABLE_KEY_LIVE=pk_live_...
# STRIPE_WEBHOOK_SECRET_LIVE=whsec_...
# STRIPE_PRICE_ID_LIVE=price_live_...

# Frontend URL for redirect after payment
FRONTEND_URL=http://localhost:3000
```

### Stripe Test Cards

When testing in test mode, use these card numbers:
- **Success**: 4242 4242 4242 4242
- **Decline**: 4000 0000 0000 0002
- **Requires authentication**: 4000 0025 0000 3155

Use any future expiry date and any 3-digit CVC.

## Testing the Flow

### 1. Test Free Upload (First Upload)

```bash
# Use any non-whitelisted email
curl -X POST http://localhost:8000/blueprint/upload \
  -F "email=testuser@example.com" \
  -F "project_label=Test Project" \
  -F "zip_code=12345" \
  -F "file=@test_blueprint.pdf" \
  -F "duct_config=ducted_attic" \
  -F "heating_fuel=gas"
```

This should succeed and return a job ID.

### 2. Test Paywall (Second Upload)

Using the same email, try uploading again:

```bash
curl -X POST http://localhost:8000/blueprint/upload \
  -F "email=testuser@example.com" \
  -F "project_label=Second Project" \
  -F "zip_code=12345" \
  -F "file=@test_blueprint.pdf" \
  -F "duct_config=ducted_attic" \
  -F "heating_fuel=gas"
```

This should return a 402 Payment Required response with a Stripe checkout URL.

### 3. Reset Free Upload (For Re-testing)

To reset the free upload flag for an email:

```bash
cd backend
python scripts/reset_free_upload.py testuser@example.com
```

To check user status without resetting:

```bash
python scripts/reset_free_upload.py testuser@example.com --check-only
```

## Webhook Testing

### Local Testing with Stripe CLI

1. Install Stripe CLI: https://stripe.com/docs/stripe-cli

2. Login to Stripe:
```bash
stripe login
```

3. Forward webhooks to your local server:
```bash
stripe listen --forward-to localhost:8000/billing/webhook
```

4. Copy the webhook signing secret and add to `.env`:
```
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Webhook Events Handled

- `checkout.session.completed` - Activates subscription after successful payment
- `invoice.paid` - Confirms active subscription
- `customer.subscription.deleted` - Deactivates subscription
- `invoice.payment_failed` - Deactivates subscription on payment failure
- `customer.subscription.updated` - Updates subscription status

## Debugging

### Check Upload Eligibility

```bash
curl http://localhost:8000/blueprint/users/testuser@example.com/can-upload
```

Response:
```json
{
  "can_upload": true,
  "has_subscription": false,
  "free_report_used": false
}
```

### View Logs

The upload endpoint logs detailed information:

```
🔍 Step 6: Checking upload eligibility
Upload eligibility for testuser@example.com: can_use_free=false, has_subscription=false, is_whitelisted=false, can_upload=false
Created Stripe checkout session for testuser@example.com: cs_test_...
```

## Whitelisted Emails

Emails in `DEV_VERIFIED_EMAILS` or when `DEBUG=true` bypass the paywall:

```python
# In app/config.py
DEV_VERIFIED_EMAILS = ["admin@example.com", "dev@example.com"]
```

## Production Checklist

Before going live:

1. [ ] Set `STRIPE_MODE=live` in production
2. [ ] Configure live Stripe keys
3. [ ] Update `FRONTEND_URL` to production URL
4. [ ] Set up webhook endpoint in Stripe dashboard
5. [ ] Configure webhook signing secret
6. [ ] Test the complete flow with a real card
7. [ ] Monitor Stripe dashboard for successful subscriptions

## Troubleshooting

### "Payment system error"
- Check Stripe API keys are correctly set
- Verify Stripe price ID exists
- Check Stripe dashboard for API errors

### Webhook not working
- Ensure webhook endpoint is accessible
- Verify webhook signing secret matches
- Check webhook logs in Stripe dashboard

### User can still upload after using free report
- Check if email is in `DEV_VERIFIED_EMAILS`
- Verify `DEBUG` is set to `false` in production
- Check database to ensure `free_report_used` is `true`
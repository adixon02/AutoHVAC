# NextAuth + Stripe Authentication Implementation Plan

## Overview
Transform the current basic NextAuth setup into a production-ready authentication system with Stripe integration.

## Current State
- NextAuth with magic links only
- In-memory storage (users lost on restart!)
- No password support
- No proper session management
- No Stripe integration

## Target State
- Database sessions with PostgreSQL
- Password + magic link authentication
- Email verification required
- Secure password reset flow
- Stripe subscription management
- Rate limiting and brute force protection
- Anonymous project claiming

## Implementation Phases

### Phase 1: Database Setup ✅
1. Install Prisma and adapters
2. Create production schema
3. Set up migrations

### Phase 2: Auth Configuration
1. Configure NextAuth with database sessions
2. Add password provider
3. Set up email verification
4. Implement password reset

### Phase 3: Security
1. Server-side password hashing
2. Rate limiting (5 attempts/minute)
3. Account lockout mechanism
4. CSRF protection
5. Session invalidation on password change

### Phase 4: Stripe Integration
1. Attach users to Stripe customers
2. Webhook handling with raw body
3. Subscription management
4. Paywall enforcement

### Phase 5: User Experience
1. Anonymous upload tracking
2. Project claiming on signup
3. Smart CTAs based on auth state
4. Smooth upgrade flow

## Key Security Requirements
- [ ] Passwords hashed server-side only (bcrypt, 12 rounds)
- [ ] Email verification not auto-granted
- [ ] Reset tokens hashed (SHA256)
- [ ] httpOnly cookies for anonymous tracking
- [ ] Database sessions (not JWT)
- [ ] Cookie domain only in production
- [ ] CSRF on custom endpoints
- [ ] Login rate limiting per email+IP

## Environment Variables Needed
```env
# NextAuth
NEXTAUTH_URL=https://autohvac.ai
NEXTAUTH_SECRET=<generate-with-openssl-rand-base64-32>

# Email
EMAIL_SERVER=smtp://...
EMAIL_FROM=noreply@autohvac.ai

# Database
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Stripe
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
NEXT_PUBLIC_STRIPE_KEY=pk_...
STRIPE_PRICE_ID=price_...
```

## Testing Checklist
- [ ] Sign up with password
- [ ] Sign up with magic link
- [ ] Email verification flow
- [ ] Password reset flow
- [ ] Anonymous upload → signup → claim
- [ ] Free report → paywall → upgrade
- [ ] Stripe webhook processing
- [ ] Rate limiting works
- [ ] Account lockout works
- [ ] Session invalidation on password change

## Next Steps
1. Install dependencies
2. Set up Prisma schema
3. Configure NextAuth
4. Implement auth APIs
5. Add Stripe integration
6. Test complete flow
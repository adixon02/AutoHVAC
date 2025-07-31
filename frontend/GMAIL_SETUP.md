# Gmail Setup for Magic Links

## Quick Setup (5 minutes)

### 1. Enable 2-Factor Authentication
- Go to https://myaccount.google.com/security
- Click on "2-Step Verification"
- Follow the setup process

### 2. Generate App Password
- After 2FA is enabled, go to https://myaccount.google.com/apppasswords
- Select "Mail" from the dropdown
- Select "Other" and type "AutoHVAC"
- Click "Generate"
- Copy the 16-character password (spaces don't matter)

### 3. Configure .env.local
```bash
# Create .env.local file in frontend directory
cp .env.local.example .env.local
```

Then add these values:
```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# NextAuth Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key-here

# Email Configuration
EMAIL_SERVER_HOST=smtp.gmail.com
EMAIL_SERVER_PORT=587
EMAIL_SERVER_USER=your-gmail@gmail.com
EMAIL_SERVER_PASSWORD=xxxx xxxx xxxx xxxx  # Your app password
EMAIL_FROM=AutoHVAC <noreply@autohvac.com>
```

### 4. Generate NextAuth Secret
```bash
# Run this command to generate a secure secret
openssl rand -base64 32
```

## Testing Email

1. Start the app and go to sign in
2. Enter your email
3. Check your inbox (and spam folder)
4. Click the magic link

## Troubleshooting

If emails aren't sending:
1. Check the console for errors
2. Verify your app password is correct
3. Make sure 2FA is enabled
4. Try the "Less secure app access" if needed (not recommended)

## Fallback Option

If email setup fails, users can still:
- Click "Continue without magic link (MVP mode)"
- This sets a cookie and lets them in
- Perfect for MVP testing without email hassle
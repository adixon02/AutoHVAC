import nodemailer from 'nodemailer'
import { createHash } from 'crypto'

// Create reusable transporter
const transporter = nodemailer.createTransport({
  host: process.env.EMAIL_SERVER_HOST || 'smtp.gmail.com',
  port: Number(process.env.EMAIL_SERVER_PORT) || 587,
  secure: false, // true for 465, false for other ports
  auth: {
    user: process.env.EMAIL_SERVER_USER,
    pass: process.env.EMAIL_SERVER_PASSWORD,
  },
})

const from = process.env.EMAIL_FROM || 'AutoHVAC <noreply@autohvac.ai>'
const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000'

/**
 * Send email verification link
 */
export async function sendVerificationEmail({
  to,
  token
}: {
  to: string
  token: string
}) {
  const verifyUrl = `${baseUrl}/auth/verify-email?token=${token}&email=${encodeURIComponent(to)}`
  
  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Verify your email</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }
          .content { background: white; padding: 30px; border: 1px solid #e5e7eb; border-radius: 0 0 10px 10px; }
          .button { display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; font-weight: 600; margin: 20px 0; }
          .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 14px; color: #6b7280; }
          .warning { background: #fef3c7; border: 1px solid #fbbf24; padding: 12px; border-radius: 5px; margin-top: 20px; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>Welcome to AutoHVAC!</h1>
          </div>
          <div class="content">
            <h2>Verify your email address</h2>
            <p>Thanks for signing up! Please verify your email address by clicking the button below:</p>
            
            <div style="text-align: center;">
              <a href="${verifyUrl}" class="button">Verify Email Address</a>
            </div>
            
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; background: #f3f4f6; padding: 10px; border-radius: 5px; font-size: 14px;">
              ${verifyUrl}
            </p>
            
            <div class="warning">
              <strong>⚠️ This link expires in 24 hours</strong><br>
              If you didn't create an account with AutoHVAC, you can safely ignore this email.
            </div>
            
            <div class="footer">
              <p>Best regards,<br>The AutoHVAC Team</p>
              <p style="font-size: 12px; color: #9ca3af;">
                This is an automated message from AutoHVAC. Please do not reply to this email.
              </p>
            </div>
          </div>
        </div>
      </body>
    </html>
  `
  
  const text = `
Welcome to AutoHVAC!

Please verify your email address by visiting this link:
${verifyUrl}

This link expires in 24 hours.

If you didn't create an account with AutoHVAC, you can safely ignore this email.

Best regards,
The AutoHVAC Team
  `.trim()
  
  await transporter.sendMail({
    from,
    to,
    subject: 'Verify your AutoHVAC account',
    text,
    html
  })
}

/**
 * Send password reset email
 */
export async function sendPasswordResetEmail({
  to,
  token
}: {
  to: string
  token: string
}) {
  const resetUrl = `${baseUrl}/auth/reset-password?token=${token}&email=${encodeURIComponent(to)}`
  
  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Reset your password</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }
          .content { background: white; padding: 30px; border: 1px solid #e5e7eb; border-radius: 0 0 10px 10px; }
          .button { display: inline-block; padding: 12px 24px; background: #f97316; color: white; text-decoration: none; border-radius: 5px; font-weight: 600; margin: 20px 0; }
          .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 14px; color: #6b7280; }
          .warning { background: #fee2e2; border: 1px solid #ef4444; padding: 12px; border-radius: 5px; margin-top: 20px; }
          .security { background: #f0fdf4; border: 1px solid #22c55e; padding: 12px; border-radius: 5px; margin-top: 20px; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>Password Reset Request</h1>
          </div>
          <div class="content">
            <h2>Reset your password</h2>
            <p>We received a request to reset your password. Click the button below to create a new password:</p>
            
            <div style="text-align: center;">
              <a href="${resetUrl}" class="button">Reset Password</a>
            </div>
            
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; background: #f3f4f6; padding: 10px; border-radius: 5px; font-size: 14px;">
              ${resetUrl}
            </p>
            
            <div class="warning">
              <strong>⏰ This link expires in 1 hour</strong><br>
              For security reasons, password reset links are only valid for a short time.
            </div>
            
            <div class="security">
              <strong>🔒 Security Notice</strong><br>
              If you didn't request this password reset, please ignore this email. Your password won't be changed unless you click the link above and create a new one.
            </div>
            
            <div class="footer">
              <p>Best regards,<br>The AutoHVAC Team</p>
              <p style="font-size: 12px; color: #9ca3af;">
                For security reasons, this link can only be used once. If you need to reset your password again, please request a new link.
              </p>
            </div>
          </div>
        </div>
      </body>
    </html>
  `
  
  const text = `
Password Reset Request

We received a request to reset your password. Visit this link to create a new password:
${resetUrl}

This link expires in 1 hour.

If you didn't request this password reset, please ignore this email. Your password won't be changed unless you click the link and create a new one.

Best regards,
The AutoHVAC Team
  `.trim()
  
  await transporter.sendMail({
    from,
    to,
    subject: 'Reset your AutoHVAC password',
    text,
    html
  })
}

/**
 * Send magic link email (for passwordless login)
 */
export async function sendMagicLinkEmail({
  to,
  url,
  token
}: {
  to: string
  url: string
  token: string
}) {
  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Sign in to AutoHVAC</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }
          .content { background: white; padding: 30px; border: 1px solid #e5e7eb; border-radius: 0 0 10px 10px; }
          .button { display: inline-block; padding: 12px 24px; background: #06b6d4; color: white; text-decoration: none; border-radius: 5px; font-weight: 600; margin: 20px 0; }
          .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 14px; color: #6b7280; }
          .code { background: #f3f4f6; padding: 15px; border-radius: 5px; font-size: 24px; font-weight: bold; text-align: center; letter-spacing: 2px; margin: 20px 0; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>Sign in to AutoHVAC</h1>
          </div>
          <div class="content">
            <h2>Your magic link is here!</h2>
            <p>Click the button below to sign in to your account:</p>
            
            <div style="text-align: center;">
              <a href="${url}" class="button">Sign In to AutoHVAC</a>
            </div>
            
            <p>Or use this verification code:</p>
            <div class="code">${token.slice(0, 6).toUpperCase()}</div>
            
            <p>Or copy and paste this link:</p>
            <p style="word-break: break-all; background: #f3f4f6; padding: 10px; border-radius: 5px; font-size: 14px;">
              ${url}
            </p>
            
            <div class="footer">
              <p><strong>This link expires in 24 hours</strong></p>
              <p style="font-size: 12px; color: #9ca3af;">
                If you didn't request this email, you can safely ignore it.
              </p>
            </div>
          </div>
        </div>
      </body>
    </html>
  `
  
  const text = `
Sign in to AutoHVAC

Click this link to sign in:
${url}

Or use this verification code: ${token.slice(0, 6).toUpperCase()}

This link expires in 24 hours.

If you didn't request this email, you can safely ignore it.
  `.trim()
  
  await transporter.sendMail({
    from,
    to,
    subject: 'Sign in to AutoHVAC',
    text,
    html
  })
}

/**
 * Send welcome email after successful verification
 */
export async function sendWelcomeEmail({
  to,
  name
}: {
  to: string
  name?: string | null
}) {
  const dashboardUrl = `${baseUrl}/dashboard`
  
  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Welcome to AutoHVAC!</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }
          .content { background: white; padding: 30px; border: 1px solid #e5e7eb; border-radius: 0 0 10px 10px; }
          .button { display: inline-block; padding: 12px 24px; background: #10b981; color: white; text-decoration: none; border-radius: 5px; font-weight: 600; margin: 20px 0; }
          .feature { padding: 15px; background: #f9fafb; border-radius: 5px; margin: 10px 0; }
          .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 14px; color: #6b7280; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>🎉 Welcome to AutoHVAC!</h1>
          </div>
          <div class="content">
            <h2>Hi${name ? ` ${name}` : ''}!</h2>
            <p>Your email has been verified and your account is ready to use.</p>
            
            <div class="feature">
              <strong>📋 Your First Free Report</strong><br>
              Upload a blueprint to get your first HVAC load calculation report completely free!
            </div>
            
            <div class="feature">
              <strong>🚀 Quick & Accurate</strong><br>
              Get professional ACCA Manual J calculations in minutes, not hours.
            </div>
            
            <div class="feature">
              <strong>💳 Flexible Pricing</strong><br>
              After your free report, get unlimited access with our affordable subscription.
            </div>
            
            <div style="text-align: center;">
              <a href="${dashboardUrl}" class="button">Go to Dashboard</a>
            </div>
            
            <div class="footer">
              <p>Need help? Reply to this email and we'll be happy to assist!</p>
              <p>Best regards,<br>The AutoHVAC Team</p>
            </div>
          </div>
        </div>
      </body>
    </html>
  `
  
  const text = `
Welcome to AutoHVAC!

Hi${name ? ` ${name}` : ''}!

Your email has been verified and your account is ready to use.

What's included:
- Your first HVAC load calculation report is FREE
- Quick & accurate ACCA Manual J calculations
- Professional reports in minutes

Get started: ${dashboardUrl}

Need help? Reply to this email and we'll be happy to assist!

Best regards,
The AutoHVAC Team
  `.trim()
  
  await transporter.sendMail({
    from,
    to,
    subject: '🎉 Welcome to AutoHVAC!',
    text,
    html
  })
}

/**
 * Send notification email (generic)
 */
export async function sendNotificationEmail({
  to,
  subject,
  heading,
  content,
  ctaText,
  ctaUrl
}: {
  to: string
  subject: string
  heading: string
  content: string
  ctaText?: string
  ctaUrl?: string
}) {
  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>${subject}</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }
          .container { max-width: 600px; margin: 0 auto; padding: 20px; }
          .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }
          .content { background: white; padding: 30px; border: 1px solid #e5e7eb; border-radius: 0 0 10px 10px; }
          .button { display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; font-weight: 600; margin: 20px 0; }
          .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 14px; color: #6b7280; }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>${heading}</h1>
          </div>
          <div class="content">
            ${content}
            
            ${ctaText && ctaUrl ? `
              <div style="text-align: center;">
                <a href="${ctaUrl}" class="button">${ctaText}</a>
              </div>
            ` : ''}
            
            <div class="footer">
              <p>Best regards,<br>The AutoHVAC Team</p>
            </div>
          </div>
        </div>
      </body>
    </html>
  `
  
  await transporter.sendMail({
    from,
    to,
    subject,
    html,
    text: content.replace(/<[^>]*>/g, '') // Strip HTML for text version
  })
}
import bcrypt from 'bcryptjs'
import crypto from 'crypto'
import { prisma } from '@/lib/prisma'
import { createAuditLog } from './audit'

/**
 * Hash a password using bcrypt with 12 rounds
 */
export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 12)
}

/**
 * Verify a password against a hash
 */
export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash)
}

/**
 * Validate password strength
 */
export function validatePasswordStrength(password: string): {
  isValid: boolean
  errors: string[]
} {
  const errors: string[] = []
  
  if (password.length < 8) {
    errors.push('Password must be at least 8 characters long')
  }
  
  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter')
  }
  
  if (!/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter')
  }
  
  if (!/[0-9]/.test(password)) {
    errors.push('Password must contain at least one number')
  }
  
  if (!/[^A-Za-z0-9]/.test(password)) {
    errors.push('Password must contain at least one special character')
  }
  
  // Check for common weak passwords
  const commonPasswords = [
    'password', 'Password1!', '12345678', 'qwerty123',
    'admin123', 'letmein', 'welcome123'
  ]
  
  if (commonPasswords.some(weak => password.toLowerCase().includes(weak.toLowerCase()))) {
    errors.push('Password is too common or weak')
  }
  
  return {
    isValid: errors.length === 0,
    errors
  }
}

/**
 * Generate a secure random token
 */
export function generateSecureToken(length: number = 32): string {
  return crypto.randomBytes(length).toString('hex')
}

/**
 * Hash a token using SHA256 (for storage)
 */
export function hashToken(token: string): string {
  return crypto.createHash('sha256').update(token).digest('hex')
}

/**
 * Create a password reset token
 */
export async function createPasswordResetToken(email: string): Promise<{
  token: string
  expires: Date
}> {
  // Generate random token
  const token = generateSecureToken(32)
  const tokenHash = hashToken(token)
  
  // Expire in 1 hour
  const expires = new Date(Date.now() + 60 * 60 * 1000)
  
  // Invalidate any existing tokens for this email
  await prisma.passwordResetToken.updateMany({
    where: {
      email: email.toLowerCase(),
      used: false,
      expires: { gt: new Date() }
    },
    data: {
      used: true
    }
  })
  
  // Create new token
  await prisma.passwordResetToken.create({
    data: {
      email: email.toLowerCase(),
      tokenHash,
      expires
    }
  })
  
  return { token, expires }
}

/**
 * Verify and use a password reset token
 */
export async function verifyPasswordResetToken(
  token: string,
  email: string
): Promise<boolean> {
  const tokenHash = hashToken(token)
  
  const resetToken = await prisma.passwordResetToken.findFirst({
    where: {
      tokenHash,
      email: email.toLowerCase(),
      used: false,
      expires: { gt: new Date() }
    }
  })
  
  if (!resetToken) {
    return false
  }
  
  // Mark token as used
  await prisma.passwordResetToken.update({
    where: { id: resetToken.id },
    data: { used: true }
  })
  
  return true
}

/**
 * Reset user password with token
 */
export async function resetPasswordWithToken(
  token: string,
  email: string,
  newPassword: string,
  ip?: string,
  userAgent?: string
): Promise<{ success: boolean; error?: string }> {
  // Validate password strength
  const validation = validatePasswordStrength(newPassword)
  if (!validation.isValid) {
    return {
      success: false,
      error: validation.errors[0]
    }
  }
  
  // Verify token
  const tokenValid = await verifyPasswordResetToken(token, email)
  if (!tokenValid) {
    return {
      success: false,
      error: 'Invalid or expired reset token'
    }
  }
  
  // Hash new password
  const hashedPassword = await hashPassword(newPassword)
  
  // Update user password
  const user = await prisma.user.update({
    where: { email: email.toLowerCase() },
    data: {
      password: hashedPassword,
      // Reset security flags
      failedLoginAttempts: 0,
      lockedUntil: null
    }
  })
  
  // Invalidate all existing sessions for this user
  await prisma.session.deleteMany({
    where: { userId: user.id }
  })
  
  // Create audit log
  await createAuditLog({
    userId: user.id,
    event: 'password_reset',
    metadata: { method: 'token' },
    ip,
    userAgent
  })
  
  return { success: true }
}

/**
 * Change user password (requires current password)
 */
export async function changePassword(
  userId: string,
  currentPassword: string,
  newPassword: string,
  ip?: string,
  userAgent?: string
): Promise<{ success: boolean; error?: string }> {
  // Get user
  const user = await prisma.user.findUnique({
    where: { id: userId }
  })
  
  if (!user?.password) {
    return {
      success: false,
      error: 'User not found or no password set'
    }
  }
  
  // Verify current password
  const isValid = await verifyPassword(currentPassword, user.password)
  if (!isValid) {
    await createAuditLog({
      userId,
      event: 'password_change_failed',
      metadata: { reason: 'invalid_current_password' },
      ip,
      userAgent
    })
    return {
      success: false,
      error: 'Current password is incorrect'
    }
  }
  
  // Validate new password
  const validation = validatePasswordStrength(newPassword)
  if (!validation.isValid) {
    return {
      success: false,
      error: validation.errors[0]
    }
  }
  
  // Check password isn't the same
  if (await verifyPassword(newPassword, user.password)) {
    return {
      success: false,
      error: 'New password must be different from current password'
    }
  }
  
  // Hash and update password
  const hashedPassword = await hashPassword(newPassword)
  
  await prisma.user.update({
    where: { id: userId },
    data: { password: hashedPassword }
  })
  
  // Invalidate all other sessions (keep current session)
  // This would need the current session ID passed in
  await prisma.session.deleteMany({
    where: {
      userId,
      // We'd exclude current session here if we had the ID
    }
  })
  
  await createAuditLog({
    userId,
    event: 'password_change',
    metadata: { invalidated_sessions: true },
    ip,
    userAgent
  })
  
  return { success: true }
}
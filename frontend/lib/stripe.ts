import Stripe from 'stripe'
import { prisma } from '@/lib/prisma'
import { createAuditLog } from '@/lib/security/audit'

// Initialize Stripe
export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2025-07-30.basil',
  typescript: true,
})

// Price IDs from environment
export const SUBSCRIPTION_PRICE_ID = process.env.STRIPE_PRICE_ID!
export const STRIPE_WEBHOOK_SECRET = process.env.STRIPE_WEBHOOK_SECRET!

/**
 * Create or get Stripe customer for a user
 */
export async function createOrGetStripeCustomer(
  userId: string
): Promise<string> {
  const user = await prisma.user.findUnique({
    where: { id: userId }
  })
  
  if (!user) {
    throw new Error('User not found')
  }
  
  // Return existing customer ID if available
  if (user.stripeCustomerId) {
    return user.stripeCustomerId
  }
  
  // Create new Stripe customer
  const customer = await stripe.customers.create({
    email: user.email,
    name: user.name || undefined,
    metadata: {
      userId: user.id,
      environment: process.env.NODE_ENV || 'development'
    }
  })
  
  // Update user with customer ID
  await prisma.user.update({
    where: { id: userId },
    data: { stripeCustomerId: customer.id }
  })
  
  await createAuditLog({
    userId,
    event: 'stripe_customer_created',
    metadata: { customerId: customer.id },
    ip: null,
    userAgent: null
  })
  
  return customer.id
}

/**
 * Create a checkout session for subscription
 */
export async function createCheckoutSession({
  userId,
  successUrl,
  cancelUrl,
  priceId = SUBSCRIPTION_PRICE_ID
}: {
  userId: string
  successUrl: string
  cancelUrl: string
  priceId?: string
}): Promise<string> {
  const customerId = await createOrGetStripeCustomer(userId)
  
  const session = await stripe.checkout.sessions.create({
    customer: customerId,
    payment_method_types: ['card'],
    line_items: [
      {
        price: priceId,
        quantity: 1,
      },
    ],
    mode: 'subscription',
    success_url: successUrl,
    cancel_url: cancelUrl,
    subscription_data: {
      metadata: {
        userId,
        environment: process.env.NODE_ENV || 'development'
      }
    },
    metadata: {
      userId
    },
    allow_promotion_codes: true,
    billing_address_collection: 'auto',
    customer_update: {
      address: 'auto'
    }
  })
  
  await createAuditLog({
    userId,
    event: 'checkout_session_created',
    metadata: { 
      sessionId: session.id,
      priceId 
    },
    ip: null,
    userAgent: null
  })
  
  return session.url || ''
}

/**
 * Create a billing portal session
 */
export async function createBillingPortalSession({
  userId,
  returnUrl
}: {
  userId: string
  returnUrl: string
}): Promise<string> {
  const user = await prisma.user.findUnique({
    where: { id: userId }
  })
  
  if (!user?.stripeCustomerId) {
    throw new Error('No Stripe customer found')
  }
  
  const session = await stripe.billingPortal.sessions.create({
    customer: user.stripeCustomerId,
    return_url: returnUrl,
  })
  
  await createAuditLog({
    userId,
    event: 'billing_portal_accessed',
    metadata: { sessionId: session.id },
    ip: null,
    userAgent: null
  })
  
  return session.url
}

/**
 * Cancel a subscription
 */
export async function cancelSubscription(
  userId: string,
  immediately: boolean = false
): Promise<void> {
  const subscription = await prisma.subscription.findFirst({
    where: {
      userId,
      status: { in: ['active', 'trialing'] }
    }
  })
  
  if (!subscription) {
    throw new Error('No active subscription found')
  }
  
  // Cancel in Stripe
  const updatedSubscription = await stripe.subscriptions.update(
    subscription.stripeSubscriptionId,
    {
      cancel_at_period_end: !immediately,
      ...(immediately && { cancel_at: 'now' })
    }
  )
  
  // Update database
  await prisma.subscription.update({
    where: { id: subscription.id },
    data: {
      cancelAtPeriodEnd: !immediately,
      status: immediately ? 'canceled' : subscription.status,
      updatedAt: new Date()
    }
  })
  
  await createAuditLog({
    userId,
    event: 'subscription_canceled',
    metadata: { 
      subscriptionId: subscription.stripeSubscriptionId,
      immediately 
    },
    ip: null,
    userAgent: null
  })
}

/**
 * Sync subscription from Stripe webhook
 */
export async function syncSubscriptionFromStripe(
  stripeSubscription: Stripe.Subscription
): Promise<void> {
  const userId = stripeSubscription.metadata.userId
  
  if (!userId) {
    console.error('No userId in subscription metadata:', stripeSubscription.id)
    return
  }
  
  // Check if subscription exists
  const existingSubscription = await prisma.subscription.findUnique({
    where: { stripeSubscriptionId: stripeSubscription.id }
  })
  
  const subscriptionData = {
    userId,
    stripeCustomerId: stripeSubscription.customer as string,
    stripeSubscriptionId: stripeSubscription.id,
    stripePriceId: stripeSubscription.items.data[0]?.price.id,
    status: stripeSubscription.status,
    currentPeriodEnd: new Date(stripeSubscription.current_period_end * 1000),
    cancelAtPeriodEnd: stripeSubscription.cancel_at_period_end,
  }
  
  if (existingSubscription) {
    // Update existing
    await prisma.subscription.update({
      where: { id: existingSubscription.id },
      data: {
        ...subscriptionData,
        updatedAt: new Date()
      }
    })
  } else {
    // Create new
    await prisma.subscription.create({
      data: subscriptionData
    })
  }
  
  await createAuditLog({
    userId,
    event: 'subscription_synced',
    metadata: { 
      subscriptionId: stripeSubscription.id,
      status: stripeSubscription.status 
    },
    ip: null,
    userAgent: null
  })
}

/**
 * Check if user has active subscription
 */
export async function hasActiveSubscription(userId: string): Promise<boolean> {
  const subscription = await prisma.subscription.findFirst({
    where: {
      userId,
      status: { in: ['active', 'trialing'] },
      currentPeriodEnd: { gt: new Date() }
    }
  })
  
  return !!subscription
}

/**
 * Check if user can upload (free report or subscription)
 */
export async function canUserUpload(userId: string | null): Promise<{
  allowed: boolean
  reason?: string
  requiresPayment?: boolean
}> {
  // Anonymous users can always upload (will hit paywall later)
  if (!userId) {
    return { allowed: true }
  }
  
  const user = await prisma.user.findUnique({
    where: { id: userId }
  })
  
  if (!user) {
    return { 
      allowed: false, 
      reason: 'User not found' 
    }
  }
  
  // Check for active subscription
  const hasSubscription = await hasActiveSubscription(userId)
  if (hasSubscription) {
    return { allowed: true }
  }
  
  // Check if free report is available
  if (!user.freeReportUsed) {
    return { allowed: true }
  }
  
  // User needs to pay
  return {
    allowed: false,
    reason: 'Payment required',
    requiresPayment: true
  }
}

/**
 * Mark free report as used
 */
export async function markFreeReportUsed(userId: string): Promise<void> {
  await prisma.user.update({
    where: { id: userId },
    data: { freeReportUsed: true }
  })
  
  await createAuditLog({
    userId,
    event: 'free_report_used',
    metadata: {},
    ip: null,
    userAgent: null
  })
}

/**
 * Get subscription details for user
 */
export async function getUserSubscription(userId: string) {
  const subscription = await prisma.subscription.findFirst({
    where: {
      userId,
      status: { in: ['active', 'trialing'] }
    },
    orderBy: { createdAt: 'desc' }
  })
  
  if (!subscription) {
    return null
  }
  
  // Get additional details from Stripe if needed
  let stripeDetails = null
  try {
    if (subscription.stripeSubscriptionId) {
      const stripeSubscription = await stripe.subscriptions.retrieve(
        subscription.stripeSubscriptionId
      )
      stripeDetails = {
        cancelAt: stripeSubscription.cancel_at 
          ? new Date(stripeSubscription.cancel_at * 1000) 
          : null,
        trialEnd: stripeSubscription.trial_end
          ? new Date(stripeSubscription.trial_end * 1000)
          : null,
        nextInvoiceAmount: null as number | null
      }
      
      // Get upcoming invoice for next payment amount
      if (stripeSubscription.status === 'active') {
        try {
          const upcomingInvoice = await stripe.invoices.retrieveUpcoming({
            customer: stripeSubscription.customer as string
          })
          stripeDetails.nextInvoiceAmount = upcomingInvoice.amount_due / 100
        } catch (e) {
          // No upcoming invoice
        }
      }
    }
  } catch (error) {
    console.error('Error fetching Stripe details:', error)
  }
  
  return {
    ...subscription,
    stripeDetails
  }
}
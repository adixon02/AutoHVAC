import { NextApiRequest, NextApiResponse } from 'next'
import { buffer } from 'micro'
import Stripe from 'stripe'
import { stripe, STRIPE_WEBHOOK_SECRET, syncSubscriptionFromStripe } from '@/lib/stripe'
import { prisma } from '@/lib/prisma'
import { createAuditLog } from '@/lib/security/audit'

// Disable body parsing - we need the raw body for webhook verification
export const config = {
  api: {
    bodyParser: false,
  },
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }
  
  const buf = await buffer(req)
  const sig = req.headers['stripe-signature']
  
  if (!sig) {
    console.error('Missing stripe-signature header')
    return res.status(400).json({ error: 'Missing stripe-signature header' })
  }
  
  let event: Stripe.Event
  
  try {
    event = stripe.webhooks.constructEvent(
      buf.toString(),
      sig,
      STRIPE_WEBHOOK_SECRET
    )
  } catch (err) {
    console.error('Webhook signature verification failed:', err)
    await createAuditLog({
      event: 'stripe_webhook_failed',
      metadata: { 
        error: err instanceof Error ? err.message : 'Unknown error',
        signature: typeof sig === 'string' ? sig.substring(0, 20) + '...' : 'invalid'
      },
      ip: req.headers['x-forwarded-for'] as string || 'unknown',
      userAgent: req.headers['user-agent'] || ''
    })
    return res.status(400).json({ error: 'Webhook signature verification failed' })
  }
  
  // Log webhook received
  console.log(`Stripe webhook received: ${event.type}`)
  
  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.Checkout.Session
        
        // Session completed - subscription should be created
        if (session.mode === 'subscription' && session.subscription) {
          const subscription = await stripe.subscriptions.retrieve(
            session.subscription as string
          )
          await syncSubscriptionFromStripe(subscription)
          
          // Mark free report as used if this is their first subscription
          if (session.metadata?.userId) {
            const user = await prisma.user.findUnique({
              where: { id: session.metadata.userId }
            })
            if (user && !user.freeReportUsed) {
              await prisma.user.update({
                where: { id: user.id },
                data: { freeReportUsed: true }
              })
            }
          }
        }
        break
      }
      
      case 'customer.subscription.created':
      case 'customer.subscription.updated': {
        const subscription = event.data.object as Stripe.Subscription
        await syncSubscriptionFromStripe(subscription)
        break
      }
      
      case 'customer.subscription.deleted': {
        const subscription = event.data.object as Stripe.Subscription
        
        // Mark subscription as canceled
        await prisma.subscription.updateMany({
          where: { stripeSubscriptionId: subscription.id },
          data: { 
            status: 'canceled',
            updatedAt: new Date()
          }
        })
        
        if (subscription.metadata.userId) {
          await createAuditLog({
            userId: subscription.metadata.userId,
            event: 'subscription_deleted',
            metadata: { subscriptionId: subscription.id },
            ip: null,
            userAgent: null
          })
        }
        break
      }
      
      case 'invoice.payment_succeeded': {
        const invoice = event.data.object as Stripe.Invoice
        
        // In Stripe API 2025-07-30.basil, subscription is under parent field
        const subscriptionId = (invoice as any).parent?.subscription || (invoice as any).subscription
        if (subscriptionId && invoice.billing_reason === 'subscription_cycle') {
          // Regular subscription payment
          const subscription = await stripe.subscriptions.retrieve(
            subscriptionId as string
          )
          await syncSubscriptionFromStripe(subscription)
          
          if (subscription.metadata.userId) {
            await createAuditLog({
              userId: subscription.metadata.userId,
              event: 'payment_succeeded',
              metadata: { 
                invoiceId: invoice.id,
                amount: invoice.amount_paid / 100
              },
              ip: null,
              userAgent: null
            })
          }
        }
        break
      }
      
      case 'invoice.payment_failed': {
        const invoice = event.data.object as Stripe.Invoice
        
        // In Stripe API 2025-07-30.basil, subscription is under parent field
        const subscriptionId = (invoice as any).parent?.subscription || (invoice as any).subscription
        if (subscriptionId) {
          const subscription = await stripe.subscriptions.retrieve(
            subscriptionId as string
          )
          
          // Update subscription status
          await prisma.subscription.updateMany({
            where: { stripeSubscriptionId: subscription.id },
            data: { 
              status: subscription.status,
              updatedAt: new Date()
            }
          })
          
          if (subscription.metadata.userId) {
            await createAuditLog({
              userId: subscription.metadata.userId,
              event: 'payment_failed',
              metadata: { 
                invoiceId: invoice.id,
                attemptCount: invoice.attempt_count,
                nextAttempt: invoice.next_payment_attempt
              },
              ip: null,
              userAgent: null
            })
            
            // TODO: Send payment failed email
          }
        }
        break
      }
      
      case 'customer.updated': {
        const customer = event.data.object as Stripe.Customer
        
        // Update user email if changed in Stripe
        if (customer.email && customer.metadata.userId) {
          const user = await prisma.user.findUnique({
            where: { id: customer.metadata.userId }
          })
          
          if (user && user.email !== customer.email) {
            // Log the change but don't auto-update (security)
            await createAuditLog({
              userId: user.id,
              event: 'stripe_email_mismatch',
              metadata: { 
                stripeEmail: customer.email,
                dbEmail: user.email
              },
              ip: null,
              userAgent: null
            })
          }
        }
        break
      }
      
      default:
        console.log(`Unhandled event type: ${event.type}`)
    }
    
    // Log successful processing
    await createAuditLog({
      event: 'stripe_webhook_processed',
      metadata: { 
        eventType: event.type,
        eventId: event.id
      },
      ip: req.headers['x-forwarded-for'] as string || 'unknown',
      userAgent: req.headers['user-agent'] || ''
    })
    
    return res.status(200).json({ received: true })
    
  } catch (error) {
    console.error('Error processing webhook:', error)
    
    await createAuditLog({
      event: 'stripe_webhook_error',
      metadata: { 
        eventType: event.type,
        error: error instanceof Error ? error.message : 'Unknown error'
      },
      ip: req.headers['x-forwarded-for'] as string || 'unknown',
      userAgent: req.headers['user-agent'] || ''
    })
    
    // Return 200 to acknowledge receipt even if processing failed
    // This prevents Stripe from retrying
    return res.status(200).json({ 
      received: true, 
      error: 'Processing failed but acknowledged' 
    })
  }
}
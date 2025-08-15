# AutoHVAC Frontend Architecture

A Next.js application providing AI-powered HVAC load calculations with a freemium SaaS business model.

## 🚀 Core Features

- **AI-Powered Manual J Calculations** - Upload blueprints, get professional ACCA reports in 60 seconds
- **Freemium Lead-to-User Pipeline** - Email capture → Account gate → Password creation → Paywall
- **NextAuth JWT Authentication** - Seamless session management with backend integration
- **Stripe Subscription Management** - Professional billing with upgrade flows
- **SEO-Optimized Blog Platform** - Expert content for HVAC professionals

## 📁 Directory Structure

```
frontend/
├── components/           # Reusable UI components
├── pages/               # Next.js pages and API routes
├── lib/                 # Utilities and shared logic
├── hooks/               # Custom React hooks
├── types/               # TypeScript type definitions
├── styles/              # Global CSS and Tailwind
└── public/              # Static assets
```

## 🧭 Pages & Routing

### Core User Pages

#### `/` - Homepage
**Responsibility**: Landing page with conversion optimization
- **Components**: Hero, FeatureSteps, ROICalculator, ContractorFAQ, Testimonials
- **Purpose**: Drive conversions with compelling value props and instant upload CTA
- **SEO**: Primary target for "AI Manual J calculator" and related keywords
- **Conversion**: File drop → Upload modal → Email capture → Processing

#### `/analyzing/[jobId]` - Processing & Results Page
**Responsibility**: Real-time job processing with account gate
- **Components**: ProcessingStages, CompletionAccountGate, ResultsPreview
- **Purpose**: Show processing progress and trigger account creation at peak engagement
- **Flow**: Processing animation → Account gate modal → Password creation → Unlock report
- **Critical**: This is where leads convert to users

#### `/dashboard` - User Project Hub
**Responsibility**: Authenticated user's project management
- **Components**: ProjectCard, MultiStepUpload
- **Purpose**: View all reports, download PDFs, launch new analyses
- **Auth Required**: Yes
- **Features**: Project history, status tracking, re-upload functionality

#### `/upgrade` - Subscription Paywall
**Responsibility**: Stripe checkout and subscription management
- **Components**: Pricing plans, feature comparison, billing portal access
- **Purpose**: Convert free users to paid subscribers
- **Integration**: Stripe Checkout Session API
- **Flow**: Plan selection → Stripe checkout → Success redirect

### Authentication Pages

#### `/auth/signin` - User Login
**Responsibility**: NextAuth credentials authentication
- **Purpose**: Login with email/password for existing users
- **Integration**: NextAuth providers, backend JWT tokens
- **Flow**: Email/password → Backend auth → Session creation

#### `/auth/signup` - User Registration
**Responsibility**: Direct account creation (alternative to lead conversion)
- **Purpose**: Traditional signup flow for users who want accounts upfront
- **Flow**: Email/password → Backend user creation → Auto-login

#### `/auth/verify` - Email Verification
**Responsibility**: Email confirmation handling
- **Purpose**: Verify email addresses for enhanced security
- **Flow**: Email link click → Verification → Dashboard redirect

### Payment Pages

#### `/payment/success` - Post-Purchase Experience
**Responsibility**: Stripe payment confirmation and onboarding
- **Purpose**: Welcome paid users, explain features, guide to dashboard
- **Flow**: Stripe redirect → Success message → Dashboard CTA

#### `/payment/cancel` - Payment Cancellation
**Responsibility**: Handle cancelled Stripe sessions
- **Purpose**: Recover cancelled payments with alternative offers
- **Flow**: Stripe redirect → Retry options → Support contact

### Content Pages

#### `/blog` - SEO Content Hub
**Responsibility**: Educational content for HVAC professionals
- **Purpose**: Drive organic traffic, establish expertise, support SEO
- **Content**: Manual J guides, AC sizing, load calculation best practices
- **Structure**: Featured posts, categories, search optimization

#### `/blog/[slug]` - Individual Blog Posts
**Responsibility**: Long-form educational content
- **Purpose**: Rank for specific HVAC keywords, drive qualified traffic
- **Features**: Rich snippets, schema markup, social sharing
- **Examples**: "AC Tonnage Calculator", "Manual J vs Rule of Thumb"

#### `/account` - User Profile Management
**Responsibility**: Account settings and profile updates
- **Purpose**: User data management, subscription details
- **Features**: Profile editing, email preferences, account deletion

#### `/billing` - Subscription Management
**Responsibility**: Stripe billing portal integration
- **Purpose**: Self-service subscription management
- **Features**: Plan changes, payment methods, billing history

## 🧩 Key Components

### 🔄 Conversion Components

#### `MultiStepUpload`
**Purpose**: Primary conversion funnel - file upload to email capture
**Responsibility**: 8-step guided upload process
- Step 1-7: Building details collection
- Step 8: Email capture (critical conversion point)
- **Integration**: FormData → Backend upload → Job processing

#### `CompletionAccountGate`
**Purpose**: Convert processing completion into account creation
**Responsibility**: Full-screen account creation modal with blurred report preview
- **Timing**: Appears when job status = "completed"
- **Design**: Compelling UX with feature bullets and urgency
- **Flow**: Password creation → convertLeadToUser API → NextAuth login

#### `PaywallModal`
**Purpose**: Convert free users to paid subscribers
**Responsibility**: Feature-limited experience with upgrade prompts
- **Triggers**: Free report used, premium features accessed
- **Design**: Feature comparison, pricing tiers
- **Integration**: Stripe Checkout API

### 🎨 UI Components

#### `Hero`
**Purpose**: Above-fold conversion optimization
**Responsibility**: Primary value prop and instant upload CTA
- **Design**: Bold headlines, social proof, file drop zone
- **CTA**: "Get Started" → Upload modal

#### `ROICalculator`
**Purpose**: Interactive engagement and value demonstration
**Responsibility**: Calculate time/cost savings vs traditional methods
- **Logic**: Desktop software (30+ min) vs AutoHVAC (60 sec)
- **Output**: Dollar savings, time savings, efficiency gains

#### `FeatureSteps`
**Purpose**: Explain the 3-step process
**Responsibility**: Visual walkthrough of upload → analyze → download
- **Design**: Icon-based steps with descriptions
- **Goal**: Reduce friction, increase conversion confidence

#### `ContractorFAQ`
**Purpose**: Address objections and build trust
**Responsibility**: Common questions about accuracy, pricing, file types
- **SEO**: Schema markup for FAQ rich snippets
- **Conversion**: Overcome hesitation, build authority

### 🔐 Authentication Components

#### `AuthProvider`
**Purpose**: NextAuth session management wrapper
**Responsibility**: Global authentication state
- **Integration**: NextAuth provider with JWT sessions
- **Storage**: Backend JWT tokens in session

#### `NavBar`
**Purpose**: Responsive navigation with auth state
**Responsibility**: Login/logout, user menu, mobile responsive
- **States**: Anonymous, authenticated, loading
- **Features**: User email display, quick actions

### 📊 Business Components

#### `ProjectCard`
**Purpose**: Display user's HVAC analysis projects
**Responsibility**: Project status, download links, metadata
- **Features**: PDF download, share functionality, re-run analysis
- **States**: Pending, completed, failed

#### `ResultsPreview`
**Purpose**: Show analysis results in dashboard
**Responsibility**: BTU calculations, room breakdowns, equipment sizing
- **Features**: Detailed metrics, professional formatting
- **Export**: PDF generation for sharing

## 🔌 API Routes

### Authentication Routes (`/api/auth/`)

#### `[...nextauth].ts`
**Purpose**: NextAuth configuration and session handling
**Responsibility**: JWT strategy, backend integration, session callbacks
**Providers**: Credentials (email/password)

#### `signup.ts`
**Purpose**: Proxy to backend signup endpoint
**Responsibility**: Forward signup requests, handle responses
**Flow**: Frontend → Next.js API → Backend → Response

### Stripe Routes (`/api/stripe/`)

#### `checkout.ts`
**Purpose**: Create Stripe Checkout sessions
**Responsibility**: Subscription plan selection, customer creation
**Flow**: Plan selection → Stripe session → Redirect to Stripe

#### `webhook.ts`
**Purpose**: Handle Stripe webhook events
**Responsibility**: Subscription updates, payment confirmations
**Security**: Webhook signature verification

#### `billing-portal.ts`
**Purpose**: Generate Stripe customer portal sessions
**Responsibility**: Self-service billing management
**Auth**: Requires authenticated user

### Job Routes (`/api/job/`)

#### `[jobId].ts`
**Purpose**: Get job status and results
**Responsibility**: Real-time job monitoring
**Flow**: Frontend polling → Backend job status → UI updates

## 🛠 Technical Architecture

### State Management
- **NextAuth Sessions**: JWT-based authentication
- **SWR**: Data fetching and caching
- **React useState**: Local component state
- **Cookies**: Email persistence, user preferences

### API Integration
- **api-client.ts**: Centralized backend communication
- **Type-safe**: Full TypeScript interfaces for all API calls
- **Error Handling**: Custom ApiError class with status codes
- **Authentication**: Automatic JWT token inclusion

### Styling
- **Tailwind CSS**: Utility-first styling
- **Mobile-First**: Responsive design patterns
- **Component-Scoped**: Modular CSS architecture
- **Dark Mode Ready**: Design system supports theme switching

### SEO Optimization
- **Next.js SSR**: Server-side rendering for all pages
- **Schema Markup**: Rich snippets for blog content
- **Meta Tags**: Dynamic SEO data per page
- **Sitemap**: Auto-generated XML sitemap
- **Robots.txt**: Search engine crawling directives

## 🔄 User Journey Flows

### Anonymous User Flow
1. **Landing** (`/`) → Upload modal → Email capture
2. **Processing** (`/analyzing/[jobId]`) → Account gate → Password creation
3. **Authenticated** (`/dashboard`) → Report access → Upgrade prompt

### Freemium Conversion Flow
1. **Upload** → Email-only analysis request
2. **Processing** → Real-time progress with HVAC facts
3. **Completion** → Full-screen account gate with blurred preview
4. **Account Creation** → Password → convertLeadToUser API → NextAuth login
5. **Report Access** → Full results → Future upload prompts

### Subscription Flow
1. **Free Report Used** → Paywall modal
2. **Plan Selection** (`/upgrade`) → Stripe checkout
3. **Payment** → Success page (`/payment/success`)
4. **Unlimited Access** → Dashboard with all features

## 🚀 Performance Features

### Core Web Vitals
- **Image Optimization**: Next.js automatic image optimization
- **Code Splitting**: Automatic route-based splitting
- **Preloading**: Critical resource preloading
- **Caching**: SWR data caching, service worker ready

### User Experience
- **Real-time Updates**: Job progress via polling
- **Optimistic UI**: Immediate feedback for user actions
- **Error Boundaries**: Graceful error handling
- **Loading States**: Skeleton screens and spinners

### SEO Performance
- **Server-Side Rendering**: All pages pre-rendered
- **Static Generation**: Blog posts and marketing pages
- **Meta Tags**: Dynamic, page-specific SEO data
- **Structured Data**: Schema markup for rich snippets

## 🔧 Environment Configuration

### Required Environment Variables
```bash
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key
STRIPE_PUBLISHABLE_KEY=pk_test_...
```

### Development vs Production
- **Local**: Points to localhost:8001 backend
- **Production**: Points to Render backend deployment
- **Stripe**: Test keys in development, live keys in production

## 📈 Business Logic

### Freemium Model
- **Free Tier**: 1 report per email address
- **Paid Tier**: Unlimited reports, premium features
- **Lead Capture**: Email-first, account creation at value delivery

### Conversion Optimization
- **Peak Engagement**: Account gate at analysis completion
- **Social Proof**: Testimonials, processing facts
- **Urgency**: Limited free access, immediate value
- **Friction Reduction**: Progressive disclosure, minimal required fields

This architecture is designed for scalable growth with a conversion-optimized freemium SaaS model targeting HVAC professionals.
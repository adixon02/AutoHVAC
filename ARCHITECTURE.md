# AutoHVAC System Architecture

## Overview
AutoHVAC follows a clean, single-source-of-truth architecture with clear separation of concerns between frontend and backend.

## Architecture Principles

### 1. Single Source of Truth
- **Backend** owns all business logic, data, and third-party integrations
- **Frontend** is purely a presentation layer
- No duplicate logic between frontend and backend
- All state management flows through the backend API

### 2. Security First
- Authentication handled by backend (JWT tokens)
- All validation happens on the backend (frontend validation is only for UX)
- Rate limiting and security checks in backend
- Frontend never directly accesses databases or third-party services

### 3. Type Safety
- Full TypeScript implementation
- Shared types between frontend and backend where possible
- API responses are strongly typed
- Proper error handling with typed error classes

## System Components

### Backend (FastAPI/Python)
**Responsibilities:**
- Business logic and rules
- Database operations (PostgreSQL via SQLAlchemy)
- Authentication & authorization (JWT)
- Third-party integrations:
  - Stripe (payments)
  - SendGrid (emails)
  - OpenAI (AI processing)
  - AWS S3 (file storage)
- Background jobs (Celery)
- Rate limiting and security
- API endpoints

**Key Technologies:**
- FastAPI for API framework
- SQLAlchemy for ORM
- Alembic for migrations
- Celery for background tasks
- Redis for caching/queuing
- JWT for authentication

### Frontend (Next.js/React)
**Responsibilities:**
- User interface
- Client-side routing
- Session management (NextAuth)
- API client for backend communication
- Form validation (UX only)
- File uploads (proxied to backend)

**Key Technologies:**
- Next.js 14 with App Router
- React 18
- TypeScript
- NextAuth for session management
- Tailwind CSS for styling
- SWR for data fetching

## API Architecture

### API Client (`/frontend/lib/api-client.ts`)
Centralized API client providing:
- Type-safe API calls
- Automatic authentication
- Error handling and retries
- Request/response transformation
- Loading states
- Custom error classes

### API Endpoints Structure

#### Authentication Flow
1. User signs up/logs in via frontend form
2. Frontend calls `/api/auth/signup` or `/api/auth/[...nextauth]`
3. These endpoints proxy to backend `/auth/signup` or `/auth/login`
4. Backend validates, creates user, returns JWT
5. Frontend stores JWT in NextAuth session
6. All subsequent API calls include JWT in Authorization header

#### Data Flow Example (File Upload)
1. User uploads file in frontend
2. Frontend sends to `/api/upload` with file
3. Frontend endpoint adds auth token, forwards to backend
4. Backend processes file, stores in S3, creates job
5. Backend returns job ID
6. Frontend polls job status
7. Backend completes processing, generates report
8. Frontend downloads report

## Database Architecture

### Backend Database (PostgreSQL)
- Users table (authentication, profile)
- Projects/Jobs table (HVAC calculations)
- Subscriptions table (Stripe integration)
- Rate limits table (security)
- Audit logs table (compliance)

### Frontend Database (PostgreSQL)
- NextAuth tables only (sessions)
- Eventually will be removed entirely

## Security Architecture

### Authentication
- JWT tokens issued by backend
- NextAuth manages sessions in frontend
- Token refresh handled automatically
- Secure HTTP-only cookies for session

### Authorization
- Role-based access control in backend
- API endpoints check user permissions
- Frontend shows/hides UI based on session

### Rate Limiting
- IP-based rate limiting in backend
- Per-endpoint limits
- Exponential backoff for repeated failures
- Temporary IP blocking for abuse

## Deployment Architecture

### Production Environment
- Frontend: Render (Node.js)
- Backend: Render (Python)
- Database: Render PostgreSQL
- Redis: Render Redis
- File Storage: AWS S3
- CDN: CloudFlare

### Environment Variables
- Frontend needs only:
  - `NEXT_PUBLIC_API_URL` (backend URL)
  - `NEXTAUTH_URL` (frontend URL)
  - `NEXTAUTH_SECRET` (session encryption)
  
- Backend handles all sensitive configs:
  - Database credentials
  - Stripe API keys
  - AWS credentials
  - SendGrid API key
  - OpenAI API key

## Migration Strategy

### Phase 1: Authentication (COMPLETED)
- ✅ Backend JWT authentication
- ✅ NextAuth using backend as provider
- ✅ Remove frontend user management

### Phase 2: Stripe Integration (COMPLETED)
- ✅ Backend handles all Stripe operations
- ✅ Frontend proxies to backend endpoints
- ✅ Webhook processing in backend

### Phase 3: Clean Architecture (IN PROGRESS)
- ✅ Create centralized API client
- ✅ Add proper TypeScript types
- 🔄 Migrate remaining endpoints
- 🔄 Remove unused dependencies

### Phase 4: Database Consolidation (PLANNED)
- Move NextAuth to backend
- Remove frontend database entirely
- Single database for entire system

## Best Practices

### Frontend Development
1. Use the API client for all backend calls
2. Handle errors gracefully with user feedback
3. Implement optimistic updates where appropriate
4. Use SWR for data fetching and caching
5. Keep components small and focused

### Backend Development
1. Validate all inputs
2. Use dependency injection
3. Implement proper logging
4. Write comprehensive tests
5. Document API endpoints

### API Design
1. RESTful conventions
2. Consistent error responses
3. Pagination for lists
4. Versioned endpoints
5. Comprehensive OpenAPI docs

## Monitoring & Observability

### Metrics to Track
- API response times
- Error rates by endpoint
- User signup/login rates
- Payment success rates
- Job completion times

### Logging Strategy
- Structured logging (JSON)
- Log levels: ERROR, WARNING, INFO, DEBUG
- Correlation IDs for request tracking
- Audit logs for compliance

## Future Enhancements

### Short Term
- [ ] WebSocket support for real-time updates
- [ ] Enhanced caching strategy
- [ ] API rate limit headers
- [ ] Request retry with exponential backoff

### Long Term
- [ ] GraphQL API option
- [ ] Microservices architecture
- [ ] Multi-region deployment
- [ ] Advanced analytics pipeline

## Development Workflow

### Local Development
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Testing Strategy
- Unit tests for business logic
- Integration tests for API endpoints
- E2E tests for critical user flows
- Load testing for performance

### Deployment Process
1. Push to GitHub
2. CI/CD runs tests
3. Auto-deploy to staging
4. Manual promotion to production
5. Monitor error rates
6. Rollback if needed

## Contact & Support

For questions about the architecture:
- Review this document first
- Check the API documentation
- Ask in the team Slack channel
- Create a GitHub issue for bugs

---

*Last Updated: January 2025*
*Version: 2.0*
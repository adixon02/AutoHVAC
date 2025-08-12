# AutoHVAC Coding Principles & Engineering Standards
**For Frontend & Backend Development**

## 🎯 Core Philosophy: WORLD-CLASS ENGINEERING ONLY

### The Three Pillars of Excellence
1. **NO BAND-AID FIXES EVER** - Address root causes, not symptoms
2. **PERFORMANCE IS A FEATURE** - Fast, efficient, scalable code
3. **USER EXPERIENCE IS SACRED** - Every interaction should delight

### The Golden Rule
**Every line of code must be production-ready from day one.**

Before implementing ANY solution, you MUST:
1. **Identify the ROOT CAUSE** - Why is this happening?
2. **Design the OPTIMAL solution** - Not just working, but excellent
3. **Implement with ZERO compromises** - Clean, efficient, maintainable
4. **Validate THOROUGHLY** - Test edge cases, performance, UX

## ❌ NEVER DO THIS (Band-Aid Fixes)

### Timeouts Are Not Fixes
```python
# ❌ WRONG - Band-aid
try:
    result = slow_function()
except TimeoutError:
    result = fallback_value

# ✅ RIGHT - Fix the algorithm
def optimized_function():
    # Make the function faster, don't just timeout
```

### Try/Catch Is Not A Fix
```python
# ❌ WRONG - Suppressing errors
try:
    process_data()
except Exception:
    pass  # Just ignore it

# ✅ RIGHT - Fix the error source
def process_data():
    # Validate inputs, handle edge cases properly
    if not data:
        raise ValueError("Data cannot be empty")
```

### Fallbacks Are Not Fixes
```python
# ❌ WRONG - Using fallback when primary fails
if gpt4_vision_fails:
    use_simple_geometry()  # This is a band-aid!

# ✅ RIGHT - Make primary method reliable
def ensure_gpt4_vision_works():
    # Fix the root cause of GPT-4V failures
```

## 🏆 World-Class Engineering Standards

### 1. Semantic Understanding Over Pattern Matching
```python
# ❌ WRONG - Trusting labels blindly
if "SECOND FLOOR" in page_text:
    floor_number = 2

# ✅ RIGHT - Semantic validation
def validate_floor_semantically(rooms):
    has_kitchen = any('kitchen' in r.name for r in rooms)
    if has_kitchen and floor_label == "SECOND FLOOR":
        # This is actually the main floor, mislabeled
        return 1
```

### 2. Physics-Based Calculations
```python
# ❌ WRONG - Magic numbers without physics
bonus_room_load = room_load * 1.5  # Why 1.5?

# ✅ RIGHT - Physics-based reasoning
# Bonus rooms over garages have:
# - Exposed floor (R-11 vs R-19)
# - Higher infiltration (1.5x)
# - Semi-conditioned space below
garage_temp_winter = outdoor_temp + 10  # Garage warmer than outside
floor_delta_t = indoor_temp - garage_temp_winter
bonus_room_load = calculate_with_physics(floor_delta_t, R_value=11)
```

### 3. Validate, Don't Assume
```python
# ❌ WRONG - Assuming data is correct
total_area = sum(room.area for room in rooms)

# ✅ RIGHT - Validate and flag issues
def validate_area_calculation(rooms, declared_total):
    calculated = sum(r.area for r in rooms)
    discrepancy = abs(calculated - declared_total) / declared_total
    if discrepancy > 0.2:  # 20% threshold
        raise DataQualityError(f"Area discrepancy: {discrepancy:.1%}")
```

## 📐 Design Principles

### 1. Explicit Over Implicit
- Name variables clearly: `is_bonus_room` not `flag`
- Document WHY, not just WHAT
- Use enums for fixed choices, not magic strings

### 2. Fail Fast and Loud
- Detect problems early in the pipeline
- Raise specific exceptions with actionable messages
- Never silently degrade functionality

### 3. Composable Components
- Each module should do ONE thing well
- Modules should be independently testable
- Clear interfaces between components

## 🔍 Problem-Solving Approach

### When You Encounter An Issue:

1. **STOP** - Don't reach for a quick fix
2. **INVESTIGATE** - Find the root cause
   - Check logs thoroughly
   - Trace data flow
   - Identify where assumptions break
3. **DESIGN** - Create a proper solution
   - How does this prevent recurrence?
   - What edge cases exist?
   - How will this scale?
4. **IMPLEMENT** - Code the solution properly
   - No shortcuts
   - Full error handling
   - Comprehensive logging
5. **VALIDATE** - Ensure it actually works
   - Test with real data
   - Check edge cases
   - Verify performance

## 🏗️ Architecture Guidelines

### Multi-Stage Processing
```python
# Each stage should be:
# 1. Independent
# 2. Validatable
# 3. Resumable

Stage 1: Page Analysis
  ↓ (validate output)
Stage 2: Floor Detection
  ↓ (validate output)
Stage 3: Room Extraction
  ↓ (validate output)
Stage 4: Load Calculation
```

### Data Flow Principles
1. **Single Source of Truth** - Don't duplicate data
2. **Validate at Boundaries** - Check data when it enters a module
3. **Transform, Don't Mutate** - Create new objects rather than modifying
4. **Audit Everything** - Log decisions and transformations

## 💡 Frontend Excellence

### UI/UX Principles
```typescript
// ❌ WRONG - Confusing UX
<Button onClick={submit}>Submit</Button>  // No loading state

// ✅ RIGHT - Clear feedback
<Button 
  onClick={submit} 
  loading={isSubmitting}
  disabled={!isValid}
>
  {isSubmitting ? 'Processing...' : 'Calculate HVAC Loads'}
</Button>
```

### State Management
- **Single source of truth** - No duplicate state
- **Optimistic updates** - Immediate UI feedback
- **Error boundaries** - Graceful failure handling
- **Persistent state** - Survive refreshes when appropriate

### Performance Standards
- **First Contentful Paint: <1.5s**
- **Time to Interactive: <3s**
- **Lighthouse score: >90**
- **Bundle size: <200KB initial**
- **No layout shifts** - CLS < 0.1

### Accessibility (A11y)
```typescript
// ❌ WRONG - Inaccessible
<div onClick={action}>Click me</div>

// ✅ RIGHT - Fully accessible
<button
  onClick={action}
  aria-label="Calculate HVAC loads for blueprint"
  aria-busy={isLoading}
>
  Calculate Loads
</button>
```

### Data Fetching
```typescript
// ❌ WRONG - No error handling, no loading state
const data = await fetch('/api/data')

// ✅ RIGHT - Complete handling
const { data, error, isLoading, mutate } = useSWR(
  '/api/data',
  fetcher,
  {
    revalidateOnFocus: false,
    dedupingInterval: 10000,
    onError: (err) => logError(err)
  }
)
```

## 🔧 Backend Excellence

### API Design
```python
# ❌ WRONG - Inconsistent, unclear
@app.get("/getData")
def get_data(id):
    return {"result": data}

# ✅ RIGHT - RESTful, versioned, clear
@app.get("/api/v1/projects/{project_id}")
def get_project(
    project_id: UUID,
    user: User = Depends(get_current_user)
) -> ProjectResponse:
    """Get project with HVAC calculations."""
    return ProjectResponse(...)
```

### Database Operations
```python
# ❌ WRONG - N+1 queries
for room in rooms:
    room.loads = db.query(Loads).filter_by(room_id=room.id).first()

# ✅ RIGHT - Eager loading
rooms = db.query(Room).options(
    joinedload(Room.loads)
).filter_by(project_id=project_id).all()
```

### Error Handling
```python
# ❌ WRONG - Generic errors
raise Exception("Error occurred")

# ✅ RIGHT - Specific, actionable
class ScaleDetectionError(BlueprintError):
    def __init__(self, detected: float, expected: float):
        super().__init__(
            message=f"Scale mismatch: detected {detected}, expected {expected}",
            error_code="SCALE_MISMATCH",
            user_message="Please verify the blueprint scale",
            suggested_actions=["Check for 1/4\" = 1' notation", "Verify PDF quality"]
        )
```

## 🎨 Full-Stack Integration

### Type Safety Across Stack
```typescript
// Frontend - types from OpenAPI schema
import { ProjectResponse } from '@/api/generated'

// Backend - Pydantic models generate OpenAPI
class ProjectResponse(BaseModel):
    id: UUID
    heating_load: float
    cooling_load: float
```

### Validation Consistency
- **Frontend validation** - Immediate UX feedback
- **Backend validation** - Security and data integrity
- **Database constraints** - Final safety net

### Caching Strategy
```typescript
// Frontend
const { data } = useSWR(key, fetcher, {
  revalidateIfStale: false,  // Use cache first
  revalidateOnFocus: false,  // Don't refetch on tab focus
})

// Backend
@cache.memoize(timeout=300)  # 5 minute cache
def calculate_expensive_operation():
    pass
```

## 💡 Specific to AutoHVAC

### Blueprint Processing (Backend)
- **Never trust page labels** - Validate semantically
- **Multi-floor context is critical** - Pass information between floors
- **Scale detection is fundamental** - Get it right or everything fails

### HVAC Calculations (Backend)
- **Use ACCA Manual J** - Industry standard, no shortcuts
- **Account for building physics** - Stack effect, thermal coupling
- **Special cases need special physics** - Bonus rooms, basements, etc.

### User Experience (Frontend)
- **Real-time progress** - Show processing stages
- **Clear error messages** - What went wrong and how to fix it
- **Intuitive flow** - Upload → Process → Review → Export

### Performance Requirements
- **Blueprint upload: <2s to start processing**
- **Processing feedback: Every 2-3 seconds**
- **Blueprint processing: <30 seconds total**
- **Report generation: <1 second**
- **API response time: p95 < 200ms**
- **Frontend interactions: <100ms feedback**

## 🚫 Anti-Patterns to Avoid

### 1. The "It Works Sometimes" Pattern
If it doesn't work reliably, it doesn't work at all.

### 2. The "Good Enough" Pattern
Our calculations affect $20,000+ equipment decisions. "Good enough" isn't.

### 3. The "We'll Fix It Later" Pattern
Technical debt compounds. Fix it now or document why you can't.

### 4. The "Magic Number" Pattern
Every number should have a source or explanation.
```python
# ❌ WRONG
adjustment_factor = 1.15

# ✅ RIGHT
# 15% increase for corner rooms per ACCA Manual J Table 4A
corner_room_factor = 1.15
```

## 🧠 AI Integration Principles

### Prompt Engineering
```python
# ❌ WRONG - Vague prompt
prompt = "Find rooms in blueprint"

# ✅ RIGHT - Specific, contextual prompt
prompt = f"""
Analyze floor {floor_num} of a residential blueprint.
Expected: {expected_rooms} rooms typical for {floor_type}.
Previous floor had: {previous_floor_context}.
Extract ALL rooms including closets and storage.
"""
```

### AI Fallback Strategy
- **Primary: GPT-4 Vision** - Most accurate
- **Never fallback to inferior methods** - Fix the primary instead
- **Validate AI output** - Don't trust blindly
- **Provide context** - Better prompts = better results

## 🏆 Excellence Metrics

### Code Quality Metrics
- **Test Coverage: >80%** - Critical paths 100%
- **Cyclomatic Complexity: <10** - Keep functions simple
- **Duplication: <3%** - DRY principle
- **Tech Debt Ratio: <5%** - Address immediately

### Performance Metrics
- **Backend API: p50 < 100ms, p95 < 200ms, p99 < 500ms**
- **Frontend: Lighthouse >90, CLS <0.1, FID <100ms**
- **Database: Query time <50ms, No N+1 queries**
- **Memory: No leaks, <500MB per worker**

### Business Metrics
- **Accuracy: >95%** - HVAC calculations within 5% of manual
- **Success Rate: >99%** - Blueprint processing succeeds
- **User Satisfaction: >4.5/5** - NPS > 50

## 🔒 Security Principles

### Input Validation
```python
# ❌ WRONG - Trust user input
area = float(request.form['area'])

# ✅ RIGHT - Validate everything
area = validate_positive_float(
    request.form.get('area'),
    min_value=100,
    max_value=10000,
    error_msg="Invalid area"
)
```

### Authentication & Authorization
- **JWT tokens** - Stateless, scalable
- **Row-level security** - Users see only their data
- **Rate limiting** - Prevent abuse
- **Audit logging** - Track all actions

## ✅ Code Review Checklist

### Before Writing Code
- [ ] Is this solving the ROOT CAUSE?
- [ ] Have I designed the OPTIMAL solution?
- [ ] Will this scale to 10x current load?
- [ ] Is there an existing pattern to follow?

### Before Committing - Backend
- [ ] No band-aid fixes
- [ ] Root cause addressed
- [ ] Error handling comprehensive
- [ ] Logging adequate
- [ ] Tests written (unit + integration)
- [ ] API documented
- [ ] Database migrations ready
- [ ] Performance validated

### Before Committing - Frontend
- [ ] Component reusable
- [ ] Accessibility complete
- [ ] Loading states handled
- [ ] Error states handled
- [ ] Responsive design tested
- [ ] Bundle size impact checked
- [ ] Browser compatibility verified
- [ ] E2E tests updated

### Before Committing - Shared
- [ ] Types/interfaces updated
- [ ] Documentation updated
- [ ] No console.logs or print statements
- [ ] No commented-out code
- [ ] No TODO without ticket number
- [ ] Follows team conventions
- [ ] Reviewed by another engineer

## 🎯 Remember

**We're building professional HVAC software that contractors rely on for expensive decisions.**

Every line of code should reflect:
- **Accuracy** - Correct calculations based on industry standards
- **Reliability** - Works every time, not just sometimes
- **Clarity** - Next developer (including future you) can understand it
- **Performance** - Fast enough for production use

## 🌟 The World-Class Engineering Mindset

### Think Like a Pro
1. **Would I be proud to show this code to the best engineers at Google/Meta/OpenAI?**
2. **Would this code work flawlessly in production for 1M users?**
3. **Could a new engineer understand this code in 5 minutes?**
4. **Will this code still be maintainable in 2 years?**

### The Excellence Standard
- **Good enough is NOT good enough**
- **If it's not excellent, it's not done**
- **Every detail matters**
- **Performance and UX are features, not nice-to-haves**

### Continuous Improvement
- **Refactor mercilessly** - Leave code better than you found it
- **Learn from failures** - Post-mortems without blame
- **Measure everything** - You can't improve what you don't measure
- **Stay current** - Use modern best practices

### The AutoHVAC Promise
We promise our users:
- **Accurate calculations** they can trust with $20K+ decisions
- **Fast processing** that respects their time
- **Clear communication** when things go wrong
- **Professional quality** in every interaction

## 📚 References

- ACCA Manual J 8th Edition - Load calculation standard
- ASHRAE Fundamentals - Building physics
- Python Best Practices - PEP 8, PEP 20
- TypeScript Best Practices - Official handbook
- Clean Code - Robert C. Martin
- Design Patterns - Gang of Four
- System Design - Martin Kleppmann
- Web Performance - Ilya Grigorik

---

### The AutoHVAC Engineering Manifesto

*"We don't write code that just works. We write code that's a joy to maintain, a pleasure to use, and reliable enough to stake our reputation on. Every line of code is an opportunity to demonstrate excellence. No band-aids, no shortcuts, no excuses - only world-class engineering."*

**Remember:** The code you write today will be running in production tomorrow, affecting real contractors making real decisions about real money. Make it count.
# CLAUDE.md - Project Context for AutoHVAC

## PROJECT OVERVIEW
AutoHVAC is a professional HVAC load calculation system that processes blueprints to generate ACCA Manual J compliant calculations. This is used by contractors to make $20,000+ equipment decisions.

## CRITICAL REQUIREMENTS

### NO BAND-AID FIXES EVER
- **TIMEOUTS ARE NOT FIXES** - Fix slow algorithms
- **TRY/CATCH IS NOT A FIX** - Fix the error source
- **FALLBACKS ARE NOT FIXES** - Fix the primary method
- Every fix must address the ROOT CAUSE

### PERFORMANCE REQUIREMENTS
- Blueprint processing: <30 seconds total
- Multi-story processing: Must handle ALL floors
- Target accuracy: 74,000 BTU/hr for 2-story test home

### TECHNICAL CONSTRAINTS
- **Vision AI**: Use ONLY gpt-4o-2024-11-20 for vision (others don't work)
- **Text AI**: Use gpt-5 or gpt-5-mini for text analysis only
- **No GPT-5 Vision** - It doesn't exist, GPT-5 is text-only

## DEVELOPMENT PHILOSOPHY

Before ANY fix, you MUST:
1. Identify the ROOT CAUSE
2. Explain how your fix addresses that root cause
3. Ensure the fix prevents the issue from recurring

If you find yourself:
- Adding a timeout → STOP, fix the algorithm
- Adding error suppression → STOP, fix the error source
- Adding a workaround → STOP, fix the actual problem

## KEY TECHNICAL DETAILS

### Current Architecture
- FastAPI backend with Celery workers
- S3 storage with job-based structure (jobs/{project_id}/)
- PostgreSQL via Render
- GPT-4o Vision for blueprint analysis
- ACCA Manual J calculations

### Known Issues & Solutions
- Polygon detection taking 5+ minutes → Fixed by ensuring GPT-4o Vision works
- Multi-story calculations wrong → Must process all floor plan pages
- Scale detection failures → GPT-4o Vision should detect scale

## TESTING APPROACH
Always test with multi-story blueprints to ensure:
1. All floors are detected and processed
2. HVAC calculations aggregate correctly
3. Performance stays under 30 seconds

## CODE QUALITY STANDARDS
- Clear domain modeling (rooms, floors, buildings)
- Intelligent parsing with proper prompting
- No magic numbers without documentation
- Performance-first design
- Comprehensive error messages for debugging

Remember: Contractors rely on our calculations for expensive decisions. Accuracy and reliability are non-negotiable.
# MANDATORY ENGINEERING PRINCIPLES FOR AUTOHVAC

## CORE PHILOSOPHY: ROOT CAUSE FIXES ONLY

### NEVER DO (BAND-AID FIXES):
1. **NEVER add timeouts** to "fix" slow code - Fix the algorithm
2. **NEVER add try/catch** to silence errors - Fix the error source
3. **NEVER add "if X fails, try Y"** patches - Fix X
4. **NEVER add magic numbers/constants** without understanding why
5. **NEVER "just make it work"** - Understand WHY it's broken first
6. **NEVER add workarounds** - Fix the actual problem
7. **NEVER skip understanding** - If you don't know why something fails, investigate first

### ALWAYS DO (ROOT CAUSE APPROACH):
1. **ALWAYS identify the root cause** before coding any fix
2. **ALWAYS optimize algorithms** instead of adding timeouts
3. **ALWAYS fix data flow issues** at their source
4. **ALWAYS understand the "why"** before the "how"
5. **ALWAYS consider performance** from the start, not as an afterthought
6. **ALWAYS fix the source** of bad data, not compensate for it later
7. **ALWAYS think systemically** - how does this affect the whole pipeline?

### SPECIFIC TO AUTOHVAC:
1. **Vision Models**: gpt-4o-2024-11-20 is the ONLY model for vision tasks
2. **Performance**: If something takes >30 seconds, the algorithm is wrong
3. **Multi-story**: Must process ALL floors, not just one
4. **Scale Detection**: Must be intelligent, not guessed
5. **Data Flow**: Fix issues where they originate, not where they manifest

### WHEN YOU'RE TEMPTED TO BAND-AID:
Ask yourself:
1. "What is the ROOT CAUSE of this issue?"
2. "Am I fixing the symptom or the disease?"
3. "Will this fix prevent the issue from EVER happening again?"
4. "Is this how a senior engineer would solve it?"

### RED FLAGS (Stop immediately if you're doing these):
- Adding `.timeout()` to anything
- Using `try/except: pass`
- Adding `if not X: use_fallback()`
- Hardcoding values to "make it work"
- Adding delays/sleeps
- Increasing limits/thresholds without understanding why

### THE AUTOHVAC WAY:
"We build robust, intelligent systems that understand blueprints like an expert HVAC engineer would. No shortcuts, no patches, no band-aids. Every line of code has a purpose rooted in domain understanding."

## HOW TO ENFORCE THIS:
1. Before coding, state the ROOT CAUSE
2. Explain WHY your fix addresses the root cause
3. If tempted to patch, STOP and investigate deeper
4. Performance issues = algorithm issues, not timeout issues
5. Data issues = source issues, not validation issues

Remember: We're building professional HVAC software that contractors trust with $20,000+ decisions. Band-aids have no place here.
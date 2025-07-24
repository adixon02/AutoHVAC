# AutoHVAC Documentation
*Everything you need to rebuild AutoHVAC from scratch*

## 🎯 Purpose
This documentation prevents the technical debt, code duplication, and unclear boundaries we encountered in our first attempt. Every document serves a specific purpose to ensure we build **lean, functional, and maintainable software**.

---

## 📚 Document Guide

### 📋 Planning Documents (Start Here)
Read these **before writing any code** to understand the overall approach:

**[system-map.md](01-planning/system-map.md)**
- 🎯 **Purpose**: Shows exactly how data flows through the application
- 🔑 **Key Insight**: Both manual input and blueprint upload create the same data structure
- ⚡ **Prevents**: Duplicate code paths and unclear data ownership

**[feature-roadmap.md](01-planning/feature-roadmap.md)**
- 🎯 **Purpose**: Defines what to build in each version (V1, V2, V3)
- 🔑 **Key Insight**: Build perfect V1 first, then add complexity
- ⚡ **Prevents**: Trying to build everything at once

---

### 🛠️ Development Documents (Reference While Coding)
Use these as your development bible:

**[data-dictionary.md](02-development/data-dictionary.md)**
- 🎯 **Purpose**: Single source of truth for all data structures  
- 🔑 **Key Insight**: One consistent format for each piece of information
- ⚡ **Prevents**: Multiple data models for the same concepts
- ❗ **Critical**: Follow these exact type definitions everywhere

**[user-journey.md](02-development/user-journey.md)**
- 🎯 **Purpose**: Step-by-step user experience flows
- 🔑 **Key Insight**: Every user interaction planned and designed
- ⚡ **Prevents**: Confusing navigation and unclear UI states
- ❗ **Critical**: Build exactly what's specified here

**[api-checklist.md](02-development/api-checklist.md)**
- 🎯 **Purpose**: Exact API endpoints and data formats
- 🔑 **Key Insight**: Clear contract between frontend and backend
- ⚡ **Prevents**: Integration issues and miscommunication
- ❗ **Critical**: Backend must match these specs exactly

**[backend-services.md](02-development/backend-services.md)**
- 🎯 **Purpose**: Technical reference for V2 backend services
- 🔑 **Key Insight**: Detailed service architecture and integration patterns
- ⚡ **Prevents**: Service misuse and integration confusion
- ❗ **Critical**: Reference for service configuration and debugging

---

### 🚀 Implementation Guide (When Ready to Code)

**[getting-started.md](03-build-guide/getting-started.md)**
- 🎯 **Purpose**: Step-by-step implementation roadmap
- 🔑 **Key Insight**: Specific order and timeline for building features
- ⚡ **Prevents**: Analysis paralysis and unclear next steps
- ❗ **Critical**: Follow the exact phase order

---

## 🎪 How to Use This Documentation

### For First-Time Builders
1. **Read** all planning documents to understand the approach
2. **Study** the data dictionary until you know every field
3. **Follow** the getting started guide step-by-step
4. **Reference** development docs while coding

### For Experienced Developers  
1. **Skim** system map and roadmap for context
2. **Memorize** data dictionary (this is your law)
3. **Use** API checklist as integration reference
4. **Follow** user journey for UI implementation

### For Team Collaboration
- **Planning docs** = shared vision and approach
- **Development docs** = daily reference and contracts
- **Implementation guide** = who does what when

---

## 🔑 Key Principles

### 1. Documentation-Driven Development
- **Plan first, code second** - prevents architecture mistakes
- **Document decisions** - reduces confusion and rework  
- **Update docs with changes** - keeps team aligned

### 2. Single Source of Truth
- **One data model** per concept (not 5 variations)
- **One flow path** from input to results
- **One place** for each type of information

### 3. Progressive Enhancement
- **V1 perfect** before starting V2
- **Simple first**, complexity later
- **User feedback** drives future features

---

## 🚨 Warning Signs

If you find yourself doing any of these, **STOP** and re-read the docs:

❌ **Creating new data types** not in the data dictionary
❌ **Building features** not in the current version roadmap  
❌ **Skipping steps** in the user journey
❌ **Making up API endpoints** not in the checklist
❌ **"Just this once"** deviating from the plan

✅ **Instead**: Reference the docs, ask questions, stick to the plan

---

## 📈 Success Metrics

### You're Following the Docs When:
- [ ] Every data structure matches the dictionary exactly
- [ ] Your code follows the system map flow
- [ ] UI matches the user journey specifications  
- [ ] APIs match the checklist contracts
- [ ] You're building features in roadmap order

### You're Ready for the Next Phase When:
- [ ] Current phase works 100% as specified
- [ ] No bugs in core functionality
- [ ] Code is clean and well-documented
- [ ] User experience is smooth and professional

---

## 🛟 Getting Help

### When Documentation Isn't Clear
1. **Check related documents** - answer might be in another file
2. **Ask specific questions** - reference which document and section
3. **Suggest improvements** - help make docs better for next person

### When You Want to Change Something
1. **Understand why** the current approach was chosen
2. **Consider implications** of the change across all documents
3. **Update all related docs** if change is approved
4. **Get team alignment** before implementing

---

## 📁 Document Structure
```
docs/
├── README.md (this file)
│
├── 01-planning/
│   ├── system-map.md       (How data flows)
│   └── feature-roadmap.md  (What to build when)
│
├── 02-development/  
│   ├── data-dictionary.md  (Data structures)
│   ├── user-journey.md     (UI specifications) 
│   ├── api-checklist.md    (Backend contracts)
│   └── backend-services.md (V2 service reference)
│
└── 03-build-guide/
    └── getting-started.md  (Implementation steps)
```

---

## 🎯 Remember
This documentation is your **insurance policy** against repeating the mistakes of V1. The extra time spent planning will save weeks of refactoring and debugging later.

**When in doubt, trust the docs. When the docs are wrong, fix them first.**

---

*These documents are living resources - keep them updated as the project evolves.*
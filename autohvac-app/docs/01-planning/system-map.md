# AutoHVAC System Map
*A visual guide to how data flows through our application*

## 🎯 Why This Matters
Our first version had duplicate code paths and confusion about where data came from. This map shows the **one clear path** that data takes, preventing us from building the same logic multiple times.

---

## 📊 The Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER STARTS HERE                         │
└─────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROJECT SETUP                                │
│  • Project Name                                                 │
│  • ZIP Code                                                     │
│  • Building Type (Residential/Commercial)                       │
│  • Construction Type (New/Retrofit)                             │
│  • Input Method Choice: [MANUAL] or [BLUEPRINT]                 │
└─────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
            ┌─────────────┴─────────────┐
            │                          │
            ▼                          ▼
    ┌──────────────┐           ┌──────────────┐
    │    MANUAL    │           │  BLUEPRINT   │
    │    INPUT     │           │   UPLOAD     │
    └──────┬───────┘           └──────┬───────┘
           │                          │
           ▼                          ▼
    ┌─────────────┐            ┌─────────────┐
    │ Building    │            │ PDF         │
    │ Details     │            │ Processing  │
    │ Entry       │            │ & AI        │
    └──────┬──────┘            │ Extraction  │
           │                   └──────┬──────┘
           ▼                          │
    ┌─────────────┐                   │
    │ Room-by-    │                   │
    │ Room Entry  │                   │
    └──────┬──────┘                   │
           │                          │
           └─────────┬──────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                 UNIFIED DATA MODEL                              │
│  Everything gets converted to this standard format:            │
│  • ProjectInfo                                                 │
│  • BuildingCharacteristics                                     │
│  • List of Rooms with details                                  │
│  • Climate data from ZIP code                                  │
└─────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 HVAC CALCULATIONS                               │
│  ONE calculation engine that handles all data:                 │
│  • Manual J Load Calculations                                  │
│  • Climate zone factors                                        │
│  • Heat transfer calculations                                  │
│  • System sizing (BTU/hr to tons)                             │
└─────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                SYSTEM RECOMMENDATIONS                           │
│  • Economy tier equipment                                      │
│  • Standard tier equipment                                     │
│  • Premium tier equipment                                      │
│  • Professional reports                                        │
└─────────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RESULTS PAGE                               │
│  • Load calculations display                                   │
│  • Equipment recommendations                                   │
│  • Professional report download                                │
│  • PDF export                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔑 Key Design Principles

### 1. **Single Path Convergence**
- Both manual input and blueprint upload create the **exact same data structure**
- No duplicate calculation logic
- One set of components handles results display

### 2. **Clear Data Ownership**
- **Frontend**: User interface, input validation, results display
- **Backend**: PDF processing, AI extraction, HVAC calculations
- **Database**: Project storage, climate data lookup

### 3. **Error Boundaries**
- Each step can fail independently
- Clear error messages at each stage
- User can restart from any point

---

## 📋 What This Prevents

❌ **Problems from V1:**
- 3 different blueprint processors
- 5 different data models for the same thing
- Duplicate calculation code
- Confusion about where data comes from

✅ **Benefits of This Design:**
- One data model to rule them all
- Clear boundaries between components
- Easy to test each piece independently
- Simple to add new features later

---

## 🎯 Implementation Order

**Phase 1: Core Flow** (Build this first)
- Project setup → Manual input → Unified data → Calculations → Results

**Phase 2: Blueprint Addition** 
- Add blueprint upload that creates the same unified data

**Phase 3: Enhancements**
- AI improvements, better UI, advanced features

---

*This map is our north star - every component we build should fit clearly into this flow.*
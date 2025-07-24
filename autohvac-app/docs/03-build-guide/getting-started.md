# AutoHVAC Getting Started Guide
*Your step-by-step roadmap from planning to code*

## 🎯 Before You Code Anything

### ✅ Pre-Development Checklist
Make sure you've completed these planning documents:
- [ ] **System Map**: You understand the data flow from input → processing → results
- [ ] **Data Dictionary**: You know exactly how to structure every piece of data
- [ ] **Feature Roadmap**: You're building V1 first (manual input only)
- [ ] **User Journey**: You know what every screen looks like
- [ ] **API Checklist**: You know what endpoints you need

**Don't start coding until all boxes are checked!** This prevents the technical debt and confusion we had in V1.

---

## 🚀 Development Setup

### 1. Archive the Old Version
```bash
# Rename current project to preserve learnings
mv autohvac-app autohvac-app-archive

# Create fresh project directory
mkdir autohvac-app
cd autohvac-app
```

### 2. Initialize New Project Structure
```bash
# Frontend setup
npx create-next-app@latest . --typescript --tailwind --app
npm install zustand react-dropzone @types/node

# Backend setup  
mkdir backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install fastapi uvicorn python-multipart
```

### 3. Create Core Directory Structure
```bash
# Frontend structure
mkdir -p app/{components,hooks,lib,store,types}
mkdir -p app/components/{ui,forms,layout,pages}

# Backend structure  
mkdir -p backend/{api,core,services,models,tests}

# Documentation (already exists)
# docs/{01-planning,02-development,03-build-guide}
```

---

## 📋 Implementation Order (V1 Only)

### Phase 1: Data Foundation (Week 1)
**What you're building:** Core data types and validation

**Tasks:**
1. **Create Type Definitions**
   ```bash
   # In app/types/
   touch index.ts project.ts building.ts room.ts climate.ts calculations.ts
   ```
   - Copy exact definitions from `docs/02-development/data-dictionary.md`
   - Add TypeScript interfaces for all data models
   - Include validation schemas using Zod

2. **Climate Data Service**
   ```bash
   # In app/lib/
   touch climate-service.ts
   ```
   - Build ZIP code → climate data lookup
   - Use climate zones from existing project
   - Test with sample ZIP codes

3. **Manual J Calculator**
   ```bash
   # In app/lib/
   touch manual-j-calculator.ts
   ```
   - Pure calculation functions (no UI dependencies)
   - Load calculations for cooling and heating
   - Room-by-room breakdown logic

**Success Criteria:**
- All type definitions compile without errors
- Climate service returns correct data for test ZIP codes
- Manual J calculator produces accurate BTU/hr results

---

### Phase 2: Core UI Components (Week 2)
**What you're building:** Reusable components for forms and display

**Tasks:**
1. **UI Component Library**
   ```bash
   # In app/components/ui/
   touch Button.tsx Input.tsx Card.tsx FormField.tsx ProgressBar.tsx
   ```
   - Build design system components from user journey specs
   - Include proper TypeScript props and variants
   - Add basic styling with Tailwind

2. **Form Components**
   ```bash
   # In app/components/forms/
   touch ProjectForm.tsx BuildingForm.tsx RoomForm.tsx
   ```
   - Create form components that use exact data types
   - Include validation and error handling
   - Match UI specifications from user journey

3. **Page Layout Components**
   ```bash
   # In app/components/layout/
   touch Header.tsx ProgressIndicator.tsx Navigation.tsx
   ```
   - Build navigation components
   - Add progress tracking
   - Include responsive design

**Success Criteria:**
- All components render without errors
- Forms validate data according to data dictionary
- UI matches designs from user journey map

---

### Phase 3: State Management (Week 3)  
**What you're building:** Application state and data flow

**Tasks:**
1. **Zustand Store Setup**
   ```bash
   # In app/store/
   touch useProjectStore.ts
   ```
   - Create single store for all project data
   - Include actions for each step in user journey
   - Add persistence for incomplete projects

2. **Data Flow Implementation**
   - Project setup → Building details → Room entry → Results
   - Follow exact flow from system map
   - Ensure data transforms match data dictionary

3. **Calculation Integration**
   - Connect Manual J calculator to UI
   - Display results in specified format
   - Handle calculation errors gracefully

**Success Criteria:**
- User can complete entire manual input flow
- Data persists between browser sessions
- Calculations produce correct results

---

### Phase 4: Results & Reports (Week 4)
**What you're building:** Results display and PDF generation

**Tasks:**
1. **Results Display**
   ```bash
   # In app/components/pages/
   touch ResultsPage.tsx LoadSummary.tsx RoomBreakdown.tsx
   ```
   - Build results page per user journey specs
   - Show load calculations clearly
   - Include room-by-room breakdown

2. **Equipment Recommendations**
   ```bash
   # In app/lib/
   touch system-recommendations.ts
   ```
   - Generate three-tier equipment recommendations
   - Include cost estimates and efficiency ratings
   - Display in clear comparison format

3. **PDF Report Generation**
   ```bash
   # Install: npm install jspdf html2canvas
   # In app/lib/
   touch report-generator.ts
   ```
   - Generate professional PDF reports
   - Include all calculation details
   - Format for permit submission

**Success Criteria:**
- Results page displays all calculation data clearly
- Equipment recommendations show appropriate options
- PDF reports generate correctly and look professional

---

## 🧪 Testing Strategy

### As You Build Each Phase
1. **Unit Tests** for calculation functions
   - Test Manual J calculations against known values
   - Verify climate data lookups
   - Check data validation rules

2. **Component Tests** for UI components
   - Test form validation
   - Check error handling
   - Verify data flow

3. **Integration Tests** for complete flows
   - Test entire user journey end-to-end
   - Verify data persistence
   - Check calculation accuracy

### Testing Commands
```bash
# Install testing dependencies
npm install -D jest @testing-library/react @testing-library/jest-dom

# Run tests
npm test
```

---

## 🔍 Quality Checkpoints

### After Each Phase
- [ ] All TypeScript types are correct and used consistently
- [ ] Code follows data dictionary exactly (no variations)
- [ ] UI matches user journey specifications
- [ ] No duplicate code or logic
- [ ] Error handling covers identified scenarios
- [ ] Performance meets targets (calculations <1s)

### Before Moving to V2
- [ ] 100% of manual input flow works perfectly
- [ ] All validation rules implemented
- [ ] PDF reports generate correctly
- [ ] No critical bugs
- [ ] Code is clean and well-documented

---

## 🚫 What NOT to Do

### Resist These Temptations
❌ **"Let's add blueprint upload now"** → No! V1 first.
❌ **"This data type should be slightly different"** → No! Use data dictionary exactly.
❌ **"Let's make the UI more advanced"** → No! Follow user journey specs.
❌ **"We need a database"** → No! V1 uses local storage only.

### When You Feel Stuck
1. **Check the planning docs first** - the answer is probably there
2. **Ask specific questions** - "How should Room.equipmentLoad be validated?"
3. **Don't invent solutions** - stick to what's planned
4. **Take breaks** - building clean code takes time

---

## 📞 Getting Help

### When to Ask for Help
- Planning documents don't cover your specific situation
- You find a genuine issue with the planned approach
- You're stuck on implementation details
- Something seems more complex than expected

### How to Ask Good Questions
1. **What you're trying to build** - specific component or feature
2. **What you've tried** - show your code attempts
3. **Specific error or problem** - exact error messages
4. **Reference planning docs** - which document you're following

---

## 🎉 Success Metrics

### You Know You're On Track When
- [ ] Every piece of data uses exact types from data dictionary
- [ ] User flow matches journey map exactly
- [ ] No duplicate code anywhere in the project
- [ ] All calculations produce correct results
- [ ] UI looks professional and works smoothly
- [ ] Code is clean and easy to understand

### Ready for V2 When
- [ ] Manual input flow is 100% functional
- [ ] Users can generate professional reports
- [ ] No bugs in core functionality
- [ ] Performance meets all targets
- [ ] Code architecture can support blueprint upload addition

---

## 📚 Quick Reference

### Key Files to Check Often
- `docs/01-planning/system-map.md` - Data flow overview
- `docs/02-development/data-dictionary.md` - Exact data formats
- `docs/02-development/user-journey.md` - UI specifications
- `docs/01-planning/feature-roadmap.md` - What to build when

### Development Mantras
1. **"Does this match the data dictionary?"**
2. **"Is this following the system map?"**
3. **"Will users understand this interface?"**
4. **"Am I building V1 or trying to jump ahead?"**

---

*Remember: The goal is not to build everything quickly. The goal is to build V1 perfectly so V2 and V3 are easy to add.*
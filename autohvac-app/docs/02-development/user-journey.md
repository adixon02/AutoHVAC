# AutoHVAC User Journey Map
*Step-by-step user experience flows*

## 🎯 Why This Matters
Our first version had unclear navigation and users got confused about what to do next. This map shows exactly what users see and click at every step, ensuring a smooth experience without guesswork.

---

## 🗺️ Journey Overview

### Two Main Paths
1. **Manual Input Path**: User enters everything by hand (V1)
2. **Blueprint Upload Path**: User uploads PDF, AI extracts data (V2)

Both paths end at the same results page with identical outputs.

---

## 📱 Manual Input Journey (V1)

### Step 1: Landing Page
**What User Sees:**
- Clean welcome screen with AutoHVAC branding
- "Start New Project" button (large, prominent)
- Brief explanation: "Professional HVAC calculations in minutes"
- Sample screenshots showing final results

**User Action:**
- Clicks "Start New Project"

**What Happens:**
- App navigates to Project Setup
- Progress indicator shows "Step 1 of 4"

---

### Step 2: Project Setup
**What User Sees:**
- Form with 4 clear fields:
  - Project Name (text input)
  - ZIP Code (5-digit input with validation)
  - Building Type (radio buttons: Residential / Commercial)
  - Construction Type (radio buttons: New Construction / Retrofit)
- Input method selector: "Manual Input" pre-selected
- "Continue" button (disabled until all fields valid)
- Progress bar shows 25% complete

**User Actions & Validation:**
- Types project name → Field turns green when valid
- Enters ZIP code → Auto-validates format, shows climate zone preview
- Selects building type → Radio button highlights
- Selects construction type → All fields now valid
- "Continue" button becomes active and blue

**Error Scenarios:**
- Invalid ZIP → Red border, "Please enter a valid 5-digit ZIP code"
- Empty project name → Red border, "Project name is required"
- Missing selections → Red border, helpful text

**What Happens on Continue:**
- Data saves to local storage
- Navigate to Building Details
- Progress bar updates to 50%

---

### Step 3: Building Details  
**What User Sees:**
- Header: "Tell us about the building"
- 8 form fields with smart defaults:
  - Total Square Footage (number input)
  - Foundation Type (dropdown with icons)
  - Wall Insulation Quality (slider: Poor → Excellent)
  - Ceiling Insulation Quality (slider: Poor → Excellent)
  - Window Type (selection grid with images)
  - Building Orientation (compass selector)
  - Number of Stories (stepper: 1, 2, 3+)
  - Building Age (dropdown with ranges)
- "Back" and "Continue" buttons
- Progress bar shows 50% complete

**User Actions:**
- Fills out form fields → Real-time validation and green checkmarks
- Can click "Back" to modify project setup
- "Continue" becomes active when all required fields complete

**Smart Features:**
- Square footage auto-suggests reasonable range based on building type
- Foundation type shows climate-appropriate defaults for ZIP code
- Insulation sliders show cost/benefit tooltips

**What Happens on Continue:**
- Building data saves to local storage
- Navigate to Room Entry
- Progress bar updates to 75%

---

### Step 4: Room Entry
**What User Sees:**
- Header: "Add your rooms"
- "Add Room" button (prominent)
- Empty state: "No rooms added yet. Click 'Add Room' to get started."
- Progress bar shows 75% complete

**Adding First Room:**
- Click "Add Room" → Modal opens
- Room template selector: Bedroom, Kitchen, Living Room, Bathroom, Office, Custom
- Select template → Pre-fills reasonable defaults
- Room form fields:
  - Room Name (pre-filled, editable)
  - Area (sq ft)
  - Ceiling Height (dropdown: 8', 9', 10', 12')
  - Exterior Walls (stepper: 0, 1, 2, 3, 4)
  - Window Area (sq ft)
  - Typical Occupants (stepper)
  - Equipment Load (slider with common examples)
- "Cancel" and "Add Room" buttons

**Room List View:**
- Added rooms show as cards with key info
- Each room card has "Edit" and "Delete" buttons
- Running total shows: "3 rooms, 1,250 sq ft total"
- "Add Another Room" button
- "Calculate Results" button (active when ≥1 room)

**What Happens on Calculate:**
- All data validation runs
- Loading spinner: "Calculating HVAC loads..."
- Navigate to Results page
- Progress bar shows 100%

---

### Step 5: Results Page
**What User Sees:**
- Success message: "Analysis Complete!"
- Project summary box (name, ZIP, building type, total sq ft)
- Load calculation summary:
  - Total Cooling Load: 36,000 BTU/hr (3.0 tons)
  - Total Heating Load: 28,000 BTU/hr (2.3 tons)
- Room-by-room breakdown (expandable table)
- Three equipment recommendation tiers:
  - Economy: Basic specs and price
  - Standard: Mid-level specs and price  
  - Premium: High-efficiency specs and price
- "Download Professional Report" button
- "Start New Project" button

**User Actions:**
- Can expand room details to see individual loads
- Can click equipment recommendations for detailed specs
- Can download PDF report for permits/client presentation
- Can start over with new project

---

## 📄 Blueprint Upload Journey (V2)

### Steps 1-2: Same as Manual Input
*Project setup identical to manual flow*

### Step 3: Blueprint Upload
**What User Sees:**
- Header: "Upload your blueprints"
- Large drag-and-drop zone with upload icon
- "Drag & drop PDF files here, or click to select"
- File requirements: "PDF format, up to 100MB"
- Progress bar shows 50% complete

**Upload Process:**
1. **File Selection:**
   - User drags PDF or clicks to browse
   - File validation (PDF, size limit)
   - Shows file name and size: "floor-plan.pdf (12.3 MB)"
   - "Upload & Process" button becomes active

2. **Processing Animation:**
   - Upload progress bar: "Uploading... 45%"
   - Then: "Processing blueprint with AI..."
   - Animated blueprint icon with progress indicator
   - Status updates: "Extracting rooms... Analyzing building details... Almost done..."

3. **Review & Correction:**
   - Split view: Blueprint image on left, extracted data on right
   - AI-detected rooms listed with confidence scores
   - Building characteristics with confidence indicators
   - Green checkmarks for high-confidence items
   - Yellow warnings for low-confidence items
   - Red flags for missing critical data

**Review Interface:**
- Each detected room shows:
  - Name (editable)
  - Area with confidence % (editable)
  - Other properties (editable)
  - "Looks good" or "Needs correction" toggle
- Missing rooms can be added manually
- "Approve & Calculate" button

**What Happens on Approve:**
- Same calculation process as manual input
- Same results page format

---

## 🚨 Error Handling Flows

### Network Errors
**What User Sees:**
- "Connection lost" banner at top
- "We're having trouble connecting. Check your internet and try again."
- Retry button
- Data is preserved locally

### Calculation Errors  
**What User Sees:**
- "Calculation Error" message
- "Something went wrong with the load calculations. Please check your room data and try again."
- Button to "Review Room Data"
- Option to "Contact Support"

### File Upload Errors
**What User Sees:**
- "Upload Failed" message with specific reason:
  - "File too large (150MB). Maximum is 100MB."
  - "Invalid file type. Please upload a PDF."
  - "Upload timeout. Please try again."
- "Try Again" button
- "Upload Different File" option

### Blueprint Processing Errors
**What User Sees:**
- "We couldn't process this blueprint" message
- Explanation: "The PDF may be too complex or low resolution"
- Options:
  - "Try Different File"
  - "Switch to Manual Input"
  - "Contact Support"

---

## 📱 Mobile Experience Notes

### Responsive Breakpoints
- **Desktop**: Full feature set, side-by-side layouts
- **Tablet**: Stacked layouts, touch-friendly controls
- **Mobile**: Single-column flow, simplified inputs

### Mobile-Specific Features
- Larger touch targets (48px minimum)
- Swipe gestures for navigation
- Auto-save every field change
- Simplified room entry with fewer fields visible

---

## 🔄 Navigation Rules

### Back Button Behavior
- Always saves current data before navigating
- Shows "Unsaved changes" warning if needed
- Maintains form state when returning

### Progress Persistence
- Progress saves across browser sessions
- "Resume Project" option on return visits
- Data expires after 7 days

### Exit Points
- "Save & Exit" option on every page
- Auto-save prevents data loss
- Email reminder option for incomplete projects

---

## ✅ Success Indicators

### User Knows They're Making Progress
- Clear step numbers and progress bars
- Completion percentages
- Data validation with immediate feedback
- Success messages at each milestone

### User Feels Confident
- Tooltips explain technical terms
- Examples show what good data looks like
- "Typical range" guidance for inputs
- Preview of final results before calculation

### User Can Recover from Mistakes
- Editable data at every step
- Clear error messages with solutions
- Alternative paths when stuck
- Human support option always visible

---

*This journey map ensures every user interaction is planned and tested before we build it.*
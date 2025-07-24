# AutoHVAC Data Dictionary
*The single source of truth for how we store information*

## 🎯 Why This Matters
Our first version had **5 different ways** to represent the same information. This caused bugs, confusion, and duplicate code. This dictionary defines **ONE way** to store each piece of data throughout the entire application.

---

## 📊 Core Data Models

### ProjectInfo
*Basic project details - same for all projects*

```typescript
{
  id: string,              // Unique project identifier
  projectName: string,     // "Smith Residence", "Office Building A"
  zipCode: string,         // "30301", "10001" (5 digits)
  buildingType: "residential" | "commercial",
  constructionType: "new" | "retrofit",
  inputMethod: "manual" | "blueprint",
  createdAt: Date,
  updatedAt: Date
}
```

**Examples:**
- `{ id: "abc123", projectName: "Jones House", zipCode: "33101", buildingType: "residential", constructionType: "new", inputMethod: "manual" }`

---

### BuildingCharacteristics
*Physical building details*

```typescript
{
  totalSquareFootage: number,     // 2500, 4200 (sq ft)
  foundationType: "slab" | "crawlspace" | "basement" | "pier",
  wallInsulation: "poor" | "average" | "good" | "excellent",
  ceilingInsulation: "poor" | "average" | "good" | "excellent", 
  windowType: "single" | "double" | "triple" | "low-E",
  buildingOrientation: "north" | "south" | "east" | "west",
  stories: number,                // 1, 2, 3
  buildingAge: "new" | "recent" | "older" | "historic"  // <5yr, 5-20yr, 20-40yr, >40yr
}
```

**Examples:**
- `{ totalSquareFootage: 2400, foundationType: "slab", wallInsulation: "good", windowType: "double", stories: 1 }`

---

### Room
*Individual room details*

```typescript
{
  id: string,                    // Unique room identifier
  name: string,                  // "Living Room", "Master Bedroom"
  area: number,                  // Square footage
  ceilingHeight: number,         // 8, 9, 10, 12 (feet)
  exteriorWalls: number,         // 0, 1, 2, 3, 4 (how many walls face outside)
  windowArea: number,            // Total window square footage
  occupants: number,             // Number of people typically in room
  equipmentLoad: number,         // Heat from electronics, appliances (watts)
  roomType: "bedroom" | "bathroom" | "kitchen" | "living" | "dining" | "office" | "other"
}
```

**Examples:**
- `{ id: "room1", name: "Living Room", area: 300, ceilingHeight: 9, exteriorWalls: 2, windowArea: 40, occupants: 4, equipmentLoad: 500, roomType: "living" }`

---

### ClimateData
*Weather information by ZIP code*

```typescript
{
  zipCode: string,               // "30301"
  zone: string,                  // "3A", "4A", "1A" (ASHRAE climate zone)
  heatingDegreeDays: number,     // Annual heating degree days
  coolingDegreeDays: number,     // Annual cooling degree days
  winterDesignTemp: number,      // 99% heating design temperature (°F)
  summerDesignTemp: number,      // 1% cooling design temperature (°F)
  humidity: number               // Summer design humidity ratio
}
```

**Examples:**
- `{ zipCode: "33101", zone: "1A", heatingDegreeDays: 130, coolingDegreeDays: 4000, winterDesignTemp: 47, summerDesignTemp: 91, humidity: 0.018 }`

---

### LoadCalculation
*Results from Manual J calculations*

```typescript
{
  projectId: string,             // Links back to project
  totalCoolingLoad: number,      // Total BTU/hr cooling needed
  totalHeatingLoad: number,      // Total BTU/hr heating needed
  coolingTons: number,           // Cooling load ÷ 12,000
  heatingTons: number,           // Heating load ÷ 12,000
  roomLoads: Array<{
    roomId: string,
    coolingLoad: number,         // BTU/hr for this room
    heatingLoad: number          // BTU/hr for this room
  }>,
  calculatedAt: Date
}
```

**Examples:**
- `{ projectId: "abc123", totalCoolingLoad: 36000, totalHeatingLoad: 28000, coolingTons: 3.0, heatingTons: 2.3 }`

---

### SystemRecommendation
*Equipment recommendations by tier*

```typescript
{
  tier: "economy" | "standard" | "premium",
  coolingSystem: {
    type: string,                // "Central AC", "Heat Pump", "Mini-Split"
    size: number,                // 2.5, 3.0, 4.0 (tons)
    seer: number,                // 14, 16, 20 (efficiency rating)
    brand: string,               // "Carrier", "Trane", "Lennox"
    model: string,               // Specific model number
    estimatedCost: number        // Installation cost estimate
  },
  heatingSystem: {
    type: string,                // "Gas Furnace", "Heat Pump", "Electric"
    size: number,                // BTU/hr capacity
    efficiency: number,          // AFUE or HSPF rating
    brand: string,
    model: string,
    estimatedCost: number
  }
}
```

---

### PDFMetadata (V2+)
*Metadata about uploaded blueprint PDF files*

```typescript
{
  filename: string,                  // "blueprint_abc123.pdf"
  original_filename: string,         // "house_plans.pdf"
  file_size_bytes: number,           // 12582912
  file_size_mb: number,              // 12.0
  page_count: number,                // 3
  uploaded_at: Date,                 // Upload timestamp
  has_text_layer: boolean,           // true if PDF has selectable text
  is_scanned: boolean                // true if appears to be scanned image
}
```

**Examples:**
- `{ filename: "blueprint_abc123.pdf", page_count: 3, file_size_mb: 12.0, has_text_layer: true, is_scanned: false }`

---

### RegexExtractionResult (V2+)
*Results from regex-based pattern matching extraction*

```typescript
{
  // Building characteristics
  floor_area_ft2: number | null,                    // 2400
  wall_insulation: {[key: string]: number} | null,  // {"cavity": 21, "continuous": 5}
  ceiling_insulation: number | null,                // 38 (R-value)
  window_schedule: {[key: string]: any} | null,     // {"total_area": 150, "u_value": 0.30, "shgc": 0.65}
  air_tightness: number | null,                     // 5.0 (ACH50)
  foundation_type: string | null,                   // "slab", "basement", "crawlspace"
  orientation: string | null,                       // "north", "south", "east", "west"
  
  // Room data
  room_dimensions: Array<{[key: string]: any}> | null,  // Room measurements from drawings
  
  // Extraction metadata
  patterns_matched: {[pattern: string]: string[]},   // Which regex patterns matched
  confidence_scores: {[field: string]: number},      // 0.0-1.0 confidence per field
  extraction_notes: string[]                         // Warnings, assumptions made
}
```

**Examples:**
- `{ floor_area_ft2: 2400, wall_insulation: {"cavity": 21}, confidence_scores: {"floor_area_ft2": 0.89} }`

---

### AIExtractionResult (V2+)
*Results from AI-powered visual analysis*

```typescript
{
  // Room analysis
  room_layouts: Array<{[key: string]: any}> | null,     // Room positions, orientations, adjacencies
  window_orientations: {[direction: string]: string[]} | null,  // {"north": ["bedroom1"], "south": ["living"]}
  
  // Building envelope
  building_envelope: {[key: string]: any} | null,       // Wall types, roof details, foundation
  architectural_details: {[key: string]: any} | null,   // Ceiling heights, structural elements
  
  // HVAC existing
  hvac_existing: {[key: string]: any} | null,           // Existing equipment and ductwork
  
  // AI metadata
  model_used: string,                                   // "gpt-4-vision-preview"
  ai_confidence: number,                                // 0.0-1.0 overall confidence
  processing_tokens: number | null,                    // Token usage for cost tracking
  api_cost_usd: number | null,                         // API cost in USD
  visual_analysis_notes: string[],                     // AI reasoning notes
  
  // Enhanced detection
  room_count_detected: number | null,                  // Number of rooms found
  floor_plan_type: string | null,                     // "ranch", "two_story", "split_level"
  architectural_style: string | null                   // "colonial", "modern", etc.
}
```

**Examples:**
- `{ room_count_detected: 4, ai_confidence: 0.87, model_used: "gpt-4-vision-preview", processing_tokens: 1250 }`

---

### CompleteExtractionResult (V2+)
*Complete extraction result with all data and metadata*

```typescript
{
  extraction_id: string,              // "ext123-abc456-def789"
  job_id: string,                     // Links to blueprint job
  
  pdf_metadata: PDFMetadata,          // File information
  raw_text: string,                   // Complete extracted text
  raw_text_by_page: string[],         // Text separated by page
  
  regex_extraction: RegexExtractionResult | null,    // Pattern matching results
  ai_extraction: AIExtractionResult | null,          // AI analysis results
  
  processing_metadata: {
    extraction_timestamp: Date,
    processing_duration_ms: number,
    extraction_version: string,        // "1.2.0"
    extraction_method: string,         // "regex_and_ai_combined"
    errors: string[],
    warnings: string[]
  }
}
```

**Examples:**
- `{ extraction_id: "ext123", job_id: "job456", processing_metadata: { extraction_method: "regex_and_ai_combined", processing_duration_ms: 45000 } }`

---

## 🔄 Data Flow Rules

### 1. **Single Conversion Points**
- Manual input → Standard models (in frontend)
- Blueprint data → Standard models (in backend)
- All calculations use standard models only

### 2. **No Data Transformation in Components** 
- UI components receive data in final format
- No "adapters" or "converters" scattered throughout code
- Data conversion happens at clear boundaries

### 3. **Consistent Units**
- Area: Square feet
- Temperature: Fahrenheit  
- Load: BTU/hr
- Capacity: Tons (1 ton = 12,000 BTU/hr)

---

## ✅ Validation Rules

### Required Fields
- ProjectInfo: All fields required
- BuildingCharacteristics: All fields required  
- Room: id, name, area required; others have defaults
- ClimateData: Auto-populated from ZIP code
- PDFMetadata (V2+): filename, file_size_bytes, page_count, uploaded_at required
- CompleteExtractionResult (V2+): extraction_id, job_id, pdf_metadata, processing_metadata required

### Data Limits
- Room area: 50 - 5000 sq ft
- Total building: 500 - 50,000 sq ft
- Occupants: 0 - 20 per room
- Equipment load: 0 - 5000 watts per room
- PDF file size: Max 100MB
- Blueprint processing: Max 20 rooms detected
- Confidence scores: 0.0 - 1.0 range
- Extraction retention: 7 days default

### Format Rules
- ZIP codes: Exactly 5 digits
- Project names: 3-50 characters
- Room names: 1-30 characters
- Extraction IDs: UUID format (e.g., "abc123-def456-ghi789")
- Job IDs: UUID format
- Blueprint filenames: PDF extension required
- Extraction methods: "regex_only", "ai_only", "regex_and_ai_combined", "fallback"

---

## 🚫 What NOT to Do

❌ **Don't create these variations:**
- `ProjectData`, `ProjectInformation`, `ProjectDetails` (pick ONE name)
- Different field names for same thing (`sqft` vs `squareFootage` vs `area`)
- Different units in different places (BTU vs tons vs kW)

✅ **Do this instead:**
- Use exact names from this dictionary
- Import types from single source file
- Validate data at boundaries using these schemas

---

## 📁 Implementation

**File Structure:**
```
/types/
  ├── project.ts        (ProjectInfo, BuildingCharacteristics)
  ├── room.ts           (Room)
  ├── climate.ts        (ClimateData)
  ├── calculations.ts   (LoadCalculation)
  ├── systems.ts        (SystemRecommendation)
  ├── extraction.ts     (PDFMetadata, RegexExtractionResult, AIExtractionResult)
  ├── blueprint.ts      (CompleteExtractionResult, ExtractionStorageInfo)
  └── index.ts          (Export all types)
```

**Usage:**
```typescript
import { ProjectInfo, Room, LoadCalculation } from '@/types'
import { PDFMetadata, CompleteExtractionResult } from '@/types'
```

---

*This dictionary is law. Every data structure in our app must match these exact definitions.*
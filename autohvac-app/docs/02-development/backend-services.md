# AutoHVAC Backend Services (V2)
*Technical reference for the 4 new backend services added in V2*

## 🎯 Purpose
This document provides detailed information about the backend services that power V2's enhanced blueprint processing and analysis capabilities. Each service has a specific role in the processing pipeline.

---

## 🏗️ Service Architecture Overview

```
Blueprint Upload → PDF Processing → Regex Extraction → AI Analysis → Storage → Results
                      ↓               ↓                ↓            ↓
                 blueprint_extractor  ai_blueprint_   extraction_   enhanced_manual_j_
                      .py            analyzer.py     storage.py    calculator.py
```

---

## 📄 1. BlueprintExtractor Service
**File:** `backend/services/blueprint_extractor.py`

### Purpose
Systematic regex-based extraction of building data from blueprint PDFs using deterministic patterns. Designed for maximum accuracy in Manual J load calculations.

### Key Features
- **Systematic pattern matching** for building characteristics
- **Room dimension extraction** from drawings
- **Insulation value detection** (R-values, U-values)
- **Confidence scoring** for extracted data
- **Multi-page PDF processing**

### Main Methods

#### `extract_building_data(pdf_path: str) -> BuildingData`
Extracts structured building data from blueprint PDF.

**Returns:**
```python
BuildingData(
    floor_area_ft2=2400,
    wall_insulation={"cavity": 21, "continuous": 5},
    ceiling_insulation=38,
    window_schedule={"total_area": 150, "u_value": 0.30, "shgc": 0.65},
    air_tightness=5.0,
    room_dimensions=[{"name": "Living", "area": 250, "perimeter": 64}],
    orientation="north",
    foundation_type="slab",
    confidence_scores={"floor_area_ft2": 0.89}
)
```

### Pattern Categories
- **Insulation patterns**: R-values, U-values, continuous insulation
- **Area patterns**: Conditioned area, room dimensions
- **Window patterns**: Window schedules, glazing specifications
- **Foundation patterns**: Slab, crawlspace, basement indicators
- **HVAC patterns**: Existing equipment, ductwork

### Usage
```python
extractor = BlueprintExtractor()
building_data = await extractor.extract_building_data("blueprint.pdf")
```

---

## 🤖 2. AIBlueprintAnalyzer Service
**File:** `backend/services/ai_blueprint_analyzer.py`

### Purpose
AI-powered visual analysis of blueprint PDFs using OpenAI GPT-4V. Complements regex extraction with intelligent interpretation of visual elements.

### Key Features
- **Visual room layout analysis** 
- **Window orientation detection**
- **Building envelope interpretation**
- **Existing HVAC system identification**
- **Architectural detail extraction**
- **Token usage and cost tracking**

### Main Methods

#### `analyze_blueprint_visual(pdf_path: str) -> AIExtractedData`
Performs visual analysis of blueprint using AI vision model.

**Returns:**
```python
AIExtractedData(
    room_layouts=[{
        "name": "Living Room",
        "dimensions": {"length_ft": 20, "width_ft": 15},
        "windows": [{"orientation": "south", "width_ft": 6}],
        "doors": [{"type": "entry", "width_ft": 3}]
    }],
    window_orientations={"north": ["bedroom1"], "south": ["living"]},
    building_envelope={"wall_type": "frame", "roof_type": "gable"},
    hvac_existing={"equipment": "central_ac", "ductwork": "supply_return"},
    architectural_details={"ceiling_height_ft": 9, "structural": "wood_frame"},
    extraction_confidence=0.87
)
```

### Configuration
- **Model**: GPT-4-vision-preview
- **Max tokens**: 4000
- **Temperature**: 0.1 (deterministic)
- **Image processing**: PDF → PNG conversion

### Usage
```python
analyzer = AIBlueprintAnalyzer(api_key="your-openai-key")
ai_data = await analyzer.analyze_blueprint_visual("blueprint.pdf")
```

### Error Handling
- **API key validation** on initialization
- **Graceful fallback** if AI analysis fails
- **Cost limiting** with configurable thresholds
- **Rate limiting** compliance

---

## 🗄️ 3. ExtractionStorageService
**File:** `backend/services/extraction_storage.py`

### Purpose
Handles persistence, retrieval, and management of JSON extraction data with compression, retention policies, and debugging capabilities.

### Key Features
- **JSON-based storage** with optional compression
- **Automatic retention management** (default 30 days)
- **Version tracking** for extraction algorithms
- **Storage statistics** and health monitoring
- **Test case management**

### Main Methods

#### `save_extraction(extraction_data: CompleteExtractionResult) -> ExtractionStorageInfo`
Saves complete extraction result to disk with metadata.

#### `load_extraction(job_id: str) -> Optional[CompleteExtractionResult]`
Loads extraction data by job ID.

#### `list_extractions(include_expired: bool = False) -> List[ExtractionStorageInfo]`
Lists stored extractions with filtering options.

#### `get_storage_stats() -> Dict[str, Any]`
Returns storage usage and health statistics.

### Storage Structure
```
extractions/
├── active/           # Current extraction data
├── archive/          # Archived/expired data  
└── test_cases/       # Test data for validation
```

### Features
- **Automatic compression** for files >1MB
- **Retention policies** with configurable expiration
- **Access tracking** for usage analytics
- **Storage optimization** with cleanup routines

### Usage
```python
storage = get_extraction_storage()
storage_info = storage.save_extraction(complete_result)
extraction_data = storage.load_extraction(job_id)
```

---

## 🧮 4. EnhancedManualJCalculator
**File:** `backend/services/enhanced_manual_j_calculator.py`

### Purpose
Component-by-component ACCA Manual J 8th Edition implementation following systematic approach for maximum accuracy in load calculations.

### Key Features
- **Detailed component breakdown** (walls, ceiling, windows, infiltration)
- **Room-by-room calculations** with validation
- **Climate zone integration** with proper design conditions
- **Internal load calculations** (occupants, equipment, lighting)
- **Solar heat gain calculations** with orientation factors
- **Validation and error checking**

### Main Methods

#### `calculate_room_loads(room_data: List[Dict], building_data: Dict, climate_data: Dict) -> SystemLoadCalculation`
Performs detailed Manual J calculation for all rooms.

**Returns:**
```python
SystemLoadCalculation(
    project_id="proj123",
    total_heating_btuh=28000,
    total_cooling_btuh=36000,
    heating_tons=2.3,
    cooling_tons=3.0,
    room_loads=[
        RoomLoadBreakdown(
            room_name="Living Room",
            total_heating_btuh=9000,
            total_cooling_btuh=12000,
            components=[
                ComponentLoad(
                    component_type="wall",
                    heating_btuh=2400,
                    cooling_btuh=1800,
                    area_ft2=120,
                    u_factor=0.045
                )
            ]
        )
    ],
    climate_data=climate_data,
    validation_results={"warnings": [], "errors": []},
    calculated_at=datetime.now()
)
```

### Calculation Components
- **Wall loads**: U-factor, area, temperature difference
- **Ceiling loads**: Insulation R-value, attic conditions
- **Window loads**: U-factor, SHGC, solar orientation
- **Infiltration loads**: ACH50, building envelope
- **Internal loads**: Occupants, equipment, lighting
- **Solar loads**: Window orientation, shading, SHGC

### Validation Features
- **Input validation** for reasonable ranges
- **Calculation validation** against industry standards
- **Warning system** for edge cases or assumptions
- **Error detection** for impossible conditions

### Usage
```python
calculator = EnhancedManualJCalculator()
system_loads = calculator.calculate_room_loads(rooms, building, climate)
```

---

## 🔄 Service Integration Flow

### 1. Blueprint Upload Processing
```
1. PDF uploaded → BlueprintExtractor
2. Regex extraction → BuildingData
3. AI analysis → AIExtractedData (parallel)
4. Combine results → CompleteExtractionResult
5. Store data → ExtractionStorageService
6. Return job results
```

### 2. Load Calculation Processing  
```
1. Get extraction data → ExtractionStorageService
2. Convert to calculation format
3. Enhanced Manual J calculation → EnhancedManualJCalculator
4. Return detailed load breakdown
```

### 3. Error Handling Strategy
- **Graceful degradation**: If AI fails, use regex-only
- **Fallback data**: Mock data if all extraction fails
- **Validation checks**: Range validation on all extracted values
- **Logging**: Comprehensive logging for debugging

---

## ⚙️ Configuration

### Environment Variables
```bash
# AI Analysis
OPENAI_API_KEY=your-openai-key
AI_ANALYSIS_ENABLED=true
AI_COST_LIMIT_USD=10.0

# Storage
EXTRACTION_STORAGE_ROOT=./extractions
EXTRACTION_RETENTION_DAYS=30
ENABLE_COMPRESSION=true

# Performance
MAX_PDF_SIZE_MB=100
MAX_PROCESSING_TIME_SECONDS=180
```

### Performance Targets
- **Regex extraction**: <5 seconds
- **AI analysis**: <30 seconds  
- **Storage operations**: <1 second
- **Load calculations**: <10 seconds
- **Total pipeline**: <90 seconds

---

## 🔧 Monitoring and Debugging

### Health Checks
Each service provides health status through the `/health` endpoint:
- **Storage usage** and available space
- **AI API** connectivity and quota
- **Processing times** and error rates
- **Queue status** and job backlog

### Debug Endpoints
- `/api/v2/blueprint/extraction/{job_id}` - Raw extraction data
- `/api/v2/blueprint/extraction-list` - List all stored extractions
- `/api/v2/blueprint/storage-stats` - Storage usage statistics

### Common Issues
- **AI API key missing**: Check `OPENAI_API_KEY` environment variable
- **PDF too large**: Reduce file size below 100MB limit
- **Low confidence scores**: Blueprint may need manual review
- **Storage full**: Clean up expired extractions

---

*These services work together to provide accurate, fast, and reliable blueprint processing in AutoHVAC V2.*
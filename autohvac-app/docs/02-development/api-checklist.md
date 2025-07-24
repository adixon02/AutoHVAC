# AutoHVAC API Checklist
*Simple endpoint reference to prevent frontend/backend confusion*

## 🎯 Why This Matters
Our first version had frontend expecting different data than backend provided. This checklist shows exactly what each endpoint does, preventing miscommunication and integration issues.

---

## 📋 API Overview

### Base URL
- **Development**: `http://localhost:8000`
- **Production**: `https://api.autohvac.com`

### Common Headers
```
Content-Type: application/json
Accept: application/json
```

### Error Response Format
All endpoints return errors in this format:
```json
{
  "error": true,
  "message": "Human-readable error description",
  "code": "ERROR_CODE",
  "details": {} // Optional additional context
}
```

---

## 🌡️ Climate Data (V1)

### GET /api/climate/{zipCode}
**What it does:** Get climate data for load calculations

**Input:**
- URL parameter: `zipCode` (5-digit string)

**Success Response (200):**
```json
{
  "zipCode": "30301",
  "zone": "3A",
  "heatingDegreeDays": 2800,
  "coolingDegreeDays": 1800,
  "winterDesignTemp": 22,
  "summerDesignTemp": 91,
  "humidity": 0.016
}
```

**Error Responses:**
- **400**: Invalid ZIP code format
- **404**: ZIP code not found in database
- **500**: Climate service unavailable

**Frontend Usage:**
- Called automatically when user enters ZIP code
- Used to validate ZIP codes and show climate zone preview
- Data stored locally for calculations

---

## 🧮 Manual Calculations (V1)

### POST /api/calculate
**What it does:** Perform Manual J load calculations

**Input Body:**
```json
{
  "project": {
    "projectName": "Smith House",
    "zipCode": "30301",
    "buildingType": "residential",
    "constructionType": "new"
  },
  "building": {
    "totalSquareFootage": 2400,
    "foundationType": "slab",
    "wallInsulation": "good",
    // ... all BuildingCharacteristics fields
  },
  "rooms": [
    {
      "name": "Living Room",
      "area": 300,
      "ceilingHeight": 9,
      // ... all Room fields
    }
  ]
}
```

**Success Response (200):**
```json
{
  "loadCalculation": {
    "totalCoolingLoad": 36000,
    "totalHeatingLoad": 28000,
    "coolingTons": 3.0,
    "heatingTons": 2.3,
    "roomLoads": [
      {
        "roomName": "Living Room",
        "coolingLoad": 12000,
        "heatingLoad": 9000
      }
    ]
  },
  "recommendations": [
    {
      "tier": "economy",
      "coolingSystem": {
        "type": "Central AC",
        "size": 3.0,
        "seer": 14,
        "estimatedCost": 4500
      },
      "heatingSystem": {
        "type": "Gas Furnace",
        "size": 80000,
        "efficiency": 80,
        "estimatedCost": 3200
      }
    }
    // ... standard and premium tiers
  ]
}
```

**Error Responses:**
- **400**: Invalid input data (missing fields, invalid ranges)
- **422**: Calculation constraints not met (rooms too large, impossible loads)
- **500**: Calculation engine error

**Frontend Usage:**
- Called when user clicks "Calculate Results"
- Shows loading spinner during processing
- Results display immediately on success

---

## 📄 Blueprint Processing (V2)

### POST /api/v2/blueprint/upload
**What it does:** Upload blueprint PDF and start AI processing

**Input:**
- `multipart/form-data` with file upload
- File field name: `file`
- Required fields: `zip_code`, `project_name`, `building_type`, `construction_type`

**Success Response (200):**
```json
{
  "job_id": "abc123-def456-ghi789",
  "message": "Blueprint uploaded successfully",
  "status": "processing"
}
```

**Error Responses:**
- **400**: No file provided or invalid file type
- **413**: File too large (>100MB)
- **422**: Corrupted PDF or unreadable format
- **500**: Upload service unavailable

**Frontend Usage:**
- Called when user drops file or clicks upload
- job_id used for polling status
- Shows upload progress bar

---

### GET /api/v2/blueprint/status/{job_id}
**What it does:** Check processing status of uploaded blueprint

**Input:**
- URL parameter: `job_id`

**Success Response (200):**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "processing", // "processing", "completed", "failed"
  "progress": 65, // 0-100
  "message": "Extracting room information..."
}
```

**When status="completed":**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "completed",
  "progress": 100,
  "message": "Blueprint processing complete"
}
```

**When status="failed":**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "failed",
  "progress": 0,
  "message": "Could not extract room data from blueprint"
}
```

**Error Responses:**
- **404**: Job ID not found
- **500**: Status service unavailable

**Frontend Usage:**
- Polled every 3 seconds during processing
- Updates progress bar and status message
- Stops polling when status is "completed" or "failed"

---

### GET /api/v2/blueprint/results/{job_id}
**What it does:** Get extracted blueprint data and calculations

**Input:**
- URL parameter: `job_id`

**Success Response (200):**
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "completed",
  "project_info": {
    "zip_code": "30301",
    "project_name": "Blueprint Project",
    "building_type": "residential",
    "construction_type": "new"
  },
  "results": {
    "total_area": 2400,
    "rooms": [
      {
        "name": "Living Room",
        "area": 300,
        "height": 10,
        "windows": 3,
        "exterior_walls": 2
      }
    ],
    "building_data": {
      "floor_area_ft2": 2400,
      "wall_insulation": {"effective_r": 19},
      "ceiling_insulation": 38,
      "window_schedule": {"u_value": 0.30, "shgc": 0.65},
      "air_tightness": 5.0,
      "foundation_type": "slab"
    },
    "building_details": {
      "floors": 1,
      "foundation_type": "slab",
      "roof_type": "standard"
    },
    "confidence_scores": {
      "floor_area_ft2": 0.89,
      "wall_insulation": 0.75
    },
    "extraction_method": "regex_based"
  }
}
```

**Error Responses:**
- **404**: Job ID not found or results not ready
- **422**: Processing failed, no results available
- **500**: Results service unavailable

**Frontend Usage:**
- Called when status polling shows "completed"
- Used to populate review/correction interface
- Pre-fills calculation results if user approves data

---

### GET /api/v2/blueprint/extraction/{job_id}
**What it does:** Get raw extraction data for debugging

**Input:**
- URL parameter: `job_id`
- Query parameter: `include_raw_text` (boolean, optional)

**Success Response (200):**
```json
{
  "extraction_id": "ext123-abc456",
  "job_id": "abc123-def456-ghi789",
  "extraction_summary": {
    "extraction_method": "regex_and_ai_combined",
    "processing_duration_ms": 45000,
    "confidence_overall": 0.82,
    "extraction_version": "1.2.0"
  },
  "raw_extraction_data": {
    "pdf_metadata": {
      "filename": "blueprint.pdf",
      "page_count": 3,
      "file_size_mb": 12.5,
      "has_text_layer": true
    },
    "regex_extraction": {
      "floor_area_ft2": 2400,
      "confidence_scores": {"floor_area_ft2": 0.89}
    },
    "ai_extraction": {
      "room_layouts": [...],
      "ai_confidence": 0.85
    }
  },
  "available_reprocessing_options": [
    "regex_only",
    "ai_only", 
    "regex_and_ai_combined"
  ]
}
```

**Error Responses:**
- **404**: Extraction data not found
- **500**: Failed to retrieve extraction data

---

### GET /api/v2/blueprint/extraction-list
**What it does:** List stored extraction data for debugging

**Input:**
- Query parameter: `include_expired` (boolean, optional)
- Query parameter: `limit` (integer, max 100, optional)

**Success Response (200):**
```json
{
  "extractions": [
    {
      "extraction_id": "ext123-abc456",
      "job_id": "abc123-def456-ghi789",
      "created_at": "2024-01-15T10:30:00Z",
      "file_size_mb": 12.5,
      "is_compressed": true,
      "access_count": 3,
      "last_accessed": "2024-01-15T11:00:00Z",
      "expires_at": "2024-01-22T10:30:00Z"
    }
  ],
  "total_count": 1,
  "include_expired": false
}
```

---

### POST /api/v2/blueprint/reprocess/{job_id}
**What it does:** Reprocess extraction data using different analysis methods

**Input:**
- URL parameter: `job_id`
- Body (optional):
```json
{
  "reprocessing_method": "ai_only", // "regex_only", "ai_only", "regex_and_ai_combined"
  "force_ai_reanalysis": false
}
```

**Success Response (200):**
```json
{
  "job_id": "abc123-def456-ghi789",
  "new_extraction_id": "ext456-def789",
  "original_extraction_id": "ext123-abc456",
  "reprocessing_method": "ai_only",
  "processing_duration_ms": 30000,
  "message": "Reprocessing completed successfully"
}
```

---

### DELETE /api/v2/blueprint/extraction/{job_id}
**What it does:** Delete extraction data

**Input:**
- URL parameter: `job_id`

**Success Response (200):**
```json
{
  "message": "Extraction data deleted for job abc123-def456-ghi789"
}
```

**Error Responses:**
- **404**: Extraction data not found
- **500**: Failed to delete extraction data

---

## 📊 Report Generation (V1)

### POST /api/reports/generate
**What it does:** Generate professional PDF report

**Input Body:**
```json
{
  "project": { /* ProjectInfo */ },
  "building": { /* BuildingCharacteristics */ },
  "rooms": [ /* Room array */ ],
  "loadCalculation": { /* LoadCalculation */ },
  "selectedRecommendation": { /* SystemRecommendation */ }
}
```

**Success Response (200):**
```json
{
  "reportUrl": "/api/reports/download/report_abc123.pdf",
  "expiresAt": "2024-01-15T10:30:00Z" // 24 hours from generation
}
```

**Error Responses:**
- **400**: Missing required calculation data
- **500**: PDF generation service unavailable

**Frontend Usage:**
- Called when user clicks "Download Report"
- Report URL opens in new tab for download
- Shows generation progress if needed

---

## 🔧 System Health (All Versions)

### GET /api/health
**What it does:** Check if API is running and healthy

**Success Response (200):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "database": "healthy",
    "calculations": "healthy",
    "ai": "healthy" // V2+
  }
}
```

**Error Responses:**
- **503**: Service unavailable (API starting up or maintenance)

**Frontend Usage:**
- Called on app startup to verify API availability
- Used by monitoring systems
- Can show "Service Unavailable" page if needed

---

## 📝 Implementation Notes

### Authentication (V1: None, V2+: Required)
- V1: No authentication required
- V2+: JWT tokens in Authorization header
- Include auth requirements in each endpoint doc

### Rate Limiting
- 100 requests per minute per IP
- Higher limits for authenticated users
- Blueprint processing has separate queue limits

### CORS Configuration
```javascript
// Development
Access-Control-Allow-Origin: http://localhost:3000

// Production  
Access-Control-Allow-Origin: https://autohvac.com
```

### Response Time Targets
- `/api/climate/*`: <200ms
- `/api/calculate`: <1000ms
- `/api/blueprint/upload`: <5000ms
- `/api/blueprint/status`: <100ms
- `/api/reports/generate`: <3000ms

---

## ✅ Testing Checklist

For each endpoint, verify:
- ✅ Success response matches documented format exactly
- ✅ All documented error codes return proper error format
- ✅ Input validation rejects invalid data with helpful messages
- ✅ Response times meet targets under normal load
- ✅ CORS headers allow frontend domain
- ✅ Large file uploads work (blueprint processing)

---

## 🚀 Development Workflow

### API-First Development
1. **Define** endpoint in this document
2. **Review** with frontend developer
3. **Build** backend endpoint with tests
4. **Test** with actual frontend integration
5. **Document** any changes back to this file

### Change Management
- All API changes require updating this document
- Breaking changes need version increment
- Backward compatibility maintained for 3 months minimum

---

*This checklist is the contract between frontend and backend. Follow it exactly to prevent integration issues.*
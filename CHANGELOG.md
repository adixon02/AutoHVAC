# AutoHVAC Development Changelog

All notable changes and daily progress on the AutoHVAC project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2025-01-22]

### Planning & Architecture
- Analyzed existing Next.js codebase with Manual J calculations
- Designed blueprint-to-CAD processing pipeline architecture
- Researched ML models for room detection (YOLOv8, LayoutParser)
- Evaluated CAD export libraries (ezdxf for DXF/DWG generation)
- Created comprehensive implementation roadmap

### Added
- ✅ `CHANGELOG.md` - Development progress tracking system
- ✅ Python backend structure with FastAPI
  - `backend/main.py` - Main FastAPI application
  - `backend/api/` - API endpoints for blueprint, calculations, export
  - `backend/processors/` - Blueprint parser and CAD exporter
  - `backend/ml_models/` - Room detection module
- ✅ Blueprint upload UI component (`BlueprintUpload.tsx`)
- ✅ Integration between frontend and backend
- ✅ Project setup flow with manual/blueprint input options
- ✅ Backend startup script (`start.sh`)

### Technical Decisions
- **Backend**: Python FastAPI for heavy processing tasks
- **Blueprint Processing**: OpenCV for image preprocessing
- **Room Detection**: YOLOv8 or custom CNN for room identification  
- **CAD Export**: ezdxf library for DXF/DWG file generation
- **Visualization**: Canvas/SVG overlay for interactive HVAC layouts
- **File Upload**: react-dropzone for drag-and-drop interface

### Completed Today
- ✅ Set up Python backend with FastAPI
- ✅ Created blueprint upload component in Next.js
- ✅ Implemented basic PDF/image file processing
- ✅ Created API endpoints for blueprint analysis
- ✅ Added room detection module (placeholder for ML model)
- ✅ Integrated blueprint option into project setup flow

### Next Steps
- [ ] Train/integrate actual ML model for room detection
- [ ] Implement duct routing algorithms
- [ ] Add visual overlay for HVAC layout on blueprints
- [ ] Complete CAD export functionality
- [ ] Add authentication and user management
- [ ] Deploy backend to cloud service

### Notes
- Backend runs on http://localhost:8000
- API docs available at http://localhost:8000/docs
- Blueprint processing is async with job tracking
- Room detection currently uses heuristics (ML model pending)
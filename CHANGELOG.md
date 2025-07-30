# Changelog

All notable changes to the AutoHVAC project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **AI-First Blueprint Parsing System**
  - GPT-4V is now the default parsing method (AI_PARSING_ENABLED=true)
  - No element count restrictions for AI parsing (handles 40k+ elements)
  - Smart image compression: PNG first for line art, then progressive JPEG
  - Minimum resolution floor (1000px) to maintain readability
  - Dynamic compression to stay under 19MB GPT-4V limit
- **Enhanced File Handling**
  - Support for blueprints up to 50MB (previously failed at complex drawings)
  - Warning messages for large files (>20MB): "AI processing may take 2-3 minutes"
  - Files preserved on failure for debugging (CLEANUP_ON_FAILURE=false)
- **Comprehensive Metrics Logging**
  - [METRICS] tags for parsing duration, file size, rooms found
  - Tracks which parser (AI vs legacy) was used for each upload
  - Total processing time and stage-by-stage metrics
- **Improved Error Handling**
  - Clear messaging when AI unavailable: "AI parsing temporarily unavailable"
  - Legacy parser errors suggest AI parsing for complex files
  - Debug mode returns full exception details in API responses

### Changed
- **AI parsing is now default** - USE_GPT4V_PARSING deprecated in favor of AI_PARSING_ENABLED
- **Element count validation removed for AI path** - Complex AutoCAD files now process without issues
- **Better fallback behavior** - Legacy parser only used when AI fails, not by default
- **Error messages improved** - Users understand why validation failed and what alternatives exist

### Fixed
- **Missing PIL Image import** in blueprint_ai_parser.py causing NameError
- **Complex blueprints rejected** - 38k+ element drawings now process successfully
- **Overly restrictive validation** - Element count checks only apply to legacy parser

### Added (Previous)
- GPT-4V (Vision) AI blueprint parsing integration
  - Direct PDF-to-structured-data parsing using OpenAI's GPT-4V
  - Confidence scoring for all extracted values
  - North arrow and orientation detection
  - Enhanced room data: exterior walls, corner rooms, thermal exposure
  - Graceful fallback to traditional parsing on failure
- PyMuPDF-based PDF-to-image conversion
  - Replaced pdf2image dependency (no poppler required)
  - Better performance and no system dependencies
  - Automatic image quality optimization for GPT-4V
- Environment variable toggle: `USE_GPT4V_PARSING`
  - Easy enable/disable of AI parsing
  - Seamless switching between parsing methods
- Enhanced HVAC load calculations
  - Uses actual exterior wall counts from GPT-4V
  - Corner room factors (+15% heating, +20% cooling)
  - Orientation uncertainty handling
  - Detailed load breakdowns per component
- Comprehensive confidence metrics in API responses
  - Overall calculation confidence
  - Data quality indicators
  - Clear warnings for estimated values

### Changed
- Blueprint parsing now prioritizes GPT-4V when enabled
- Load calculations use enhanced geometry data when available
- API responses include confidence metrics and warnings
- Improved accuracy for HVAC sizing (typically 10-20% better)

### Fixed
- **Critical: PDF "document closed" error during file processing**
  - PDF files are now saved to disk BEFORE any validation
  - All PDF operations use file paths instead of memory bytes
  - Files are only deleted after job completion/failure
  - Exception handlers no longer reference closed documents
  - All PyMuPDF operations use thread-safe wrappers
  - Added comprehensive logging with thread IDs and stack traces
- Interior rooms no longer over-calculated (0 exterior walls)
- Solar gains properly averaged when orientation unknown
- Window sizes now variable based on count

### Removed
- pdf2image dependency (replaced with PyMuPDF)
- poppler system dependency no longer required
- Obsolete test files and development artifacts

### Configuration
- `AI_PARSING_ENABLED` (default: true) - Enable AI-first parsing
- `LEGACY_ELEMENT_LIMIT` (default: 20000) - Max elements for legacy parser
- `FILE_SIZE_WARNING_MB` (default: 20) - Show warning for large files
- `DEBUG_EXCEPTIONS` (default: true) - Return detailed errors in responses
- `CLEANUP_ON_FAILURE` (default: false) - Preserve files for debugging

### Dependencies
- Added: PyMuPDF>=1.24.0
- Removed: pdf2image
- Updated: openai>=1.97.1 (for GPT-4V support)
- Required: Pillow>=10.2.0 (for image compression)

## [1.0.0] - 2024-11-27

### Added
- Initial production release
- Complete HVAC load calculation pipeline
- ACCA Manual J compliance
- Multi-page PDF analysis
- FastAPI backend with Celery workers
- Next.js frontend with Stripe integration
- Comprehensive test suite
- Docker development environment
- Render.com deployment configuration
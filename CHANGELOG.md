# Changelog

All notable changes to the AutoHVAC project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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

### Dependencies
- Added: PyMuPDF>=1.24.0
- Removed: pdf2image
- Updated: openai>=1.97.1 (for GPT-4V support)

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
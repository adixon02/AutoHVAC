# Changelog

All notable changes to the AutoHVAC project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Zero-Friction "First Report Free" User Experience**
  - Completely removed email verification requirements for all users
  - Users can upload first blueprint with just email (no password, no verification)
  - Dashboard accessible with email-only parameter (no authentication required)
  - Implemented backend-enforced paywall after free report usage
  - Added `/users/{email}/can-upload` endpoint for eligibility checking
  - Created professional PaywallModal component with Stripe integration
  - Streamlined upload flow with email collection moved to step 2
  - Added share functionality to results page with copyable links
  - Enhanced spam email validation with comprehensive domain/pattern blocking
  - All paywall logic enforced server-side (no client-side bypasses possible)
  - Deprecated `require_verified()` method - verification no longer required
  - Added `can_upload_new_report()` method to UserService for centralized logic
  - Integrated PaywallModal into both dashboard and upload flows
  - 402 Payment Required responses automatically trigger upgrade modal
  - Share reports via email or copyable link for viral growth

### Added (Previous)
- **"First Report Free" Flow with Payment Gating**
  - First blueprint upload proceeds without email verification requirement
  - Automatic user creation on first upload for frictionless experience
  - Subsequent uploads require Stripe subscription with clear payment gate
  - Structured 402 Payment Required responses with upgrade benefits
  - Graceful handling of existing subscribers (unlimited uploads)
- **Enhanced Email Notifications**
  - New `send_report_ready_with_upgrade_cta()` method in email service
  - Report completion emails with strong upgrade CTAs
  - Customer testimonials and value propositions in emails
  - Limited-time offer messaging (20% off) for conversions
  - Different templates for first-time vs returning users
- **Analytics Tracking for User Insights**
  - Added fields to projects table: `client_ip`, `user_agent`, `referrer`
  - Captures analytics data on first upload for attribution
  - Browser fingerprinting support for future expansion
  - Marketing attribution through referrer tracking
- **Frontend API Enhancements**
  - Job status endpoint returns `upgrade_prompt` object for completed jobs
  - Structured data for frontend modals with benefits and CTAs
  - Clear messaging about free report usage and upgrade path
- **Email Validation**
  - Basic regex validation to prevent spam signups
  - Blocks common spam patterns (test@test.com, asdf@asdf.com)
  - Blocks disposable email domains (mailinator, throwaway)
  - Still allows first report even with less common email providers
- **Comprehensive Utility Functions**
  - `check_free_report_eligibility()`: Detailed eligibility checking
  - `sync_check_is_first_report()`: Synchronous version for Celery workers
  - Returns detailed status including email verification and subscription state
- **Database Migrations**
  - Migration for analytics tracking fields
  - Backward compatible with existing deployments
- **Organized Storage Directory Structure**
  - New `/var/data` subdirectories: `uploads/`, `processed/`, `reports/`, `temp/`
  - Automatic directory initialization with permission checks on startup
  - Storage service handles all file operations with proper error handling
  - Backward compatibility for existing files
- **Automated File Cleanup System**
  - Scheduled Celery tasks for automatic file cleanup
  - Configurable retention periods via environment variables
  - `cleanup_temp_files`: Runs every 6 hours (6-hour retention)
  - `cleanup_old_uploads`: Runs daily at 2 AM (30-day retention)
  - `cleanup_old_processed`: Runs weekly on Mondays (90-day retention)
- **Storage Service Enhancements**
  - New methods: `save_processed_data()`, `save_report()`, `get_temp_dir()`, `cleanup_temp()`
  - Centralized file path management
  - Thread-safe operations with proper locking
- **Migration Support**
  - One-time migration script for existing files (`scripts/migrate_storage.py`)
  - Dry-run mode for safe testing
  - Comprehensive logging of migration process
- **Environment Variables for Cleanup**
  - `STORAGE_CLEANUP_ENABLED`: Enable/disable automated cleanup
  - `TEMP_RETENTION_HOURS`: Hours to keep temporary files (default: 6)
  - `UPLOAD_RETENTION_DAYS`: Days to keep uploaded PDFs (default: 30)
  - `PROCESSED_RETENTION_DAYS`: Days to keep processed data (default: 90)

### Changed
- **Upload Flow** - Email verification now only required after free report is used
- **User Creation** - Users automatically created on first upload (no pre-registration needed)
- **API Responses** - Upload endpoint returns structured payment data on 402 status
- **Email Service** - Enhanced with upgrade-focused messaging and CTAs
- **Job Status API** - Returns upgrade prompts for users who've used free report
- **PDF Reports** now saved to dedicated `reports/` directory
- **Download endpoints** handle both legacy (full path) and new (relative path) formats
- **File operations** now use centralized storage service
- **Cleanup tasks** run as scheduled jobs, not on-demand (prevents race conditions)

### Fixed
- **File organization** - Clear separation between uploads, processed data, and reports
- **Cleanup race conditions** - Files no longer deleted during active processing
- **Storage permissions** - All directories tested for write access on startup

### Added (Previous)
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

### Changed (Previous)
- **AI parsing is now default** - USE_GPT4V_PARSING deprecated in favor of AI_PARSING_ENABLED
- **Element count validation removed for AI path** - Complex AutoCAD files now process without issues
- **Better fallback behavior** - Legacy parser only used when AI fails, not by default
- **Error messages improved** - Users understand why validation failed and what alternatives exist

### Fixed (Previous)
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
# File Storage Configuration for AutoHVAC

## Problem Summary
PDF files were disappearing from `/tmp` before the Celery worker could process them because:
1. FastAPI backend and Celery worker run in separate containers with isolated file systems
2. Files saved to `/tmp` in one container are not accessible from another container
3. No shared persistent storage was configured between the services

## Solution Implemented

### 1. Shared Persistent Storage
- Both `autohvac-backend` and `autohvac-worker` services now use the same persistent disk named `shared-storage`
- The disk is mounted at `/var/data` with 10GB of storage
- Files are stored in `/var/data/uploads` subdirectory

### 2. Environment Configuration
- Added `RENDER_DISK_PATH=/var/data/uploads` to both services
- Storage service now validates the path is writable on startup
- Falls back to `/tmp` only if persistent storage fails

### 3. File Lifecycle Management
- Removed automatic cleanup from `sync_set_project_completed` and `sync_set_project_failed`
- Files are now preserved until explicitly cleaned up
- Added `cleanup_completed_project` method for manual/scheduled cleanup
- File cleanup should only happen after all processing is complete

### 4. Retry Logic
- Celery task now retries file existence check up to 5 times with 2-second delays
- This handles potential delays in file system synchronization on cold starts
- Extensive logging added for debugging file access issues

## Local vs Production Differences

### Local Development (Docker Compose)
- Services share volumes through Docker Compose volume mounts
- File system is immediately consistent
- Uses local directory (e.g., `./uploads`) for storage

### Production (Render)
- Services run in separate containers/instances
- Shared persistent disk provides common storage
- Potential for slight delays in file visibility across containers
- Uses `/var/data/uploads` for storage

## Configuration Checklist

### For Local Development
1. Add to `.env`:
   ```
   RENDER_DISK_PATH=./uploads
   ```
2. Ensure the directory exists and is writable

### For Production (Render)
1. `render.yaml` is already configured with:
   - Shared disk mount for both services
   - RENDER_DISK_PATH environment variable
   - Same disk name (`shared-storage`) for both services

## Monitoring
- Check logs for `[STORAGE]` tags to track file operations
- Monitor `[CELERY START]` logs for file existence checks
- Look for retry attempts if files are not immediately available

## Troubleshooting
1. If files are still not found:
   - Check that both services have the same `RENDER_DISK_PATH`
   - Verify the disk is properly mounted in Render dashboard
   - Check file permissions on the storage directory

2. For debugging:
   - Files are preserved on failure for investigation
   - Check the logged file paths and directory listings
   - Verify the storage path initialization logs
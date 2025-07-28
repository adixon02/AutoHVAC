#!/usr/bin/env python3
"""
Smoke test for AutoHVAC pipeline
Tests the full flow: upload -> processing -> completion
"""
import requests
import time
import sys
import logging
from io import BytesIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "https://autohvac-backend.onrender.com"
TEST_EMAIL = "test@example.com"
TIMEOUT_SECONDS = 300  # 5 minutes
POLL_INTERVAL = 5  # 5 seconds

def create_dummy_pdf():
    """Create a minimal valid PDF for testing"""
    # Minimal PDF content
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Blueprint) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000125 00000 n 
0000000185 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
279
%%EOF"""
    return pdf_content

def upload_blueprint():
    """Upload a test blueprint and return job ID"""
    try:
        logger.info("📤 Uploading test blueprint...")
        
        pdf_content = create_dummy_pdf()
        
        files = {
            'file': ('test_blueprint.pdf', BytesIO(pdf_content), 'application/pdf')
        }
        
        data = {
            'email': TEST_EMAIL,
            'project_label': 'Smoke Test Project',
            'duct_config': 'ducted_attic',
            'heating_fuel': 'gas'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/blueprint/upload",
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"❌ Upload failed: {response.status_code} - {response.text}")
            return None
            
        result = response.json()
        job_id = result.get('job_id')
        
        if not job_id:
            logger.error(f"❌ No job_id in response: {result}")
            return None
            
        logger.info(f"✅ Upload successful, job_id: {job_id}")
        return job_id
        
    except Exception as e:
        logger.exception(f"❌ Upload error: {e}")
        return None

def poll_job_status(job_id):
    """Poll job status until completion or timeout"""
    try:
        logger.info(f"🔄 Polling job status for {job_id}...")
        start_time = time.time()
        
        while time.time() - start_time < TIMEOUT_SECONDS:
            try:
                response = requests.get(
                    f"{BASE_URL}/api/v1/job/{job_id}",
                    timeout=10
                )
                
                if response.status_code == 404:
                    logger.warning(f"⚠️  Job not found: {job_id}")
                    time.sleep(POLL_INTERVAL)
                    continue
                    
                if response.status_code != 200:
                    logger.error(f"❌ Status check failed: {response.status_code} - {response.text}")
                    return False
                    
                job_data = response.json()
                status = job_data.get('status')
                error = job_data.get('error')
                
                logger.info(f"📊 Job {job_id} status: {status}")
                
                if status == 'completed':
                    logger.info("✅ Job completed successfully!")
                    logger.info(f"📋 Result keys: {list(job_data.get('result', {}).keys()) if job_data.get('result') else 'No result'}")
                    return True
                    
                elif status == 'failed':
                    logger.error(f"❌ Job failed: {error}")
                    return False
                    
                elif status in ['pending', 'processing']:
                    logger.info(f"⏳ Job {status}, waiting...")
                    time.sleep(POLL_INTERVAL)
                    continue
                    
                else:
                    logger.warning(f"⚠️  Unknown status: {status}")
                    time.sleep(POLL_INTERVAL)
                    continue
                    
            except requests.RequestException as e:
                logger.warning(f"⚠️  Request error: {e}, retrying...")
                time.sleep(POLL_INTERVAL)
                continue
                
        logger.error(f"❌ Timeout after {TIMEOUT_SECONDS} seconds")
        return False
        
    except Exception as e:
        logger.exception(f"❌ Polling error: {e}")
        return False

def run_smoke_test():
    """Run the complete smoke test"""
    logger.info("🚀 Starting AutoHVAC smoke test...")
    
    # Test 1: Upload blueprint
    job_id = upload_blueprint()
    if not job_id:
        logger.error("❌ Upload test failed")
        return False
    
    # Test 2: Poll until completion
    if not poll_job_status(job_id):
        logger.error("❌ Job processing test failed")
        return False
    
    logger.info("🎉 Smoke test completed successfully!")
    return True

if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)
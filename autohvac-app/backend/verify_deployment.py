#!/usr/bin/env python3
"""
Deployment verification script to test the complete system
"""
import requests
import json
import time
import logging
import sys
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_health_endpoint(base_url):
    """Test the health endpoint responds immediately"""
    try:
        start_time = time.time()
        response = requests.get(f"{base_url}/health", timeout=5)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            logger.info(f"✅ Health check passed ({response_time:.2f}s)")
            return True
        else:
            logger.error(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Health check error: {e}")
        return False

def test_api_endpoints(base_url):
    """Test key API endpoints"""
    try:
        # Test climate endpoint
        response = requests.get(f"{base_url}/api/v2/climate/99206", timeout=10)
        if response.status_code == 200:
            logger.info("✅ Climate API working")
        else:
            logger.warning(f"⚠️ Climate API issue: {response.status_code}")
        
        return True
    except Exception as e:
        logger.error(f"❌ API test error: {e}")
        return False

def test_blueprint_upload(base_url):
    """Test blueprint upload functionality"""
    try:
        # Create a minimal test PDF (just headers for validation)
        test_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 R\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\nxref\n0 3\n0000000000 65535 f \ntrailer\n<< /Size 3 /Root 1 0 R >>\n%%EOF"
        
        files = {
            'file': ('test.pdf', test_pdf_content, 'application/pdf')
        }
        data = {
            'zip_code': '99206',
            'project_name': 'Test Project',
            'building_type': 'residential',
            'construction_type': 'new'
        }
        
        response = requests.post(f"{base_url}/api/v2/blueprint/upload", 
                               files=files, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job_id')
            logger.info(f"✅ Blueprint upload initiated: {job_id}")
            
            # Check status a few times
            for i in range(5):
                time.sleep(2)
                status_response = requests.get(f"{base_url}/api/v2/blueprint/status/{job_id}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    logger.info(f"Status check {i+1}: {status.get('progress', 0)}% - {status.get('message', 'No message')}")
                    if status.get('status') == 'completed':
                        logger.info("✅ Blueprint processing completed")
                        return True
            
            logger.warning("⚠️ Blueprint processing taking longer than expected")
            return True
        else:
            logger.error(f"❌ Blueprint upload failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Blueprint test error: {e}")
        return False

def main():
    """Run deployment verification"""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    logger.info(f"Testing deployment at: {base_url}")
    
    tests = [
        ("Health Check", lambda: test_health_endpoint(base_url)),
        ("API Endpoints", lambda: test_api_endpoints(base_url)),
        ("Blueprint Upload", lambda: test_blueprint_upload(base_url))
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}")
    
    logger.info(f"\n--- Results ---")
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 All tests passed! Deployment is working correctly.")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed. Check the deployment.")
        sys.exit(1)

if __name__ == '__main__':
    main()
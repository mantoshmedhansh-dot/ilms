#!/usr/bin/env python3
"""
Test Phase 1 multi-tenant API endpoints
"""
import requests
import time
import sys

# Test tenant ID from previous step
TENANT_ID = "f1aa6a6a-ee69-414b-b11e-67032a27d52a"
BASE_URL = "http://localhost:8000/api/v1"

def wait_for_server(max_attempts=30):
    """Wait for server to be ready"""
    print("Waiting for server to start...")
    for i in range(max_attempts):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print("✅ Server is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
        if (i + 1) % 5 == 0:
            print(f"  Still waiting... ({i+1}/{max_attempts})")
    print("❌ Server failed to start")
    return False

def test_endpoint(name, url, headers, expected_status, should_contain=None):
    """Test a single endpoint"""
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")
    print(f"URL: {url}")
    print(f"Headers: {headers}")

    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.json()}")

        # Check status code
        if response.status_code == expected_status:
            print(f"✅ Status code matches expected: {expected_status}")
        else:
            print(f"❌ Expected status {expected_status}, got {response.status_code}")
            return False

        # Check response contains expected text
        if should_contain:
            response_text = str(response.json())
            if should_contain in response_text:
                print(f"✅ Response contains: '{should_contain}'")
            else:
                print(f"❌ Response does not contain: '{should_contain}'")
                return False

        return True

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    print("="*70)
    print("PHASE 1 API TESTING")
    print("="*70)
    print(f"Tenant ID: {TENANT_ID}")
    print(f"Base URL: {BASE_URL}")

    # Wait for server
    if not wait_for_server():
        print("\n❌ Server not available. Please start the server first:")
        print("  cd /Users/mantosh/Desktop/ilms.ai")
        print("  source .venv/bin/activate")
        print("  uvicorn app.main:app --reload --port 8000")
        sys.exit(1)

    headers_with_tenant = {"X-Tenant-ID": TENANT_ID}
    headers_without_tenant = {}

    results = []

    # Test 1: Get tenant info
    results.append(test_endpoint(
        "Get Tenant Info",
        f"{BASE_URL}/test/tenant/info",
        headers_with_tenant,
        200,
        "Test Company"
    ))

    # Test 2: Get enabled modules
    results.append(test_endpoint(
        "Get Enabled Modules",
        f"{BASE_URL}/test/modules/enabled",
        headers_with_tenant,
        200,
        "oms_fulfillment"
    ))

    # Test 3: Access OMS module (should succeed)
    results.append(test_endpoint(
        "Access OMS Module (should succeed)",
        f"{BASE_URL}/test/modules/oms-allowed",
        headers_with_tenant,
        200,
        "OMS, WMS & Fulfillment"
    ))

    # Test 4: Access D2C Storefront module (should succeed)
    results.append(test_endpoint(
        "Access D2C Storefront Module (should succeed)",
        f"{BASE_URL}/test/modules/storefront-allowed",
        headers_with_tenant,
        200,
        "D2C E-Commerce Storefront"
    ))

    # Test 5: Access Finance module (should fail with 403)
    results.append(test_endpoint(
        "Access Finance Module (should fail with 403)",
        f"{BASE_URL}/test/modules/finance-blocked",
        headers_with_tenant,
        403,
        "not enabled"
    ))

    # Test 6: Access Procurement module (should fail with 403)
    results.append(test_endpoint(
        "Access Procurement Module (should fail with 403)",
        f"{BASE_URL}/test/modules/procurement-blocked",
        headers_with_tenant,
        403,
        "not enabled"
    ))

    # Test 7: Access without tenant header (should fail with 404)
    results.append(test_endpoint(
        "Access Without Tenant Header (should fail with 404)",
        f"{BASE_URL}/test/modules/enabled",
        headers_without_tenant,
        404,
        "Tenant not found"
    ))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    total_tests = len(results)
    passed_tests = sum(results)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")

    if passed_tests == total_tests:
        print("\n✅ ALL TESTS PASSED! Phase 1 is working correctly.")
        return 0
    else:
        print(f"\n❌ {total_tests - passed_tests} test(s) failed. Please review.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

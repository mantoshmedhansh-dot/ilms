#!/usr/bin/env python3
"""
Phase 2B: Test Module Access Control
Tests that @require_module decorators correctly allow/block access based on tenant subscriptions.
"""
import requests
import sys
from typing import Dict, List

BASE_URL = "http://localhost:8000"
TEST_TENANT_ID = "f1aa6a6a-ee69-414b-b11e-67032a27d52a"

# Test tenant has these modules (from Phase 1):
# - system_admin
# - oms_fulfillment
# - d2c_storefront

# Test endpoints: module_code -> endpoint_path
TEST_ENDPOINTS = {
    # Should ALLOW (test tenant has these modules)
    "system_admin": {
        "endpoint": "/api/v1/test/tenant/info",
        "should_allow": True,
        "method": "GET"
    },
    "oms_fulfillment": {
        "endpoint": "/api/v1/test/modules/oms-allowed",
        "should_allow": True,
        "method": "GET"
    },
    "d2c_storefront": {
        "endpoint": "/api/v1/test/modules/storefront-allowed",
        "should_allow": True,
        "method": "GET"
    },

    # Should BLOCK (test tenant does NOT have these modules)
    "finance": {
        "endpoint": "/api/v1/test/modules/finance-blocked",
        "should_allow": False,
        "method": "GET"
    },
    "procurement": {
        "endpoint": "/api/v1/test/modules/procurement-blocked",
        "should_allow": False,
        "method": "GET"
    },
}


def run_tests() -> Dict[str, bool]:
    """Run all module access control tests."""
    print("=" * 70)
    print("PHASE 2B: Module Access Control Testing")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print(f"Test Tenant ID: {TEST_TENANT_ID}")
    print()

    headers = {"X-Tenant-ID": TEST_TENANT_ID}
    results = {}

    for module_code, test_config in TEST_ENDPOINTS.items():
        endpoint = test_config["endpoint"]
        should_allow = test_config["should_allow"]
        method = test_config["method"]

        print(f"\n📦 Module: {module_code}")
        print(f"  Endpoint: {endpoint}")
        print(f"  Expected: {'✅ ALLOW (200 OK)' if should_allow else '🚫 BLOCK (403 Forbidden)'}")

        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=5)
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", headers=headers, timeout=5)

            status_code = response.status_code

            # Check if result matches expectation
            if should_allow:
                # Should get 200 OK
                if status_code == 200:
                    print(f"  Result: ✅ PASS - Got 200 OK (access allowed)")
                    results[module_code] = True
                else:
                    print(f"  Result: ❌ FAIL - Got {status_code} (expected 200 OK)")
                    print(f"  Response: {response.text[:200]}")
                    results[module_code] = False
            else:
                # Should get 403 Forbidden
                if status_code == 403:
                    print(f"  Result: ✅ PASS - Got 403 Forbidden (access blocked)")
                    try:
                        error_detail = response.json().get("detail", "")
                        if "module" in error_detail.lower() and "not enabled" in error_detail.lower():
                            print(f"  Message: {error_detail}")
                        else:
                            print(f"  Warning: Error message doesn't mention module restriction")
                    except:
                        pass
                    results[module_code] = True
                else:
                    print(f"  Result: ❌ FAIL - Got {status_code} (expected 403 Forbidden)")
                    print(f"  Response: {response.text[:200]}")
                    results[module_code] = False

        except requests.exceptions.RequestException as e:
            print(f"  Result: ❌ ERROR - {type(e).__name__}: {e}")
            results[module_code] = False

    return results


def print_summary(results: Dict[str, bool]):
    """Print test summary."""
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(passed/total*100):.1f}%")

    if failed > 0:
        print("\n❌ Failed tests:")
        for module_code, passed in results.items():
            if not passed:
                print(f"  - {module_code}")

    print()
    if all(results.values()):
        print("✅ ALL TESTS PASSED - Phase 2B Complete!")
        print("\n🎯 Next: Phase 2C - Handle multi-module endpoints")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED - Review decorator implementation")
        return 1


def main():
    """Main test runner."""
    try:
        # Check if server is running
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            print(f"✓ Server is running (health check: {response.status_code})\n")
        except requests.exceptions.RequestException:
            print("❌ Server is not running!")
            print("Please start the server:")
            print("  .venv/bin/python -m uvicorn app.main:app --reload --port 8000")
            return 1

        # Run tests
        results = run_tests()

        # Print summary
        return print_summary(results)

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
End-to-End API Testing Script
Tests all Phase 1-6 endpoints with real Supabase database
"""

import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

async def test_health():
    """Test health endpoint"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health", timeout=10.0)
            print(f"✓ Health Check: {response.status_code}")
            if response.status_code == 200:
                print(f"  Response: {response.json()}")
            return response.status_code == 200
        except Exception as e:
            print(f"✗ Health Check Failed: {e}")
            return False

async def test_docs():
    """Test API docs are accessible"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/docs", timeout=10.0)
            print(f"✓ API Docs: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"✗ API Docs Failed: {e}")
            return False

async def test_subdomain_check():
    """Phase 3: Test subdomain availability check"""
    async with httpx.AsyncClient() as client:
        try:
            payload = {"subdomain": "testcompany"}
            response = await client.post(
                f"{BASE_URL}/api/v1/onboarding/check-subdomain",
                json=payload,
                timeout=10.0
            )
            print(f"✓ Subdomain Check: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  Available: {result.get('available')}")
                print(f"  Message: {result.get('message')}")
            return response.status_code == 200
        except Exception as e:
            print(f"✗ Subdomain Check Failed: {e}")
            return False

async def test_list_modules():
    """Phase 2: Test listing available modules"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/onboarding/modules",
                timeout=10.0
            )
            print(f"✓ List Modules: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  Total Modules: {result.get('total')}")
                if result.get('modules'):
                    print(f"  First Module: {result['modules'][0].get('name')}")
            return response.status_code == 200
        except Exception as e:
            print(f"✗ List Modules Failed: {e}")
            return False

async def test_tenant_registration():
    """Phase 3: Test complete tenant registration"""
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "subdomain": f"testorg{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "company_name": "Test Organization",
                "admin_email": "admin@testorg.com",
                "admin_phone": "+919876543210",
                "admin_password": "SecurePass123!",
                "admin_first_name": "Test",
                "admin_last_name": "Admin",
                "selected_modules": ["system_admin", "oms_fulfillment", "finance"],
                "billing_cycle": "monthly"
            }
            response = await client.post(
                f"{BASE_URL}/api/v1/onboarding/register",
                json=payload,
                timeout=30.0
            )
            print(f"✓ Tenant Registration: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  Tenant ID: {result.get('tenant', {}).get('id')}")
                print(f"  Subdomain: {result.get('tenant', {}).get('subdomain')}")
                print(f"  Schema: {result.get('tenant', {}).get('schema_name')}")
                print(f"  Access Token: {'Present' if result.get('access_token') else 'Missing'}")
                return result
            elif response.status_code == 422:
                print(f"  Validation Error: {response.json()}")
            return None
        except Exception as e:
            import traceback
            print(f"✗ Tenant Registration Failed: {e}")
            traceback.print_exc()
            return None

async def test_module_subscriptions(access_token, tenant_id):
    """Phase 2: Test module subscriptions listing"""
    if not access_token or not tenant_id:
        print("⊘ Skipping Module Subscriptions (no auth)")
        return False

    async with httpx.AsyncClient() as client:
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Tenant-ID": tenant_id
            }
            response = await client.get(
                f"{BASE_URL}/api/v1/modules/subscriptions",
                headers=headers,
                timeout=10.0
            )
            print(f"✓ Module Subscriptions: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  Active Subscriptions: {len(result.get('subscriptions', []))}")
            return response.status_code == 200
        except Exception as e:
            print(f"✗ Module Subscriptions Failed: {e}")
            return False

async def test_billing_history(access_token, tenant_id):
    """Phase 5: Test billing history"""
    if not access_token or not tenant_id:
        print("⊘ Skipping Billing History (no auth)")
        return False

    async with httpx.AsyncClient() as client:
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Tenant-ID": tenant_id
            }
            response = await client.get(
                f"{BASE_URL}/api/v1/billing/subscription-billing/history",
                headers=headers,
                timeout=10.0
            )
            print(f"✓ Billing History: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"  Total Records: {result.get('total')}")
            return response.status_code == 200
        except Exception as e:
            print(f"✗ Billing History Failed: {e}")
            return False

async def main():
    print("=" * 70)
    print("ILMS.AI Multi-Tenant SaaS - End-to-End API Testing")
    print("=" * 70)
    print()

    print("Phase 0: Infrastructure Tests")
    print("-" * 70)
    health_ok = await test_health()
    docs_ok = await test_docs()
    print()

    if not health_ok:
        print("✗ Server not healthy. Exiting...")
        return

    print("Phase 1-3: Tenant Onboarding Tests")
    print("-" * 70)
    subdomain_ok = await test_subdomain_check()
    modules_ok = await test_list_modules()
    registration_result = await test_tenant_registration()
    print()

    # Extract auth details for protected endpoint tests
    access_token = None
    tenant_id = None
    if registration_result:
        access_token = registration_result.get('access_token')
        tenant_id = registration_result.get('tenant', {}).get('id')

    print("Phase 2: Module Management Tests")
    print("-" * 70)
    module_subs_ok = await test_module_subscriptions(access_token, tenant_id)
    print()

    print("Phase 5: Billing Tests")
    print("-" * 70)
    billing_ok = await test_billing_history(access_token, tenant_id)
    print()

    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Health Check:          {'✓ PASS' if health_ok else '✗ FAIL'}")
    print(f"API Docs:              {'✓ PASS' if docs_ok else '✗ FAIL'}")
    print(f"Subdomain Check:       {'✓ PASS' if subdomain_ok else '✗ FAIL'}")
    print(f"List Modules:          {'✓ PASS' if modules_ok else '✗ FAIL'}")
    print(f"Tenant Registration:   {'✓ PASS' if registration_result else '✗ FAIL'}")
    print(f"Module Subscriptions:  {'✓ PASS' if module_subs_ok else '✗ FAIL'}")
    print(f"Billing History:       {'✓ PASS' if billing_ok else '✗ FAIL'}")
    print()

    total_tests = 7
    passed_tests = sum([
        health_ok, docs_ok, subdomain_ok, modules_ok,
        bool(registration_result), module_subs_ok, billing_ok
    ])
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print()

if __name__ == "__main__":
    asyncio.run(main())

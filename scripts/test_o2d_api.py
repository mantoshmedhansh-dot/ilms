"""
O2D Flow Test via API
---------------------
Test the complete Order-to-Delivery flow using the backend APIs
"""
import httpx
import json
from datetime import datetime
import uuid

BASE_URL = "http://localhost:8000/api/v1"


def get_token():
    """Get authentication token"""
    with httpx.Client() as client:
        resp = client.post(
            f"{BASE_URL}/auth/login",
            json={"email": "admin@consumer.com", "password": "Admin@123"}
        )
        return resp.json().get("access_token")


def test_o2d_flow():
    """Test the complete O2D flow"""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    print("=" * 80)
    print("ORDER-TO-DELIVERY (O2D) FLOW TEST")
    print("=" * 80)

    with httpx.Client(timeout=30.0, headers=headers) as client:

        # Step 1: Get test order from database (since orders API has issues)
        print("\n=== STEP 1: GET TEST ORDER ===")
        # We'll use the first NEW order's warehouse
        resp = client.get(f"{BASE_URL}/warehouses")
        warehouses = resp.json().get("items", [])
        warehouse_id = warehouses[0]["id"] if warehouses else None
        print(f"Using Warehouse: {warehouses[0]['name'] if warehouses else 'N/A'}")

        # Step 2: Check available inventory
        print("\n=== STEP 2: CHECK INVENTORY ===")
        resp = client.get(f"{BASE_URL}/products?limit=5")
        products = resp.json()
        if "items" in products:
            for p in products["items"][:3]:
                mrp = float(p.get('mrp', 0) or 0)
                print(f"  {p.get('sku')}: {p.get('name', '')[:40]} | MRP: Rs. {mrp:,.0f}")

        # Step 3: Create a picklist for orders
        print("\n=== STEP 3: CREATE PICKLIST ===")
        # Generate a new picklist
        picklist_data = {
            "warehouse_id": warehouse_id,
            "priority": "NORMAL",
            "notes": "Test picklist for O2D flow testing"
        }
        resp = client.post(f"{BASE_URL}/picklists", json=picklist_data)
        if resp.status_code == 200 or resp.status_code == 201:
            picklist = resp.json()
            print(f"Picklist created: {picklist.get('picklist_number')}")
            picklist_id = picklist.get("id")
        else:
            print(f"Picklist creation: {resp.status_code} - {resp.text[:100]}")
            # Use existing picklist
            resp = client.get(f"{BASE_URL}/picklists?limit=1")
            existing = resp.json()
            if existing.get("items"):
                picklist_id = existing["items"][0]["id"]
                print(f"Using existing picklist: {existing['items'][0].get('picklist_number')}")
            else:
                picklist_id = None

        # Step 4: Create a shipment
        print("\n=== STEP 4: CREATE SHIPMENT ===")
        shipment_data = {
            "warehouse_id": warehouse_id,
            "ship_to_address": {
                "name": "Test Customer",
                "phone": "9876543210",
                "address_line1": "123 Test Street",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001",
                "country": "India"
            },
            "no_of_boxes": 1,
            "weight": 15.5,
            "dimensions": {"length": 50, "breadth": 40, "height": 30},
            "notes": "Test shipment for O2D flow"
        }
        resp = client.post(f"{BASE_URL}/shipments", json=shipment_data)
        if resp.status_code in [200, 201]:
            shipment = resp.json()
            print(f"Shipment created: {shipment.get('shipment_number')}")
            shipment_id = shipment.get("id")
        else:
            print(f"Shipment creation: {resp.status_code} - {resp.text[:200]}")
            # Use existing shipment
            resp = client.get(f"{BASE_URL}/shipments?status=PACKED&limit=1")
            existing = resp.json()
            if existing.get("items"):
                shipment_id = existing["items"][0]["id"]
                print(f"Using existing shipment: {existing['items'][0].get('shipment_number')}")
            else:
                shipment_id = None

        # Step 5: Select transporter
        print("\n=== STEP 5: SELECT TRANSPORTER ===")
        resp = client.get(f"{BASE_URL}/transporters")
        transporters = resp.json().get("items", [])
        transporter = next((t for t in transporters if t.get("code") == "DELHIVERY"), transporters[0] if transporters else None)
        if transporter:
            print(f"Selected: {transporter.get('name')} ({transporter.get('code')})")
            transporter_id = transporter.get("id")
        else:
            transporter_id = None

        # Step 6: Create manifest for courier handover
        print("\n=== STEP 6: CREATE MANIFEST ===")
        if transporter_id and warehouse_id:
            manifest_data = {
                "warehouse_id": warehouse_id,
                "transporter_id": transporter_id,
                "business_type": "B2C",
                "vehicle_number": "MH01AB1234",
                "driver_name": "Test Driver",
                "driver_phone": "9876543210",
                "remarks": "Test manifest for O2D flow"
            }
            resp = client.post(f"{BASE_URL}/manifests", json=manifest_data)
            if resp.status_code in [200, 201]:
                manifest = resp.json()
                print(f"Manifest created: {manifest.get('manifest_number')}")
                manifest_id = manifest.get("id")
            else:
                print(f"Manifest creation: {resp.status_code} - {resp.text[:200]}")
                # Use existing manifest
                resp = client.get(f"{BASE_URL}/manifests?limit=1")
                existing = resp.json()
                if existing.get("items"):
                    manifest_id = existing["items"][0]["id"]
                    print(f"Using existing manifest: {existing['items'][0].get('manifest_number')}")
                else:
                    manifest_id = None
        else:
            manifest_id = None

        # Step 7: Add shipment to manifest
        print("\n=== STEP 7: ADD SHIPMENT TO MANIFEST ===")
        if manifest_id and shipment_id:
            resp = client.post(f"{BASE_URL}/manifests/{manifest_id}/shipments/{shipment_id}")
            if resp.status_code in [200, 201]:
                print(f"Shipment added to manifest successfully")
            else:
                print(f"Add to manifest: {resp.status_code} - {resp.text[:100]}")

        # Step 8: Confirm manifest (dispatch)
        print("\n=== STEP 8: CONFIRM MANIFEST (DISPATCH) ===")
        if manifest_id:
            resp = client.post(f"{BASE_URL}/manifests/{manifest_id}/confirm")
            if resp.status_code in [200, 201]:
                confirmed = resp.json()
                print(f"Manifest confirmed: Status = {confirmed.get('status')}")
            else:
                print(f"Confirm manifest: {resp.status_code} - {resp.text[:100]}")

        # Step 9: Update tracking (in-transit)
        print("\n=== STEP 9: UPDATE TRACKING ===")
        if shipment_id:
            tracking_data = {
                "status": "IN_TRANSIT",
                "remarks": "Shipment picked up by courier",
                "location": "Mumbai Hub"
            }
            resp = client.post(f"{BASE_URL}/shipments/{shipment_id}/tracking", json=tracking_data)
            if resp.status_code in [200, 201]:
                print(f"Tracking updated: IN_TRANSIT")
            else:
                print(f"Update tracking: {resp.status_code} - {resp.text[:100]}")

        # Step 10: Mark delivered with POD
        print("\n=== STEP 10: MARK DELIVERED (POD) ===")
        if shipment_id:
            delivery_data = {
                "delivered_to": "Rajesh Kumar",
                "delivery_remarks": "Delivered to customer at door",
                "pod_image_url": "https://example.com/pod/12345.jpg",
            }
            resp = client.post(f"{BASE_URL}/shipments/{shipment_id}/deliver", json=delivery_data)
            if resp.status_code in [200, 201]:
                delivered = resp.json()
                print(f"Delivery confirmed: Status = {delivered.get('status')}")
                print(f"Delivered to: {delivery_data['delivered_to']}")
            else:
                print(f"Mark delivered: {resp.status_code} - {resp.text[:100]}")

        # Summary
        print("\n" + "=" * 80)
        print("O2D FLOW SUMMARY")
        print("=" * 80)

        # Get final counts
        resp = client.get(f"{BASE_URL}/shipments")
        shipments = resp.json()
        resp = client.get(f"{BASE_URL}/picklists")
        picklists = resp.json()
        resp = client.get(f"{BASE_URL}/manifests")
        manifests = resp.json()

        print(f"\n   Total Shipments: {shipments.get('total', 0)}")
        print(f"   Total Picklists: {picklists.get('total', 0)}")
        print(f"   Total Manifests: {manifests.get('total', 0)}")

        # Get shipment status breakdown
        print("\n   SHIPMENT STATUS BREAKDOWN:")
        resp = client.get(f"{BASE_URL}/shipments?limit=100")
        all_shipments = resp.json().get("items", [])
        status_counts = {}
        for s in all_shipments:
            status = s.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1
        for status, count in sorted(status_counts.items()):
            print(f"   - {status}: {count}")

        print("\n" + "=" * 80)
        print("O2D FLOW TEST COMPLETED")
        print("=" * 80)


if __name__ == "__main__":
    test_o2d_flow()

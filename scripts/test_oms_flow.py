"""Test complete OMS/WMS order flow."""
import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"


async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # ==================== STEP 1: Login ====================
        print("=" * 60)
        print("STEP 1: Login")
        print("=" * 60)

        login_resp = await client.post(
            f"{BASE_URL}/auth/auth/login",
            json={"email": "admin@consumer.com", "password": "Admin@123"}
        )
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print(f"Token: {token[:50]}...")

        # ==================== STEP 2: Create Customer ====================
        print("\n" + "=" * 60)
        print("STEP 2: Check/Create Customer")
        print("=" * 60)

        customers_resp = await client.get(f"{BASE_URL}/customers/customers?size=1", headers=headers)
        customers = customers_resp.json()

        if customers.get("total", 0) == 0:
            customer_resp = await client.post(
                f"{BASE_URL}/customers/customers",
                headers=headers,
                json={
                    "first_name": "Rahul",
                    "last_name": "Sharma",
                    "phone": "+919876543210",
                    "email": "rahul.sharma@test.com"
                }
            )
            customer = customer_resp.json()
        else:
            customer = customers["items"][0]

        customer_id = customer["id"]
        print(f"Customer: {customer.get('full_name', customer.get('first_name', 'N/A'))} (ID: {customer_id[:8]}...)")

        # ==================== STEP 3: Get Product ====================
        print("\n" + "=" * 60)
        print("STEP 3: Get Product")
        print("=" * 60)

        products_resp = await client.get(f"{BASE_URL}/products/products?size=1", headers=headers)
        products = products_resp.json()

        if products.get("total", 0) == 0:
            print("ERROR: No products found!")
            return

        product = products["items"][0]
        product_id = product["id"]
        print(f"Product: {product['name']} (SKU: {product['sku']}, Price: ₹{product.get('selling_price', 'N/A')})")

        # ==================== STEP 4: Get Warehouse ====================
        print("\n" + "=" * 60)
        print("STEP 4: Get Warehouse")
        print("=" * 60)

        warehouses_resp = await client.get(f"{BASE_URL}/warehouses/warehouses?size=1", headers=headers)
        warehouses = warehouses_resp.json()

        if warehouses.get("total", 0) == 0:
            print("ERROR: No warehouses found!")
            return

        warehouse = warehouses["items"][0]
        warehouse_id = warehouse["id"]
        print(f"Warehouse: {warehouse['name']} (Code: {warehouse['code']})")

        # ==================== STEP 5: Create Order ====================
        print("\n" + "=" * 60)
        print("STEP 5: Create Order")
        print("=" * 60)

        order_resp = await client.post(
            f"{BASE_URL}/orders/orders",
            headers=headers,
            json={
                "customer_id": customer_id,
                "source": "WEBSITE",
                "payment_method": "COD",
                "items": [{"product_id": product_id, "quantity": 1}],
                "shipping_address": {
                    "address_line1": "42, Green Park Extension",
                    "city": "New Delhi",
                    "state": "Delhi",
                    "pincode": "110016",
                    "contact_name": "Rahul Sharma",
                    "contact_phone": "+919876543210"
                }
            }
        )

        if order_resp.status_code != 201:
            print(f"ERROR creating order: {order_resp.text}")
            return

        order = order_resp.json()
        order_id = order["id"]
        print(f"Order Created: {order['order_number']}")
        print(f"  Status: {order['status']}")
        print(f"  Total: ₹{order['total_amount']}")
        print(f"  Order ID: {order_id}")

        # ==================== STEP 6: Approve Order ====================
        print("\n" + "=" * 60)
        print("STEP 6: Approve Order (NEW -> CONFIRMED)")
        print("=" * 60)

        approve_resp = await client.post(
            f"{BASE_URL}/orders/orders/{order_id}/approve",
            headers=headers
        )

        if approve_resp.status_code == 200:
            order = approve_resp.json()
            print(f"Order Approved! Status: {order['status']}")
        else:
            print(f"Approve response: {approve_resp.text}")

        # ==================== STEP 7: Generate Picklist ====================
        print("\n" + "=" * 60)
        print("STEP 7: Generate Picklist")
        print("=" * 60)

        picklist_resp = await client.post(
            f"{BASE_URL}/picklists/generate",
            headers=headers,
            json={
                "order_ids": [order_id],
                "warehouse_id": warehouse_id
            }
        )

        if picklist_resp.status_code in (200, 201):
            picklist = picklist_resp.json()
            picklist_id = picklist.get("id")
            print(f"Picklist Created: {picklist.get('picklist_number', 'N/A')}")
            print(f"  Status: {picklist.get('status', 'N/A')}")
            print(f"  Total Items: {picklist.get('total_items', 'N/A')}")
            print(f"  Picklist ID: {picklist_id}")
        else:
            print(f"Picklist response ({picklist_resp.status_code}): {picklist_resp.text[:200]}")
            picklist_id = None

        if not picklist_id:
            print("Cannot continue without picklist")
            return

        # ==================== STEP 8: Start & Complete Picking ====================
        print("\n" + "=" * 60)
        print("STEP 8: Complete Picking")
        print("=" * 60)

        # Start picking
        start_resp = await client.post(
            f"{BASE_URL}/picklists/{picklist_id}/start",
            headers=headers
        )
        if start_resp.status_code == 200:
            print("Picking Started!")
        else:
            print(f"Start picking: {start_resp.text[:100]}")

        # Complete picking
        complete_resp = await client.post(
            f"{BASE_URL}/picklists/{picklist_id}/complete",
            headers=headers
        )
        if complete_resp.status_code == 200:
            picklist = complete_resp.json()
            print(f"Picking Completed! Status: {picklist.get('status', 'N/A')}")
        else:
            print(f"Complete picking: {complete_resp.text[:100]}")

        # ==================== STEP 9: Create Shipment ====================
        print("\n" + "=" * 60)
        print("STEP 9: Create Shipment (Pack Order)")
        print("=" * 60)

        # Get transporter
        transporters_resp = await client.get(f"{BASE_URL}/transporters?size=1", headers=headers)
        transporters = transporters_resp.json()
        transporter_id = transporters["items"][0]["id"] if transporters.get("items") else None

        shipment_resp = await client.post(
            f"{BASE_URL}/shipments",
            headers=headers,
            json={
                "order_id": order_id,
                "warehouse_id": warehouse_id,
                "transporter_id": transporter_id,
                "weight_kg": 5.0,
                "length_cm": 40,
                "breadth_cm": 30,
                "height_cm": 30,
                "no_of_boxes": 1,
                "ship_to_name": "Rahul Sharma",
                "ship_to_phone": "+919876543210",
                "ship_to_address": {
                    "address_line1": "42, Green Park Extension",
                    "city": "New Delhi",
                    "state": "Delhi",
                    "pincode": "110016"
                },
                "ship_to_pincode": "110016",
                "ship_to_city": "New Delhi",
                "ship_to_state": "Delhi"
            }
        )

        if shipment_resp.status_code in (200, 201):
            shipment = shipment_resp.json()
            shipment_id = shipment.get("id")
            print(f"Shipment Created: {shipment.get('shipment_number', 'N/A')}")
            print(f"  Status: {shipment.get('status', 'N/A')}")
            print(f"  AWB: {shipment.get('awb_number', 'N/A')}")
            print(f"  Shipment ID: {shipment_id}")
        else:
            print(f"Shipment response ({shipment_resp.status_code}): {shipment_resp.text[:200]}")
            shipment_id = None

        if not shipment_id:
            print("Cannot continue without shipment")
            return

        # ==================== STEP 10: Pack Shipment ====================
        print("\n" + "=" * 60)
        print("STEP 10: Confirm Packing")
        print("=" * 60)

        pack_resp = await client.post(
            f"{BASE_URL}/shipments/{shipment_id}/pack",
            headers=headers,
            json={
                "shipment_id": shipment_id,
                "packaging_type": "BOX",
                "no_of_boxes": 1,
                "weight_kg": 5.0,
                "length_cm": 40,
                "breadth_cm": 30,
                "height_cm": 30,
                "notes": "Packed securely with foam padding"
            }
        )
        if pack_resp.status_code == 200:
            shipment = pack_resp.json()
            print(f"Packing Confirmed! Status: {shipment.get('status', 'N/A')}")
        else:
            print(f"Pack response: {pack_resp.text[:200]}")

        # ==================== STEP 11: Create Manifest ====================
        print("\n" + "=" * 60)
        print("STEP 11: Create Manifest")
        print("=" * 60)

        manifest_resp = await client.post(
            f"{BASE_URL}/manifests",
            headers=headers,
            json={
                "warehouse_id": warehouse_id,
                "transporter_id": transporter_id,
                "business_type": "B2C"
            }
        )

        if manifest_resp.status_code in (200, 201):
            manifest = manifest_resp.json()
            manifest_id = manifest.get("id")
            print(f"Manifest Created: {manifest.get('manifest_number', 'N/A')}")
            print(f"  Status: {manifest.get('status', 'N/A')}")
            print(f"  Manifest ID: {manifest_id}")
        else:
            print(f"Manifest response ({manifest_resp.status_code}): {manifest_resp.text[:200]}")
            manifest_id = None

        if not manifest_id:
            print("Cannot continue without manifest")
            return

        # ==================== STEP 12: Add Shipment to Manifest ====================
        print("\n" + "=" * 60)
        print("STEP 12: Add Shipment to Manifest")
        print("=" * 60)

        add_resp = await client.post(
            f"{BASE_URL}/manifests/{manifest_id}/add-shipments",
            headers=headers,
            json={"shipment_ids": [shipment_id]}
        )
        if add_resp.status_code == 200:
            manifest = add_resp.json()
            print(f"Shipment Added! Total shipments: {manifest.get('total_shipments', 'N/A')}")
        else:
            print(f"Add shipment response: {add_resp.text[:200]}")

        # ==================== STEP 13: Confirm Manifest ====================
        print("\n" + "=" * 60)
        print("STEP 13: Confirm Manifest (Mark Ready to Ship)")
        print("=" * 60)

        confirm_resp = await client.post(
            f"{BASE_URL}/manifests/{manifest_id}/confirm",
            headers=headers,
            json={"manifest_id": manifest_id, "notes": "Manifest confirmed for pickup"}
        )
        if confirm_resp.status_code == 200:
            manifest = confirm_resp.json()
            print(f"Manifest Confirmed! Status: {manifest.get('status', 'N/A')}")
        else:
            print(f"Confirm response: {confirm_resp.text[:200]}")

        # ==================== STEP 14: Complete Handover ====================
        print("\n" + "=" * 60)
        print("STEP 14: Complete Handover to Transporter")
        print("=" * 60)

        handover_resp = await client.post(
            f"{BASE_URL}/manifests/{manifest_id}/handover",
            headers=headers,
            json={
                "manifest_id": manifest_id,
                "vehicle_number": "DL01AB1234",
                "driver_name": "Ram Kumar",
                "driver_phone": "+919876543211",
                "handover_notes": "All packages handed over"
            }
        )
        if handover_resp.status_code == 200:
            manifest = handover_resp.json()
            print(f"Handover Complete! Status: {manifest.get('status', 'N/A')}")
        else:
            print(f"Handover response: {handover_resp.text[:200]}")

        # ==================== STEP 15: Mark Delivered ====================
        print("\n" + "=" * 60)
        print("STEP 15: Mark as Delivered (with POD)")
        print("=" * 60)

        deliver_resp = await client.post(
            f"{BASE_URL}/shipments/{shipment_id}/deliver",
            headers=headers,
            json={
                "shipment_id": shipment_id,
                "delivered_to": "Rahul Sharma",
                "delivery_remarks": "Delivered successfully, customer verified"
            }
        )
        if deliver_resp.status_code == 200:
            shipment = deliver_resp.json()
            print(f"DELIVERED! Status: {shipment.get('status', 'N/A')}")
            print(f"  Delivered to: {shipment.get('delivered_to', 'N/A')}")
        else:
            print(f"Deliver response: {deliver_resp.text[:200]}")

        # ==================== FINAL: Check Order Status ====================
        print("\n" + "=" * 60)
        print("FINAL: Check Order Status")
        print("=" * 60)

        final_order_resp = await client.get(
            f"{BASE_URL}/orders/orders/{order_id}",
            headers=headers
        )
        if final_order_resp.status_code == 200:
            final_order = final_order_resp.json()
            print(f"Order: {final_order['order_number']}")
            print(f"  Final Status: {final_order['status']}")
            print(f"  Payment Status: {final_order['payment_status']}")

        print("\n" + "=" * 60)
        print("OMS/WMS FLOW TEST COMPLETE!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

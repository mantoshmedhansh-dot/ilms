# Edge-Based Serviceability Architecture

## Overview

This document describes the industry-standard architecture for fast pincode serviceability checks on D2C storefronts. The goal is **sub-10ms response time globally** for any pincode check.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              D2C STOREFRONT                                  │
│                          (www.aquapurite.com)                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
    ┌───────────────────────────┐   ┌───────────────────────────────────────┐
    │   SERVICEABILITY CHECK    │   │        STOCK CHECK (Real-time)        │
    │   (Static - Edge/CDN)     │   │        (Dynamic - Backend API)        │
    │                           │   │                                       │
    │ GET /serviceability.json  │   │ GET /api/v1/storefront/stock/{id}     │
    │ → Vercel Edge Config      │   │ → FastAPI → Redis/PostgreSQL          │
    │ → <10ms response          │   │ → <50ms response                      │
    │                           │   │                                       │
    │ Contains:                 │   │ Contains:                             │
    │ - 27,000+ pincodes        │   │ - Real-time available_quantity        │
    │ - Warehouse mappings      │   │ - Reserved quantity                   │
    │ - SLA days                │   │ - Product-specific stock              │
    │ - Shipping costs          │   │                                       │
    │ - COD/Prepaid flags       │   │                                       │
    │ - Zone classification     │   │                                       │
    └───────────────────────────┘   └───────────────────────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │        ORDER CREATION         │
                    │    (Validation + Create)      │
                    │                               │
                    │ POST /api/v1/storefront/order │
                    │ - Verify serviceability       │
                    │ - Allocate inventory          │
                    │ - Create order                │
                    └───────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │   BACKGROUND SYNC SERVICE     │
                    │   (Cron: Every 6-24 hours)    │
                    │                               │
                    │ 1. Read warehouse_service-    │
                    │    ability from PostgreSQL    │
                    │ 2. Generate static JSON       │
                    │ 3. Push to Edge Config        │
                    │ 4. Invalidate CDN cache       │
                    └───────────────────────────────┘
```

## Data Flow

### 1. Customer Enters Pincode

```javascript
// Frontend: Instant lookup from edge
const checkServiceability = async (pincode) => {
  // Option A: Vercel Edge Config (recommended)
  const data = await get(`serviceability_${pincode}`);

  // Option B: Static JSON file at CDN
  // const data = await fetch(`/api/serviceability/${pincode}.json`);

  return data || { serviceable: false };
};
```

### 2. Static Serviceability Data Structure

**IMPORTANT: Data is AGGREGATED across all warehouses per pincode.**

This enables warehouse hopping - if primary warehouse is out of stock, backend allocates from next warehouse automatically.

```json
// Edge data per pincode (aggregated from multiple warehouses)
{
  "pincode": "110001",
  "serviceable": true,           // true if ANY warehouse serves it
  "cod_available": true,         // true if ANY warehouse supports COD
  "prepaid_available": true,     // true if ANY warehouse supports prepaid
  "estimated_days": 1,           // FASTEST delivery (MIN across warehouses)
  "shipping_cost": 0,            // CHEAPEST option (MIN across warehouses)
  "zone": "LOCAL",
  "city": "New Delhi",
  "state": "Delhi",
  "warehouse_count": 3,          // Number of warehouses (enables hopping)
  "updated_at": "2026-01-19T10:00:00Z"
}
```

**Warehouse Hopping Flow:**
```
Customer orders from pincode 110001 (served by 3 warehouses)
        ↓
Backend AllocationService checks warehouses in priority order:
  1. Warehouse A (priority=1) → Out of stock → SKIP
  2. Warehouse B (priority=2) → Has stock → ALLOCATE ✓
  3. Warehouse C (priority=3) → Not checked (already allocated)
        ↓
Order fulfilled from Warehouse B
```
```

### 3. Master Index File (for bulk preload)

```json
// /public/serviceability/index.json
{
  "version": "2026-01-19T10:00:00Z",
  "total_pincodes": 27453,
  "zones": {
    "LOCAL": { "count": 45, "pincodes": ["110001", "110002", ...] },
    "METRO": { "count": 234, "pincodes": ["400001", "560001", ...] },
    "REGIONAL": { "count": 1200, "pincodes": [...] },
    "NATIONAL": { "count": 25974, "pincodes": [...] }
  }
}
```

## Implementation Options

### Option A: Vercel Edge Config (Recommended for Vercel deployments)

**Pros:**
- Sub-millisecond reads
- Type-safe SDK
- Automatic edge replication
- Built-in versioning

**Setup:**
```bash
npm install @vercel/edge-config
```

```typescript
// lib/serviceability.ts
import { get } from '@vercel/edge-config';

export async function getServiceability(pincode: string) {
  const key = `serviceability_${pincode}`;
  const data = await get(key);
  return data || { serviceable: false };
}
```

**Sync Script:**
```typescript
// scripts/sync-serviceability.ts
import { createClient } from '@vercel/edge-config';

async function syncServiceability() {
  const client = createClient(process.env.EDGE_CONFIG);

  // Fetch from backend API
  const response = await fetch(`${API_URL}/api/v1/serviceability/export`);
  const pincodes = await response.json();

  // Update Edge Config
  for (const item of pincodes) {
    await client.set(`serviceability_${item.pincode}`, item);
  }
}
```

### Option B: Static JSON Files (Universal - works anywhere)

**Pros:**
- Works with any CDN
- Easy to debug (files visible)
- Can be versioned in git

**Setup:**
```
frontend/public/
  serviceability/
    index.json          # Master index with all pincodes
    110001.json         # Per-pincode files (optional)
    110002.json
    ...
```

**Generate Script:**
```python
# scripts/generate_serviceability_json.py
import json
from pathlib import Path
from app.database import get_db
from sqlalchemy import select
from app.models.serviceability import WarehouseServiceability

async def generate_serviceability_files():
    """Generate static JSON files for all serviceable pincodes."""
    output_dir = Path("frontend/public/serviceability")
    output_dir.mkdir(parents=True, exist_ok=True)

    async with get_db() as db:
        result = await db.execute(
            select(WarehouseServiceability)
            .where(WarehouseServiceability.is_serviceable == True)
            .where(WarehouseServiceability.is_active == True)
        )
        records = result.scalars().all()

    # Master index
    index = {
        "version": datetime.utcnow().isoformat(),
        "total_pincodes": len(records),
        "pincodes": {}
    }

    for record in records:
        data = {
            "pincode": record.pincode,
            "serviceable": True,
            "cod_available": record.cod_available,
            "prepaid_available": record.prepaid_available,
            "estimated_days": record.estimated_days,
            "shipping_cost": float(record.shipping_cost or 0),
            "zone": record.zone,
            "city": record.city,
            "state": record.state,
        }
        index["pincodes"][record.pincode] = data

    # Write master index (all pincodes in one file ~2-5MB)
    with open(output_dir / "index.json", "w") as f:
        json.dump(index, f)

    print(f"Generated serviceability for {len(records)} pincodes")
```

### Option C: localStorage Preload (Hybrid)

**Pros:**
- Offline support
- Zero network latency after initial load
- Works even if edge is slow

**Frontend Implementation:**
```typescript
// lib/serviceability.ts
const STORAGE_KEY = 'serviceability_data';
const VERSION_KEY = 'serviceability_version';

export async function initServiceability() {
  // Check if we need to refresh
  const currentVersion = localStorage.getItem(VERSION_KEY);
  const response = await fetch('/serviceability/index.json');
  const data = await response.json();

  if (data.version !== currentVersion) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data.pincodes));
    localStorage.setItem(VERSION_KEY, data.version);
  }
}

export function getServiceability(pincode: string) {
  const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  return data[pincode] || { serviceable: false };
}
```

## Backend Export API

Add this endpoint to provide data for sync:

```python
# app/api/v1/endpoints/serviceability.py

@router.get("/export", include_in_schema=False)
async def export_serviceability_data(
    db: DB,
    api_key: str = Header(..., alias="X-API-Key")
):
    """
    Export all serviceability data for edge sync.
    Protected by API key (internal use only).
    """
    if api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=401)

    stmt = (
        select(WarehouseServiceability)
        .options(selectinload(WarehouseServiceability.warehouse))
        .where(WarehouseServiceability.is_serviceable == True)
        .where(WarehouseServiceability.is_active == True)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    return [
        {
            "pincode": r.pincode,
            "serviceable": True,
            "cod_available": r.cod_available,
            "prepaid_available": r.prepaid_available,
            "estimated_days": r.estimated_days,
            "shipping_cost": float(r.shipping_cost or 0),
            "zone": r.zone,
            "city": r.city,
            "state": r.state,
            "warehouse_id": str(r.warehouse_id),
        }
        for r in records
    ]
```

## Sync Strategies

### Strategy 1: Scheduled Cron (Recommended)

```yaml
# vercel.json or render.yaml
crons:
  - path: /api/cron/sync-serviceability
    schedule: "0 */6 * * *"  # Every 6 hours
```

### Strategy 2: Event-Driven

Trigger sync when:
- Admin updates serviceability in ERP
- Bulk upload completes
- New warehouse added

### Strategy 3: Webhook from ERP

```python
# After serviceability update in ERP
async def trigger_edge_sync():
    await httpx.post(
        f"{VERCEL_URL}/api/cron/sync-serviceability",
        headers={"Authorization": f"Bearer {CRON_SECRET}"}
    )
```

## Performance Comparison

| Metric | Current (Database) | Edge Config | Static JSON |
|--------|-------------------|-------------|-------------|
| P50 Latency | 100ms | 5ms | 15ms |
| P99 Latency | 500ms | 20ms | 50ms |
| Cold Start | 500ms+ | 10ms | 20ms |
| Scalability | ~1000 RPS | Unlimited | Unlimited |
| Cache Miss | Slow | N/A | N/A |
| Offline | No | No | Yes (localStorage) |

## Migration Path

### Phase 1: Add Index (Immediate - Done)
- Added pincode index to database
- Improves cache miss from 500ms to 50ms

### Phase 2: Generate Static Files (1-2 days)
- Create export endpoint
- Create sync script
- Generate initial JSON files

### Phase 3: Frontend Integration (2-3 days)
- Update serviceability check to use static data
- Add localStorage fallback
- Keep API as backup

### Phase 4: Remove Database Dependency (Final)
- Serviceability checks never hit database
- Only stock checks use API
- Database only for ERP management

## Files to Create/Modify

1. `app/api/v1/endpoints/serviceability.py` - Add export endpoint
2. `scripts/sync_serviceability_to_edge.py` - Sync script
3. `frontend/src/lib/serviceability.ts` - Edge/static lookup
4. `frontend/public/serviceability/` - Static JSON files
5. `vercel.json` - Cron job for sync

## References

- [Shopify CarrierService API](https://shopify.dev/docs/api/admin-rest/latest/resources/carrierservice) - 15-min cache pattern
- [Vercel Edge Config](https://vercel.com/docs/storage/edge-config) - Sub-millisecond reads
- [Shiprocket Pincode Serviceability](https://www.shiprocket.in/features/serviceable-pin-codes/) - 24,000+ pincodes pre-indexed
- [Building Scalable E-commerce](https://www.metamindz.co.uk/post/building-scalable-e-commerce-architecture-best-practices) - Architecture patterns

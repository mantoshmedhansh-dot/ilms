# Aquapurite ERP - Warehousing & Logistics User Guide

## For Warehouse Manager, Logistics Team & Dispatch

**Version:** 1.0
**Last Updated:** January 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [Inventory Management](#2-inventory-management)
3. [Warehouse Management (WMS)](#3-warehouse-management-wms)
4. [Logistics & Shipping](#4-logistics--shipping)
5. [Common Workflows](#5-common-workflows)
6. [Reports & Analytics](#6-reports--analytics)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Overview

### Modules Covered

| Module | Purpose |
|--------|---------|
| **Inventory** | Stock levels, transfers, adjustments |
| **WMS** | Zones, bins, putaway rules |
| **Logistics** | Shipments, transporters, tracking |

### Setup Sequence

```
1. Create Warehouses
      ↓
2. Define Zones (WMS)
      ↓
3. Create Bins (WMS)
      ↓
4. Setup Putaway Rules
      ↓
5. Add Transporters
      ↓
6. Configure Serviceability
      ↓
7. Set Rate Cards
      ↓
Ready for Operations
```

---

## 2. Inventory Management

### 2.1 Warehouses Setup

**Navigation:** Inventory → Warehouses

#### Standard Warehouse Structure

| Code | Name | Type | Purpose |
|------|------|------|---------|
| WH-HQ | Head Office Warehouse | OWNED | Primary storage |
| WH-DEL | Delhi Regional Hub | OWNED | North India distribution |
| WH-MUM | Mumbai Regional Hub | OWNED | West India distribution |
| WH-BLR | Bangalore Hub | OWNED | South India distribution |
| WH-QC | Quality Check | OWNED | Inspection area |
| WH-DEF | Defective Stock | OWNED | Rejected/returned items |
| WH-TRN | In Transit | VIRTUAL | Goods being shipped |

#### Creating a Warehouse

1. Go to **Inventory → Warehouses**
2. Click **+ New Warehouse**
3. Enter:

| Field | Required | Description |
|-------|----------|-------------|
| Code | Yes | Unique identifier (e.g., WH-DEL) |
| Name | Yes | Full warehouse name |
| Type | Yes | OWNED, RENTED, VIRTUAL, 3PL |
| Address | Yes | Complete address |
| City | Yes | City name |
| State | Yes | State |
| Pincode | Yes | 6-digit PIN |
| Manager | No | Warehouse in-charge |
| Contact Phone | Yes | For coordination |
| Is Active | Yes | Enable/disable |

4. Click **Save**

#### Warehouse Types

| Type | Description | Example |
|------|-------------|---------|
| **OWNED** | Company-owned facility | Factory warehouse |
| **RENTED** | Leased space | Rented godown |
| **VIRTUAL** | Logical warehouse | In-transit stock |
| **3PL** | Third-party logistics | Delhivery hub |
| **FRANCHISE** | Franchisee location | Dealer stock point |

---

### 2.2 Stock Summary

**Navigation:** Inventory → Stock Summary

View real-time inventory levels across all warehouses.

#### Understanding Stock Levels

| Column | Meaning |
|--------|---------|
| **Available** | Stock ready for sale/dispatch |
| **Reserved** | Allocated to orders (not yet shipped) |
| **In Transit** | Shipped but not delivered |
| **Damaged** | Defective/returned stock |
| **Total** | Sum of all stock |

#### Stock Formula

```
Available = Total - Reserved - Damaged
Sellable = Available
```

#### Filtering Stock View

Filter by:
- Warehouse
- Product Category
- Brand
- Stock Status (In Stock, Low Stock, Out of Stock)
- Below Reorder Level

---

### 2.3 Stock Items

**Navigation:** Inventory → Stock Items

Detailed view of individual SKU inventory.

#### Information Shown

| Field | Description |
|-------|-------------|
| SKU | Product code |
| Product Name | Product description |
| Warehouse | Location |
| Batch Number | Manufacturing batch |
| Serial Numbers | Individual unit serials |
| Expiry Date | For consumables |
| Last Updated | Last movement date |

---

### 2.4 Stock Transfers

**Navigation:** Inventory → Transfers

Move stock between warehouses.

#### Creating a Transfer

1. Go to **Inventory → Transfers**
2. Click **+ New Transfer**
3. Enter:

| Field | Required | Description |
|-------|----------|-------------|
| Source Warehouse | Yes | Where stock is coming from |
| Destination Warehouse | Yes | Where stock is going |
| Transfer Date | Yes | When transfer initiated |
| Transfer Type | Yes | INTER_WAREHOUSE, BRANCH, RETURN |
| Reference | No | PO number, return reference |

4. Add items:
   - Select Product
   - Enter Quantity
   - Select Batch/Serials (if applicable)
5. Click **Save** or **Submit for Approval**

#### Transfer Status Flow

```
DRAFT → PENDING_APPROVAL → APPROVED → IN_TRANSIT → RECEIVED → COMPLETED
```

| Status | Action |
|--------|--------|
| **Draft** | Can edit items |
| **Pending Approval** | Waiting for manager approval |
| **Approved** | Ready for dispatch |
| **In Transit** | Goods shipped, update tracking |
| **Received** | Destination confirmed receipt |
| **Completed** | Stock updated in both warehouses |

#### Receiving a Transfer

At destination warehouse:
1. Go to **Inventory → Transfers**
2. Filter: Status = In Transit, Destination = Your Warehouse
3. Open transfer
4. Click **Receive**
5. Enter received quantities (can be partial)
6. Note any discrepancies
7. Click **Complete Receipt**

---

### 2.5 Stock Adjustments

**Navigation:** Inventory → Adjustments

Record inventory changes outside normal transactions.

#### Adjustment Reasons

| Reason | When to Use |
|--------|-------------|
| **Physical Count** | After cycle count/annual inventory |
| **Damaged** | Goods damaged in storage |
| **Expired** | Products past expiry date |
| **Lost** | Cannot locate stock |
| **Found** | Located previously lost stock |
| **Sample** | Given as samples |
| **Demo** | Display/demo units |
| **Write Off** | Management approved write-off |

#### Creating an Adjustment

1. Go to **Inventory → Adjustments**
2. Click **+ New Adjustment**
3. Enter:

| Field | Description |
|-------|-------------|
| Warehouse | Where adjustment is being made |
| Adjustment Date | When counted/discovered |
| Reason | Select from list |
| Reference | Count sheet number, etc. |

4. Add items:
   - Product
   - Current System Qty (auto-filled)
   - Actual Qty (what you counted)
   - Variance (calculated)
   - Notes
5. Submit for Approval

#### Adjustment Approval

- Minor adjustments (<5% variance): Auto-approved
- Major adjustments (>5%): Requires manager approval
- Write-offs: Requires finance approval

---

## 3. Warehouse Management (WMS)

### 3.1 Zones

**Navigation:** WMS → Zones

Zones are logical divisions of your warehouse.

#### Standard Zone Structure

| Zone Code | Name | Purpose |
|-----------|------|---------|
| RECV | Receiving | Incoming goods staging |
| QC | Quality Check | Inspection area |
| BULK | Bulk Storage | Main storage area |
| PICK | Picking | Order picking area |
| PACK | Packing | Order packing station |
| SHIP | Shipping | Dispatch staging |
| RET | Returns | Returned goods |
| DEF | Defective | Damaged/defective items |

#### Creating a Zone

1. Go to **WMS → Zones**
2. Click **+ New Zone**
3. Enter:
   - Zone Code
   - Zone Name
   - Warehouse
   - Zone Type (Receiving, Storage, Picking, Shipping)
   - Is Active
4. Click **Save**

---

### 3.2 Bins (Locations)

**Navigation:** WMS → Bins

Bins are specific storage locations within zones.

#### Bin Naming Convention

```
Format: [Zone]-[Aisle]-[Rack]-[Level]-[Position]

Example: BULK-A-01-03-02
         │    │  │   │   │
         │    │  │   │   └── Position 2
         │    │  │   └────── Level 3 (shelf)
         │    │  └────────── Rack 01
         │    └───────────── Aisle A
         └────────────────── Zone BULK
```

#### Creating Bins

**Option 1: Individual Bin**
1. Go to **WMS → Bins**
2. Click **+ New Bin**
3. Enter:
   - Bin Code
   - Zone
   - Aisle
   - Rack
   - Level
   - Max Capacity (units or kg)
   - Bin Type (Storage, Pick, Reserve)
4. Click **Save**

**Option 2: Bulk Create**
1. Click **Bulk Create**
2. Select Zone
3. Define pattern:
   - Number of Aisles (A-E)
   - Racks per Aisle (01-10)
   - Levels per Rack (1-5)
4. System generates all bins automatically

#### Bin Types

| Type | Purpose |
|------|---------|
| **Reserve** | Long-term storage |
| **Pick** | Active picking location |
| **Overflow** | Temporary overflow |
| **Cross-dock** | Direct transfer (no storage) |
| **Returns** | Returned goods |
| **Quarantine** | QC hold items |

---

### 3.3 Bin Enquiry

**Navigation:** WMS → Bin Enquiry

Find what's stored where.

#### Search Options

| Search By | Description |
|-----------|-------------|
| Bin Code | Show contents of specific bin |
| Product | Find which bins have this product |
| Serial Number | Locate specific serial |
| Batch Number | Find batch locations |
| Empty Bins | List available bins |

#### Using Bin Enquiry

1. Go to **WMS → Bin Enquiry**
2. Enter search criteria
3. View results:
   - Bin location
   - Product
   - Quantity
   - Batch/Serial
   - Last movement date

---

### 3.4 Putaway Rules

**Navigation:** WMS → Putaway Rules

Automated rules for where to store incoming goods.

#### Rule Types

| Rule | Description |
|------|-------------|
| **Product-based** | Specific bins for specific products |
| **Category-based** | Zone assignment by product category |
| **Velocity-based** | Fast movers near picking, slow in back |
| **FIFO** | First In First Out |
| **FEFO** | First Expiry First Out (consumables) |

#### Creating a Putaway Rule

1. Go to **WMS → Putaway Rules**
2. Click **+ New Rule**
3. Enter:

| Field | Description |
|-------|-------------|
| Rule Name | Descriptive name |
| Priority | Order of rule application (1 = highest) |
| Product/Category | What products this applies to |
| Zone | Preferred zone |
| Bin Type | Storage/Pick/Reserve |
| Allocation Method | FIFO, FEFO, Nearest |

4. Click **Save**

#### Example Rules

| Priority | Rule | Condition | Action |
|----------|------|-----------|--------|
| 1 | Fast Movers | Velocity = High | Zone: PICK |
| 2 | RO Membranes | Category = Consumables | Zone: BULK, FEFO |
| 3 | Water Purifiers | Category = Finished Goods | Zone: BULK, Rack A-C |
| 4 | Default | All others | Zone: BULK, Any bin |

---

### 3.5 GRN and Putaway

When goods are received (GRN), putaway process:

```
GRN Created
      ↓
System applies putaway rules
      ↓
Suggests bin locations
      ↓
Warehouse staff confirms/changes
      ↓
Stock moved to bin
      ↓
Bin inventory updated
```

---

## 4. Logistics & Shipping

### 4.1 Transporters

**Navigation:** Logistics → Transporters

Manage your delivery partners.

#### Transporter Types

| Type | Description | Example |
|------|-------------|---------|
| **COURIER** | Express delivery partners | Delhivery, BlueDart |
| **SELF_SHIP** | Own delivery fleet | Company vehicles |
| **MARKETPLACE** | Platform logistics | Amazon Easy Ship |
| **LOCAL** | Local delivery | City courier |
| **FRANCHISE** | Franchisee delivery | Partner delivery |

#### Adding a Transporter

1. Go to **Logistics → Transporters**
2. Click **+ New Transporter**
3. Enter:

| Field | Description |
|-------|-------------|
| Code | Unique code (e.g., DELHIVERY) |
| Name | Full name |
| Type | COURIER, SELF_SHIP, etc. |
| Contact Person | Primary contact |
| Phone | Contact number |
| Email | For communications |
| API Credentials | For integration |
| Is Active | Enable/disable |

4. Click **Save**

---

### 4.2 Rate Cards

**Navigation:** Logistics → Rate Cards

Shipping rates by transporter, zone, and weight.

#### Rate Card Types

| Type | Use Case |
|------|----------|
| **D2C** | Direct to consumer (courier) |
| **B2B** | Business deliveries (LTL/PTL) |
| **FTL** | Full truck load |

#### Zone Structure

| Zone | Coverage | Example |
|------|----------|---------|
| **A** | Local (same city) | Delhi to Delhi |
| **B** | Within State | Delhi to Gurgaon |
| **C** | Regional | Delhi to Jaipur |
| **D** | Metro to Metro | Delhi to Mumbai |
| **E** | North East / J&K | Delhi to Guwahati |
| **F** | Remote | Islands, border areas |

#### Creating Rate Card

1. Go to **Logistics → Rate Cards**
2. Select segment (D2C/B2B/FTL)
3. Click **+ New Rate Card**
4. Enter:
   - Transporter
   - Effective From/To dates
   - Service Type (Standard/Express)
5. Add weight slabs per zone:

| Zone | 0-0.5 kg | 0.5-1 kg | 1-2 kg | Additional /kg |
|------|----------|----------|--------|----------------|
| A | ₹40 | ₹50 | ₹65 | ₹25 |
| B | ₹50 | ₹60 | ₹80 | ₹30 |
| C | ₹60 | ₹75 | ₹100 | ₹35 |

6. Add surcharges:
   - Fuel surcharge (%)
   - COD charges
   - ODA charges

7. Click **Save**

---

### 4.3 Serviceability

**Navigation:** Logistics → Serviceability

Define which pincodes you can deliver to.

#### Serviceability Fields

| Field | Description |
|-------|-------------|
| Pincode | 6-digit PIN code |
| City | City name |
| State | State name |
| Is Serviceable | Yes/No |
| COD Available | Cash on delivery allowed |
| Prepaid Available | Online payment only |
| Estimated Days | Delivery timeline |
| Transporters | Which couriers serve this PIN |

#### Bulk Upload Serviceability

1. Go to **Logistics → Serviceability**
2. Click **Import**
3. Download template
4. Fill in Excel:
   - Pincode
   - City
   - State
   - Serviceable (Y/N)
   - COD (Y/N)
   - Days
5. Upload file
6. Review and confirm

---

### 4.4 Shipments

**Navigation:** Logistics → Shipments

Manage outbound deliveries.

#### Shipment Status Flow

```
ORDER PLACED
      ↓
READY_TO_SHIP (Packed, label printed)
      ↓
MANIFESTED (Handed to courier)
      ↓
PICKED_UP (Courier collected)
      ↓
IN_TRANSIT
      ↓
OUT_FOR_DELIVERY
      ↓
DELIVERED / RTO (Return to Origin)
```

#### Creating a Shipment

1. Go to **Logistics → Shipments**
2. Click **+ New Shipment**
3. Select Order (or create ad-hoc)
4. Enter:

| Field | Description |
|-------|-------------|
| Order Number | Source order |
| Customer | Delivery recipient |
| Delivery Address | Shipping address |
| Warehouse | Dispatch location |
| Weight | Actual weight |
| Dimensions | L x W x H |
| Package Count | Number of boxes |
| Payment Mode | COD/Prepaid |
| Declared Value | For insurance |

5. Select Transporter (or let system auto-allocate)
6. Click **Create Shipment**

#### Auto Allocation

System can automatically select best transporter based on:
- Serviceability (can deliver to PIN)
- Cost (cheapest option)
- SLA (fastest delivery)
- Performance (best delivery rate)

**Allocation Rules:** Logistics → Allocation Rules

---

### 4.5 Manifests

**Navigation:** Logistics → Manifests

Group shipments for courier handover.

#### Creating a Manifest

1. Go to **Logistics → Manifests**
2. Click **+ New Manifest**
3. Select:
   - Transporter
   - Pickup Date
   - Warehouse
4. Add shipments:
   - System shows ready shipments
   - Select shipments to include
5. Click **Generate Manifest**
6. Print manifest document
7. Handover to courier with packages

#### Manifest Status

| Status | Meaning |
|--------|---------|
| **Open** | Adding shipments |
| **Closed** | Finalized, ready for pickup |
| **Picked Up** | Courier collected |
| **Processed** | Courier scanned all packages |

---

### 4.6 SLA Dashboard

**Navigation:** Logistics → SLA Dashboard

Monitor delivery performance.

#### Key Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| On-Time Delivery | >95% | Delivered within promised time |
| RTO Rate | <5% | Return to origin rate |
| Delivery Attempts | <1.5 avg | Attempts before delivery |
| First Attempt Delivery | >80% | Delivered on first try |
| NDR Resolution | <24 hrs | Non-delivery report resolution |

#### SLA by Zone

| Zone | Standard SLA | Express SLA |
|------|--------------|-------------|
| A (Local) | 1-2 days | Same day |
| B (State) | 2-3 days | 1-2 days |
| C (Regional) | 3-4 days | 2-3 days |
| D (Metro) | 3-5 days | 2-3 days |
| E (NE/J&K) | 5-7 days | 4-5 days |
| F (Remote) | 7-10 days | 5-7 days |

---

### 4.7 Tracking

Track shipments in real-time:

1. Go to **Logistics → Shipments**
2. Click on shipment
3. View tracking timeline:
   - Pickup time
   - Hub movements
   - Out for delivery
   - Delivery attempt
   - Delivered / RTO

---

## 5. Common Workflows

### 5.1 Goods Receipt (GRN) to Putaway

```
1. PO arrives at warehouse gate
      ↓
2. Verify documents (Invoice, DC, PO copy)
      ↓
3. Unload and stage in RECV zone
      ↓
4. Create GRN (Procurement → GRN)
      ↓
5. Quality check (QC zone)
      ↓
6. Accept/Reject items
      ↓
7. System suggests putaway locations
      ↓
8. Move goods to assigned bins
      ↓
9. Confirm putaway in system
      ↓
10. Stock updated and available
```

### 5.2 Order Picking and Packing

```
1. Order received (status: Confirmed)
      ↓
2. System reserves inventory
      ↓
3. Picklist generated (Orders → Picklists)
      ↓
4. Picker collects items from bins
      ↓
5. Verify picked items (scan serials)
      ↓
6. Move to PACK zone
      ↓
7. Pack items, print invoice & label
      ↓
8. Create shipment
      ↓
9. Move to SHIP zone
      ↓
10. Add to manifest
      ↓
11. Handover to courier
```

### 5.3 Stock Transfer Between Warehouses

```
1. Identify need for stock at destination
      ↓
2. Create transfer request
      ↓
3. Get approval (if required)
      ↓
4. Pick items at source warehouse
      ↓
5. Pack and create shipment
      ↓
6. Update transfer to "In Transit"
      ↓
7. Ship to destination
      ↓
8. Receive at destination warehouse
      ↓
9. Verify quantities
      ↓
10. Complete transfer
      ↓
11. Stock updated at both locations
```

### 5.4 Handling Returns (RTO)

```
1. Shipment returned by courier
      ↓
2. Receive at RECV zone
      ↓
3. Verify AWB/Shipment number
      ↓
4. Inspect condition
      ↓
5. If good → Return to PICK zone
   If damaged → Move to DEF zone
      ↓
6. Update system:
   - Mark shipment as RTO received
   - Create stock adjustment (if damaged)
   - Update inventory
      ↓
7. Process refund/reship (as applicable)
```

### 5.5 Cycle Count

```
1. Generate count sheet (selected bins)
      ↓
2. Print count sheet
      ↓
3. Physical count by team
      ↓
4. Record actual quantities
      ↓
5. Enter in system (Inventory → Adjustments)
      ↓
6. System calculates variance
      ↓
7. Investigate large variances
      ↓
8. Submit for approval
      ↓
9. Adjustments posted
      ↓
10. Inventory corrected
```

---

## 6. Reports & Analytics

### 6.1 Inventory Reports

| Report | Purpose |
|--------|---------|
| Stock Summary | Current stock by warehouse |
| Stock Aging | How long items in stock |
| Stock Movement | Inward/outward history |
| Reorder Report | Items below reorder level |
| Dead Stock | No movement in 90+ days |

### 6.2 Warehouse Reports

| Report | Purpose |
|--------|---------|
| Bin Utilization | Space usage by zone |
| Putaway Efficiency | Time to putaway |
| Pick Efficiency | Picks per hour |
| Inventory Accuracy | Count vs system variance |

### 6.3 Logistics Reports

| Report | Purpose |
|--------|---------|
| Shipment Summary | Daily/weekly shipments |
| Transporter Performance | Delivery rates by courier |
| Zone-wise Cost | Shipping cost by zone |
| RTO Analysis | Return reasons & rate |
| SLA Compliance | On-time delivery % |

### 6.4 Key Metrics to Monitor

**Daily:**
- Orders pending shipment
- Shipments in transit
- RTOs received
- Inventory alerts (low stock)

**Weekly:**
- Delivery success rate
- Average delivery time
- Warehouse throughput
- Pending transfers

**Monthly:**
- Inventory turnover
- Shipping cost per order
- RTO rate
- Storage utilization

---

## 7. Troubleshooting

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Cannot create shipment | No transporter for PIN | Check serviceability, add transporter |
| Stock mismatch | Unreported movement | Do cycle count, adjust |
| Bin not found | Incorrect code | Verify bin exists in WMS |
| Transfer stuck | Not approved | Check approvals, escalate |
| Wrong allocation | Rules priority | Review allocation rules |

### Error Messages

| Error | Meaning | Action |
|-------|---------|--------|
| "Insufficient stock" | Not enough available | Check reservations, adjustments |
| "PIN not serviceable" | Cannot deliver to PIN | Add to serviceability |
| "Bin at capacity" | Bin full | Use alternate bin |
| "Invalid weight" | Weight not entered | Enter package weight |
| "Transporter inactive" | Transporter disabled | Activate or use alternate |

---

## Quick Reference Card

### Daily Tasks - Warehouse Executive

| Time | Task | Navigation |
|------|------|------------|
| 8:00 AM | Check pending GRNs | Procurement → GRN |
| 9:00 AM | Process GRN receipts | GRN → Receive |
| 10:00 AM | Complete putaway | WMS → Putaway |
| 11:00 AM | Pick orders | Orders → Picklists |
| 2:00 PM | Pack and label | Packing station |
| 3:00 PM | Create shipments | Logistics → Shipments |
| 4:00 PM | Generate manifest | Logistics → Manifests |
| 5:00 PM | Handover to courier | Physical handover |

### Daily Tasks - Logistics Coordinator

| Time | Task | Navigation |
|------|------|------------|
| 9:00 AM | Check delivery status | Logistics → Shipments |
| 10:00 AM | Follow up NDRs | Shipments → Filter: NDR |
| 11:00 AM | Coordinate RTOs | Shipments → Filter: RTO |
| 2:00 PM | Monitor SLA | Logistics → SLA Dashboard |
| 4:00 PM | Escalate delays | Contact transporters |
| 5:00 PM | End of day report | Reports |

---

*Document prepared for Aquapurite ERP v1.0*

# Aquapurite ERP - Service & CRM User Guide

## For Service Manager, CRM Team & Customer Support

**Version:** 1.0
**Last Updated:** January 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [CRM Module](#2-crm-module)
3. [Service Module](#3-service-module)
4. [Common Workflows](#4-common-workflows)
5. [Reports & Analytics](#5-reports--analytics)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Overview

### What This Guide Covers

| Module | Purpose |
|--------|---------|
| **CRM** | Customer management, leads, 360° view, call center |
| **Service** | Service requests, installations, warranty, AMC, technicians |

### Setup Sequence

Before using these modules, ensure:

```
1. Products created (Catalog)
      ↓
2. Customers created (CRM)
      ↓
3. Technicians added (Service → Technicians)
      ↓
4. Service areas defined
      ↓
Ready for Service & CRM operations
```

---

## 2. CRM Module

### 2.1 Customer Management

**Navigation:** CRM → Customers

#### Customer Types

| Type | Description | Example |
|------|-------------|---------|
| **B2C** | Individual consumers | Home buyers |
| **B2B** | Business customers | Hotels, Offices |
| **Dealer** | Resellers | Distribution partners |
| **Franchise** | Franchise partners | Service franchisees |

#### Creating a Customer

1. Go to **CRM → Customers**
2. Click **+ New Customer**
3. Fill in details:

**Basic Information:**
| Field | Required | Description |
|-------|----------|-------------|
| Name | Yes | Full name or company name |
| Email | Yes* | Primary email (*or phone required) |
| Phone | Yes* | Primary contact number |
| Customer Type | Yes | B2C, B2B, Dealer, Franchise |

**Address:**
| Field | Required | Description |
|-------|----------|-------------|
| Address Line 1 | Yes | Street address |
| Address Line 2 | No | Apartment, floor, etc. |
| City | Yes | City name |
| State | Yes | State (for GST) |
| Pincode | Yes | 6-digit PIN code |

**GST Details (for B2B):**
| Field | Required | Description |
|-------|----------|-------------|
| GSTIN | For B2B | 15-character GST number |
| PAN | Optional | 10-character PAN |

**Credit Settings:**
| Field | Description |
|-------|-------------|
| Credit Limit | Maximum outstanding allowed |
| Payment Terms | Net 15, Net 30, etc. |

4. Click **Save**

#### Editing a Customer

1. Go to **CRM → Customers**
2. Find customer in list (use search)
3. Click on customer row or **Edit** button
4. Update fields
5. Click **Save**

#### Customer Status

| Status | Meaning |
|--------|---------|
| **Active** | Can place orders, receive service |
| **Inactive** | Temporarily disabled |
| **Blocked** | Credit issues, cannot transact |
| **Prospect** | Potential customer (from leads) |

---

### 2.2 Customer 360° View

**Navigation:** CRM → Customer 360

A complete view of customer history and interactions.

#### What You Can See

| Section | Information |
|---------|-------------|
| **Profile** | Contact details, addresses |
| **Orders** | All orders placed |
| **Invoices** | All invoices generated |
| **Payments** | Payment history |
| **Service History** | All service requests |
| **Products Owned** | Installed products with serial numbers |
| **AMC Status** | Active contracts |
| **Warranty Status** | Warranty expiry dates |
| **Communication Log** | Calls, emails, notes |

#### How to Use

1. Go to **CRM → Customer 360**
2. Search for customer by:
   - Name
   - Phone number
   - Email
   - Customer ID
3. View complete history
4. Take actions:
   - Create new order
   - Raise service request
   - Add note
   - Schedule callback

---

### 2.3 Lead Management

**Navigation:** CRM → Leads

#### Lead Sources

| Source | Description |
|--------|-------------|
| Website | Online inquiry form |
| Phone | Inbound calls |
| Referral | Customer referrals |
| Walk-in | Showroom visitors |
| Campaign | Marketing campaigns |
| Social Media | Facebook, Instagram inquiries |
| Just Dial | JustDial leads |
| IndiaMART | IndiaMART inquiries |

#### Creating a Lead

1. Go to **CRM → Leads**
2. Click **+ New Lead**
3. Enter:
   - Name
   - Phone
   - Email (optional)
   - Source
   - Product Interest
   - Notes
4. Assign to sales person
5. Click **Save**

#### Lead Stages

```
NEW → CONTACTED → QUALIFIED → PROPOSAL → NEGOTIATION → WON/LOST
```

| Stage | Action Required |
|-------|-----------------|
| **New** | First contact within 24 hours |
| **Contacted** | Initial call made, gather requirements |
| **Qualified** | Budget confirmed, decision timeline known |
| **Proposal** | Quotation sent |
| **Negotiation** | Price/terms discussion |
| **Won** | Convert to customer & order |
| **Lost** | Record reason, close lead |

#### Converting Lead to Customer

1. Open lead in **Won** stage
2. Click **Convert to Customer**
3. System creates customer record
4. Lead is marked as converted

---

### 2.4 Call Center

**Navigation:** CRM → Call Center

For managing inbound and outbound calls.

#### Logging a Call

1. Go to **CRM → Call Center**
2. Click **+ Log Call**
3. Enter:
   - Customer (search by phone/name)
   - Call Type (Inbound/Outbound)
   - Purpose (Inquiry, Complaint, Follow-up, etc.)
   - Notes
   - Next Action
   - Follow-up Date
4. Click **Save**

#### Call Types

| Type | Purpose |
|------|---------|
| **Inquiry** | Product/price questions |
| **Complaint** | Service issues |
| **Follow-up** | Post-sale check |
| **Feedback** | Customer satisfaction |
| **Collection** | Payment reminder |
| **Scheduling** | Installation/service scheduling |

#### Call Disposition

| Disposition | Meaning |
|-------------|---------|
| Answered | Call connected |
| No Answer | Customer didn't pick up |
| Busy | Line busy |
| Callback Requested | Customer asked to call later |
| Wrong Number | Invalid number |
| DND | Do Not Disturb |

---

### 2.5 Escalations

**Navigation:** CRM → Escalations

For tracking and resolving escalated issues.

#### Escalation Levels

| Level | Handled By | SLA |
|-------|------------|-----|
| **L1** | Customer Support | 4 hours |
| **L2** | Team Lead | 8 hours |
| **L3** | Manager | 24 hours |
| **L4** | Head of Service | 48 hours |

#### Creating an Escalation

1. Go to **CRM → Escalations**
2. Click **+ New Escalation**
3. Enter:
   - Customer
   - Related Service Request (if any)
   - Issue Description
   - Priority (Low/Medium/High/Critical)
   - Escalation Level
4. Assign to handler
5. Click **Save**

#### Escalation Status

| Status | Meaning |
|--------|---------|
| **Open** | Being worked on |
| **Pending Customer** | Awaiting customer response |
| **Pending Internal** | Awaiting internal action |
| **Resolved** | Issue fixed |
| **Closed** | Customer confirmed resolution |

---

## 3. Service Module

### 3.1 Service Request Management

**Navigation:** Service → Service Requests

#### Service Request Types

| Type | Description | SLA |
|------|-------------|-----|
| **Installation** | New product installation | 48 hours |
| **Repair** | Product not working | 24 hours |
| **Maintenance** | Routine service/filter change | 72 hours |
| **Complaint** | Quality/service issue | 24 hours |
| **AMC Visit** | Scheduled AMC service | As per schedule |
| **Warranty Claim** | Warranty-covered repair | 48 hours |

#### Creating a Service Request

1. Go to **Service → Service Requests**
2. Click **+ New Request**
3. Enter:

**Customer Details:**
| Field | Required | Description |
|-------|----------|-------------|
| Customer | Yes | Search by phone/name |
| Contact Person | No | If different from customer |
| Contact Phone | Yes | For technician coordination |
| Service Address | Yes | Where service is needed |

**Product Details:**
| Field | Required | Description |
|-------|----------|-------------|
| Product | Yes | Which product needs service |
| Serial Number | Recommended | For warranty verification |
| Purchase Date | If known | To check warranty |

**Request Details:**
| Field | Required | Description |
|-------|----------|-------------|
| Request Type | Yes | Installation, Repair, etc. |
| Priority | Yes | Low, Medium, High, Urgent |
| Problem Description | Yes | Detailed issue description |
| Preferred Date | No | Customer's preferred date |
| Preferred Time Slot | No | Morning/Afternoon/Evening |

4. Click **Save**

#### Service Request Status Flow

```
NEW
  ↓
ASSIGNED (Technician assigned)
  ↓
SCHEDULED (Date/time confirmed)
  ↓
IN_PROGRESS (Technician on site)
  ↓
COMPLETED / PENDING_PARTS / ESCALATED
  ↓
CLOSED (Customer confirmed)
```

#### Assigning Technician

1. Open service request
2. Click **Assign Technician**
3. Select technician based on:
   - Availability
   - Location/pincode
   - Skill set
   - Current workload
4. Set scheduled date/time
5. Click **Assign**

---

### 3.2 Installations

**Navigation:** Service → Installations

Track new product installations.

#### Installation Workflow

```
Order Delivered
      ↓
Installation Request Created (Auto/Manual)
      ↓
Technician Assigned
      ↓
Installation Scheduled
      ↓
Technician Visits
      ↓
Installation Completed
      ↓
Customer Sign-off
      ↓
Warranty Activated
```

#### Creating Installation Request

**Option 1: From Order**
- When order is marked delivered, system can auto-create installation request

**Option 2: Manual**
1. Go to **Service → Installations**
2. Click **+ New Installation**
3. Select customer and product
4. Enter delivery date
5. Assign technician
6. Save

#### Installation Checklist

Technician must complete:
- [ ] Product unpacked and inspected
- [ ] Site survey done
- [ ] Installation location confirmed
- [ ] Water source checked
- [ ] Drain outlet available
- [ ] Electrical point available
- [ ] Installation completed
- [ ] Product tested
- [ ] Customer trained on usage
- [ ] Customer signed installation report
- [ ] Before/After photos uploaded

#### Completing Installation

1. Technician opens installation in mobile app
2. Completes checklist
3. Enters:
   - Serial number (scan barcode)
   - Installation date/time
   - Photos
   - Customer signature
4. Submits completion
5. System activates warranty

---

### 3.3 Warranty Management

**Navigation:** Service → Warranty Claims

#### Warranty Types

| Type | Duration | Coverage |
|------|----------|----------|
| **Standard** | 1 year | Manufacturing defects |
| **Extended** | 2-5 years | Manufacturing defects |
| **AMC** | 1 year | All parts + service |
| **Comprehensive** | 1-3 years | Parts + labor + consumables |

#### Checking Warranty Status

1. Go to **Service → Service Requests**
2. Enter product serial number
3. System shows:
   - Purchase date
   - Warranty type
   - Expiry date
   - Coverage details
   - Claim history

#### Creating Warranty Claim

1. Go to **Service → Warranty Claims**
2. Click **+ New Claim**
3. Enter:
   - Customer
   - Product Serial Number
   - Problem Description
   - Defect Type
4. System validates warranty
5. If valid, claim is created
6. Assign technician for inspection

#### Warranty Claim Status

| Status | Meaning |
|--------|---------|
| **Submitted** | Claim received |
| **Under Review** | Being evaluated |
| **Approved** | Claim accepted |
| **Rejected** | Not covered (reason given) |
| **Parts Ordered** | Replacement parts ordered |
| **In Progress** | Repair/replacement ongoing |
| **Completed** | Claim resolved |

#### Claim Rejection Reasons

| Reason | Description |
|--------|-------------|
| Out of Warranty | Warranty period expired |
| Physical Damage | Customer-caused damage |
| Unauthorized Repair | Third-party tampering |
| Consumable | Item not covered (e.g., filters) |
| Misuse | Product used incorrectly |

---

### 3.4 AMC (Annual Maintenance Contracts)

**Navigation:** Service → AMC Contracts

#### AMC Types

| Type | Includes | Price Range |
|------|----------|-------------|
| **Basic** | 2 services/year | ₹1,500 - 2,500 |
| **Standard** | 4 services + parts discount | ₹3,000 - 4,500 |
| **Premium** | Unlimited services + free parts | ₹5,000 - 8,000 |
| **Comprehensive** | All inclusive + priority | ₹8,000 - 12,000 |

#### Creating AMC Contract

1. Go to **Service → AMC**
2. Click **+ New AMC**
3. Enter:
   - Customer
   - Product(s) covered
   - AMC Type
   - Start Date
   - Duration (1/2/3 years)
   - Amount
   - Payment received (Yes/No)
4. Click **Save**

#### AMC Renewal Workflow

```
30 days before expiry → System sends renewal reminder
      ↓
Customer contacted by CRM
      ↓
If renewed → New AMC created, linked to previous
      ↓
If not renewed → Mark as expired
```

#### Scheduled AMC Visits

System auto-generates service visits based on AMC terms:

| AMC Type | Visits/Year | Schedule |
|----------|-------------|----------|
| Basic | 2 | Every 6 months |
| Standard | 4 | Every 3 months |
| Premium | As needed | On request |

---

### 3.5 Technician Management

**Navigation:** Service → Technicians

#### Adding a Technician

1. Go to **Service → Technicians**
2. Click **+ Add Technician**
3. Enter:
   - Name
   - Phone
   - Email
   - Employee ID (if internal)
   - Technician Type (Internal/Franchisee/Contract)
   - Skills (Installation, Repair, etc.)
   - Service Areas (Pincodes)
4. Click **Save**

#### Technician Types

| Type | Description |
|------|-------------|
| **Internal** | Company employee |
| **Franchisee** | Franchise partner technician |
| **Contract** | Third-party contractor |

#### Technician Skills

| Skill | Jobs Assigned |
|-------|---------------|
| Installation | New installations |
| Repair - Basic | Simple repairs |
| Repair - Advanced | Complex repairs |
| Electrical | Electrical issues |
| Plumbing | Water connection issues |
| RO Specialist | RO system expert |

#### Viewing Technician Schedule

1. Go to **Service → Technicians**
2. Click on technician name
3. View calendar showing:
   - Assigned jobs
   - Completed jobs
   - Available slots

#### Technician Performance Metrics

| Metric | Target |
|--------|--------|
| Jobs Completed/Day | 4-6 |
| First-Time Fix Rate | >85% |
| Customer Rating | >4.0/5 |
| On-Time Arrival | >90% |
| Average Job Duration | <2 hours |

---

## 4. Common Workflows

### 4.1 New Customer Onboarding

```
1. Customer inquiry (Phone/Website/Walk-in)
      ↓
2. Create Lead (CRM → Leads)
      ↓
3. Qualify lead (call, understand requirements)
      ↓
4. Send quotation
      ↓
5. Convert to Customer (CRM → Customers)
      ↓
6. Create Order
      ↓
7. Delivery
      ↓
8. Installation (Service → Installations)
      ↓
9. Post-installation call (CRM → Call Center)
      ↓
10. Offer AMC (Service → AMC)
```

### 4.2 Service Request Resolution

```
1. Customer calls with issue
      ↓
2. Log call (CRM → Call Center)
      ↓
3. Create Service Request (Service → Service Requests)
      ↓
4. Check warranty status
      ↓
5. Assign technician
      ↓
6. Schedule visit
      ↓
7. Technician visits & resolves
      ↓
8. Close service request
      ↓
9. Collect feedback
      ↓
10. If issue persists → Escalate
```

### 4.3 AMC Service Visit

```
1. System generates scheduled visit
      ↓
2. Customer notified (SMS/Email)
      ↓
3. Technician assigned
      ↓
4. Technician visits
      ↓
5. Performs maintenance:
   - Filter check/replacement
   - Water quality test
   - General inspection
   - Cleaning
      ↓
6. Updates service record
      ↓
7. Customer signs off
      ↓
8. Next visit scheduled
```

### 4.4 Handling Customer Complaint

```
1. Complaint received (Call/Email/Social)
      ↓
2. Log in CRM → Call Center
      ↓
3. Create service request if technical issue
      ↓
4. If serious → Create Escalation
      ↓
5. Assign handler based on escalation level
      ↓
6. Investigate & resolve
      ↓
7. Communicate resolution to customer
      ↓
8. Get confirmation
      ↓
9. Close complaint
      ↓
10. Analyze root cause for improvement
```

---

## 5. Reports & Analytics

### 5.1 CRM Reports

| Report | Navigation | Purpose |
|--------|------------|---------|
| Lead Conversion | CRM Reports | Track lead-to-customer rate |
| Customer Acquisition | CRM Reports | New customers by period |
| Customer Segmentation | CRM Reports | Customers by type/region |
| Call Analytics | CRM Reports | Call volume, disposition |

### 5.2 Service Reports

| Report | Navigation | Purpose |
|--------|------------|---------|
| Service Summary | Service Reports | Requests by type/status |
| Technician Performance | Service Reports | Jobs, ratings, efficiency |
| SLA Compliance | Service Reports | On-time resolution rate |
| Warranty Claims | Service Reports | Claims analysis |
| AMC Status | Service Reports | Active, expiring, expired |

### 5.3 Key Metrics to Monitor

**Daily:**
- New service requests
- Pending assignments
- Today's scheduled visits
- Overdue requests

**Weekly:**
- First-time fix rate
- Customer satisfaction score
- Technician utilization
- Escalation count

**Monthly:**
- Total installations
- AMC renewals
- Warranty claims
- Revenue from service

---

## 6. Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| Cannot find customer | Check phone number format, try alternate search |
| Serial number not found | Verify number, check if product registered |
| Cannot assign technician | Check technician is active and has matching skills |
| Warranty shows invalid | Verify installation date in system |
| AMC visits not generating | Check AMC is active and schedule is set |

### Error Messages

| Error | Meaning | Action |
|-------|---------|--------|
| "Customer not found" | No matching customer | Create customer first |
| "Product not registered" | Serial not in system | Register product |
| "No technicians available" | All technicians busy | Check schedules, add capacity |
| "Warranty expired" | Out of warranty period | Offer paid service or AMC |
| "Duplicate request" | Similar request exists | Check existing requests |

### Support Contacts

| Issue Type | Contact |
|------------|---------|
| Technical/System | IT Support |
| Process/Training | Operations Manager |
| Customer Escalation | Service Head |

---

## Quick Reference Card

### Daily Tasks - Service Coordinator

| Time | Task | Navigation |
|------|------|------------|
| 9:00 AM | Check new requests | Service → Requests (filter: New) |
| 9:30 AM | Assign technicians | Service → Requests → Assign |
| 10:00 AM | Confirm today's schedule | Service → Calendar |
| 2:00 PM | Follow up on pending | Service → Requests (filter: Pending) |
| 4:00 PM | Check completed jobs | Service → Requests (filter: Completed) |
| 5:00 PM | Close resolved requests | Service → Requests → Close |

### Daily Tasks - CRM Executive

| Time | Task | Navigation |
|------|------|------------|
| 9:00 AM | Check new leads | CRM → Leads (filter: New) |
| 10:00 AM | Follow-up calls | CRM → Call Center |
| 12:00 PM | Update lead status | CRM → Leads |
| 2:00 PM | Customer callbacks | CRM → Call Center |
| 4:00 PM | Log all calls | CRM → Call Center |
| 5:00 PM | Plan tomorrow's calls | CRM → Tasks |

---

*Document prepared for Aquapurite ERP v1.0*

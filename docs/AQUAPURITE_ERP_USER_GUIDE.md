# Aquapurite ERP - Finance & Operations User Guide

## For Finance Head, Accounts Head & Operations Team

**Version:** 1.0
**Last Updated:** January 2026

---

## Table of Contents

1. [Getting Started - Setup Sequence](#1-getting-started---setup-sequence)
2. [Master Data Setup](#2-master-data-setup)
3. [Finance Module](#3-finance-module)
4. [Procurement Module](#4-procurement-module)
5. [Billing Module](#5-billing-module)
6. [Inventory Module](#6-inventory-module)
7. [Common Workflows](#7-common-workflows)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Getting Started - Setup Sequence

### IMPORTANT: Follow This Order

Before using the ERP for daily transactions, master data must be set up in the correct sequence. **If you skip steps, dropdown menus will appear empty.**

```
STEP 1: Company Setup
    ↓
STEP 2: Chart of Accounts (Finance)
    ↓
STEP 3: Financial Periods (Finance)
    ↓
STEP 4: Warehouses (Inventory)
    ↓
STEP 5: Product Categories & Brands (Catalog)
    ↓
STEP 6: Products (Catalog)
    ↓
STEP 7: Vendors (Procurement)
    ↓
STEP 8: Customers (CRM)
    ↓
STEP 9: Cost Centers (Finance) - Optional
    ↓
NOW YOU CAN START TRANSACTIONS
```

### Quick Reference: What Depends on What

| Feature | Requires First |
|---------|---------------|
| **Receipts** | Customers must exist |
| **Auto Journal** | Chart of Accounts (Bank accounts) must exist |
| **Invoices** | Customers + Products must exist |
| **Purchase Orders** | Vendors + Products must exist |
| **GRN** | Purchase Order must be approved |
| **Stock Transfers** | Multiple Warehouses must exist |
| **Journal Entries** | Chart of Accounts must exist |

---

## 2. Master Data Setup

### 2.1 Chart of Accounts (MUST DO FIRST)

**Navigation:** Finance → Chart of Accounts

The Chart of Accounts is the foundation of all financial transactions. Without accounts, you cannot:
- Record receipts (need Bank/Cash accounts)
- Create journal entries
- Generate financial reports

#### Standard Account Structure for Aquapurite

| Account Code | Account Name | Type | Purpose |
|--------------|--------------|------|---------|
| **1000** | **ASSETS** | Header | |
| 1100 | Current Assets | Header | |
| 1101 | Cash in Hand | ASSET | Petty cash |
| 1102 | HDFC Bank - Current A/c | ASSET | Main bank account |
| 1103 | ICICI Bank - Current A/c | ASSET | Secondary bank |
| 1104 | Razorpay Settlement | ASSET | Payment gateway |
| 1110 | Accounts Receivable | ASSET | Customer dues |
| 1120 | Inventory | ASSET | Stock value |
| 1130 | Advance to Suppliers | ASSET | PO advances |
| **2000** | **LIABILITIES** | Header | |
| 2100 | Current Liabilities | Header | |
| 2101 | Accounts Payable | LIABILITY | Vendor dues |
| 2102 | GST Payable - CGST | LIABILITY | Tax liability |
| 2103 | GST Payable - SGST | LIABILITY | Tax liability |
| 2104 | GST Payable - IGST | LIABILITY | Tax liability |
| 2105 | TDS Payable | LIABILITY | TDS deducted |
| 2110 | Advance from Customers | LIABILITY | Customer advances |
| **3000** | **EQUITY** | Header | |
| 3001 | Share Capital | EQUITY | Owner's capital |
| 3002 | Retained Earnings | EQUITY | Accumulated profit |
| **4000** | **REVENUE** | Header | |
| 4001 | Sales - Water Purifiers | REVENUE | Product sales |
| 4002 | Sales - Spare Parts | REVENUE | Spare sales |
| 4003 | Sales - AMC | REVENUE | Service contracts |
| 4004 | Installation Income | REVENUE | Installation fees |
| **5000** | **EXPENSES** | Header | |
| 5001 | Cost of Goods Sold | EXPENSE | Product cost |
| 5002 | Freight & Logistics | EXPENSE | Shipping costs |
| 5003 | Salaries & Wages | EXPENSE | Employee cost |
| 5004 | Rent | EXPENSE | Office/warehouse rent |
| 5005 | Utilities | EXPENSE | Electricity, water |
| 5006 | Marketing & Advertising | EXPENSE | Promotions |
| 5007 | Bank Charges | EXPENSE | Transaction fees |

#### How to Create Accounts

1. Go to **Finance → Chart of Accounts**
2. Click **+ Add Account**
3. Fill in:
   - **Code**: Use the numbering system above
   - **Name**: Account name
   - **Type**: ASSET, LIABILITY, EQUITY, REVENUE, or EXPENSE
   - **Parent**: Select parent account (e.g., 1100 for 1101)
   - **Is Active**: Yes
4. Click **Save**

**TIP:** Create header accounts first (1000, 2000, 3000, 4000, 5000), then create sub-accounts under them.

---

### 2.2 Financial Periods

**Navigation:** Finance → Financial Periods

Financial periods define your accounting year and control which months are open for transactions.

#### Setup Steps

1. Go to **Finance → Financial Periods**
2. Click **+ Create Period**
3. Enter:
   - **Financial Year**: 2025-26 (or current year)
   - **Start Date**: 01-Apr-2025
   - **End Date**: 31-Mar-2026
4. The system will create 12 monthly periods
5. **Open** the current month for transactions
6. **Close** past months after reconciliation

#### Period Status

| Status | Meaning |
|--------|---------|
| **OPEN** | Transactions allowed |
| **CLOSED** | No new transactions (month-end done) |
| **LOCKED** | Audit complete, cannot modify |

---

### 2.3 Customers (Required for Receipts & Invoices)

**Navigation:** CRM → Customers

#### Creating a Customer

1. Go to **CRM → Customers**
2. Click **+ New Customer**
3. **Required Fields:**
   - Name
   - Email or Phone
   - Billing Address
   - State (for GST)
   - GSTIN (if B2B customer)
4. **Optional but Recommended:**
   - Credit Limit
   - Payment Terms (e.g., Net 30)
   - Customer Type (B2B/B2C)
5. Click **Save**

**WHY THIS MATTERS:** The Receipts page shows "Select Customer" dropdown. If no customers exist, this dropdown will be empty.

---

### 2.4 Vendors (Required for Procurement)

**Navigation:** Procurement → Vendors

#### Creating a Vendor

1. Go to **Procurement → Vendors**
2. Click **+ New Vendor**
3. **Required Fields:**
   - Vendor Name
   - Email
   - Phone
   - Address
   - State
   - GSTIN
   - PAN
4. **Bank Details (for payments):**
   - Bank Name
   - Account Number
   - IFSC Code
5. Click **Save**

---

### 2.5 Warehouses (Required for Inventory)

**Navigation:** Inventory → Warehouses

#### Standard Warehouse Setup

| Code | Name | Type | Purpose |
|------|------|------|---------|
| WH-MAIN | Main Warehouse | OWNED | Primary storage |
| WH-DELHI | Delhi Hub | OWNED | Regional hub |
| WH-MUMBAI | Mumbai Hub | OWNED | Regional hub |
| WH-DEFECT | Defective Stock | OWNED | QC rejected items |
| WH-TRANSIT | In Transit | VIRTUAL | Goods in shipment |

---

## 3. Finance Module

### 3.1 Journal Entries

**Navigation:** Finance → Journal Entries

Journal entries record all financial transactions using double-entry bookkeeping.

#### Golden Rule of Accounting

| Account Type | Debit When | Credit When |
|--------------|------------|-------------|
| ASSET | Increases | Decreases |
| LIABILITY | Decreases | Increases |
| EQUITY | Decreases | Increases |
| REVENUE | Decreases | Increases |
| EXPENSE | Increases | Decreases |

#### Creating a Manual Journal Entry

1. Go to **Finance → Journal Entries**
2. Click **+ New Entry**
3. Enter:
   - **Entry Date**: Transaction date
   - **Narration**: Description of the transaction
4. Add lines:
   - Select Account
   - Enter Debit OR Credit amount
   - Add description for line
5. **Total Debits MUST equal Total Credits**
6. Click **Save as Draft** or **Post**

#### Example: Recording a Bank Deposit

| Account | Debit | Credit | Description |
|---------|-------|--------|-------------|
| HDFC Bank (1102) | 50,000 | | Cash deposited |
| Cash in Hand (1101) | | 50,000 | Cash deposited to bank |

---

### 3.2 Auto Journal (Automatic Entry Generation)

**Navigation:** Finance → Auto Journal

Auto Journal automatically creates journal entries from:
- Sales Invoices
- Payment Receipts
- Bank Transactions

#### Prerequisites

Before using Auto Journal, you MUST have:
1. ✅ Chart of Accounts created (especially bank accounts)
2. ✅ Invoices created in the system
3. ✅ Receipts recorded

#### How to Use Auto Journal

**From Sales Invoice:**
1. Go to **Finance → Auto Journal**
2. Click **From Sales Invoice** card
3. Select an invoice from dropdown
4. Check "Auto-post" if you want to post immediately
5. Click **Generate Journal**

**Generated Entry:**
| Account | Debit | Credit |
|---------|-------|--------|
| Accounts Receivable | Invoice Amount | |
| Sales Revenue | | Net Amount |
| GST Payable - CGST | | CGST Amount |
| GST Payable - SGST | | SGST Amount |

**From Payment Receipt:**
1. Click **From Payment Receipt** card
2. Enter Receipt ID
3. Select Bank Account (where money was received)
4. Click **Generate Journal**

**Generated Entry:**
| Account | Debit | Credit |
|---------|-------|--------|
| Bank Account (HDFC) | Receipt Amount | |
| Accounts Receivable | | Receipt Amount |

**WHY BANK ACCOUNT DROPDOWN IS EMPTY:**
If you don't see bank accounts in the dropdown, it means no bank accounts have been created in Chart of Accounts. Go to Finance → Chart of Accounts and create bank accounts first (Account Type: ASSET).

---

### 3.3 General Ledger

**Navigation:** Finance → General Ledger

View all transactions for a specific account.

1. Select Account from dropdown
2. Select Date Range
3. Click **View Ledger**

Shows: Opening Balance → All Transactions → Closing Balance

---

### 3.4 Bank Reconciliation

**Navigation:** Finance → Bank Reconciliation

Match bank statement entries with recorded transactions.

1. Select Bank Account
2. Upload Bank Statement (Excel/CSV) or enter manually
3. System shows unmatched transactions
4. Match each bank entry with system entry
5. Mark as Reconciled

---

### 3.5 TDS Management

**Navigation:** Finance → TDS Management

Record Tax Deducted at Source on vendor payments.

#### Common TDS Sections

| Section | Nature of Payment | Rate |
|---------|-------------------|------|
| 194C | Contractor Payment | 1% / 2% |
| 194J | Professional Fees | 10% |
| 194H | Commission | 5% |
| 194I | Rent | 10% |

#### Recording TDS

1. Go to **Finance → TDS Management**
2. Click **+ Record Deduction**
3. Enter:
   - Vendor (Deductee)
   - Section (194C, 194J, etc.)
   - Payment Amount
   - TDS Amount (auto-calculated)
4. Mark as Deposited after paying to government

---

## 4. Procurement Module

### 4.1 Procurement Workflow

```
Purchase Requisition (PR)
    ↓ (Approval)
Vendor Proforma / Quotation
    ↓ (Selection)
Purchase Order (PO)
    ↓ (Approval & Send to Vendor)
Goods Receipt Note (GRN)
    ↓ (Quality Check)
Vendor Invoice
    ↓ (3-Way Match)
Payment to Vendor
```

### 4.2 Purchase Requisition

**Navigation:** Procurement → Requisitions

Create a request for items needed.

1. Click **+ New Requisition**
2. Enter:
   - Required Date
   - Priority (Low/Medium/High/Urgent)
   - Department
3. Add Items:
   - Select Product
   - Enter Quantity
   - Add specifications/notes
4. Submit for Approval

### 4.3 Purchase Order

**Navigation:** Procurement → Purchase Orders

After requisition approval, create PO.

1. Click **+ New PO**
2. Select Vendor
3. Add Items (can import from requisition)
4. Enter:
   - Unit Price
   - GST Rate
   - Delivery Date
5. Add Terms & Conditions
6. Save as Draft
7. Submit for Approval
8. After approval, **Send to Vendor**

#### PO Statuses

| Status | Meaning |
|--------|---------|
| DRAFT | Being prepared |
| PENDING_APPROVAL | Waiting for approval |
| APPROVED | Ready to send |
| SENT_TO_VENDOR | Vendor notified |
| PARTIALLY_RECEIVED | Some items received |
| FULLY_RECEIVED | All items received |
| CLOSED | PO completed |

### 4.4 Goods Receipt Note (GRN)

**Navigation:** Procurement → GRN

Record goods received against a PO.

1. Click **+ Create GRN**
2. Select Purchase Order
3. Enter:
   - Received Date
   - Received Quantity (per item)
   - Quality Check Status (Accept/Reject)
   - Warehouse location
4. Scan or enter serial numbers (for serialized items)
5. Submit

**After GRN:**
- Inventory is updated automatically
- Vendor invoice can be matched

### 4.5 Vendor Invoice & 3-Way Match

**Navigation:** Procurement → Vendor Invoices → 3-Way Match

Before paying a vendor, verify:
1. **PO Amount** matches
2. **GRN Quantity** matches
3. **Invoice Amount** matches

1. Go to **3-Way Match**
2. Select Vendor Invoice
3. System shows PO, GRN, and Invoice side by side
4. Highlight any mismatches
5. Approve if matched
6. Process Payment

---

## 5. Billing Module

### 5.1 Billing Workflow

```
Sales Order
    ↓
Invoice Generation
    ↓
E-Way Bill (if applicable)
    ↓
Dispatch/Delivery
    ↓
Payment Receipt
    ↓
(If return) Credit Note
```

### 5.2 Creating an Invoice

**Navigation:** Billing → Invoices

1. Click **+ New Invoice**
2. Select Customer (MUST exist in CRM → Customers)
3. Select Sales Order (optional)
4. Add Line Items:
   - Product
   - Quantity
   - Unit Price
   - Discount (if any)
   - GST Rate
5. System calculates:
   - Subtotal
   - GST (CGST + SGST or IGST)
   - Grand Total
6. Add Payment Terms
7. **Save** or **Save & Send**

### 5.3 E-Way Bill

**Navigation:** Billing → E-Way Bills

Required for goods movement above ₹50,000.

1. Go to **E-Way Bills**
2. Select Invoice
3. Enter:
   - Transporter Name
   - Vehicle Number
   - Distance (km)
4. Generate E-Way Bill Number

### 5.4 Payment Receipts

**Navigation:** Billing → Receipts

**IMPORTANT:** Customers must exist before recording receipts.

#### Recording a Receipt

1. Go to **Billing → Receipts**
2. Click **+ Record Payment**
3. Select **Customer** (from dropdown)
4. Select **Invoice** (optional - for allocation)
5. Enter:
   - Amount Received
   - Payment Date
   - Payment Mode (Cash/UPI/Bank Transfer/Cheque)
   - Reference Number (transaction ID, cheque number)
6. Click **Record Payment**

#### Why Customer Dropdown is Empty?

If no customers appear:
1. Go to **CRM → Customers**
2. Create customers first
3. Return to Receipts page

### 5.5 Credit Notes

**Navigation:** Billing → Credit Notes

Issue when:
- Customer returns goods
- Pricing error in invoice
- Quality issues

1. Click **+ New Credit Note**
2. Select Original Invoice
3. Enter reason
4. Enter amount to credit
5. Submit

---

## 6. Inventory Module

### 6.1 Stock Summary

**Navigation:** Inventory → Stock Summary

View current stock levels across all warehouses.

| Column | Meaning |
|--------|---------|
| Available | Can be sold |
| Reserved | Allocated to orders |
| In Transit | Being shipped |
| Total | All stock |

### 6.2 Stock Adjustments

**Navigation:** Inventory → Adjustments

Record inventory changes outside normal transactions.

**Reasons for Adjustment:**
- Physical count variance
- Damaged goods
- Expired products
- Sample/Demo units

1. Click **+ New Adjustment**
2. Select Warehouse
3. Select Product
4. Enter:
   - Current System Qty (shown)
   - Actual Qty (counted)
   - Variance (calculated)
   - Reason
5. Submit for Approval

### 6.3 Stock Transfers

**Navigation:** Inventory → Transfers

Move stock between warehouses.

1. Click **+ New Transfer**
2. Select:
   - Source Warehouse
   - Destination Warehouse
3. Add Products and Quantities
4. Submit
5. At destination, **Receive Transfer**

---

## 7. Common Workflows

### 7.1 Complete Sales Cycle

```
1. Customer calls/orders online
    ↓
2. Create Sales Order (Orders → New Order)
    ↓
3. Check inventory availability
    ↓
4. Generate Invoice (Billing → Invoices)
    ↓
5. Create Shipment (Logistics → Shipments)
    ↓
6. Generate E-Way Bill (if > ₹50,000)
    ↓
7. Dispatch goods
    ↓
8. Customer receives & pays
    ↓
9. Record Receipt (Billing → Receipts)
    ↓
10. Generate Journal Entry (Finance → Auto Journal)
```

### 7.2 Complete Purchase Cycle

```
1. Identify need for stock
    ↓
2. Create Purchase Requisition
    ↓
3. Get approval
    ↓
4. Request quotations from vendors
    ↓
5. Create Purchase Order
    ↓
6. Get PO approved
    ↓
7. Send PO to vendor
    ↓
8. Receive goods, create GRN
    ↓
9. Quality check
    ↓
10. Receive vendor invoice
    ↓
11. 3-Way match (PO vs GRN vs Invoice)
    ↓
12. Process payment (with TDS if applicable)
    ↓
13. Record in journal
```

### 7.3 Month-End Closing

```
1. Ensure all invoices are generated
    ↓
2. Ensure all receipts are recorded
    ↓
3. Ensure all vendor invoices are entered
    ↓
4. Bank reconciliation
    ↓
5. Review pending journal entries (Auto Journal → Post All)
    ↓
6. Run Trial Balance (Reports → Trial Balance)
    ↓
7. Check Debits = Credits
    ↓
8. Close the month (Finance → Periods → Close)
```

---

## 8. Troubleshooting

### Problem: Dropdown is Empty

| Dropdown | Solution |
|----------|----------|
| Customer (in Receipts) | Create customers in CRM → Customers |
| Bank Account (in Auto Journal) | Create bank accounts in Finance → Chart of Accounts |
| Vendor (in PO) | Create vendors in Procurement → Vendors |
| Product (in Invoice) | Create products in Catalog |
| Warehouse (in GRN) | Create warehouses in Inventory → Warehouses |

### Problem: Cannot Create Invoice

**Check:**
1. Is customer created? (CRM → Customers)
2. Are products created? (Catalog)
3. Is current financial period OPEN?

### Problem: Cannot Create GRN

**Check:**
1. Is there an approved PO?
2. Is the PO sent to vendor?
3. Is warehouse created?

### Problem: Journal Entry Won't Post

**Check:**
1. Do Debits equal Credits?
2. Is the entry date in an OPEN period?
3. Are all accounts valid and active?

### Problem: Reports Show Zero

**Check:**
1. Are journal entries posted (not just saved as draft)?
2. Is the date range correct?
3. Is the financial period correct?

---

## Quick Reference Card

### Daily Tasks (Accounts Executive)

| Time | Task | Navigation |
|------|------|------------|
| Morning | Record yesterday's receipts | Billing → Receipts |
| Morning | Check pending invoices | Billing → Invoices |
| Midday | Enter vendor invoices | Procurement → Vendor Invoices |
| Midday | Process 3-way matches | Procurement → 3-Way Match |
| Evening | Bank reconciliation | Finance → Bank Reconciliation |
| Evening | Post pending journals | Finance → Auto Journal |

### Weekly Tasks (Accounts Manager)

| Day | Task | Navigation |
|-----|------|------------|
| Monday | Review pending approvals | Approvals |
| Wednesday | Check outstanding receivables | Reports |
| Friday | Review week's transactions | Finance → Journal Entries |

### Monthly Tasks (Finance Head)

| Task | Navigation |
|------|------------|
| Bank reconciliation (all accounts) | Finance → Bank Reconciliation |
| GST filing preparation | Finance → GSTR-1, GSTR-3B |
| TDS deposit verification | Finance → TDS Management |
| Trial Balance review | Reports → Trial Balance |
| P&L review | Reports → Profit & Loss |
| Close month | Finance → Periods |

---

## Support

For technical issues:
- Check this guide first
- Contact system administrator
- Email: support@aquapurite.com

---

*Document prepared for Aquapurite ERP v1.0*

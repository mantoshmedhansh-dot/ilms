# Aquapurite ERP - Initial Setup Checklist

**For Finance & Accounts Team**

Print this checklist and tick off each item as you complete it.

---

## PHASE 1: Foundation Setup (Day 1)

### Chart of Accounts
**Navigation:** Finance → Chart of Accounts

- [ ] Create Header: **1000 - ASSETS**
- [ ] Create Header: **2000 - LIABILITIES**
- [ ] Create Header: **3000 - EQUITY**
- [ ] Create Header: **4000 - REVENUE**
- [ ] Create Header: **5000 - EXPENSES**

### Bank Accounts (Under Assets)
- [ ] **1101** - Cash in Hand (Type: ASSET)
- [ ] **1102** - HDFC Bank Current A/c (Type: ASSET)
- [ ] **1103** - ICICI Bank Current A/c (Type: ASSET)
- [ ] **1104** - Razorpay Settlement A/c (Type: ASSET)

### Receivables & Payables
- [ ] **1110** - Accounts Receivable (Type: ASSET)
- [ ] **2101** - Accounts Payable (Type: LIABILITY)

### GST Accounts
- [ ] **2102** - GST Payable - CGST (Type: LIABILITY)
- [ ] **2103** - GST Payable - SGST (Type: LIABILITY)
- [ ] **2104** - GST Payable - IGST (Type: LIABILITY)
- [ ] **1115** - GST Input - CGST (Type: ASSET)
- [ ] **1116** - GST Input - SGST (Type: ASSET)
- [ ] **1117** - GST Input - IGST (Type: ASSET)

### Revenue Accounts
- [ ] **4001** - Sales - Water Purifiers (Type: REVENUE)
- [ ] **4002** - Sales - Spare Parts (Type: REVENUE)
- [ ] **4003** - Sales - AMC (Type: REVENUE)

### Expense Accounts
- [ ] **5001** - Cost of Goods Sold (Type: EXPENSE)
- [ ] **5002** - Freight & Logistics (Type: EXPENSE)
- [ ] **5003** - Salaries (Type: EXPENSE)

---

## PHASE 2: Financial Periods (Day 1)

**Navigation:** Finance → Financial Periods

- [ ] Create Financial Year 2025-26 (Apr 2025 - Mar 2026)
- [ ] Open current month for transactions
- [ ] Verify: Current month shows status "OPEN"

---

## PHASE 3: Warehouses (Day 1-2)

**Navigation:** Inventory → Warehouses

- [ ] Create **Main Warehouse** (Code: WH-MAIN)
- [ ] Create **Delhi Hub** (Code: WH-DEL) - if applicable
- [ ] Create **Defective Stock** warehouse (Code: WH-DEF)

---

## PHASE 4: Product Catalog (Day 2)

**Navigation:** Catalog → Categories, then Catalog → Products

### Categories
- [ ] Create Category: Water Purifiers
- [ ] Create Category: Spare Parts
- [ ] Create Category: Consumables

### Products (at least 2-3 for testing)
- [ ] Create 1 Water Purifier product
- [ ] Create 1 Spare Part product
- [ ] Verify: Products appear in dropdowns

---

## PHASE 5: Vendors (Day 2)

**Navigation:** Procurement → Vendors

- [ ] Create at least 1 vendor with:
  - [ ] Name
  - [ ] GSTIN
  - [ ] Bank Details
  - [ ] Address
- [ ] Verify: Vendor appears in PO dropdown

---

## PHASE 6: Customers (Day 2-3)

**Navigation:** CRM → Customers

- [ ] Create at least 2-3 customers with:
  - [ ] Name
  - [ ] Phone/Email
  - [ ] Address
  - [ ] State (for GST)
- [ ] Verify: Customers appear in **Receipts** dropdown
- [ ] Verify: Customers appear in **Invoice** dropdown

---

## PHASE 7: Verification Tests (Day 3)

### Test 1: Receipts Page
**Navigation:** Billing → Receipts

- [ ] Click "+ Record Payment"
- [ ] Verify: Customer dropdown shows customers
- [ ] Cancel (don't save test data)

### Test 2: Auto Journal
**Navigation:** Finance → Auto Journal

- [ ] Click "From Payment Receipt"
- [ ] Verify: Bank Account dropdown shows bank accounts (1102, 1103, etc.)
- [ ] Cancel (don't save test data)

### Test 3: Invoice Creation
**Navigation:** Billing → Invoices

- [ ] Click "+ New Invoice"
- [ ] Verify: Customer dropdown works
- [ ] Verify: Product dropdown works
- [ ] Cancel (don't save test data)

### Test 4: Purchase Order
**Navigation:** Procurement → Purchase Orders

- [ ] Click "+ New PO"
- [ ] Verify: Vendor dropdown works
- [ ] Verify: Product dropdown works
- [ ] Cancel (don't save test data)

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Customer dropdown empty | Go to CRM → Customers and create customers |
| Bank account dropdown empty | Go to Finance → Chart of Accounts and create bank accounts (Type: ASSET) |
| Product dropdown empty | Go to Catalog and create products |
| Vendor dropdown empty | Go to Procurement → Vendors and create vendors |
| Cannot post journal | Check if financial period is OPEN |

---

## Sign-Off

| Phase | Completed By | Date | Verified By |
|-------|--------------|------|-------------|
| Phase 1: Chart of Accounts | | | |
| Phase 2: Financial Periods | | | |
| Phase 3: Warehouses | | | |
| Phase 4: Products | | | |
| Phase 5: Vendors | | | |
| Phase 6: Customers | | | |
| Phase 7: Verification | | | |

**Setup Completed:** ____________________

**Finance Head Signature:** ____________________

**Date:** ____________________

---

*After completing this checklist, the ERP is ready for daily transactions.*

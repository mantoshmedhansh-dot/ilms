# Aquapurite ERP - HR & Payroll User Guide

## For HR Manager, Payroll Team & Department Heads

**Version:** 1.0
**Last Updated:** January 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [Employee Management](#2-employee-management)
3. [Attendance Management](#3-attendance-management)
4. [Leave Management](#4-leave-management)
5. [Payroll Processing](#5-payroll-processing)
6. [Performance Management](#6-performance-management)
7. [HR Reports](#7-hr-reports)
8. [Compliance (PF, ESIC, TDS)](#8-compliance-pf-esic-tds)
9. [Common Workflows](#9-common-workflows)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Overview

### Modules Covered

| Module | Purpose |
|--------|---------|
| **Employees** | Employee master data, documents |
| **Departments** | Organization structure |
| **Attendance** | Daily attendance tracking |
| **Leave** | Leave requests and balances |
| **Payroll** | Salary processing |
| **Performance** | Appraisals, goals, KPIs |

### Setup Sequence

```
1. Create Departments
      ↓
2. Define Roles (Access Control)
      ↓
3. Add Employees
      ↓
4. Setup Salary Structures
      ↓
5. Configure Leave Policies
      ↓
6. Initialize Leave Balances
      ↓
Ready for HR Operations
```

---

## 2. Employee Management

### 2.1 Departments

**Navigation:** HR → Departments

#### Creating a Department

1. Go to **HR → Departments**
2. Click **+ New Department**
3. Enter:

| Field | Required | Description |
|-------|----------|-------------|
| Code | Yes | Unique code (e.g., HR, FIN, OPS) |
| Name | Yes | Full department name |
| Description | No | Purpose of department |
| Parent Department | No | For hierarchy |
| Department Head | No | Manager of department |
| Is Active | Yes | Enable/disable |

4. Click **Save**

#### Standard Department Structure

```
CEO
├── Operations (OPS)
│   ├── Warehouse (WH)
│   ├── Logistics (LOG)
│   └── Quality (QC)
├── Sales & Marketing (SM)
│   ├── Sales (SALES)
│   └── Marketing (MKT)
├── Finance (FIN)
│   ├── Accounts (ACC)
│   └── Taxation (TAX)
├── Human Resources (HR)
├── Technology (IT)
└── Service (SVC)
    ├── Installation (INST)
    └── Support (SUP)
```

---

### 2.2 Adding Employees

**Navigation:** HR → Employees

#### Employee Onboarding

1. Go to **HR → Employees**
2. Click **+ New Employee**
3. Fill in sections:

**Personal Information:**
| Field | Required | Description |
|-------|----------|-------------|
| First Name | Yes | Employee first name |
| Last Name | No | Employee last name |
| Email (Official) | Yes | Company email |
| Phone | Yes | Contact number |
| Date of Birth | Yes | For records |
| Gender | Yes | Male/Female/Other |
| Blood Group | No | Emergency info |
| Marital Status | No | Single/Married |
| Nationality | No | Default: Indian |

**Personal Contact:**
| Field | Description |
|-------|-------------|
| Personal Email | Non-work email |
| Personal Phone | Alternate number |
| Current Address | Present residence |
| Permanent Address | Native address |

**Emergency Contact:**
| Field | Description |
|-------|-------------|
| Contact Name | Emergency person |
| Relationship | Spouse, Parent, etc. |
| Contact Phone | Emergency number |

**Employment Details:**
| Field | Required | Description |
|-------|----------|-------------|
| Department | Yes | Assigned department |
| Designation | Yes | Job title |
| Employment Type | Yes | Permanent/Contract/Intern |
| Joining Date | Yes | Date of joining |
| Confirmation Date | No | After probation |
| Reporting Manager | Yes | Direct supervisor |

**Statutory Information:**
| Field | Required | Description |
|-------|----------|-------------|
| PAN Number | Yes | For TDS |
| Aadhaar Number | Yes | Identity proof |
| UAN Number | No | PF account (if existing) |
| ESIC Number | No | If applicable |

**Bank Details:**
| Field | Required | Description |
|-------|----------|-------------|
| Bank Name | Yes | Salary bank |
| Account Number | Yes | Salary account |
| IFSC Code | Yes | Bank IFSC |
| Account Type | No | Savings/Current |

4. Upload documents (if available)
5. Assign roles (system access)
6. Click **Save**

#### Employee Code Generation

System auto-generates employee codes:
```
Format: AQ-YYYY-NNNN
Example: AQ-2026-0001

AQ = Company prefix
2026 = Year of joining
0001 = Sequential number
```

---

### 2.3 Employee Status

| Status | Description |
|--------|-------------|
| **Active** | Currently employed |
| **Probation** | In probation period |
| **Notice Period** | Resigned, serving notice |
| **On Leave** | Extended leave |
| **Suspended** | Under investigation |
| **Terminated** | Employment ended |
| **Resigned** | Left company |
| **Retired** | Retired from service |

#### Changing Status

1. Open employee record
2. Click **Change Status**
3. Select new status
4. Enter effective date
5. Add reason/notes
6. Click **Update**

---

### 2.4 Salary Structure

**Navigation:** HR → Employees → [Employee] → Salary

#### Salary Components

**Earnings:**
| Component | Description | Typical % of CTC |
|-----------|-------------|------------------|
| Basic Salary | Base pay (PF calculated on this) | 40-50% |
| HRA | House Rent Allowance | 40-50% of Basic |
| Conveyance | Transport allowance | Fixed (₹1,600/month) |
| Medical | Medical allowance | Fixed or % |
| Special Allowance | Balancing figure | Variable |
| Other Allowances | Any additional | As applicable |

**Deductions:**
| Component | Description | Rate |
|-----------|-------------|------|
| Employee PF | Provident Fund | 12% of Basic |
| Employee ESIC | If gross < ₹21,000 | 0.75% of Gross |
| Professional Tax | State tax | ₹200/month (varies by state) |
| TDS | Income tax | As per slab |
| Loan EMI | If any loan | As applicable |
| Advances | Salary advance recovery | As applicable |

**Employer Contributions (not deducted from salary):**
| Component | Description | Rate |
|-----------|-------------|------|
| Employer PF | Company PF contribution | 12% of Basic |
| Employer ESIC | Company ESIC | 3.25% of Gross |

#### Setting Up Salary

1. Go to **HR → Employees**
2. Click on employee
3. Go to **Salary** tab
4. Click **Setup Salary Structure**
5. Enter:

| Field | Description |
|-------|-------------|
| Effective From | When this structure starts |
| Basic Salary | Monthly basic |
| HRA | Monthly HRA |
| Conveyance | Monthly conveyance |
| Medical | Monthly medical |
| Special Allowance | Monthly special |
| Other Allowances | Any other |
| PF Applicable | Yes/No |
| ESIC Applicable | Yes/No (auto if gross < ₹21,000) |
| PT Applicable | Yes/No |

6. System calculates:
   - Gross Salary
   - Total Deductions
   - Net Salary
   - Monthly CTC
   - Annual CTC

7. Click **Save**

#### CTC Calculation

```
Monthly CTC = Gross Salary + Employer PF + Employer ESIC

Annual CTC = Monthly CTC × 12

Example:
Basic: ₹25,000
HRA: ₹10,000
Conveyance: ₹1,600
Special: ₹13,400
─────────────────
Gross: ₹50,000

Employer PF: ₹3,000 (12% of Basic)
Employer ESIC: ₹0 (Gross > ₹21,000)
─────────────────
Monthly CTC: ₹53,000
Annual CTC: ₹6,36,000
```

---

## 3. Attendance Management

### 3.1 Daily Attendance

**Navigation:** HR → Attendance

#### Attendance Methods

| Method | Description |
|--------|-------------|
| **Biometric** | Fingerprint/Face ID (integrated) |
| **Mobile App** | GPS-based check-in |
| **Manual** | HR marks attendance |
| **Web Portal** | Employee self check-in |

#### Marking Attendance (Manual)

1. Go to **HR → Attendance**
2. Click **+ Mark Attendance** or **Bulk Entry**
3. Select Date
4. For each employee:
   - Select Status
   - Enter Check-in Time
   - Enter Check-out Time
5. Click **Save**

#### Attendance Status

| Status | Code | Description |
|--------|------|-------------|
| **Present** | P | Normal working day |
| **Absent** | A | Unexcused absence |
| **Half Day** | HD | Worked partial day |
| **Leave** | L | On approved leave |
| **Holiday** | H | Company holiday |
| **Week Off** | WO | Weekly off (Sunday) |
| **On Duty** | OD | Official travel/duty |
| **Work From Home** | WFH | Remote work |
| **Comp Off** | CO | Compensatory off |

#### Late Coming / Early Going

System tracks:
- **Late**: Check-in after grace period (e.g., after 9:30 AM)
- **Early Out**: Check-out before shift end
- **Short Hours**: Total work < 8 hours

Configuration:
| Setting | Value |
|---------|-------|
| Shift Start | 9:00 AM |
| Grace Period | 30 minutes |
| Late After | 9:30 AM |
| Half Day Threshold | 4 hours |
| Full Day Threshold | 8 hours |

---

### 3.2 Attendance Reports

| Report | Purpose |
|--------|---------|
| Daily Attendance | Today's attendance |
| Monthly Summary | Month view by employee |
| Late Coming Report | Employees coming late |
| Absent Report | Absences list |
| Attendance Register | Official register format |

---

## 4. Leave Management

### 4.1 Leave Types

| Leave Type | Code | Annual Quota | Carry Forward |
|------------|------|--------------|---------------|
| Casual Leave | CL | 12 | No |
| Sick Leave | SL | 6 | No |
| Earned Leave | EL | 15 | Yes (max 30) |
| Maternity Leave | ML | 26 weeks | N/A |
| Paternity Leave | PL | 5 | N/A |
| Bereavement | BL | 3 | No |
| Comp Off | CO | As earned | Expire in 60 days |
| Loss of Pay | LOP | Unlimited | N/A |

### 4.2 Leave Balances

**Navigation:** HR → Leave Management

#### Viewing Balances

1. Go to **HR → Leave Management**
2. Select Employee
3. View leave balances:
   - Opening Balance
   - Accrued
   - Taken
   - Pending Approval
   - Available

#### Initializing Balances

For new financial year:
1. Go to **HR → Leave Management → Initialize Balances**
2. Select Financial Year
3. System:
   - Carries forward eligible leaves
   - Resets non-carry-forward leaves
   - Applies new year quotas
4. Click **Process**

---

### 4.3 Leave Requests

**Navigation:** HR → Leave Management → Requests

#### Applying for Leave

**Employee Self-Service:**
1. Employee logs in
2. Goes to **My Leaves**
3. Clicks **Apply Leave**
4. Enters:
   - Leave Type
   - From Date
   - To Date
   - Half Day (if applicable)
   - Reason
5. Submits

**HR on Behalf:**
1. Go to **HR → Leave Management**
2. Click **+ New Request**
3. Select Employee
4. Fill leave details
5. Submit or Direct Approve

#### Leave Approval Flow

```
Employee Applies
      ↓
Reporting Manager Reviews
      ↓
APPROVED / REJECTED
      ↓
Leave Balance Updated
      ↓
Attendance Marked as Leave
```

#### Leave Status

| Status | Meaning |
|--------|---------|
| **Pending** | Awaiting approval |
| **Approved** | Manager approved |
| **Rejected** | Manager rejected |
| **Cancelled** | Employee cancelled |
| **Revoked** | Approved but later cancelled |

---

### 4.4 Leave Rules

| Rule | Description |
|------|-------------|
| Minimum Notice | CL: 1 day, EL: 7 days |
| Max Consecutive | CL: 3, EL: 10 |
| Sandwich Rule | Weekend between leaves counts |
| Encashment | EL can be encashed on exit |
| Negative Balance | Not allowed (except LOP) |

---

## 5. Payroll Processing

### 5.1 Payroll Cycle

**Navigation:** HR → Payroll

#### Monthly Payroll Process

```
1st - 25th: Attendance finalization
      ↓
26th - 28th: Payroll processing
      ↓
28th: Salary disbursement
      ↓
7th: PF/ESIC deposit
      ↓
End of month: Reports & compliance
```

### 5.2 Running Payroll

1. Go to **HR → Payroll**
2. Click **+ Process Payroll**
3. Select:
   - Payroll Month (e.g., January 2026)
   - Department (All or specific)
4. Click **Calculate**

#### System Calculates:

**For Each Employee:**
```
Earnings:
  Basic Salary (prorated for days worked)
  + HRA
  + Conveyance
  + Medical
  + Special Allowance
  + Overtime (if any)
  + Arrears (if any)
  + Bonus (if any)
  ─────────────────────
  = Gross Earnings

Deductions:
  - Employee PF (12% of Basic)
  - Employee ESIC (0.75% if applicable)
  - Professional Tax
  - TDS (as per declaration)
  - Loan EMI
  - Advance Recovery
  - Other Deductions
  ─────────────────────
  = Total Deductions

Net Salary = Gross Earnings - Total Deductions
```

5. Review calculated salaries
6. Make adjustments if needed:
   - Add bonus
   - Add deductions
   - Correct attendance
7. Click **Submit for Approval**

---

### 5.3 Payroll Approval

1. Finance Head receives payroll for approval
2. Reviews:
   - Total headcount
   - Total gross
   - Total deductions
   - Total net payout
3. Checks:
   - Any unusual amounts
   - New joiners included
   - Exits processed
4. Approves or Returns for correction

---

### 5.4 Salary Disbursement

After approval:

1. Go to approved payroll
2. Click **Generate Bank File**
3. Download file (NEFT/RTGS format)
4. Upload to bank portal
5. Process payment
6. Update payment status in system
7. Click **Mark as Paid**

---

### 5.5 Payslips

**Navigation:** HR → Payroll → [Month] → Payslips

#### Generating Payslips

1. Open processed payroll
2. Click **Generate Payslips**
3. System creates PDF payslips
4. Options:
   - Email to employees
   - Download all as ZIP
   - Print individual

#### Payslip Contents

| Section | Details |
|---------|---------|
| Header | Company name, month, employee details |
| Earnings | All earning components |
| Deductions | All deduction components |
| Summary | Gross, Deductions, Net |
| YTD | Year-to-date figures |
| Leave Balance | Current leave balance |

---

## 6. Performance Management

### 6.1 Appraisal Cycles

**Navigation:** HR → Performance

#### Setting Up Appraisal Cycle

1. Go to **HR → Performance → Cycles**
2. Click **+ New Cycle**
3. Enter:
   - Cycle Name (e.g., "FY 2025-26 Annual Review")
   - Financial Year
   - Start Date
   - End Date
   - Review Start Date
   - Review End Date
4. Click **Save**

#### Cycle Phases

```
GOAL SETTING (Apr-May)
      ↓
MID-YEAR REVIEW (Oct)
      ↓
SELF REVIEW (Mar)
      ↓
MANAGER REVIEW (Mar-Apr)
      ↓
HR CALIBRATION (Apr)
      ↓
COMPLETED
```

---

### 6.2 Goals & KPIs

**Navigation:** HR → Performance → Goals

#### Creating Goals

1. Go to **HR → Performance → Goals**
2. Click **+ New Goal**
3. Enter:

| Field | Description |
|-------|-------------|
| Employee | Whose goal |
| Cycle | Which appraisal cycle |
| Title | Goal title |
| Description | Detailed description |
| Category | Strategic/Operational/Development |
| KPI | Linked KPI (if any) |
| Target Value | Measurable target |
| Weightage | % contribution to overall |
| Start Date | When to start |
| Due Date | Deadline |

4. Click **Save**

#### Goal Categories

| Category | Example |
|----------|---------|
| **Strategic** | Launch new product line |
| **Operational** | Reduce delivery TAT by 20% |
| **Development** | Complete certification course |
| **Team** | Improve team productivity |

#### Goal Status

| Status | Meaning |
|--------|---------|
| **Pending** | Not started |
| **In Progress** | Working on it |
| **Completed** | Achieved |
| **Cancelled** | No longer relevant |

---

### 6.3 Appraisals

**Navigation:** HR → Performance → Appraisals

#### Appraisal Flow

```
1. Employee Self-Review
   - Rate own performance (1-5)
   - Add comments
   - Submit to manager
      ↓
2. Manager Review
   - Review employee rating
   - Give manager rating
   - Add feedback
   - Submit to HR
      ↓
3. HR Review
   - Calibration across teams
   - Final rating
   - Recommend increment/promotion
      ↓
4. Completed
   - Share with employee
   - Lock record
```

#### Rating Scale

| Rating | Description | Typical Increment |
|--------|-------------|-------------------|
| 5 | Exceptional | 15-20% |
| 4 | Exceeds Expectations | 10-15% |
| 3 | Meets Expectations | 5-10% |
| 2 | Needs Improvement | 0-5% |
| 1 | Unsatisfactory | 0% / PIP |

#### Performance Bands

| Band | Rating Range | Description |
|------|--------------|-------------|
| **A+** | 4.5 - 5.0 | Top performer |
| **A** | 4.0 - 4.4 | High performer |
| **B+** | 3.5 - 3.9 | Good performer |
| **B** | 3.0 - 3.4 | Solid performer |
| **C** | 2.0 - 2.9 | Needs improvement |
| **D** | 1.0 - 1.9 | Underperformer |

---

### 6.4 Feedback

**Navigation:** HR → Performance → Feedback

Give continuous feedback (not just during appraisal):

1. Click **+ Give Feedback**
2. Select Employee
3. Choose Type:
   - Appreciation
   - Improvement
   - Suggestion
4. Enter feedback
5. Make private (manager only) or public
6. Submit

---

## 7. HR Reports

### 7.1 Available Reports

| Report | Navigation | Purpose |
|--------|------------|---------|
| Employee Directory | HR → Reports | Full employee list |
| Headcount Report | HR → Reports | Count by department |
| Attendance Register | HR → Reports | Official attendance |
| Leave Balance Report | HR → Reports | All leave balances |
| Salary Register | HR → Reports | Detailed salary |
| PF Report | HR → Reports | PF contributions |
| ESIC Report | HR → Reports | ESIC contributions |
| Payroll Summary | HR → Reports | Month-wise summary |

### 7.2 Generating Reports

1. Go to **HR → Reports**
2. Select Report Type
3. Set filters:
   - Date Range / Month
   - Department
   - Employee Type
4. Click **Generate**
5. View online or Download (Excel/PDF)

---

## 8. Compliance (PF, ESIC, TDS)

### 8.1 Provident Fund (PF)

#### Monthly PF Process

1. Process payroll
2. Go to **HR → Reports → PF Report**
3. Download PF ECR (Electronic Challan Return)
4. Upload to EPFO portal
5. Generate challan
6. Pay before 15th of next month
7. Mark as deposited in system

#### PF Calculation

```
Basic Salary: ₹25,000

Employee PF: 12% of Basic = ₹3,000
Employer PF: 12% of Basic = ₹3,000
  - EPS (Pension): 8.33% = ₹2,082.50
  - EPF: 3.67% = ₹917.50

Total PF Deposit: ₹6,000
```

---

### 8.2 ESIC (Employee State Insurance)

Applicable if Gross Salary ≤ ₹21,000/month

#### ESIC Calculation

```
Gross Salary: ₹18,000

Employee ESIC: 0.75% = ₹135
Employer ESIC: 3.25% = ₹585

Total ESIC: ₹720
```

#### Monthly ESIC Process

1. Generate ESIC report
2. Download in prescribed format
3. Upload to ESIC portal
4. Pay by 15th of next month

---

### 8.3 Professional Tax (PT)

Varies by state. Example (Karnataka):

| Monthly Salary | PT Amount |
|----------------|-----------|
| Up to ₹15,000 | Nil |
| ₹15,001 - ₹25,000 | ₹150 |
| Above ₹25,000 | ₹200 |

---

### 8.4 TDS on Salary

#### TDS Slabs (New Regime FY 2025-26)

| Income Slab | Rate |
|-------------|------|
| Up to ₹3,00,000 | Nil |
| ₹3,00,001 - ₹7,00,000 | 5% |
| ₹7,00,001 - ₹10,00,000 | 10% |
| ₹10,00,001 - ₹12,00,000 | 15% |
| ₹12,00,001 - ₹15,00,000 | 20% |
| Above ₹15,00,000 | 30% |

#### Investment Declarations

Employees submit Form 12BB with:
- HRA receipts
- LIC premiums (80C)
- PPF/ELSS (80C)
- Medical insurance (80D)
- Home loan interest (24B)

System calculates TDS based on declarations.

---

## 9. Common Workflows

### 9.1 New Employee Joining

```
1. Offer accepted
      ↓
2. HR creates employee record
      ↓
3. Bank account details collected
      ↓
4. Documents verified
      ↓
5. UAN generated/transferred
      ↓
6. Salary structure setup
      ↓
7. Leave balances initialized (prorated)
      ↓
8. IT declaration collected
      ↓
9. System access provided
      ↓
10. Reporting manager notified
```

### 9.2 Employee Exit

```
1. Resignation received
      ↓
2. Status changed to "Notice Period"
      ↓
3. Exit interview scheduled
      ↓
4. Final working day confirmed
      ↓
5. Full & Final calculation:
   - Pending salary
   - Leave encashment
   - Deductions (advance, notice shortfall)
   - Gratuity (if applicable)
      ↓
6. Generate relieving letter
      ↓
7. Generate experience letter
      ↓
8. Final settlement paid
      ↓
9. Status changed to "Resigned"
      ↓
10. System access revoked
```

### 9.3 Monthly Payroll Checklist

```
□ Attendance finalized (all days marked)
□ Leave requests approved/rejected
□ New joiners added with salary
□ Exits processed
□ Arrears calculated (if any)
□ Loans/advances updated
□ Payroll processed
□ Payroll approved
□ Bank file generated
□ Salaries disbursed
□ Payslips generated and sent
□ PF challan generated
□ ESIC challan generated
□ Challans paid (by 15th)
```

---

## 10. Troubleshooting

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Salary not calculating | No salary structure | Setup salary structure |
| PF showing zero | PF not applicable | Enable PF in salary structure |
| Leave balance wrong | Not initialized | Initialize balances |
| Attendance missing | Not marked | Mark attendance |
| Payroll stuck | Not approved | Get manager approval |

### Error Messages

| Error | Meaning | Action |
|-------|---------|--------|
| "Salary structure not found" | Not setup | Create salary structure |
| "Attendance incomplete" | Missing days | Mark all days |
| "Leave balance insufficient" | Not enough leaves | Apply LOP or adjust |
| "Duplicate UAN" | Already exists | Verify and correct |
| "Period locked" | Payroll already done | Cannot modify |

---

## Quick Reference Card

### Daily Tasks - HR Executive

| Time | Task | Navigation |
|------|------|------------|
| 9:00 AM | Mark attendance | HR → Attendance |
| 10:00 AM | Review leave requests | HR → Leave → Pending |
| 11:00 AM | Update employee records | HR → Employees |
| 2:00 PM | Generate letters/docs | HR → Documents |
| 4:00 PM | Exit formalities | HR → Employees → Exits |

### Monthly Tasks - Payroll

| Date | Task |
|------|------|
| 1st - 25th | Finalize attendance |
| 25th | Lock attendance |
| 26th | Process payroll |
| 27th | Review and approve |
| 28th | Disburse salaries |
| 7th | Deposit PF/ESIC |
| 15th | File PF/ESIC returns |

### Compliance Calendar

| Month | Due Date | Compliance |
|-------|----------|------------|
| Every | 15th | PF deposit |
| Every | 15th | ESIC deposit |
| April | 30th | PF Annual Return |
| July | 31st | TDS Q1 Return |
| October | 31st | TDS Q2 Return |
| January | 31st | TDS Q3 Return |
| March | 31st | Full & Final settlements |
| May | 31st | TDS Q4 Return |

---

*Document prepared for Aquapurite ERP v1.0*

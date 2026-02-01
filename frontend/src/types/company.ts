// Company Types - matching backend models

export type CompanyType =
  | 'PRIVATE_LIMITED'
  | 'PUBLIC_LIMITED'
  | 'LLP'
  | 'PARTNERSHIP'
  | 'PROPRIETORSHIP'
  | 'OPC'
  | 'TRUST'
  | 'SOCIETY'
  | 'HUF'
  | 'GOVERNMENT';

export type GSTRegistrationType =
  | 'REGULAR'
  | 'COMPOSITION'
  | 'CASUAL'
  | 'SEZ_UNIT'
  | 'SEZ_DEVELOPER'
  | 'ISD'
  | 'TDS_DEDUCTOR'
  | 'TCS_COLLECTOR'
  | 'NON_RESIDENT'
  | 'UNREGISTERED';

export type BankAccountType = 'CURRENT' | 'SAVINGS' | 'OD' | 'CC';

export type BankAccountPurpose = 'GENERAL' | 'COLLECTIONS' | 'PAYMENTS' | 'SALARY' | 'TAX';

export type MSMECategory = 'MICRO' | 'SMALL' | 'MEDIUM';

export interface CompanyBankAccount {
  id: string;
  company_id: string;
  bank_name: string;
  branch_name: string;
  account_number: string;
  ifsc_code: string;
  account_type: BankAccountType;
  account_name: string;
  upi_id?: string;
  swift_code?: string;
  purpose: BankAccountPurpose;
  is_primary: boolean;
  is_active: boolean;
  show_on_invoice: boolean;
  created_at: string;
}

export interface CompanyBranch {
  id: string;
  company_id: string;
  code: string;
  name: string;
  branch_type: string;
  gstin?: string;
  state_code: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  state: string;
  pincode: string;
  email?: string;
  phone?: string;
  contact_person?: string;
  warehouse_id?: string;
  is_active: boolean;
  is_billing_address: boolean;
  is_shipping_address: boolean;
  created_at: string;
  updated_at: string;
}

export interface Company {
  id: string;

  // Basic Information
  legal_name: string;
  trade_name?: string;
  code: string;
  company_type: CompanyType;

  // Tax Registration (India)
  gstin: string;
  gst_registration_type: GSTRegistrationType;
  state_code: string;
  pan: string;
  tan?: string;
  cin?: string;
  llpin?: string;

  // MSME
  msme_registered: boolean;
  udyam_number?: string;
  msme_category?: MSMECategory;

  // Registered Address
  address_line1: string;
  address_line2?: string;
  city: string;
  district?: string;
  state: string;
  pincode: string;
  country: string;

  // Contact Information
  email: string;
  phone: string;
  mobile?: string;
  fax?: string;
  website?: string;

  // Primary Bank Details
  bank_name?: string;
  bank_branch?: string;
  bank_account_number?: string;
  bank_ifsc?: string;
  bank_account_type?: BankAccountType;
  bank_account_name?: string;

  // Branding
  logo_url?: string;
  logo_small_url?: string;
  favicon_url?: string;
  signature_url?: string;

  // E-Invoice Configuration
  einvoice_enabled: boolean;
  einvoice_username?: string;
  einvoice_api_mode: 'SANDBOX' | 'PRODUCTION';

  // E-Way Bill Configuration
  ewb_enabled: boolean;
  ewb_username?: string;
  ewb_api_mode: 'SANDBOX' | 'PRODUCTION';

  // Invoice Settings
  invoice_prefix: string;
  invoice_suffix?: string;
  financial_year_start_month: number;
  invoice_terms?: string;
  invoice_notes?: string;
  invoice_footer?: string;

  // PO Settings
  po_prefix: string;
  po_terms?: string;

  // Currency/Tax Configuration
  currency_code: string;
  currency_symbol: string;
  default_cgst_rate: number;
  default_sgst_rate: number;
  default_igst_rate: number;
  tds_deductor: boolean;
  default_tds_rate: number;

  // Status
  is_active: boolean;
  is_primary: boolean;
  created_at: string;
  updated_at: string;

  // Relations
  branches?: CompanyBranch[];
  bank_accounts?: CompanyBankAccount[];
}

// Form types for creating/updating
export type CompanyBankAccountCreate = Omit<CompanyBankAccount, 'id' | 'company_id' | 'created_at'>;
export type CompanyBankAccountUpdate = Partial<CompanyBankAccountCreate>;

// Display helpers
export const companyTypeLabels: Record<CompanyType, string> = {
  PRIVATE_LIMITED: 'Private Limited',
  PUBLIC_LIMITED: 'Public Limited',
  LLP: 'LLP',
  PARTNERSHIP: 'Partnership',
  PROPRIETORSHIP: 'Proprietorship',
  OPC: 'One Person Company',
  TRUST: 'Trust',
  SOCIETY: 'Society',
  HUF: 'Hindu Undivided Family',
  GOVERNMENT: 'Government',
};

export const gstRegistrationTypeLabels: Record<GSTRegistrationType, string> = {
  REGULAR: 'Regular',
  COMPOSITION: 'Composition',
  CASUAL: 'Casual Taxable Person',
  SEZ_UNIT: 'SEZ Unit',
  SEZ_DEVELOPER: 'SEZ Developer',
  ISD: 'Input Service Distributor',
  TDS_DEDUCTOR: 'TDS Deductor',
  TCS_COLLECTOR: 'TCS Collector',
  NON_RESIDENT: 'Non-Resident',
  UNREGISTERED: 'Unregistered',
};

export const bankAccountTypeLabels: Record<BankAccountType, string> = {
  CURRENT: 'Current Account',
  SAVINGS: 'Savings Account',
  OD: 'Overdraft',
  CC: 'Cash Credit',
};

export const bankAccountPurposeLabels: Record<BankAccountPurpose, string> = {
  GENERAL: 'General',
  COLLECTIONS: 'Collections',
  PAYMENTS: 'Payments',
  SALARY: 'Salary',
  TAX: 'Tax Payments',
};

export const msmeCategories: Record<MSMECategory, string> = {
  MICRO: 'Micro',
  SMALL: 'Small',
  MEDIUM: 'Medium',
};

// Indian states for dropdown
export const indianStates = [
  { code: '01', name: 'Jammu & Kashmir' },
  { code: '02', name: 'Himachal Pradesh' },
  { code: '03', name: 'Punjab' },
  { code: '04', name: 'Chandigarh' },
  { code: '05', name: 'Uttarakhand' },
  { code: '06', name: 'Haryana' },
  { code: '07', name: 'Delhi' },
  { code: '08', name: 'Rajasthan' },
  { code: '09', name: 'Uttar Pradesh' },
  { code: '10', name: 'Bihar' },
  { code: '11', name: 'Sikkim' },
  { code: '12', name: 'Arunachal Pradesh' },
  { code: '13', name: 'Nagaland' },
  { code: '14', name: 'Manipur' },
  { code: '15', name: 'Mizoram' },
  { code: '16', name: 'Tripura' },
  { code: '17', name: 'Meghalaya' },
  { code: '18', name: 'Assam' },
  { code: '19', name: 'West Bengal' },
  { code: '20', name: 'Jharkhand' },
  { code: '21', name: 'Odisha' },
  { code: '22', name: 'Chhattisgarh' },
  { code: '23', name: 'Madhya Pradesh' },
  { code: '24', name: 'Gujarat' },
  { code: '26', name: 'Dadra & Nagar Haveli and Daman & Diu' },
  { code: '27', name: 'Maharashtra' },
  { code: '29', name: 'Karnataka' },
  { code: '30', name: 'Goa' },
  { code: '31', name: 'Lakshadweep' },
  { code: '32', name: 'Kerala' },
  { code: '33', name: 'Tamil Nadu' },
  { code: '34', name: 'Puducherry' },
  { code: '35', name: 'Andaman & Nicobar Islands' },
  { code: '36', name: 'Telangana' },
  { code: '37', name: 'Andhra Pradesh' },
  { code: '38', name: 'Ladakh' },
];

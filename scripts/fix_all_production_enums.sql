-- =====================================================
-- COMPREHENSIVE ENUM TO VARCHAR CONVERSION
-- Production Database - Run in Supabase SQL Editor
-- Generated: 2026-01-17
-- =====================================================
-- This script converts ALL 147 remaining ENUM types to VARCHAR
-- Run this ONCE to fix all ENUM-related issues permanently
-- =====================================================

BEGIN;

-- =====================================================
-- 1. CHART OF ACCOUNTS
-- =====================================================
ALTER TABLE chart_of_accounts ALTER COLUMN account_sub_type TYPE VARCHAR(50) USING account_sub_type::text;
ALTER TABLE chart_of_accounts ALTER COLUMN account_type TYPE VARCHAR(50) USING account_type::text;

-- =====================================================
-- 2. LEADS & CRM
-- =====================================================
ALTER TABLE lead_activities ALTER COLUMN activity_type TYPE VARCHAR(50) USING activity_type::text;
ALTER TABLE lead_activities ALTER COLUMN new_status TYPE VARCHAR(50) USING new_status::text;
ALTER TABLE lead_activities ALTER COLUMN old_status TYPE VARCHAR(50) USING old_status::text;
ALTER TABLE leads ALTER COLUMN interest TYPE VARCHAR(50) USING interest::text;
ALTER TABLE leads ALTER COLUMN priority TYPE VARCHAR(50) USING priority::text;
ALTER TABLE leads ALTER COLUMN source TYPE VARCHAR(50) USING source::text;
ALTER TABLE leads ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE leads ALTER COLUMN lead_type TYPE VARCHAR(50) USING lead_type::text;
ALTER TABLE leads ALTER COLUMN lost_reason TYPE VARCHAR(100) USING lost_reason::text;
ALTER TABLE lead_assignment_rules ALTER COLUMN source TYPE VARCHAR(50) USING source::text;
ALTER TABLE lead_assignment_rules ALTER COLUMN lead_type TYPE VARCHAR(50) USING lead_type::text;

-- =====================================================
-- 3. CUSTOMERS
-- =====================================================
ALTER TABLE customer_addresses ALTER COLUMN address_type TYPE VARCHAR(50) USING address_type::text;
ALTER TABLE customers ALTER COLUMN source TYPE VARCHAR(50) USING source::text;
ALTER TABLE customers ALTER COLUMN customer_type TYPE VARCHAR(50) USING customer_type::text;

-- =====================================================
-- 4. STOCK & INVENTORY
-- =====================================================
ALTER TABLE stock_adjustments ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE stock_adjustments ALTER COLUMN adjustment_type TYPE VARCHAR(50) USING adjustment_type::text;
ALTER TABLE stock_items ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE stock_movements ALTER COLUMN movement_type TYPE VARCHAR(50) USING movement_type::text;
ALTER TABLE stock_transfers ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE stock_transfers ALTER COLUMN transfer_type TYPE VARCHAR(50) USING transfer_type::text;

-- =====================================================
-- 5. ALLOCATION
-- =====================================================
ALTER TABLE allocation_rules ALTER COLUMN allocation_type TYPE VARCHAR(50) USING allocation_type::text;
ALTER TABLE allocation_rules ALTER COLUMN channel_code TYPE VARCHAR(50) USING channel_code::text;

-- =====================================================
-- 6. AMC & SERVICE
-- =====================================================
ALTER TABLE amc_contracts ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE amc_contracts ALTER COLUMN amc_type TYPE VARCHAR(50) USING amc_type::text;
ALTER TABLE amc_plans ALTER COLUMN amc_type TYPE VARCHAR(50) USING amc_type::text;
ALTER TABLE service_requests ALTER COLUMN priority TYPE VARCHAR(50) USING priority::text;
ALTER TABLE service_requests ALTER COLUMN source TYPE VARCHAR(50) USING source::text;
ALTER TABLE service_requests ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE service_requests ALTER COLUMN service_type TYPE VARCHAR(50) USING service_type::text;
ALTER TABLE service_status_history ALTER COLUMN from_status TYPE VARCHAR(50) USING from_status::text;
ALTER TABLE service_status_history ALTER COLUMN to_status TYPE VARCHAR(50) USING to_status::text;

-- =====================================================
-- 7. HR & APPRAISALS
-- =====================================================
ALTER TABLE appraisal_cycles ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE appraisals ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE goals ALTER COLUMN status TYPE VARCHAR(50) USING status::text;

-- =====================================================
-- 8. ASSETS
-- =====================================================
ALTER TABLE assets ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE assets ALTER COLUMN depreciation_method TYPE VARCHAR(50) USING depreciation_method::text;
ALTER TABLE asset_transfers ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE asset_categories ALTER COLUMN depreciation_method TYPE VARCHAR(50) USING depreciation_method::text;
ALTER TABLE asset_maintenance ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE depreciation_entries ALTER COLUMN depreciation_method TYPE VARCHAR(50) USING depreciation_method::text;

-- =====================================================
-- 9. CAMPAIGNS & MARKETING
-- =====================================================
ALTER TABLE audience_segments ALTER COLUMN segment_type TYPE VARCHAR(50) USING segment_type::text;
ALTER TABLE campaigns ALTER COLUMN audience_type TYPE VARCHAR(50) USING audience_type::text;
ALTER TABLE campaigns ALTER COLUMN category TYPE VARCHAR(50) USING category::text;
ALTER TABLE campaigns ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE campaigns ALTER COLUMN campaign_type TYPE VARCHAR(50) USING campaign_type::text;
ALTER TABLE campaign_templates ALTER COLUMN category TYPE VARCHAR(50) USING category::text;
ALTER TABLE campaign_templates ALTER COLUMN campaign_type TYPE VARCHAR(50) USING campaign_type::text;
ALTER TABLE campaign_automations ALTER COLUMN campaign_type TYPE VARCHAR(50) USING campaign_type::text;
ALTER TABLE campaign_recipients ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE unsubscribe_list ALTER COLUMN channel TYPE VARCHAR(50) USING channel::text;

-- =====================================================
-- 10. FRANCHISEE
-- =====================================================
ALTER TABLE franchisees ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE franchisees ALTER COLUMN tier TYPE VARCHAR(50) USING tier::text;
ALTER TABLE franchisees ALTER COLUMN franchisee_type TYPE VARCHAR(50) USING franchisee_type::text;
ALTER TABLE franchisee_audits ALTER COLUMN result TYPE VARCHAR(50) USING result::text;
ALTER TABLE franchisee_audits ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE franchisee_audits ALTER COLUMN audit_type TYPE VARCHAR(50) USING audit_type::text;
ALTER TABLE franchisee_contracts ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE franchisee_territories ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE franchisee_trainings ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE franchisee_trainings ALTER COLUMN training_type TYPE VARCHAR(50) USING training_type::text;
ALTER TABLE franchisee_support_tickets ALTER COLUMN category TYPE VARCHAR(50) USING category::text;
ALTER TABLE franchisee_support_tickets ALTER COLUMN priority TYPE VARCHAR(50) USING priority::text;
ALTER TABLE franchisee_support_tickets ALTER COLUMN status TYPE VARCHAR(50) USING status::text;

-- =====================================================
-- 11. BANKING & RECONCILIATION
-- =====================================================
ALTER TABLE bank_reconciliations ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE bank_statement_lines ALTER COLUMN transaction_type TYPE VARCHAR(50) USING transaction_type::text;

-- =====================================================
-- 12. WAREHOUSE
-- =====================================================
ALTER TABLE warehouse_bins ALTER COLUMN bin_type TYPE VARCHAR(50) USING bin_type::text;
ALTER TABLE warehouse_zones ALTER COLUMN zone_type TYPE VARCHAR(50) USING zone_type::text;

-- =====================================================
-- 13. MANIFESTS & SHIPPING
-- =====================================================
ALTER TABLE manifests ALTER COLUMN business_type TYPE VARCHAR(50) USING business_type::text;
ALTER TABLE manifests ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE shipments ALTER COLUMN packaging_type TYPE VARCHAR(50) USING packaging_type::text;
ALTER TABLE shipments ALTER COLUMN payment_mode TYPE VARCHAR(50) USING payment_mode::text;
ALTER TABLE shipments ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE shipment_tracking ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE transporters ALTER COLUMN transporter_type TYPE VARCHAR(50) USING transporter_type::text;

-- =====================================================
-- 14. COMMISSIONS
-- =====================================================
ALTER TABLE commission_plans ALTER COLUMN calculation_basis TYPE VARCHAR(50) USING calculation_basis::text;
ALTER TABLE commission_plans ALTER COLUMN commission_type TYPE VARCHAR(50) USING commission_type::text;
ALTER TABLE commission_transactions ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE commission_earners ALTER COLUMN earner_type TYPE VARCHAR(50) USING earner_type::text;
ALTER TABLE commission_payouts ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE channel_commission_earnings ALTER COLUMN beneficiary_type TYPE VARCHAR(50) USING beneficiary_type::text;
ALTER TABLE channel_commission_plans ALTER COLUMN beneficiary_type TYPE VARCHAR(50) USING beneficiary_type::text;

-- =====================================================
-- 15. CALLS & CALLBACKS
-- =====================================================
ALTER TABLE callback_schedules ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE callback_schedules ALTER COLUMN category TYPE VARCHAR(50) USING category::text;
ALTER TABLE callback_schedules ALTER COLUMN priority TYPE VARCHAR(50) USING priority::text;
ALTER TABLE calls ALTER COLUMN category TYPE VARCHAR(50) USING category::text;
ALTER TABLE calls ALTER COLUMN outcome TYPE VARCHAR(50) USING outcome::text;
ALTER TABLE calls ALTER COLUMN priority TYPE VARCHAR(50) USING priority::text;
ALTER TABLE calls ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE calls ALTER COLUMN call_type TYPE VARCHAR(50) USING call_type::text;
ALTER TABLE calls ALTER COLUMN sentiment TYPE VARCHAR(50) USING sentiment::text;
ALTER TABLE call_dispositions ALTER COLUMN category TYPE VARCHAR(50) USING category::text;
ALTER TABLE call_qa_reviews ALTER COLUMN status TYPE VARCHAR(50) USING status::text;

-- =====================================================
-- 16. SALES CHANNELS
-- =====================================================
ALTER TABLE sales_channels ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE sales_channels ALTER COLUMN channel_type TYPE VARCHAR(50) USING channel_type::text;

-- =====================================================
-- 17. COMPANY
-- =====================================================
ALTER TABLE companies ALTER COLUMN company_type TYPE VARCHAR(50) USING company_type::text;
ALTER TABLE companies ALTER COLUMN gst_registration_type TYPE VARCHAR(50) USING gst_registration_type::text;

-- =====================================================
-- 18. DEALER
-- =====================================================
ALTER TABLE dealer_tier_pricing ALTER COLUMN tier TYPE VARCHAR(50) USING tier::text;
ALTER TABLE dealer_schemes ALTER COLUMN scheme_type TYPE VARCHAR(50) USING scheme_type::text;
ALTER TABLE dealer_credit_ledger ALTER COLUMN transaction_type TYPE VARCHAR(50) USING transaction_type::text;

-- =====================================================
-- 19. DOCUMENTS
-- =====================================================
ALTER TABLE product_documents ALTER COLUMN document_type TYPE VARCHAR(50) USING document_type::text;

-- =====================================================
-- 20. ESCALATIONS
-- =====================================================
ALTER TABLE escalation_history ALTER COLUMN from_level TYPE VARCHAR(50) USING from_level::text;
ALTER TABLE escalation_history ALTER COLUMN to_level TYPE VARCHAR(50) USING to_level::text;
ALTER TABLE escalation_history ALTER COLUMN from_status TYPE VARCHAR(50) USING from_status::text;
ALTER TABLE escalation_history ALTER COLUMN to_status TYPE VARCHAR(50) USING to_status::text;
ALTER TABLE escalation_matrix ALTER COLUMN level TYPE VARCHAR(50) USING level::text;
ALTER TABLE escalation_matrix ALTER COLUMN priority TYPE VARCHAR(50) USING priority::text;
ALTER TABLE escalation_matrix ALTER COLUMN source_type TYPE VARCHAR(50) USING source_type::text;
ALTER TABLE escalations ALTER COLUMN current_level TYPE VARCHAR(50) USING current_level::text;
ALTER TABLE escalations ALTER COLUMN priority TYPE VARCHAR(50) USING priority::text;
ALTER TABLE escalations ALTER COLUMN reason TYPE VARCHAR(100) USING reason::text;
ALTER TABLE escalations ALTER COLUMN source_type TYPE VARCHAR(50) USING source_type::text;
ALTER TABLE escalations ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE escalation_notifications ALTER COLUMN channel TYPE VARCHAR(50) USING channel::text;
ALTER TABLE sla_configurations ALTER COLUMN priority TYPE VARCHAR(50) USING priority::text;
ALTER TABLE sla_configurations ALTER COLUMN source_type TYPE VARCHAR(50) USING source_type::text;

-- =====================================================
-- 21. BILLING & INVOICES
-- =====================================================
ALTER TABLE eway_bills ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE credit_debit_notes ALTER COLUMN document_type TYPE VARCHAR(50) USING document_type::text;
ALTER TABLE credit_debit_notes ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE credit_debit_notes ALTER COLUMN reason TYPE VARCHAR(100) USING reason::text;
ALTER TABLE tax_invoices ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE tax_invoices ALTER COLUMN invoice_type TYPE VARCHAR(50) USING invoice_type::text;
ALTER TABLE payment_receipts ALTER COLUMN payment_mode TYPE VARCHAR(50) USING payment_mode::text;

-- =====================================================
-- 22. FINANCIAL
-- =====================================================
ALTER TABLE financial_periods ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE journal_entries ALTER COLUMN status TYPE VARCHAR(50) USING status::text;

-- =====================================================
-- 23. PURCHASE
-- =====================================================
ALTER TABLE goods_receipt_notes ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE goods_receipt_notes ALTER COLUMN qc_status TYPE VARCHAR(50) USING qc_status::text;
ALTER TABLE grn_items ALTER COLUMN qc_result TYPE VARCHAR(50) USING qc_result::text;
ALTER TABLE purchase_requisitions ALTER COLUMN status TYPE VARCHAR(50) USING status::text;

-- =====================================================
-- 24. INSTALLATIONS
-- =====================================================
ALTER TABLE installations ALTER COLUMN status TYPE VARCHAR(50) USING status::text;

-- =====================================================
-- 25. NOTIFICATIONS
-- =====================================================
ALTER TABLE notification_templates ALTER COLUMN default_priority TYPE VARCHAR(50) USING default_priority::text;
ALTER TABLE notification_templates ALTER COLUMN notification_type TYPE VARCHAR(50) USING notification_type::text;
ALTER TABLE notifications ALTER COLUMN priority TYPE VARCHAR(50) USING priority::text;
ALTER TABLE notifications ALTER COLUMN notification_type TYPE VARCHAR(50) USING notification_type::text;

-- =====================================================
-- 26. ORDERS
-- =====================================================
ALTER TABLE orders ALTER COLUMN source TYPE VARCHAR(50) USING source::text;
ALTER TABLE orders ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE orders ALTER COLUMN payment_method TYPE VARCHAR(50) USING payment_method::text;
ALTER TABLE orders ALTER COLUMN payment_status TYPE VARCHAR(50) USING payment_status::text;
ALTER TABLE order_status_history ALTER COLUMN from_status TYPE VARCHAR(50) USING from_status::text;
ALTER TABLE order_status_history ALTER COLUMN to_status TYPE VARCHAR(50) USING to_status::text;

-- =====================================================
-- 27. PAYMENTS
-- =====================================================
ALTER TABLE payments ALTER COLUMN method TYPE VARCHAR(50) USING method::text;
ALTER TABLE payments ALTER COLUMN status TYPE VARCHAR(50) USING status::text;

-- =====================================================
-- 28. PICKLISTS
-- =====================================================
ALTER TABLE picklists ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE picklists ALTER COLUMN picklist_type TYPE VARCHAR(50) USING picklist_type::text;

-- =====================================================
-- 29. PROMOTIONS
-- =====================================================
ALTER TABLE promotions ALTER COLUMN discount_application TYPE VARCHAR(50) USING discount_application::text;
ALTER TABLE promotions ALTER COLUMN promotion_scope TYPE VARCHAR(50) USING promotion_scope::text;
ALTER TABLE promotions ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE promotions ALTER COLUMN promotion_type TYPE VARCHAR(50) USING promotion_type::text;

-- =====================================================
-- 30. REGIONS
-- =====================================================
ALTER TABLE regions ALTER COLUMN type TYPE VARCHAR(50) USING type::text;

-- =====================================================
-- 31. ROLES
-- =====================================================
ALTER TABLE roles ALTER COLUMN level TYPE VARCHAR(50) USING level::text;

-- =====================================================
-- 32. TECHNICIANS
-- =====================================================
ALTER TABLE technicians ALTER COLUMN skill_level TYPE VARCHAR(50) USING skill_level::text;
ALTER TABLE technicians ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE technicians ALTER COLUMN technician_type TYPE VARCHAR(50) USING technician_type::text;

-- =====================================================
-- 33. VENDORS
-- =====================================================
ALTER TABLE vendors ALTER COLUMN grade TYPE VARCHAR(10) USING grade::text;
ALTER TABLE vendors ALTER COLUMN payment_terms TYPE VARCHAR(50) USING payment_terms::text;
ALTER TABLE vendors ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE vendors ALTER COLUMN vendor_type TYPE VARCHAR(50) USING vendor_type::text;
ALTER TABLE vendor_invoices ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE vendor_proforma_invoices ALTER COLUMN status TYPE VARCHAR(50) USING status::text;
ALTER TABLE vendor_ledger ALTER COLUMN transaction_type TYPE VARCHAR(50) USING transaction_type::text;

COMMIT;

-- =====================================================
-- DROP ALL ENUM TYPES (Run after verifying conversions)
-- =====================================================
-- Uncomment and run after confirming all conversions succeeded

/*
DROP TYPE IF EXISTS accountsubtype CASCADE;
DROP TYPE IF EXISTS accounttype CASCADE;
DROP TYPE IF EXISTS activitytype CASCADE;
DROP TYPE IF EXISTS addresstype CASCADE;
DROP TYPE IF EXISTS adjustmentstatus CASCADE;
DROP TYPE IF EXISTS adjustmenttype CASCADE;
DROP TYPE IF EXISTS allocationtype CASCADE;
DROP TYPE IF EXISTS amcstatus CASCADE;
DROP TYPE IF EXISTS amctype CASCADE;
DROP TYPE IF EXISTS appraisalcyclestatus CASCADE;
DROP TYPE IF EXISTS appraisalstatus CASCADE;
DROP TYPE IF EXISTS approvalentitytype CASCADE;
DROP TYPE IF EXISTS approvallevel CASCADE;
DROP TYPE IF EXISTS approvalstatus CASCADE;
DROP TYPE IF EXISTS assetstatus CASCADE;
DROP TYPE IF EXISTS assettransferstatus CASCADE;
DROP TYPE IF EXISTS attendancestatus CASCADE;
DROP TYPE IF EXISTS audiencetype CASCADE;
DROP TYPE IF EXISTS auditresult CASCADE;
DROP TYPE IF EXISTS auditstatus CASCADE;
DROP TYPE IF EXISTS audittype CASCADE;
DROP TYPE IF EXISTS bankreconciliationstatus CASCADE;
DROP TYPE IF EXISTS banktransactiontype CASCADE;
DROP TYPE IF EXISTS bintype CASCADE;
DROP TYPE IF EXISTS businesstype CASCADE;
DROP TYPE IF EXISTS calculationbasis CASCADE;
DROP TYPE IF EXISTS callbackstatus CASCADE;
DROP TYPE IF EXISTS callcategory CASCADE;
DROP TYPE IF EXISTS calloutcome CASCADE;
DROP TYPE IF EXISTS callpriority CASCADE;
DROP TYPE IF EXISTS callstatus CASCADE;
DROP TYPE IF EXISTS calltype CASCADE;
DROP TYPE IF EXISTS campaigncategory CASCADE;
DROP TYPE IF EXISTS campaignstatus CASCADE;
DROP TYPE IF EXISTS campaigntype CASCADE;
DROP TYPE IF EXISTS channelcode CASCADE;
DROP TYPE IF EXISTS channelstatus CASCADE;
DROP TYPE IF EXISTS channeltype CASCADE;
DROP TYPE IF EXISTS commissionbeneficiary CASCADE;
DROP TYPE IF EXISTS commissionstatus CASCADE;
DROP TYPE IF EXISTS commissiontype CASCADE;
DROP TYPE IF EXISTS company_type CASCADE;
DROP TYPE IF EXISTS companytype CASCADE;
DROP TYPE IF EXISTS contractstatus CASCADE;
DROP TYPE IF EXISTS creditstatus CASCADE;
DROP TYPE IF EXISTS customersentiment CASCADE;
DROP TYPE IF EXISTS customersource CASCADE;
DROP TYPE IF EXISTS customertype CASCADE;
DROP TYPE IF EXISTS dealerstatus CASCADE;
DROP TYPE IF EXISTS dealertier CASCADE;
DROP TYPE IF EXISTS dealertype CASCADE;
DROP TYPE IF EXISTS deliverystatus CASCADE;
DROP TYPE IF EXISTS depreciationmethod CASCADE;
DROP TYPE IF EXISTS discountapplication CASCADE;
DROP TYPE IF EXISTS documenttype CASCADE;
DROP TYPE IF EXISTS employeestatus CASCADE;
DROP TYPE IF EXISTS employmenttype CASCADE;
DROP TYPE IF EXISTS escalationlevel CASCADE;
DROP TYPE IF EXISTS escalationpriority CASCADE;
DROP TYPE IF EXISTS escalationreason CASCADE;
DROP TYPE IF EXISTS escalationsource CASCADE;
DROP TYPE IF EXISTS escalationstatus CASCADE;
DROP TYPE IF EXISTS ewaybillstatus CASCADE;
DROP TYPE IF EXISTS financialperiodstatus CASCADE;
DROP TYPE IF EXISTS franchiseestatus CASCADE;
DROP TYPE IF EXISTS franchiseetier CASCADE;
DROP TYPE IF EXISTS franchiseetype CASCADE;
DROP TYPE IF EXISTS gender CASCADE;
DROP TYPE IF EXISTS goalstatus CASCADE;
DROP TYPE IF EXISTS grnstatus CASCADE;
DROP TYPE IF EXISTS gst_registration_type CASCADE;
DROP TYPE IF EXISTS gstregistrationtype CASCADE;
DROP TYPE IF EXISTS installationstatus CASCADE;
DROP TYPE IF EXISTS invoicestatus CASCADE;
DROP TYPE IF EXISTS invoicetype CASCADE;
DROP TYPE IF EXISTS itemcondition CASCADE;
DROP TYPE IF EXISTS journalentrystatus CASCADE;
DROP TYPE IF EXISTS leadinterest CASCADE;
DROP TYPE IF EXISTS leadpriority CASCADE;
DROP TYPE IF EXISTS leadsource CASCADE;
DROP TYPE IF EXISTS leadstatus CASCADE;
DROP TYPE IF EXISTS leadtype CASCADE;
DROP TYPE IF EXISTS leavestatus CASCADE;
DROP TYPE IF EXISTS leavetype CASCADE;
DROP TYPE IF EXISTS lostreason CASCADE;
DROP TYPE IF EXISTS maintenancestatus CASCADE;
DROP TYPE IF EXISTS manifeststatus CASCADE;
DROP TYPE IF EXISTS maritalstatus CASCADE;
DROP TYPE IF EXISTS notereason CASCADE;
DROP TYPE IF EXISTS notificationchannel CASCADE;
DROP TYPE IF EXISTS notificationpriority CASCADE;
DROP TYPE IF EXISTS notificationtype CASCADE;
DROP TYPE IF EXISTS ordersource CASCADE;
DROP TYPE IF EXISTS orderstatus CASCADE;
DROP TYPE IF EXISTS packagingtype CASCADE;
DROP TYPE IF EXISTS paymentmethod CASCADE;
DROP TYPE IF EXISTS paymentmode CASCADE;
DROP TYPE IF EXISTS paymentstatus CASCADE;
DROP TYPE IF EXISTS paymentterms CASCADE;
DROP TYPE IF EXISTS payoutstatus CASCADE;
DROP TYPE IF EXISTS payrollstatus CASCADE;
DROP TYPE IF EXISTS pickliststatus CASCADE;
DROP TYPE IF EXISTS picklisttype CASCADE;
DROP TYPE IF EXISTS pickupstatus CASCADE;
DROP TYPE IF EXISTS productitemtype CASCADE;
DROP TYPE IF EXISTS productstatus CASCADE;
DROP TYPE IF EXISTS proformastatus CASCADE;
DROP TYPE IF EXISTS promotionscope CASCADE;
DROP TYPE IF EXISTS promotionstatus CASCADE;
DROP TYPE IF EXISTS promotiontype CASCADE;
DROP TYPE IF EXISTS qastatus CASCADE;
DROP TYPE IF EXISTS qualitycheckresult CASCADE;
DROP TYPE IF EXISTS regiontype CASCADE;
DROP TYPE IF EXISTS requisitionstatus CASCADE;
DROP TYPE IF EXISTS resolutiontype CASCADE;
DROP TYPE IF EXISTS restockdecision CASCADE;
DROP TYPE IF EXISTS returnreason CASCADE;
DROP TYPE IF EXISTS rolelevel CASCADE;
DROP TYPE IF EXISTS schemetype CASCADE;
DROP TYPE IF EXISTS servicepriority CASCADE;
DROP TYPE IF EXISTS servicesource CASCADE;
DROP TYPE IF EXISTS servicestatus CASCADE;
DROP TYPE IF EXISTS servicetype CASCADE;
DROP TYPE IF EXISTS shipmentstatus CASCADE;
DROP TYPE IF EXISTS skilllevel CASCADE;
DROP TYPE IF EXISTS srnstatus CASCADE;
DROP TYPE IF EXISTS stockitemstatus CASCADE;
DROP TYPE IF EXISTS stockmovementtype CASCADE;
DROP TYPE IF EXISTS supportticketcategory CASCADE;
DROP TYPE IF EXISTS supportticketpriority CASCADE;
DROP TYPE IF EXISTS supportticketstatus CASCADE;
DROP TYPE IF EXISTS technicianstatus CASCADE;
DROP TYPE IF EXISTS techniciantype CASCADE;
DROP TYPE IF EXISTS territorystatus CASCADE;
DROP TYPE IF EXISTS trainingstatus CASCADE;
DROP TYPE IF EXISTS trainingtype CASCADE;
DROP TYPE IF EXISTS transactiontype CASCADE;
DROP TYPE IF EXISTS transferstatus CASCADE;
DROP TYPE IF EXISTS transfertype CASCADE;
DROP TYPE IF EXISTS transportertype CASCADE;
DROP TYPE IF EXISTS vendorgrade CASCADE;
DROP TYPE IF EXISTS vendorinvoicestatus CASCADE;
DROP TYPE IF EXISTS vendorstatus CASCADE;
DROP TYPE IF EXISTS vendortransactiontype CASCADE;
DROP TYPE IF EXISTS vendortype CASCADE;
DROP TYPE IF EXISTS warehousetype CASCADE;
DROP TYPE IF EXISTS zonetype CASCADE;
*/

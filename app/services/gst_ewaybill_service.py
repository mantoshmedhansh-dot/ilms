"""
GST E-Way Bill Service

Integrates with NIC (National Informatics Centre) E-Way Bill Portal for:
- E-Way Bill generation for goods transport > Rs. 50,000
- Part-B update (transporter/vehicle details)
- E-Way Bill cancellation within 24 hours
- E-Way Bill extension for validity
- Consolidated E-Way Bill generation

API Documentation: https://ewaybillgst.gov.in/
Sandbox: https://gsp.adaabortal.in/test/
Production: https://ewaybillgst.gov.in/

E-Way Bill is mandatory for:
- Interstate movement of goods > Rs. 50,000
- Intrastate movement (threshold varies by state)
"""

import httpx
import json
import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import Company
from app.models.billing import EWayBill, EWayBillItem, EWayBillStatus, TaxInvoice


class GSTEWayBillError(Exception):
    """Custom exception for E-Way Bill errors."""
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class GSTEWayBillService:
    """
    Service for GST E-Way Bill operations via NIC portal.

    Supports:
    - Authentication and token management
    - E-Way Bill generation
    - Part-B update (vehicle details)
    - E-Way Bill cancellation
    - E-Way Bill extension
    - Consolidated E-Way Bill
    """

    # NIC E-Way Bill API Endpoints
    SANDBOX_BASE_URL = "https://gsp.adaabortal.in/test/enriched/ewb/ewayapi"
    PRODUCTION_BASE_URL = "https://gsp.adaabortal.in/enriched/ewb/ewayapi"

    # Alternative official NIC endpoints
    NIC_SANDBOX_URL = "https://ewb.nic.in/ewb_sandbox"
    NIC_PRODUCTION_URL = "https://ewaybillgst.gov.in/ewaybill"

    # API Paths
    AUTH_PATH = "/authenticate"
    GENERATE_EWB_PATH = "/ewayapi"
    GET_EWB_PATH = "/ewayapi/GetEwayBill"
    CANCEL_EWB_PATH = "/ewayapi/ewbCancel"
    UPDATE_PARTB_PATH = "/ewayapi/VEHEWB"
    EXTEND_VALIDITY_PATH = "/ewayapi/EXTENDEWB"
    CONSOLIDATED_EWB_PATH = "/ewayapi/CEWB"
    GET_TRANSPORTER_PATH = "/ewayapi/GetTransporterDetails"

    # Supply Type Codes
    SUPPLY_TYPES = {
        "O": "Outward",
        "I": "Inward"
    }

    # Sub Supply Types
    SUB_SUPPLY_TYPES = {
        1: "Supply",
        2: "Import",
        3: "Export",
        4: "Job Work",
        5: "For Own Use",
        6: "Job Work Returns",
        7: "Sales Return",
        8: "Others",
        9: "SKD/CKD/Lots",
        10: "Line Sales",
        11: "Recipient Not Known",
        12: "Exhibition or Fairs"
    }

    # Document Types
    DOC_TYPES = {
        "INV": "Tax Invoice",
        "BIL": "Bill of Supply",
        "BOE": "Bill of Entry",
        "CHL": "Delivery Challan",
        "CNT": "Credit Note",
        "OTH": "Others"
    }

    # Transport Modes
    TRANSPORT_MODES = {
        "1": "Road",
        "2": "Rail",
        "3": "Air",
        "4": "Ship/Waterways"
    }

    # Vehicle Types
    VEHICLE_TYPES = {
        "R": "Regular",
        "O": "Over Dimensional Cargo (ODC)"
    }

    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id
        self._company: Optional[Company] = None
        self._auth_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    async def _get_company(self) -> Company:
        """Get company with E-Way Bill settings."""
        if self._company:
            return self._company

        result = await self.db.execute(
            select(Company).where(Company.id == self.company_id)
        )
        company = result.scalar_one_or_none()

        if not company:
            raise GSTEWayBillError("Company not found")

        if not company.ewaybill_enabled:
            raise GSTEWayBillError("E-Way Bill not enabled for this company")

        if not company.ewaybill_username:
            raise GSTEWayBillError("E-Way Bill username not configured")

        self._company = company
        return company

    @property
    def base_url(self) -> str:
        """Get base URL based on API mode."""
        if self._company and self._company.ewaybill_api_mode == "PRODUCTION":
            return self.PRODUCTION_BASE_URL
        return self.SANDBOX_BASE_URL

    def _encrypt_password(self, password: str, public_key: str) -> str:
        """Encrypt password using RSA public key (for NIC authentication)."""
        # NIC uses RSA encryption for password
        # For now, return base64 encoded (sandbox may accept this)
        return base64.b64encode(password.encode()).decode()

    async def authenticate(self) -> str:
        """
        Authenticate with NIC E-Way Bill portal.

        Returns auth token for subsequent API calls.
        """
        # Check if token is still valid
        if self._auth_token and self._token_expiry and datetime.now(timezone.utc) < self._token_expiry:
            return self._auth_token

        company = await self._get_company()

        # Get decrypted password
        password = company.ewaybill_password
        if password and password.startswith("ENC:"):
            password = password[4:]  # Remove encryption prefix

        auth_payload = {
            "action": "ACCESSTOKEN",
            "username": company.ewaybill_username,
            "password": password,
            "app_key": company.ewaybill_app_key or "",
        }

        headers = {
            "Content-Type": "application/json",
            "gstin": company.gstin,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{self.AUTH_PATH}",
                    json=auth_payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()

                if result.get("status") == 1:
                    self._auth_token = result.get("authToken")
                    # Token valid for 6 hours, but refresh after 5 hours
                    self._token_expiry = datetime.now(timezone.utc) + timedelta(hours=5)
                    return self._auth_token
                else:
                    raise GSTEWayBillError(
                        message=result.get("error", {}).get("message", "Authentication failed"),
                        error_code=result.get("error", {}).get("errorCodes"),
                        details=result
                    )

            except httpx.HTTPStatusError as e:
                raise GSTEWayBillError(
                    message=f"Authentication HTTP error: {e.response.status_code}",
                    details={"response": e.response.text}
                )

    def _build_ewb_payload(self, ewb: EWayBill, invoice: TaxInvoice) -> Dict:
        """
        Build E-Way Bill JSON payload as per NIC specifications.

        Reference: https://ewaybillgst.gov.in/Documents/ewaybill_apispec.pdf
        """
        # Load items
        items = ewb.items if ewb.items else []

        payload = {
            # Supply details
            "supplyType": ewb.supply_type,  # O = Outward, I = Inward
            "subSupplyType": ewb.sub_supply_type,  # 1-12 codes
            "subSupplyDesc": "",
            "docType": ewb.document_type,  # INV, BIL, BOE, CHL, CNT, OTH
            "docNo": ewb.document_number,
            "docDate": ewb.document_date.strftime("%d/%m/%Y"),

            # From (Consignor) details
            "fromGstin": ewb.from_gstin,
            "fromTrdName": ewb.from_name,
            "fromAddr1": ewb.from_address1,
            "fromAddr2": ewb.from_address2 or "",
            "fromPlace": ewb.from_place,
            "fromPincode": int(ewb.from_pincode),
            "fromStateCode": int(ewb.from_state_code),
            "actFromStateCode": int(ewb.from_state_code),

            # To (Consignee) details
            "toGstin": ewb.to_gstin or "URP",  # URP = Unregistered Person
            "toTrdName": ewb.to_name,
            "toAddr1": ewb.to_address1,
            "toAddr2": ewb.to_address2 or "",
            "toPlace": ewb.to_place,
            "toPincode": int(ewb.to_pincode),
            "toStateCode": int(ewb.to_state_code),
            "actToStateCode": int(ewb.to_state_code),

            # Transaction type
            "transactionType": ewb.transaction_type or 1,  # 1 = Regular, 2 = Bill To Ship To, etc.

            # Values
            "totalValue": float(invoice.taxable_amount),
            "cgstValue": float(invoice.cgst_amount or 0),
            "sgstValue": float(invoice.sgst_amount or 0),
            "igstValue": float(invoice.igst_amount or 0),
            "cessValue": float(invoice.cess_amount or 0),
            "cessNonAdvolValue": 0,
            "otherValue": float(invoice.shipping_charges or 0) + float(invoice.other_charges or 0),
            "totInvValue": float(invoice.grand_total),

            # Transport details
            "transporterId": ewb.transporter_id or "",
            "transporterName": ewb.transporter_name or "",
            "transMode": ewb.transport_mode or "1",
            "transDistance": ewb.distance_km or 0,
            "vehicleNo": ewb.vehicle_number or "",
            "vehicleType": ewb.vehicle_type or "R",
            "transDocNo": ewb.transport_doc_number or "",
            "transDocDate": ewb.transport_doc_date.strftime("%d/%m/%Y") if ewb.transport_doc_date else "",

            # Item list
            "itemList": []
        }

        # Add items
        for idx, item in enumerate(items, 1):
            item_data = {
                "itemNo": idx,
                "productName": item.product_name,
                "productDesc": item.product_name,
                "hsnCode": int(item.hsn_code) if item.hsn_code else 0,
                "quantity": float(item.quantity),
                "qtyUnit": item.uom or "NOS",
                "taxableAmount": float(item.taxable_value),
                "cgstRate": float(item.gst_rate / 2) if not invoice.is_interstate else 0,
                "sgstRate": float(item.gst_rate / 2) if not invoice.is_interstate else 0,
                "igstRate": float(item.gst_rate) if invoice.is_interstate else 0,
                "cessRate": 0,
            }
            payload["itemList"].append(item_data)

        return payload

    async def generate_ewaybill(self, ewb_id: UUID) -> Dict:
        """
        Generate E-Way Bill for goods transport.

        Returns:
            Dict with ewbNo, ewbDt, ewbValidTill
        """
        await self.authenticate()

        # Get E-Way Bill record
        result = await self.db.execute(
            select(EWayBill)
            .options(selectinload(EWayBill.items))
            .where(EWayBill.id == ewb_id)
        )
        ewb = result.scalar_one_or_none()

        if not ewb:
            raise GSTEWayBillError("E-Way Bill record not found")

        if ewb.eway_bill_number:
            raise GSTEWayBillError("E-Way Bill number already generated")

        # Get related invoice
        invoice_result = await self.db.execute(
            select(TaxInvoice).where(TaxInvoice.id == ewb.invoice_id)
        )
        invoice = invoice_result.scalar_one_or_none()

        if not invoice:
            raise GSTEWayBillError("Related invoice not found")

        # Build payload
        payload = self._build_ewb_payload(ewb, invoice)
        payload["action"] = "GENEWAYBILL"

        company = await self._get_company()
        headers = {
            "Content-Type": "application/json",
            "gstin": company.gstin,
            "authToken": self._auth_token,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{self.GENERATE_EWB_PATH}",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()

                if result.get("status") == 1:
                    ewb_data = result.get("data", {})

                    # Update E-Way Bill record
                    ewb.eway_bill_number = str(ewb_data.get("ewayBillNo"))
                    ewb.generated_at = datetime.now(timezone.utc)
                    ewb.valid_from = datetime.strptime(
                        ewb_data.get("ewayBillDate"), "%d/%m/%Y %H:%M:%S"
                    ) if ewb_data.get("ewayBillDate") else datetime.now(timezone.utc)
                    ewb.valid_until = datetime.strptime(
                        ewb_data.get("validUpto"), "%d/%m/%Y %H:%M:%S"
                    ) if ewb_data.get("validUpto") else None
                    ewb.status = EWayBillStatus.GENERATED.value

                    await self.db.commit()
                    await self.db.refresh(ewb)

                    return {
                        "ewb_number": ewb.eway_bill_number,
                        "ewb_date": ewb.valid_from,
                        "valid_until": ewb.valid_until,
                        "status": "SUCCESS"
                    }
                else:
                    error = result.get("error", {})
                    raise GSTEWayBillError(
                        message=error.get("message", "E-Way Bill generation failed"),
                        error_code=error.get("errorCodes"),
                        details=result
                    )

            except httpx.HTTPStatusError as e:
                raise GSTEWayBillError(
                    message=f"E-Way Bill generation HTTP error: {e.response.status_code}",
                    details={"response": e.response.text}
                )

    async def update_part_b(
        self,
        ewb_id: UUID,
        vehicle_number: str,
        transport_mode: str = "1",
        reason_code: str = "1",
        reason_remarks: str = "",
        from_place: str = "",
        from_state: str = "",
        transporter_id: str = ""
    ) -> Dict:
        """
        Update Part-B (vehicle/transporter details) of E-Way Bill.

        Reason codes:
        1 - Due to breakdown
        2 - Due to transshipment
        3 - Others
        4 - First time

        Args:
            ewb_id: E-Way Bill UUID
            vehicle_number: New vehicle registration number
            transport_mode: 1=Road, 2=Rail, 3=Air, 4=Ship
            reason_code: Reason for update
            reason_remarks: Additional remarks
            from_place: Place from where vehicle is starting
            from_state: State code from where vehicle is starting
            transporter_id: Transporter GSTIN (if applicable)
        """
        await self.authenticate()

        result = await self.db.execute(
            select(EWayBill).where(EWayBill.id == ewb_id)
        )
        ewb = result.scalar_one_or_none()

        if not ewb:
            raise GSTEWayBillError("E-Way Bill not found")

        if not ewb.eway_bill_number:
            raise GSTEWayBillError("E-Way Bill number not generated yet")

        if ewb.status == EWayBillStatus.CANCELLED:
            raise GSTEWayBillError("Cannot update cancelled E-Way Bill")

        # Check if validity has expired
        if ewb.valid_until and datetime.now(timezone.utc) > ewb.valid_until:
            raise GSTEWayBillError("E-Way Bill validity has expired. Please extend validity first.")

        payload = {
            "action": "VEHEWB",
            "ewbNo": int(ewb.eway_bill_number),
            "vehicleNo": vehicle_number.upper().replace(" ", ""),
            "fromPlace": from_place or ewb.from_place,
            "fromState": int(from_state) if from_state else int(ewb.from_state_code),
            "reasonCode": reason_code,
            "reasonRem": reason_remarks,
            "transDocNo": ewb.transport_doc_number or "",
            "transDocDate": ewb.transport_doc_date.strftime("%d/%m/%Y") if ewb.transport_doc_date else "",
            "transMode": transport_mode,
            "vehicleType": ewb.vehicle_type or "R",
        }

        if transporter_id:
            payload["transporterId"] = transporter_id

        company = await self._get_company()
        headers = {
            "Content-Type": "application/json",
            "gstin": company.gstin,
            "authToken": self._auth_token,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{self.UPDATE_PARTB_PATH}",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()

                if result.get("status") == 1:
                    # Update local record
                    ewb.vehicle_number = vehicle_number.upper().replace(" ", "")
                    ewb.transport_mode = transport_mode

                    if result.get("data", {}).get("validUpto"):
                        ewb.valid_until = datetime.strptime(
                            result["data"]["validUpto"], "%d/%m/%Y %H:%M:%S"
                        )

                    await self.db.commit()

                    return {
                        "ewb_number": ewb.eway_bill_number,
                        "vehicle_number": ewb.vehicle_number,
                        "valid_until": ewb.valid_until,
                        "status": "SUCCESS"
                    }
                else:
                    error = result.get("error", {})
                    raise GSTEWayBillError(
                        message=error.get("message", "Part-B update failed"),
                        error_code=error.get("errorCodes"),
                        details=result
                    )

            except httpx.HTTPStatusError as e:
                raise GSTEWayBillError(
                    message=f"Part-B update HTTP error: {e.response.status_code}",
                    details={"response": e.response.text}
                )

    async def cancel_ewaybill(self, ewb_id: UUID, reason_code: str, remarks: str = "") -> Dict:
        """
        Cancel E-Way Bill within 24 hours of generation.

        Cancel reason codes:
        1 - Duplicate
        2 - Order Cancelled
        3 - Data Entry Mistake
        4 - Others
        """
        await self.authenticate()

        result = await self.db.execute(
            select(EWayBill).where(EWayBill.id == ewb_id)
        )
        ewb = result.scalar_one_or_none()

        if not ewb:
            raise GSTEWayBillError("E-Way Bill not found")

        if not ewb.eway_bill_number:
            raise GSTEWayBillError("E-Way Bill number not generated")

        if ewb.status == EWayBillStatus.CANCELLED:
            raise GSTEWayBillError("E-Way Bill is already cancelled")

        # Check 24-hour window
        if ewb.generated_at:
            hours_elapsed = (datetime.now(timezone.utc) - ewb.generated_at).total_seconds() / 3600
            if hours_elapsed > 24:
                raise GSTEWayBillError("E-Way Bill can only be cancelled within 24 hours")

        payload = {
            "action": "CANEWB",
            "ewbNo": int(ewb.eway_bill_number),
            "cancelRsnCode": int(reason_code),
            "cancelRmrk": remarks or f"Cancelled with reason code {reason_code}"
        }

        company = await self._get_company()
        headers = {
            "Content-Type": "application/json",
            "gstin": company.gstin,
            "authToken": self._auth_token,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{self.CANCEL_EWB_PATH}",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()

                if result.get("status") == 1:
                    ewb.status = EWayBillStatus.CANCELLED.value
                    ewb.cancelled_at = datetime.now(timezone.utc)
                    ewb.cancel_reason = remarks or reason_code

                    await self.db.commit()

                    return {
                        "ewb_number": ewb.eway_bill_number,
                        "cancel_date": ewb.cancelled_at,
                        "status": "CANCELLED"
                    }
                else:
                    error = result.get("error", {})
                    raise GSTEWayBillError(
                        message=error.get("message", "E-Way Bill cancellation failed"),
                        error_code=error.get("errorCodes"),
                        details=result
                    )

            except httpx.HTTPStatusError as e:
                raise GSTEWayBillError(
                    message=f"Cancellation HTTP error: {e.response.status_code}",
                    details={"response": e.response.text}
                )

    async def extend_validity(
        self,
        ewb_id: UUID,
        from_place: str,
        from_state: int,
        remaining_distance: int,
        reason_code: str = "1",
        reason_remarks: str = "",
        transit_type: str = "C",  # C = In-transit, R = Reached destination
        vehicle_number: str = "",
        transport_mode: str = "1"
    ) -> Dict:
        """
        Extend E-Way Bill validity when goods are in transit.

        Can be extended 8 hours before expiry or 8 hours after expiry.

        Extension reason codes:
        1 - Natural calamity
        2 - Law and order situation
        3 - Transshipment
        4 - Accident
        99 - Others
        """
        await self.authenticate()

        result = await self.db.execute(
            select(EWayBill).where(EWayBill.id == ewb_id)
        )
        ewb = result.scalar_one_or_none()

        if not ewb:
            raise GSTEWayBillError("E-Way Bill not found")

        if not ewb.eway_bill_number:
            raise GSTEWayBillError("E-Way Bill number not generated")

        if ewb.status == EWayBillStatus.CANCELLED:
            raise GSTEWayBillError("Cannot extend cancelled E-Way Bill")

        # Check extension window (8 hours before or after expiry)
        if ewb.valid_until:
            hours_from_expiry = (ewb.valid_until - datetime.now(timezone.utc)).total_seconds() / 3600
            if hours_from_expiry < -8 or hours_from_expiry > 8:
                raise GSTEWayBillError(
                    "E-Way Bill can only be extended 8 hours before or after expiry"
                )

        payload = {
            "action": "EXTENDEWB",
            "ewbNo": int(ewb.eway_bill_number),
            "vehicleNo": vehicle_number or ewb.vehicle_number,
            "fromPlace": from_place,
            "fromState": from_state,
            "remainingDistance": remaining_distance,
            "transDocNo": ewb.transport_doc_number or "",
            "transDocDate": ewb.transport_doc_date.strftime("%d/%m/%Y") if ewb.transport_doc_date else "",
            "transMode": transport_mode,
            "extnRsnCode": int(reason_code),
            "extnRemarks": reason_remarks,
            "consignmentStatus": transit_type
        }

        company = await self._get_company()
        headers = {
            "Content-Type": "application/json",
            "gstin": company.gstin,
            "authToken": self._auth_token,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{self.EXTEND_VALIDITY_PATH}",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()

                if result.get("status") == 1:
                    ewb_data = result.get("data", {})

                    if ewb_data.get("validUpto"):
                        ewb.valid_until = datetime.strptime(
                            ewb_data["validUpto"], "%d/%m/%Y %H:%M:%S"
                        )

                    await self.db.commit()

                    return {
                        "ewb_number": ewb.eway_bill_number,
                        "new_validity": ewb.valid_until,
                        "status": "EXTENDED"
                    }
                else:
                    error = result.get("error", {})
                    raise GSTEWayBillError(
                        message=error.get("message", "E-Way Bill extension failed"),
                        error_code=error.get("errorCodes"),
                        details=result
                    )

            except httpx.HTTPStatusError as e:
                raise GSTEWayBillError(
                    message=f"Extension HTTP error: {e.response.status_code}",
                    details={"response": e.response.text}
                )

    async def get_ewaybill_details(self, ewb_number: str) -> Dict:
        """Get details of an existing E-Way Bill from portal."""
        await self.authenticate()

        company = await self._get_company()
        headers = {
            "Content-Type": "application/json",
            "gstin": company.gstin,
            "authToken": self._auth_token,
        }

        payload = {
            "action": "GETEWB",
            "ewbNo": int(ewb_number)
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{self.GET_EWB_PATH}",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()

                if result.get("status") == 1:
                    return result.get("data", {})
                else:
                    error = result.get("error", {})
                    raise GSTEWayBillError(
                        message=error.get("message", "Failed to get E-Way Bill details"),
                        error_code=error.get("errorCodes"),
                        details=result
                    )

            except httpx.HTTPStatusError as e:
                raise GSTEWayBillError(
                    message=f"Get E-Way Bill HTTP error: {e.response.status_code}",
                    details={"response": e.response.text}
                )

    async def get_transporter_details(self, transporter_id: str) -> Dict:
        """Get transporter details by GSTIN."""
        await self.authenticate()

        company = await self._get_company()
        headers = {
            "Content-Type": "application/json",
            "gstin": company.gstin,
            "authToken": self._auth_token,
        }

        payload = {
            "action": "GETTRANSDETAILS",
            "transId": transporter_id
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{self.GET_TRANSPORTER_PATH}",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()

                if result.get("status") == 1:
                    return result.get("data", {})
                else:
                    return {"error": result.get("error", {}).get("message", "Transporter not found")}

            except httpx.HTTPStatusError:
                return {"error": "Failed to get transporter details"}


def calculate_ewb_validity_days(distance_km: int) -> int:
    """
    Calculate E-Way Bill validity based on distance.

    As per GST rules:
    - Up to 100 km: 1 day
    - Every additional 100 km: 1 additional day
    - Over Dimensional Cargo (ODC): 1 day per 20 km
    """
    if distance_km <= 100:
        return 1
    else:
        return 1 + ((distance_km - 1) // 100)


def calculate_ewb_validity_days_odc(distance_km: int) -> int:
    """Calculate E-Way Bill validity for Over Dimensional Cargo."""
    if distance_km <= 20:
        return 1
    else:
        return 1 + ((distance_km - 1) // 20)

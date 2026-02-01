"""
GST E-Invoice Service

Integrates with NIC (National Informatics Centre) E-Invoice Portal for:
- IRN (Invoice Reference Number) generation
- QR Code generation
- IRN cancellation
- E-Invoice validation

API Documentation: https://einvoice1.gst.gov.in/
Sandbox: https://einvoice1-sandbox.nic.in/
Production: https://einvoice1.gst.gov.in/
"""

import httpx
import json
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.billing import TaxInvoice, InvoiceItem


class GSTEInvoiceError(Exception):
    """Custom exception for E-Invoice errors."""
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class GSTEInvoiceService:
    """
    Service for GST E-Invoice operations via NIC portal.

    Supports:
    - Authentication and token management
    - IRN generation for B2B invoices
    - IRN cancellation within 24 hours
    - QR code generation and validation
    """

    # NIC API Endpoints
    SANDBOX_BASE_URL = "https://einvoice1-sandbox.nic.in"
    PRODUCTION_BASE_URL = "https://einvoice1.gst.gov.in"

    # API Paths
    AUTH_PATH = "/eivital/v1.04/auth"
    GENERATE_IRN_PATH = "/eicore/v1.03/Invoice"
    GET_IRN_PATH = "/eicore/v1.03/Invoice/irn"
    CANCEL_IRN_PATH = "/eicore/v1.03/Invoice/Cancel"
    GET_GSTIN_PATH = "/eivital/v1.03/Master/gstin"

    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id
        self._company: Optional[Company] = None
        self._auth_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._sek: Optional[bytes] = None  # Session Encryption Key

    async def _get_company(self) -> Company:
        """Get company with E-Invoice settings."""
        if self._company:
            return self._company

        result = await self.db.execute(
            select(Company).where(Company.id == self.company_id)
        )
        company = result.scalar_one_or_none()

        if not company:
            raise GSTEInvoiceError("Company not found")

        if not company.einvoice_enabled:
            raise GSTEInvoiceError("E-Invoice not enabled for this company")

        if not company.einvoice_username:
            raise GSTEInvoiceError("E-Invoice username not configured")

        self._company = company
        return company

    @property
    def base_url(self) -> str:
        """Get base URL based on API mode."""
        if self._company and self._company.einvoice_api_mode == "PRODUCTION":
            return self.PRODUCTION_BASE_URL
        return self.SANDBOX_BASE_URL

    def _decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt the stored E-Invoice password.
        In production, use proper key management (AWS KMS, HashiCorp Vault, etc.)
        """
        # For now, return as-is if not encrypted
        # TODO: Implement proper decryption with KMS
        if encrypted_password.startswith("ENC:"):
            # Encrypted format: ENC:base64_encrypted_data
            # This is a placeholder - implement actual decryption
            return encrypted_password[4:]  # Remove ENC: prefix
        return encrypted_password

    def _encrypt_request(self, data: Dict, key: bytes) -> str:
        """Encrypt request data using AES-256."""
        json_data = json.dumps(data).encode('utf-8')

        # Pad to 16 bytes (AES block size)
        padding_length = 16 - (len(json_data) % 16)
        padded_data = json_data + bytes([padding_length] * padding_length)

        # Generate IV
        iv = os.urandom(16)

        # Encrypt
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()

        # Return base64 encoded: IV + encrypted data
        return base64.b64encode(iv + encrypted).decode('utf-8')

    def _decrypt_response(self, encrypted_data: str, key: bytes) -> Dict:
        """Decrypt response data using AES-256."""
        data = base64.b64decode(encrypted_data)

        # Extract IV (first 16 bytes)
        iv = data[:16]
        encrypted = data[16:]

        # Decrypt
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted) + decryptor.finalize()

        # Remove padding
        padding_length = decrypted[-1]
        decrypted = decrypted[:-padding_length]

        return json.loads(decrypted.decode('utf-8'))

    async def authenticate(self) -> str:
        """
        Authenticate with NIC E-Invoice portal and get auth token.
        Token is valid for 6 hours.
        """
        # Check if we have a valid token
        if self._auth_token and self._token_expiry and datetime.now(timezone.utc) < self._token_expiry:
            return self._auth_token

        company = await self._get_company()
        password = self._decrypt_password(company.einvoice_password_encrypted or "")

        # Prepare auth request
        auth_data = {
            "UserName": company.einvoice_username,
            "Password": password,
            "AppKey": base64.b64encode(os.urandom(32)).decode('utf-8'),  # Random app key
            "ForceRefreshAccessToken": False
        }

        headers = {
            "Content-Type": "application/json",
            "gstin": company.gstin,
            "client-id": company.einvoice_username,
            "client-secret": password,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{self.AUTH_PATH}",
                    json=auth_data,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()

                if result.get("Status") == 1:
                    self._auth_token = result["Data"]["AuthToken"]
                    self._sek = base64.b64decode(result["Data"]["Sek"])
                    # Token valid for 6 hours, refresh at 5.5 hours
                    self._token_expiry = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
                    return self._auth_token
                else:
                    raise GSTEInvoiceError(
                        message=result.get("ErrorDetails", [{}])[0].get("ErrorMessage", "Authentication failed"),
                        error_code=result.get("ErrorDetails", [{}])[0].get("ErrorCode"),
                        details=result
                    )

            except httpx.HTTPStatusError as e:
                raise GSTEInvoiceError(
                    message=f"Authentication HTTP error: {e.response.status_code}",
                    details={"response": e.response.text}
                )
            except httpx.RequestError as e:
                raise GSTEInvoiceError(
                    message=f"Authentication request failed: {str(e)}"
                )

    def _build_invoice_payload(self, invoice: TaxInvoice) -> Dict:
        """
        Build E-Invoice JSON payload as per NIC schema.
        Reference: https://einvoice1.gst.gov.in/Others/GSTINVSchemaV1.1.pdf
        """
        # Transaction details
        payload = {
            "Version": "1.1",
            "TranDtls": {
                "TaxSch": "GST",
                "SupTyp": "B2B",  # B2B, SEZWP, SEZWOP, EXPWP, EXPWOP, DEXP
                "RegRev": "N",  # Reverse charge
                "EcmGstin": None,  # E-commerce GSTIN if applicable
                "IgstOnIntra": "N"
            },
            "DocDtls": {
                "Typ": "INV",  # INV, CRN, DBN
                "No": invoice.invoice_number,
                "Dt": invoice.invoice_date.strftime("%d/%m/%Y")
            },
            "SellerDtls": {
                "Gstin": invoice.seller_gstin,
                "LglNm": invoice.seller_name,
                "TrdNm": invoice.seller_trade_name or invoice.seller_name,
                "Addr1": invoice.seller_address_line1,
                "Addr2": invoice.seller_address_line2 or "",
                "Loc": invoice.seller_city,
                "Pin": int(invoice.seller_pincode),
                "Stcd": invoice.seller_state_code,
                "Ph": invoice.seller_phone or "",
                "Em": invoice.seller_email or ""
            },
            "BuyerDtls": {
                "Gstin": invoice.buyer_gstin or "URP",  # URP for unregistered
                "LglNm": invoice.buyer_name,
                "TrdNm": invoice.buyer_trade_name or invoice.buyer_name,
                "Pos": invoice.place_of_supply,
                "Addr1": invoice.buyer_address_line1,
                "Addr2": invoice.buyer_address_line2 or "",
                "Loc": invoice.buyer_city,
                "Pin": int(invoice.buyer_pincode) if invoice.buyer_pincode else 0,
                "Stcd": invoice.buyer_state_code,
                "Ph": invoice.buyer_phone or "",
                "Em": invoice.buyer_email or ""
            },
            "ItemList": [],
            "ValDtls": {
                "AssVal": float(invoice.taxable_amount),
                "CgstVal": float(invoice.cgst_amount or 0),
                "SgstVal": float(invoice.sgst_amount or 0),
                "IgstVal": float(invoice.igst_amount or 0),
                "CesVal": float(invoice.cess_amount or 0),
                "StCesVal": 0,
                "Discount": float(invoice.discount_amount or 0),
                "OthChrg": float(invoice.other_charges or 0),
                "RndOffAmt": float(invoice.round_off or 0),
                "TotInvVal": float(invoice.total_amount),
                "TotInvValFc": 0
            }
        }

        # Add items
        for idx, item in enumerate(invoice.items, 1):
            item_data = {
                "SlNo": str(idx),
                "PrdDesc": item.description,
                "IsServc": "Y" if item.is_service else "N",
                "HsnCd": item.hsn_code,
                "Barcde": item.barcode or "",
                "Qty": float(item.quantity),
                "FreeQty": 0,
                "Unit": item.unit or "NOS",
                "UnitPrice": float(item.unit_price),
                "TotAmt": float(item.total_amount),
                "Discount": float(item.discount or 0),
                "PreTaxVal": 0,
                "AssAmt": float(item.taxable_amount),
                "GstRt": float(item.gst_rate),
                "IgstAmt": float(item.igst_amount or 0),
                "CgstAmt": float(item.cgst_amount or 0),
                "SgstAmt": float(item.sgst_amount or 0),
                "CesRt": float(item.cess_rate or 0),
                "CesAmt": float(item.cess_amount or 0),
                "CesNonAdvlAmt": 0,
                "StateCesRt": 0,
                "StateCesAmt": 0,
                "StateCesNonAdvlAmt": 0,
                "OthChrg": 0,
                "TotItemVal": float(item.total_with_tax)
            }
            payload["ItemList"].append(item_data)

        return payload

    async def generate_irn(self, invoice_id: UUID) -> Dict:
        """
        Generate IRN for an invoice.

        Returns:
            Dict with IRN, AckNo, AckDt, SignedQRCode, SignedInvoice
        """
        # Get auth token
        await self.authenticate()

        # Get invoice
        result = await self.db.execute(
            select(TaxInvoice).where(TaxInvoice.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise GSTEInvoiceError("Invoice not found")

        if invoice.irn:
            raise GSTEInvoiceError("IRN already generated for this invoice")

        # Build payload
        payload = self._build_invoice_payload(invoice)

        # Encrypt payload
        encrypted_payload = self._encrypt_request(payload, self._sek)

        company = await self._get_company()
        headers = {
            "Content-Type": "application/json",
            "gstin": company.gstin,
            "auth-token": self._auth_token,
            "user_name": company.einvoice_username,
        }

        request_body = {
            "Data": encrypted_payload
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{self.GENERATE_IRN_PATH}",
                    json=request_body,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()

                if result.get("Status") == 1:
                    # Decrypt response
                    decrypted_data = self._decrypt_response(result["Data"], self._sek)

                    # Update invoice with IRN details
                    invoice.irn = decrypted_data["Irn"]
                    invoice.ack_number = decrypted_data["AckNo"]
                    invoice.ack_date = datetime.strptime(
                        decrypted_data["AckDt"], "%Y-%m-%d %H:%M:%S"
                    )
                    invoice.irn_generated_at = datetime.now(timezone.utc)
                    invoice.signed_qr_code = decrypted_data.get("SignedQRCode")
                    invoice.signed_invoice_data = decrypted_data.get("SignedInvoice")
                    invoice.status = "IRN_GENERATED"

                    await self.db.commit()
                    await self.db.refresh(invoice)

                    return {
                        "irn": invoice.irn,
                        "ack_number": invoice.ack_number,
                        "ack_date": invoice.ack_date,
                        "signed_qr_code": invoice.signed_qr_code,
                        "status": "SUCCESS"
                    }
                else:
                    error_details = result.get("ErrorDetails", [{}])[0]
                    raise GSTEInvoiceError(
                        message=error_details.get("ErrorMessage", "IRN generation failed"),
                        error_code=error_details.get("ErrorCode"),
                        details=result
                    )

            except httpx.HTTPStatusError as e:
                raise GSTEInvoiceError(
                    message=f"IRN generation HTTP error: {e.response.status_code}",
                    details={"response": e.response.text}
                )

    async def cancel_irn(self, invoice_id: UUID, reason: str, cancel_remarks: str = "") -> Dict:
        """
        Cancel IRN within 24 hours of generation.

        Args:
            invoice_id: Invoice UUID
            reason: Cancel reason code (1-4)
                1 - Duplicate
                2 - Data entry mistake
                3 - Order cancelled
                4 - Others
            cancel_remarks: Additional remarks
        """
        await self.authenticate()

        result = await self.db.execute(
            select(TaxInvoice).where(TaxInvoice.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise GSTEInvoiceError("Invoice not found")

        if not invoice.irn:
            raise GSTEInvoiceError("No IRN to cancel")

        # Check 24-hour window
        if invoice.irn_generated_at:
            hours_elapsed = (datetime.now(timezone.utc) - invoice.irn_generated_at).total_seconds() / 3600
            if hours_elapsed > 24:
                raise GSTEInvoiceError("IRN can only be cancelled within 24 hours of generation")

        cancel_payload = {
            "Irn": invoice.irn,
            "CnlRsn": reason,
            "CnlRem": cancel_remarks or f"Cancelled: {reason}"
        }

        encrypted_payload = self._encrypt_request(cancel_payload, self._sek)

        company = await self._get_company()
        headers = {
            "Content-Type": "application/json",
            "gstin": company.gstin,
            "auth-token": self._auth_token,
            "user_name": company.einvoice_username,
        }

        request_body = {
            "Data": encrypted_payload
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{self.CANCEL_IRN_PATH}",
                    json=request_body,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()

                if result.get("Status") == 1:
                    decrypted_data = self._decrypt_response(result["Data"], self._sek)

                    invoice.irn_cancelled_at = datetime.now(timezone.utc)
                    invoice.irn_cancel_reason = cancel_remarks or reason
                    invoice.status = "IRN_CANCELLED"

                    await self.db.commit()

                    return {
                        "irn": invoice.irn,
                        "cancel_date": decrypted_data.get("CancelDate"),
                        "status": "CANCELLED"
                    }
                else:
                    error_details = result.get("ErrorDetails", [{}])[0]
                    raise GSTEInvoiceError(
                        message=error_details.get("ErrorMessage", "IRN cancellation failed"),
                        error_code=error_details.get("ErrorCode"),
                        details=result
                    )

            except httpx.HTTPStatusError as e:
                raise GSTEInvoiceError(
                    message=f"IRN cancellation HTTP error: {e.response.status_code}",
                    details={"response": e.response.text}
                )

    async def get_irn_details(self, irn: str) -> Dict:
        """Get details of an existing IRN."""
        await self.authenticate()

        company = await self._get_company()
        headers = {
            "Content-Type": "application/json",
            "gstin": company.gstin,
            "auth-token": self._auth_token,
            "user_name": company.einvoice_username,
            "irn": irn
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}{self.GET_IRN_PATH}/{irn}",
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()

                if result.get("Status") == 1:
                    return self._decrypt_response(result["Data"], self._sek)
                else:
                    error_details = result.get("ErrorDetails", [{}])[0]
                    raise GSTEInvoiceError(
                        message=error_details.get("ErrorMessage", "Failed to get IRN details"),
                        error_code=error_details.get("ErrorCode"),
                        details=result
                    )

            except httpx.HTTPStatusError as e:
                raise GSTEInvoiceError(
                    message=f"Get IRN HTTP error: {e.response.status_code}",
                    details={"response": e.response.text}
                )

    async def verify_gstin(self, gstin: str) -> Dict:
        """
        Verify a GSTIN via the E-Invoice portal.

        Returns taxpayer details if valid.
        """
        await self.authenticate()

        company = await self._get_company()
        headers = {
            "Content-Type": "application/json",
            "gstin": company.gstin,
            "auth-token": self._auth_token,
            "user_name": company.einvoice_username,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}{self.GET_GSTIN_PATH}/{gstin}",
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()

                if result.get("Status") == 1:
                    data = self._decrypt_response(result["Data"], self._sek)
                    return {
                        "gstin": data.get("Gstin"),
                        "legal_name": data.get("LegalName"),
                        "trade_name": data.get("TradeName"),
                        "address": data.get("AddrBnm"),
                        "state_code": data.get("StateCode"),
                        "pincode": data.get("AddrPncd"),
                        "status": data.get("Status"),
                        "is_valid": data.get("Status") == "Active"
                    }
                else:
                    return {
                        "gstin": gstin,
                        "is_valid": False,
                        "error": result.get("ErrorDetails", [{}])[0].get("ErrorMessage")
                    }

            except httpx.HTTPStatusError as e:
                return {
                    "gstin": gstin,
                    "is_valid": False,
                    "error": f"Verification failed: {e.response.status_code}"
                }


# Utility function for generating QR code image from signed QR data
def generate_qr_code_image(signed_qr_code: str) -> bytes:
    """
    Generate QR code image from signed QR code data.

    Returns PNG image bytes.
    """
    try:
        import qrcode
        from io import BytesIO

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(signed_qr_code)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    except ImportError:
        raise GSTEInvoiceError("qrcode library not installed. Run: pip install qrcode[pil]")

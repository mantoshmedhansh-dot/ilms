"""API endpoints for managing encrypted credentials."""
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.company import Company
from app.api.deps import DB, get_current_user
from app.schemas.credentials import (
    GSTCredentialsUpdate,
    GSTCredentialsResponse,
    EncryptRequest,
    EncryptResponse,
    TestConnectionRequest,
)
from app.services.encryption_service import (

    EncryptionService,
    CredentialManager,
    EncryptionError,
    encrypt_value,
    decrypt_value
)
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== GST Credentials ====================

@router.get("/gst", response_model=GSTCredentialsResponse)
@require_module("system_admin")
async def get_gst_credentials(
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Get GST portal credentials for a company.

    Returns masked credentials (passwords are not returned, only whether they are set).
    """
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required"
        )

    result = await db.execute(
        select(Company).where(Company.id == effective_company_id)
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return GSTCredentialsResponse(
        company_id=company.id,
        einvoice_username=company.einvoice_username,
        einvoice_password_set=bool(company.einvoice_password),
        einvoice_enabled=company.einvoice_enabled or False,
        einvoice_api_mode=company.einvoice_api_mode or "SANDBOX",
        ewaybill_username=company.ewaybill_username,
        ewaybill_password_set=bool(company.ewaybill_password),
        ewaybill_enabled=company.ewaybill_enabled or False,
        ewaybill_api_mode=company.ewaybill_api_mode or "SANDBOX",
        updated_at=company.updated_at
    )


@router.put("/gst")
@require_module("system_admin")
async def update_gst_credentials(
    credentials: GSTCredentialsUpdate,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Update GST portal credentials for a company.

    Passwords are automatically encrypted before storage.
    """
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required"
        )

    result = await db.execute(
        select(Company).where(Company.id == effective_company_id)
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    try:
        # Update E-Invoice credentials
        if credentials.einvoice_username is not None:
            company.einvoice_username = credentials.einvoice_username

        if credentials.einvoice_password is not None:
            company.einvoice_password = encrypt_value(credentials.einvoice_password)

        if credentials.einvoice_api_key is not None:
            company.einvoice_api_key = encrypt_value(credentials.einvoice_api_key)

        if credentials.einvoice_enabled is not None:
            company.einvoice_enabled = credentials.einvoice_enabled

        if credentials.einvoice_api_mode is not None:
            if credentials.einvoice_api_mode not in ["SANDBOX", "PRODUCTION"]:
                raise HTTPException(
                    status_code=400,
                    detail="API mode must be SANDBOX or PRODUCTION"
                )
            company.einvoice_api_mode = credentials.einvoice_api_mode

        # Update E-Way Bill credentials
        if credentials.ewaybill_username is not None:
            company.ewaybill_username = credentials.ewaybill_username

        if credentials.ewaybill_password is not None:
            company.ewaybill_password = encrypt_value(credentials.ewaybill_password)

        if credentials.ewaybill_app_key is not None:
            company.ewaybill_app_key = encrypt_value(credentials.ewaybill_app_key)

        if credentials.ewaybill_enabled is not None:
            company.ewaybill_enabled = credentials.ewaybill_enabled

        if credentials.ewaybill_api_mode is not None:
            if credentials.ewaybill_api_mode not in ["SANDBOX", "PRODUCTION"]:
                raise HTTPException(
                    status_code=400,
                    detail="API mode must be SANDBOX or PRODUCTION"
                )
            company.ewaybill_api_mode = credentials.ewaybill_api_mode

        await db.commit()

        return {
            "success": True,
            "message": "GST credentials updated successfully",
            "einvoice_enabled": company.einvoice_enabled,
            "ewaybill_enabled": company.ewaybill_enabled
        }

    except EncryptionError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Encryption error: {str(e)}"
        )


@router.post("/gst/test-connection")
@require_module("system_admin")
async def test_gst_connection(
    request: TestConnectionRequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Test connection to GST portal.

    Attempts to authenticate with the stored credentials.
    """
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required"
        )

    if request.portal_type not in ["EINVOICE", "EWAYBILL"]:
        raise HTTPException(
            status_code=400,
            detail="portal_type must be EINVOICE or EWAYBILL"
        )

    try:
        if request.portal_type == "EINVOICE":
            from app.services.gst_einvoice_service import GSTEInvoiceService, GSTEInvoiceError
            service = GSTEInvoiceService(db, effective_company_id)
            await service.authenticate()
            return {
                "success": True,
                "portal": "E-Invoice",
                "message": "Successfully authenticated with NIC E-Invoice portal",
                "mode": service._company.einvoice_api_mode if service._company else "SANDBOX"
            }
        else:
            from app.services.gst_ewaybill_service import GSTEWayBillService, GSTEWayBillError

            service = GSTEWayBillService(db, effective_company_id)
            await service.authenticate()
            return {
                "success": True,
                "portal": "E-Way Bill",
                "message": "Successfully authenticated with NIC E-Way Bill portal",
                "mode": service._company.ewaybill_api_mode if service._company else "SANDBOX"
            }

    except Exception as e:
        return {
            "success": False,
            "portal": request.portal_type,
            "message": f"Connection failed: {str(e)}",
            "error": str(e)
        }


@router.delete("/gst")
@require_module("system_admin")
async def clear_gst_credentials(
    db: DB,
    portal_type: str,  # EINVOICE, EWAYBILL, or ALL
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Clear GST portal credentials.

    Use with caution - this will remove stored credentials.
    """
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required"
        )

    result = await db.execute(
        select(Company).where(Company.id == effective_company_id)
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if portal_type in ["EINVOICE", "ALL"]:
        company.einvoice_username = None
        company.einvoice_password = None
        company.einvoice_api_key = None
        company.einvoice_enabled = False

    if portal_type in ["EWAYBILL", "ALL"]:
        company.ewaybill_username = None
        company.ewaybill_password = None
        company.ewaybill_app_key = None
        company.ewaybill_enabled = False

    await db.commit()

    return {
        "success": True,
        "message": f"Credentials cleared for {portal_type}"
    }


# ==================== Encryption Utilities (Admin Only) ====================

@router.post("/encrypt", response_model=EncryptResponse)
@require_module("system_admin")
async def encrypt_value_endpoint(
    request: EncryptRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Encrypt a value.

    Admin utility for encrypting values before storage.
    """
    # Check if user is admin (you may want to add proper role check)
    try:
        encrypted = encrypt_value(request.value)
        return EncryptResponse(
            encrypted=encrypted,
            is_encrypted=True
        )
    except EncryptionError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Encryption failed: {str(e)}"
        )


@router.post("/verify-encrypted")
@require_module("system_admin")
async def verify_encrypted_value(
    encrypted_value: str,
    current_user: User = Depends(get_current_user),
):
    """
    Verify that an encrypted value can be decrypted.

    Does not return the decrypted value, only confirms it's valid.
    """
    try:
        decrypted = decrypt_value(encrypted_value)
        return {
            "valid": True,
            "is_encrypted": encrypted_value.startswith("ENC:"),
            "decrypted_length": len(decrypted)
        }
    except EncryptionError:
        return {
            "valid": False,
            "error": "Unable to decrypt value"
        }

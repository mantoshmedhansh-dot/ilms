"""File upload endpoints."""
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from app.schemas.upload import (
    UploadCategory,
    UploadResponse,
    MultiUploadResponse,
    DeleteRequest,
    DeleteResponse,
)
from app.services.upload_service import UploadService, UploadError
from app.api.deps import get_current_user
from app.core.module_decorators import require_module

router = APIRouter()


@router.post("/image", response_model=UploadResponse)
@require_module("system_admin")
async def upload_image(
    file: UploadFile = File(..., description="Image file to upload"),
    category: UploadCategory = Form(UploadCategory.LOGOS, description="Upload category"),
    current_user=Depends(get_current_user),
):
    """
    Upload a single image file.

    Supported formats: JPEG, PNG, WebP, SVG
    Maximum size: 5MB

    Returns the public URL and thumbnail URL (for non-SVG images).
    """
    try:
        # Read file content
        content = await file.read()

        # Get content type
        content_type = file.content_type or "application/octet-stream"

        # Upload
        result = await UploadService.upload_image(
            content=content,
            filename=file.filename or "image",
            content_type=content_type,
            category=category,
        )

        return UploadResponse(**result)

    except UploadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/images", response_model=MultiUploadResponse)
@require_module("system_admin")
async def upload_images(
    files: List[UploadFile] = File(..., description="Image files to upload"),
    category: UploadCategory = Form(UploadCategory.PRODUCTS, description="Upload category"),
    current_user=Depends(get_current_user),
):
    """
    Upload multiple image files.

    Maximum: 10 files
    Supported formats: JPEG, PNG, WebP, SVG
    Maximum size per file: 5MB

    Returns list of public URLs and thumbnail URLs.
    """
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed")

    try:
        # Read all files
        file_data = []
        for file in files:
            content = await file.read()
            content_type = file.content_type or "application/octet-stream"
            filename = file.filename or "image"
            file_data.append((content, filename, content_type))

        # Upload all
        results = await UploadService.upload_images(file_data, category)

        return MultiUploadResponse(
            files=[UploadResponse(**r) for r in results],
            total=len(results),
        )

    except UploadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/document", response_model=UploadResponse)
@require_module("system_admin")
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    category: UploadCategory = Form(UploadCategory.DOCUMENTS, description="Upload category"),
    current_user=Depends(get_current_user),
):
    """
    Upload a document file.

    Supported formats: PDF
    Maximum size: 10MB

    Returns the public URL.
    """
    try:
        # Read file content
        content = await file.read()

        # Get content type
        content_type = file.content_type or "application/octet-stream"

        # Upload
        result = await UploadService.upload_document(
            content=content,
            filename=file.filename or "document.pdf",
            content_type=content_type,
            category=category,
        )

        return UploadResponse(**result)

    except UploadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.delete("", response_model=DeleteResponse)
@require_module("system_admin")
async def delete_file(
    request: DeleteRequest,
    current_user=Depends(get_current_user),
):
    """
    Delete a file by its URL.

    Only files in the configured storage bucket can be deleted.
    """
    try:
        success = await UploadService.delete_file(request.url)

        if success:
            return DeleteResponse(success=True, message="File deleted successfully")
        else:
            return DeleteResponse(success=False, message="File not found or already deleted")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

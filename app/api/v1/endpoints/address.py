"""
Address Lookup API Endpoints

Provides address autocomplete and lookup functionality for D2C storefront:
- Google Places Autocomplete
- Place details lookup
- DigiPin encoding/decoding
- Reverse geocoding
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from app.services.address_service import (

    address_service,
    AddressSuggestion,
    AddressDetails,
    DigiPinInfo,
)
from app.core.module_decorators import require_module

router = APIRouter()


# Request/Response schemas
class AutocompleteRequest(BaseModel):
    """Request for address autocomplete."""
    query: str = Field(..., min_length=3, description="Search query")
    session_token: Optional[str] = Field(None, description="Session token for billing optimization")


class AutocompleteResponse(BaseModel):
    """Response for address autocomplete."""
    suggestions: List[AddressSuggestion]


class PlaceDetailsRequest(BaseModel):
    """Request for place details."""
    place_id: str = Field(..., description="Google Place ID")
    session_token: Optional[str] = Field(None, description="Session token")


class DigiPinRequest(BaseModel):
    """Request for DigiPin lookup."""
    digipin: str = Field(..., min_length=10, max_length=12, description="DigiPin code")


class CoordinatesRequest(BaseModel):
    """Request for reverse geocoding."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")


class PincodeRequest(BaseModel):
    """Request for pincode lookup."""
    pincode: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$", description="6-digit pincode")


class PincodeResponse(BaseModel):
    """Response for pincode lookup."""
    pincode: str
    city: Optional[str]
    state: Optional[str]
    areas: Optional[List[str]]


# API Endpoints

@router.get("/autocomplete", response_model=AutocompleteResponse)
@require_module("system_admin")
async def autocomplete_address(
    query: str = Query(..., min_length=3, description="Address search query"),
    session_token: Optional[str] = Query(None, description="Session token for billing")
):
    """
    Get address suggestions using Google Places Autocomplete.

    This endpoint returns address suggestions as the user types.
    Use session_token to group autocomplete requests for billing optimization.

    Example:
        GET /api/v1/address/autocomplete?query=sector 62 noida
    """
    suggestions = await address_service.autocomplete(query, session_token)
    return AutocompleteResponse(suggestions=suggestions)


@router.get("/place/{place_id}", response_model=AddressDetails)
@require_module("system_admin")
async def get_place_details(
    place_id: str,
    session_token: Optional[str] = Query(None, description="Session token")
):
    """
    Get full address details from a Google Place ID.

    Returns structured address with all components (line1, line2, city, state, pincode).
    Also includes DigiPin code if coordinates are available.

    Example:
        GET /api/v1/address/place/ChIJxxxxxxxxxx
    """
    details = await address_service.get_place_details(place_id, session_token)
    if not details:
        raise HTTPException(status_code=404, detail="Place not found")
    return details


@router.post("/place", response_model=AddressDetails)
@require_module("system_admin")
async def get_place_details_post(request: PlaceDetailsRequest):
    """
    Get full address details from a Google Place ID (POST version).

    Same as GET /place/{place_id} but accepts POST request with body.
    """
    details = await address_service.get_place_details(
        request.place_id,
        request.session_token
    )
    if not details:
        raise HTTPException(status_code=404, detail="Place not found")
    return details


@router.get("/digipin/{digipin}", response_model=DigiPinInfo)
@require_module("system_admin")
async def lookup_digipin(digipin: str):
    """
    Get location info from a DigiPin code.

    DigiPin is India's digital addressing system that provides a unique
    10-character code for any location. This endpoint decodes the DigiPin
    to get coordinates and address.

    Example:
        GET /api/v1/address/digipin/4H8J9K2M3P
    """
    info = await address_service.get_coordinates_from_digipin(digipin)
    if not info:
        raise HTTPException(status_code=400, detail="Invalid DigiPin code")
    return info


@router.post("/digipin", response_model=DigiPinInfo)
@require_module("system_admin")
async def lookup_digipin_post(request: DigiPinRequest):
    """
    Get location info from a DigiPin code (POST version).
    """
    info = await address_service.get_coordinates_from_digipin(request.digipin)
    if not info:
        raise HTTPException(status_code=400, detail="Invalid DigiPin code")
    return info


@router.post("/reverse-geocode", response_model=AddressDetails)
@require_module("system_admin")
async def reverse_geocode(request: CoordinatesRequest):
    """
    Get address from coordinates (latitude/longitude).

    Useful when user shares their current location.
    Returns full address details including DigiPin.

    Example:
        POST /api/v1/address/reverse-geocode
        {"latitude": 28.6139, "longitude": 77.2090}
    """
    details = await address_service.reverse_geocode(
        request.latitude,
        request.longitude
    )
    if not details:
        raise HTTPException(status_code=404, detail="Could not resolve address")
    return details


@router.get("/reverse-geocode", response_model=AddressDetails)
@require_module("system_admin")
async def reverse_geocode_get(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180)
):
    """
    Get address from coordinates (GET version).

    Example:
        GET /api/v1/address/reverse-geocode?latitude=28.6139&longitude=77.2090
    """
    details = await address_service.reverse_geocode(latitude, longitude)
    if not details:
        raise HTTPException(status_code=404, detail="Could not resolve address")
    return details


@router.get("/pincode/{pincode}", response_model=PincodeResponse)
@require_module("system_admin")
async def lookup_pincode(pincode: str):
    """
    Get city and state from Indian pincode.

    Useful for auto-filling city/state when user enters pincode.

    Example:
        GET /api/v1/address/pincode/201301
    """
    if not pincode.isdigit() or len(pincode) != 6:
        raise HTTPException(status_code=400, detail="Invalid pincode format")

    info = await address_service.get_address_from_pincode(pincode)
    if not info:
        raise HTTPException(status_code=404, detail="Pincode not found")

    return PincodeResponse(
        pincode=info["pincode"],
        city=info.get("city"),
        state=info.get("state"),
        areas=[a for a in info.get("areas", []) if a],
    )


@router.post("/encode-digipin", response_model=DigiPinInfo)
@require_module("system_admin")
async def encode_digipin(request: CoordinatesRequest):
    """
    Generate DigiPin code from coordinates.

    Returns the DigiPin code for the given latitude/longitude.

    Example:
        POST /api/v1/address/encode-digipin
        {"latitude": 28.6139, "longitude": 77.2090}
    """
    info = await address_service.get_digipin_from_coordinates(
        request.latitude,
        request.longitude
    )
    if not info:
        raise HTTPException(status_code=500, detail="Failed to generate DigiPin")
    return info

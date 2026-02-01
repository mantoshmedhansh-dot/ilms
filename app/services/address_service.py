"""
Address Service - Google Places & DigiPin Integration

Provides address lookup functionality for the D2C storefront:
- Google Places Autocomplete for address suggestions
- Google Place Details for full address info
- DigiPin lookup and reverse lookup
- Pincode to location mapping
"""

import logging
import httpx
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.config import settings

logger = logging.getLogger(__name__)


# Request/Response Models
class AddressSuggestion(BaseModel):
    """Address suggestion from autocomplete."""
    place_id: str
    description: str
    main_text: str
    secondary_text: str


class AddressDetails(BaseModel):
    """Full address details."""
    place_id: Optional[str] = None
    formatted_address: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    pincode: str
    country: str = "India"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    digipin: Optional[str] = None


class DigiPinInfo(BaseModel):
    """DigiPin information."""
    digipin: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


class AddressService:
    """
    Service for address lookup using Google Places and DigiPin.
    """

    def __init__(self):
        self.google_api_key = settings.GOOGLE_MAPS_API_KEY
        self.country_restriction = settings.GOOGLE_PLACES_COUNTRY_RESTRICTION
        self.digipin_api_url = settings.DIGIPIN_API_URL
        self.digipin_api_key = settings.DIGIPIN_API_KEY

    async def autocomplete(
        self,
        query: str,
        session_token: Optional[str] = None
    ) -> List[AddressSuggestion]:
        """
        Get address suggestions using Google Places Autocomplete.

        Args:
            query: User's input text
            session_token: Optional session token for billing optimization

        Returns:
            List of address suggestions
        """
        if not self.google_api_key:
            logger.warning("Google Maps API key not configured")
            return []

        if len(query) < 3:
            return []

        try:
            url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
            params = {
                "input": query,
                "key": self.google_api_key,
                "components": f"country:{self.country_restriction}",
                "types": "address",
                "language": "en",
            }
            if session_token:
                params["sessiontoken"] = session_token

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                data = response.json()

            if data.get("status") != "OK":
                logger.warning(f"Google Places API error: {data.get('status')}")
                return []

            suggestions = []
            for prediction in data.get("predictions", []):
                structured = prediction.get("structured_formatting", {})
                suggestions.append(AddressSuggestion(
                    place_id=prediction["place_id"],
                    description=prediction["description"],
                    main_text=structured.get("main_text", prediction["description"]),
                    secondary_text=structured.get("secondary_text", ""),
                ))

            return suggestions

        except Exception as e:
            logger.error(f"Address autocomplete error: {e}")
            return []

    async def get_place_details(
        self,
        place_id: str,
        session_token: Optional[str] = None
    ) -> Optional[AddressDetails]:
        """
        Get full address details from Google Place ID.

        Args:
            place_id: Google Place ID
            session_token: Optional session token

        Returns:
            AddressDetails or None
        """
        if not self.google_api_key:
            logger.warning("Google Maps API key not configured")
            return None

        try:
            url = "https://maps.googleapis.com/maps/api/place/details/json"
            params = {
                "place_id": place_id,
                "key": self.google_api_key,
                "fields": "formatted_address,address_components,geometry",
                "language": "en",
            }
            if session_token:
                params["sessiontoken"] = session_token

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                data = response.json()

            if data.get("status") != "OK":
                logger.warning(f"Google Place Details API error: {data.get('status')}")
                return None

            result = data.get("result", {})
            components = result.get("address_components", [])
            geometry = result.get("geometry", {}).get("location", {})

            # Parse address components
            address_parts = self._parse_address_components(components)

            # Build address line 1 (street number + route)
            address_line1_parts = []
            if address_parts.get("subpremise"):
                address_line1_parts.append(address_parts["subpremise"])
            if address_parts.get("premise"):
                address_line1_parts.append(address_parts["premise"])
            if address_parts.get("street_number"):
                address_line1_parts.append(address_parts["street_number"])
            if address_parts.get("route"):
                address_line1_parts.append(address_parts["route"])

            address_line1 = ", ".join(address_line1_parts) if address_line1_parts else ""

            # Build address line 2 (sublocality, locality)
            address_line2_parts = []
            if address_parts.get("sublocality_level_2"):
                address_line2_parts.append(address_parts["sublocality_level_2"])
            if address_parts.get("sublocality_level_1"):
                address_line2_parts.append(address_parts["sublocality_level_1"])
            if address_parts.get("neighborhood"):
                address_line2_parts.append(address_parts["neighborhood"])

            address_line2 = ", ".join(address_line2_parts) if address_line2_parts else None

            # If address_line1 is empty, use sublocality as line 1
            if not address_line1 and address_line2:
                address_line1 = address_line2
                address_line2 = None

            city = (
                address_parts.get("locality") or
                address_parts.get("administrative_area_level_2") or
                address_parts.get("sublocality_level_1") or
                ""
            )

            state = address_parts.get("administrative_area_level_1", "")
            pincode = address_parts.get("postal_code", "")

            # Get DigiPin if we have coordinates
            digipin = None
            if geometry.get("lat") and geometry.get("lng"):
                digipin_info = await self.get_digipin_from_coordinates(
                    geometry["lat"],
                    geometry["lng"]
                )
                if digipin_info:
                    digipin = digipin_info.digipin

            return AddressDetails(
                place_id=place_id,
                formatted_address=result.get("formatted_address", ""),
                address_line1=address_line1,
                address_line2=address_line2,
                city=city,
                state=state,
                pincode=pincode,
                country="India",
                latitude=geometry.get("lat"),
                longitude=geometry.get("lng"),
                digipin=digipin,
            )

        except Exception as e:
            logger.error(f"Get place details error: {e}")
            return None

    def _parse_address_components(self, components: List[Dict]) -> Dict[str, str]:
        """Parse Google address components into a flat dict."""
        result = {}
        for component in components:
            types = component.get("types", [])
            value = component.get("long_name", "")

            if "street_number" in types:
                result["street_number"] = value
            elif "route" in types:
                result["route"] = value
            elif "premise" in types:
                result["premise"] = value
            elif "subpremise" in types:
                result["subpremise"] = value
            elif "neighborhood" in types:
                result["neighborhood"] = value
            elif "sublocality_level_2" in types:
                result["sublocality_level_2"] = value
            elif "sublocality_level_1" in types:
                result["sublocality_level_1"] = value
            elif "sublocality" in types:
                result["sublocality"] = value
            elif "locality" in types:
                result["locality"] = value
            elif "administrative_area_level_2" in types:
                result["administrative_area_level_2"] = value
            elif "administrative_area_level_1" in types:
                result["administrative_area_level_1"] = value
            elif "postal_code" in types:
                result["postal_code"] = value
            elif "country" in types:
                result["country"] = value

        return result

    async def get_digipin_from_coordinates(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[DigiPinInfo]:
        """
        Get DigiPin code from latitude/longitude.

        DigiPin is India's digital addressing system that provides
        a unique 10-character alphanumeric code for any location.

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            DigiPinInfo or None
        """
        try:
            # DigiPin encoding algorithm
            # DigiPin uses a grid-based system to encode lat/lng into a 10-char code
            digipin = self._encode_digipin(latitude, longitude)

            return DigiPinInfo(
                digipin=digipin,
                latitude=latitude,
                longitude=longitude,
            )

        except Exception as e:
            logger.error(f"DigiPin encoding error: {e}")
            return None

    async def get_coordinates_from_digipin(
        self,
        digipin: str
    ) -> Optional[DigiPinInfo]:
        """
        Get coordinates from DigiPin code.

        Args:
            digipin: 10-character DigiPin code

        Returns:
            DigiPinInfo with coordinates or None
        """
        try:
            # Validate DigiPin format
            digipin = digipin.upper().replace("-", "").replace(" ", "")
            if len(digipin) != 10:
                logger.warning(f"Invalid DigiPin format: {digipin}")
                return None

            # Decode DigiPin to coordinates
            coords = self._decode_digipin(digipin)
            if not coords:
                return None

            latitude, longitude = coords

            # Reverse geocode to get address
            address_details = await self.reverse_geocode(latitude, longitude)

            return DigiPinInfo(
                digipin=digipin,
                latitude=latitude,
                longitude=longitude,
                address=address_details.formatted_address if address_details else None,
                city=address_details.city if address_details else None,
                state=address_details.state if address_details else None,
                pincode=address_details.pincode if address_details else None,
            )

        except Exception as e:
            logger.error(f"DigiPin decode error: {e}")
            return None

    def _encode_digipin(self, latitude: float, longitude: float) -> str:
        """
        Encode latitude/longitude to DigiPin format.

        DigiPin uses a modified geohash-like algorithm with custom character set.
        India bounds: Lat 6.5-37.5, Lng 68-97.5

        Format: XXX-XXX-XXXX (10 chars without hyphens)
        """
        # DigiPin character set (excludes confusing chars like 0,O,1,I,L)
        CHARS = "23456789CFGHJMPQRVWX"
        base = len(CHARS)

        # India bounding box
        lat_min, lat_max = 6.5, 37.5
        lng_min, lng_max = 68.0, 97.5

        # Normalize to 0-1 range
        lat_norm = (latitude - lat_min) / (lat_max - lat_min)
        lng_norm = (longitude - lng_min) / (lng_max - lng_min)

        # Clamp values
        lat_norm = max(0, min(1, lat_norm))
        lng_norm = max(0, min(1, lng_norm))

        # Encode using interleaved bits
        digipin = ""
        for i in range(10):
            # Alternate between longitude and latitude
            if i % 2 == 0:
                idx = int(lng_norm * base)
                lng_norm = (lng_norm * base) - idx
            else:
                idx = int(lat_norm * base)
                lat_norm = (lat_norm * base) - idx

            idx = min(idx, base - 1)
            digipin += CHARS[idx]

        return digipin

    def _decode_digipin(self, digipin: str) -> Optional[tuple]:
        """
        Decode DigiPin to latitude/longitude.

        Returns:
            Tuple of (latitude, longitude) or None
        """
        CHARS = "23456789CFGHJMPQRVWX"
        base = len(CHARS)

        # India bounding box
        lat_min, lat_max = 6.5, 37.5
        lng_min, lng_max = 68.0, 97.5

        try:
            lat_norm = 0.0
            lng_norm = 0.0

            for i, char in enumerate(digipin):
                idx = CHARS.index(char.upper())
                if i % 2 == 0:
                    lng_norm = lng_norm + idx / (base ** (i // 2 + 1))
                else:
                    lat_norm = lat_norm + idx / (base ** ((i + 1) // 2))

            latitude = lat_min + lat_norm * (lat_max - lat_min)
            longitude = lng_min + lng_norm * (lng_max - lng_min)

            return (latitude, longitude)

        except ValueError:
            return None

    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[AddressDetails]:
        """
        Get address from coordinates using Google Geocoding API.

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            AddressDetails or None
        """
        if not self.google_api_key:
            logger.warning("Google Maps API key not configured")
            return None

        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "latlng": f"{latitude},{longitude}",
                "key": self.google_api_key,
                "language": "en",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                data = response.json()

            if data.get("status") != "OK":
                logger.warning(f"Google Geocoding API error: {data.get('status')}")
                return None

            results = data.get("results", [])
            if not results:
                return None

            # Use the first result
            result = results[0]
            components = result.get("address_components", [])

            address_parts = self._parse_address_components(components)

            # Build address lines
            address_line1_parts = []
            if address_parts.get("premise"):
                address_line1_parts.append(address_parts["premise"])
            if address_parts.get("street_number"):
                address_line1_parts.append(address_parts["street_number"])
            if address_parts.get("route"):
                address_line1_parts.append(address_parts["route"])

            address_line1 = ", ".join(address_line1_parts) if address_line1_parts else ""

            address_line2_parts = []
            if address_parts.get("sublocality_level_1"):
                address_line2_parts.append(address_parts["sublocality_level_1"])
            if address_parts.get("neighborhood"):
                address_line2_parts.append(address_parts["neighborhood"])

            address_line2 = ", ".join(address_line2_parts) if address_line2_parts else None

            if not address_line1 and address_line2:
                address_line1 = address_line2
                address_line2 = None

            city = (
                address_parts.get("locality") or
                address_parts.get("administrative_area_level_2") or
                ""
            )
            state = address_parts.get("administrative_area_level_1", "")
            pincode = address_parts.get("postal_code", "")

            # Get DigiPin
            digipin = self._encode_digipin(latitude, longitude)

            return AddressDetails(
                formatted_address=result.get("formatted_address", ""),
                address_line1=address_line1,
                address_line2=address_line2,
                city=city,
                state=state,
                pincode=pincode,
                country="India",
                latitude=latitude,
                longitude=longitude,
                digipin=digipin,
            )

        except Exception as e:
            logger.error(f"Reverse geocode error: {e}")
            return None

    async def get_address_from_pincode(
        self,
        pincode: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get city, state info from Indian pincode.

        Args:
            pincode: 6-digit Indian pincode

        Returns:
            Dict with city, state, and area info
        """
        if not self.google_api_key:
            # Fallback to India Post data or return None
            return None

        try:
            # Use Google Geocoding with pincode
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": f"{pincode}, India",
                "key": self.google_api_key,
                "language": "en",
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                data = response.json()

            if data.get("status") != "OK":
                return None

            results = data.get("results", [])
            if not results:
                return None

            result = results[0]
            components = result.get("address_components", [])
            address_parts = self._parse_address_components(components)

            return {
                "pincode": pincode,
                "city": address_parts.get("locality") or address_parts.get("administrative_area_level_2"),
                "state": address_parts.get("administrative_area_level_1"),
                "areas": [
                    address_parts.get("sublocality_level_1"),
                    address_parts.get("sublocality_level_2"),
                ],
            }

        except Exception as e:
            logger.error(f"Pincode lookup error: {e}")
            return None


# Singleton instance
address_service = AddressService()

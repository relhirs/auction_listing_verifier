import httpx
from pydantic import BaseModel
from typing import Optional


# --- Data Model ---
class VINData(BaseModel):
    vin: str
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    engine_displacement: Optional[str] = None
    engine_cylinders: Optional[str] = None
    engine_hp: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    drive_type: Optional[str] = None
    body_style: Optional[str] = None
    plant_country: Optional[str] = None
    decode_error: Optional[str] = None  # set when NHTSA couldn't decode this VIN, or the request failed
    pre_standard_vin: bool = False  # True when decode_error is due to the VIN predating the 17-char
    # standard (1981+), not a system/request failure -- see verify_vin's length check below. Lets
    # core/verifier.py distinguish "couldn't verify due to an error" from "no data exists for this era."


# --- Helper: convert empty strings to None ---
def clean(value: str) -> Optional[str]:
    return value.strip() if value and value.strip() else None


# --- Main function ---
def verify_vin(vin: str) -> VINData:
    # NHTSA's decoder is built for the 17-character VIN format standardized
    # in 1981 -- a shorter/non-standard VIN means decode data simply
    # doesn't exist for this vehicle (it predates the standard), not that a
    # request or the system failed. Checked locally, before ever calling
    # NHTSA, since it's a purely mechanical fact about the VIN itself and
    # avoids wasting a call NHTSA will reject anyway. Confirmed empirically
    # against a real 9-character pre-1981 VIN: NHTSA does respond (not a
    # network failure) but rejects it outright ("Incomplete VIN", "Invalid
    # Characters Present") -- this is a real, observed failure mode, not a
    # hypothetical.
    if len(vin.strip()) != 17:
        return VINData(
            vin=vin,
            decode_error=(
                "This VIN is not in the standard 17-character format used since "
                "1981, so no NHTSA decode data exists for it. This typically means "
                "the vehicle predates VIN standardization -- a data-availability "
                "gap, not a system or request error."
            ),
            pre_standard_vin=True,
        )

    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"

    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as e:
        return VINData(vin=vin, decode_error=f"NHTSA request failed: {e}")

    results = response.json().get("Results", [])

    # Convert list of {Variable, Value} dicts into a flat lookup dict
    data = {item["Variable"]: item["Value"] for item in results}

    # Helper to safely extract and clean a field
    def get(key: str) -> Optional[str]:
        return clean(data.get(key, ""))

    # NHTSA reports its own decode success/failure via "Error Code" ("0" = clean
    # decode). A non-"0" code (or a message-only failure with no code at all)
    # means the VIN itself is malformed/undecodable, distinct from "NHTSA just
    # didn't have this particular field" for an otherwise-valid VIN.
    error_code = get("Error Code")
    error_text = get("Error Text")
    decode_error = None
    if error_code and error_code != "0":
        decode_error = error_text or f"NHTSA reported error code {error_code}"
    elif not results:
        decode_error = "NHTSA returned no results for this VIN"

    # Year needs to be an int or None
    raw_year = get("Model Year")
    year = int(raw_year) if raw_year and raw_year.isdigit() else None

    vin_data = VINData(
        vin=vin,
        make=get("Make"),
        model=get("Model"),
        year=year,
        engine_displacement=get("Displacement (L)"),
        engine_cylinders=get("Engine Number of Cylinders"),
        engine_hp=get("Engine Brake (hp) From"),
        fuel_type=get("Fuel Type - Primary"),
        transmission=get("Transmission Style"),
        drive_type=get("Drive Type"),
        body_style=get("Body Class"),
        plant_country=get("Plant Country"),
        decode_error=decode_error,
    )

    return vin_data


# --- Quick test ---
if __name__ == "__main__":
    # BMW M3 from previous listing
    vin = "3TMLB5JN9SM096273"
    result = verify_vin(vin)
    print(result.model_dump_json(indent=2))
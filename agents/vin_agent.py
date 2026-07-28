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


# --- Helper: convert empty strings to None ---
def clean(value: str) -> Optional[str]:
    return value.strip() if value and value.strip() else None


# --- Main function ---
def verify_vin(vin: str) -> VINData:
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"

    response = httpx.get(url, timeout=10)
    response.raise_for_status()

    results = response.json().get("Results", [])

    # Convert list of {Variable, Value} dicts into a flat lookup dict
    data = {item["Variable"]: item["Value"] for item in results}

    # Helper to safely extract and clean a field
    def get(key: str) -> Optional[str]:
        return clean(data.get(key, ""))

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
    )

    return vin_data


# --- Quick test ---
if __name__ == "__main__":
    # BMW M3 from previous listing
    vin = "3TMLB5JN9SM096273"
    result = verify_vin(vin)
    print(result.model_dump_json(indent=2))
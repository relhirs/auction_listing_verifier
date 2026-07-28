import anthropic
import instructor
from pydantic import BaseModel, Field
from typing import Optional


# --- Data Model ---
class ListingData(BaseModel):
    make: str = Field(description="The manufacturer of the vehicle, e.g. Toyota, Ford")
    model: str = Field(description="The model name, e.g. Camry, F-150")
    year: int = Field(description="The model year as a 4-digit integer, e.g. 2019")
    mileage: Optional[int] = Field(description="Odometer reading in miles as an integer, e.g. 45000")
    color: Optional[str] = Field(description="Exterior color of the vehicle")
    vin: Optional[str] = Field(description="The 17-character Vehicle Identification Number")
    engine: Optional[str] = Field(description="Engine description, e.g. 2.5L 4-cylinder, 5.0L V8")
    transmission: Optional[str] = Field(description="Transmission type, e.g. automatic, manual, CVT")
    asking_price: Optional[int] = Field(description="The seller's asking price in dollars as an integer, no symbols")
    seller_description: str = Field(description="The full original listing text, copied verbatim")


# --- Instructor-wrapped Anthropic client ---
client = instructor.from_anthropic(anthropic.Anthropic())


# --- Extraction function ---
def extract_listing(raw_text: str) -> tuple[ListingData, int, int]:
    listing_data, raw = client.messages.create_with_completion(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"""You are a structured data extraction engine for used car listings.

Extract the vehicle details from the listing below. Follow these rules strictly:
- year must be a 4-digit integer (e.g. 2019, not '19)
- mileage must be an integer with no commas or symbols (e.g. 45000, not 45,000)
- asking_price must be an integer with no commas or symbols (e.g. 12500, not $12,500)
- year must be a 4-digit integer (e.g. 2019, not '19)
- mileage must be an integer with no commas or symbols (e.g. 45000, not 45,000)
- asking_price must be an integer with no commas or symbols (e.g. 12500, not $12,500). If this is an auction listing with no fixed price, return null
- transmission must be normalized to just the type: "automatic", "manual", or "cvt" — strip any gear count or extra details
- color should be the exterior color exactly as listed, including manufacturer color names (e.g. "Yas Marina Blue Metallic")
- seller_description must be the full original listing text, copied exactly- seller_description must be the full original listing text, copied exactly

Listing:
{raw_text}"""
            }
        ],
        response_model=ListingData,
    )
    return listing_data, raw.usage.input_tokens, raw.usage.output_tokens


# --- Quick test ---
if __name__ == "__main__":
   if __name__ == "__main__":
    sample = """ Make
Lotus
Engine
3.5L Supercharged V6
Model
Emira
Save
Drivetrain
Rear-wheel drive
Mileage
700
Transmission
Manual (6-Speed)
VIN
SCCLEKAX9RHB11345
Body Style
Coupe
Title Status
Clean (CT)
Exterior Color
Hethel Yellow
Location
Avon, CT 06001
Interior Color
Ice Grey
Seller
Newtsie
Newtsie
Seller Type
Private Party
Highlights
THIS... is a 2024 Lotus Emira V6 First Edition, finished in Hethel Yellow with an Ice Grey interior.

This Emira is equipped with the desirable 6-speed manual transmission, and the odometer currently indicates 700 miles.
The attached Carfax vehicle history report lists no accidents or mileage discrepancies in this Lotus's past.
According to the window sticker provided in the gallery, this Emira is a First Edition model, and notable factory equipment includes the Full Black Pack, 20-inch diamond-cut forged wheels, yellow brake calipers, heated seats, and Apple CarPlay and Android Auto connectivity. The seller reports no notable modifications
Lotus launched the two-seater Emira for the 2022 model year. The coupe falls in line with the brand's famous "light is right" philosophy thanks in part to a bonded aluminum chassis, and it's offered with either a Toyota-derived supercharged V6 or an AMG-sourced turbocharged 4-cylinder. Light doesn't necessarily mean bare-bones, however, and the Emira is available with more comfort and technology features than earlier Lotus sports cars.
Power comes from a 3.5-liter supercharged V6, rated at 400 horsepower and 310 lb-ft of torque. Output is sent to the rear wheels via a 6-speed manual transmission.
Equipment
This Emira is a First Edition model. A window sticker is provided in the photo gallery, and a partial list of notable equipment reported by the seller includes:

Full Black Pack
20-inch diamond-cut forged wheels
Yellow brake calipers
Automatic LED headlights
Heated seats
Dual-zone climate control
Apple CarPlay and Android Auto connectivity
Recent Service History
The attached Carfax vehicle history report indicates that the following maintenance has been performed:

September 2024 (46 miles): Battery replaced
May 2024 (24 miles): Charcoal/vapor canister replaced
Other Items Included in Sale
2 keys
Owner's manual
Window sticker
Ownership History
The seller reports that they purchased this Lotus when new in September 2024.

Seller Notes
The seller notes that paint protection film has been applied to the front end.
"""
    result = extract_listing(sample)
    print(result.model_dump_json(indent=2))

    
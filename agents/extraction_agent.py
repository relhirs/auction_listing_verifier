import anthropic
import instructor
from pydantic import BaseModel, Field
from typing import Optional

from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request


# --- Data Model ---
class ListingData(BaseModel):
    make: str = Field(description="The manufacturer of the vehicle, e.g. Toyota, Ford")
    model: str = Field(description="The model name, e.g. Camry, F-150")
    year: int = Field(description="The model year as a 4-digit integer, e.g. 2019")
    mileage: Optional[int] = Field(description="Vehicle mileage in miles as stated in the listing, as an integer, e.g. 45000")
    color: Optional[str] = Field(description="Exterior color of the vehicle")
    vin: Optional[str] = Field(description="The 17-character Vehicle Identification Number")
    engine: Optional[str] = Field(description="Engine description, e.g. 2.5L 4-cylinder, 5.0L V8")
    transmission: Optional[str] = Field(description="Transmission type, e.g. automatic, manual, CVT")
    drivetrain: Optional[str] = Field(description="Drivetrain, normalized to one of: RWD, AWD, FWD, 4WD")
    trim: Optional[str] = Field(description="Trim level, e.g. Base, Sport, Limited, or null if not stated")
    interior_color: Optional[str] = Field(description="Interior color of the vehicle")
    modifications: list[str] = Field(default_factory=list, description="Explicit modifications claimed by the seller; empty list if the seller states there are none or doesn't mention any")
    asking_price: Optional[int] = Field(description="The seller's asking price in dollars as an integer, no symbols")
    seller_description: str = Field(description="The full original listing text, copied verbatim")


# --- Instructor-wrapped Anthropic client ---
# raw_client is kept alongside the instructor-wrapped client because Instructor's
# wrapper doesn't expose .messages.batches (needed by build_batch_request below).
raw_client = anthropic.Anthropic()
client = instructor.from_anthropic(raw_client)


def _extraction_prompt(raw_text: str) -> str:
    return f"""You are a structured data extraction engine for used car listings.

Extract the vehicle details from the listing below. Follow these rules strictly:
- year must be a 4-digit integer (e.g. 2019, not '19)
- mileage must be an integer with no commas or symbols (e.g. 45000, not 45,000)
- asking_price must be an integer with no commas or symbols (e.g. 12500, not $12,500). If this is an auction listing with no fixed price, return null
- transmission must be normalized to just the type: "automatic", "manual", or "cvt" — strip any gear count or extra details
- drivetrain must be extracted literally from the listing's labeled "Drivetrain" field, normalized to one of: "RWD", "AWD", "FWD", "4WD" (e.g. "Rear-wheel drive" -> "RWD") — even if it looks inconsistent with the engine description, trim badges, or narrative text elsewhere in the listing. Do not infer or "correct" the drivetrain from other context; report exactly what the Drivetrain field states. Return null if not stated
- trim is the trim level exactly as listed (e.g. "Touring", "Base", "First Edition"), or null if not stated
- interior_color should be the interior color exactly as listed, or null if not stated
- modifications must be a list of specific modifications explicitly claimed by the seller (e.g. ["Aftermarket exhaust", "Coilover suspension"]). Return an empty list if the seller states there are no modifications or doesn't mention any
- color should be the exterior color exactly as listed, including manufacturer color names (e.g. "Yas Marina Blue Metallic")
- make must be extracted literally from the listing's labeled "Make" field, exactly as given — even if it looks inconsistent with the model name, VIN, or narrative text elsewhere in the listing. Do not infer or "correct" the make from other context; report exactly what the Make field states. Cross-checking make against other fields is a separate downstream step, not part of extraction
- seller_description must be the full original listing text, copied exactly

Listing:
{raw_text}"""


# --- Extraction function ---
def extract_listing(raw_text: str) -> tuple[ListingData, int, int]:
    listing_data, raw = client.messages.create_with_completion(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": _extraction_prompt(raw_text)}],
        response_model=ListingData,
    )
    return listing_data, raw.usage.input_tokens, raw.usage.output_tokens


# --- Batch API support ---
# Same prompt and schema as extract_listing above, forced via tool_choice
# instead of Instructor's structured-output patching, since Instructor's
# wrapper doesn't support the Batches API. See agents/comment_mining_agent.py
# for the same pattern applied to comment classification.
BATCH_TOOL_NAME = "extract_listing"


def _batch_tool_schema() -> dict:
    schema = ListingData.model_json_schema()
    schema.pop("title", None)
    return {
        "name": BATCH_TOOL_NAME,
        "description": "Extract structured vehicle listing data from raw listing text.",
        "input_schema": schema,
    }


def build_batch_request(custom_id: str, raw_text: str) -> Request:
    return Request(
        custom_id=custom_id,
        params=MessageCreateParamsNonStreaming(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": _extraction_prompt(raw_text)}],
            tools=[_batch_tool_schema()],
            tool_choice={"type": "tool", "name": BATCH_TOOL_NAME},
        ),
    )


def parse_batch_result(message) -> ListingData:
    """message is the anthropic Message from a succeeded batch result
    (result.result.message)."""
    for block in message.content:
        if block.type == "tool_use" and block.name == BATCH_TOOL_NAME:
            return ListingData(**block.input)
    raise ValueError("No extract_listing tool_use block found in batch result message")


# --- Quick test ---
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

    
import anthropic
import json
import re
from pydantic import BaseModel
from typing import Optional


# --- Data Model ---
class EditorialFlags(BaseModel):
    highlights_text: str
    has_consistent_voice: bool
    missing_sections: list[str]
    grammar_issues: list[str]
    completeness_score: float  # 0.0 to 1.0
    notes: Optional[str] = None


# --- Client ---
client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a Cars & Bids editorial writer. Your job is to generate the Highlights section for a used car listing, exactly matching the Cars & Bids house style.

The Highlights section always follows this exact structure:

LINE 1 (not a bullet):
"THIS... is a [year] [make] [model], finished in [exterior color] with [if convertible: color soft top and] a [interior color] interior."

BULLET 1 — Carfax and ownership:
State whether the Carfax shows no accidents and no mileage discrepancies. If one owner, say so and mention the state. If there are Carfax gaps, flag them honestly.

BULLET 2 — Equipment and modifications:
"A partial list of notable equipment reported by the seller includes [list key equipment]. Notable modifications reported by the seller include [list mods]." If no modifications, omit the modifications sentence.

BULLET 3 — Model history:
Write 3-5 sentences of enthusiast-level automotive context about this specific model. Cover: when it launched, what makes it significant, what it is known for among enthusiasts, and when production ended if relevant. This must be accurate and specific to the exact model — not generic.

BULLET 4 — Powertrain (always last, always this exact phrasing):
"Power comes from a [full engine description], rated at [hp] horsepower and [torque] lb-ft of torque. Output is sent to the [drive wheels] via a [transmission description]."

RULES:
- Never use first person
- Always use present tense
- Be specific — never use vague language like "well maintained" or "runs great"
- If modifications are present, always disclose them in bullet 2
- The opening line always starts with "THIS... is"
- Bullet 4 always uses the exact phrasing above
- Do not add any sections beyond these four bullets
- Do not editorialize or add opinions beyond the model history bullet"""


def check_editorial(listing_text: str) -> tuple[EditorialFlags, int, int]:
    # Step 1: Web search for verified model history facts
    year_m = re.search(r'\b(19[5-9]\d|20[0-2]\d)\b', listing_text)
    make_m = re.search(r'(?i)\bMake[:\s\n]+([A-Za-z][^\n]+)', listing_text)
    model_m = re.search(r'(?i)\bModel[:\s\n]+([A-Za-z0-9][^\n]+)', listing_text)
    year = year_m.group() if year_m else ""
    make = make_m.group(1).strip() if make_m else ""
    model = model_m.group(1).strip() if model_m else ""

    web_context = ""
    search_input_tokens = 0
    search_output_tokens = 0

    query_parts = [p for p in [year, make, model] if p]
    if query_parts:
        search_query = " ".join(query_parts) + " production history specs"
        try:
            raw_client = anthropic.Anthropic()
            search_response = raw_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[
                    {
                        "role": "user",
                        "content": f"Search for production history, launch year, and enthusiast significance of the {search_query}."
                    }
                ],
            )
            web_context = " ".join(
                block.text for block in search_response.content if hasattr(block, "text")
            )
            search_input_tokens = search_response.usage.input_tokens
            search_output_tokens = search_response.usage.output_tokens
            if len(web_context) < 100:
                web_context = ""
        except Exception:
            web_context = ""
            search_input_tokens = 0
            search_output_tokens = 0

    # Step 2: Generate the Highlights section
    if web_context:
        generation_prompt = f"""Generate the Highlights section for this listing. Follow the Cars & Bids house style exactly.

The following web search results contain verified facts about this vehicle's model history. The model history bullet (bullet 3) must be grounded in these results and must not contradict them:

{web_context}

Listing:
{listing_text}"""
    else:
        generation_prompt = f"""Generate the Highlights section for this listing. Follow the Cars & Bids house style exactly.

Listing:
{listing_text}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": generation_prompt
            }
        ],
    )

    highlights = response.content[0].text.strip()

    # Step 3: Check the generated highlights for quality
    check_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""You are a Cars & Bids editorial quality checker. Review this generated Highlights section and return a JSON object only — no preamble, no markdown, no backticks.

Highlights to review:
{highlights}

Return exactly this JSON structure:
{{
  "has_consistent_voice": true or false — does it match Cars & Bids house style throughout,
  "missing_sections": ["list any of the 4 required elements that are missing or malformed"],
  "grammar_issues": ["list any grammar, tense, or style issues"],
  "completeness_score": 0.0 to 1.0 based on how complete and accurate the highlights are,
  "notes": "any other editorial notes, or null"
}}"""
            }
        ],
    )

    raw = check_response.content[0].text.strip()
    # Model sometimes wraps JSON in markdown fences despite being asked not to;
    # extract the first {...} block to handle both cases robustly.
    start, end = raw.find("{"), raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object in editorial check response: {raw!r}")
    parsed = json.loads(raw[start:end])

    input_tokens = search_input_tokens + response.usage.input_tokens + check_response.usage.input_tokens
    output_tokens = search_output_tokens + response.usage.output_tokens + check_response.usage.output_tokens

    return EditorialFlags(
        highlights_text=highlights,
        has_consistent_voice=parsed.get("has_consistent_voice", False),
        missing_sections=parsed.get("missing_sections", []),
        grammar_issues=parsed.get("grammar_issues", []),
        completeness_score=float(parsed.get("completeness_score", 0.5)),
        notes=parsed.get("notes"),
    ), input_tokens, output_tokens


# --- Quick test ---
if __name__ == "__main__":
    sample = """
Make: Honda
Model: S2000
Year: 2004
Exterior Color: Silverstone Metallic
Interior Color: Black
Body Style: Convertible
Engine: 2.2L I4 (F22C), 240 horsepower, 162 lb-ft torque
Transmission: Manual (6-Speed)
Drivetrain: Rear-wheel drive
Mileage: 64,200
VIN: JHMAP21474T001128
Title Status: Clean (LA)

Carfax: No accidents, no mileage discrepancies, one owner in Louisiana since new.

Equipment: 17-inch wheels, limited-slip differential, HID headlights, power-operated soft top,
leather upholstery, digital instrument cluster, cruise control.

Modifications: Braided brake lines, Kenwood sound system (head unit, amplifier, speakers, subwoofer).

Known Flaws: Chips and cracked paint on front bumper, ding on passenger door, curb rash on wheels,
2015 date codes on tires, some wear on seats and shift knob.

Service History:
- April 2026 (64,103 miles): Engine oil and filter changed
- 2023: Hoses, drive belt, brake pads, brake rotors replaced, fluids changed (no documentation)

Ownership: One owner since new, purchased December 2003.
    """

    result = check_editorial(sample)
    print("=== GENERATED HIGHLIGHTS ===")
    print(result.highlights_text)
    print("\n=== EDITORIAL FLAGS ===")
    print(result.model_dump_json(indent=2))
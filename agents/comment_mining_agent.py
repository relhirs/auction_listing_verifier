import anthropic
import instructor
from pydantic import BaseModel
from typing import Literal

from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request


# --- Prefilter ---

# Deliberately permissive: false negatives here mean a real discrepancy
# disappears from the corpus with no error, so recall matters more than
# saving Claude calls at this stage.
KEYWORDS = [
    # mileage / odometer
    "mileage", "miles", "odometer", "actual miles", "true miles", "real miles",
    "rolled back", "rollback", "tmu", "exempt",
    # VIN / title / spec mismatch
    "vin", "chassis", "title", "salvage", "rebuilt", "branded", "clean title",
    "not the same", "doesn't match", "does not match", "mismatch", "mismatched",
    "wrong color", "wrong engine", "wrong transmission", "factory spec",
    "factory correct", "not original", "non-original", "swapped",
    # damage / condition
    "rust", "rusty", "corrosion", "damage", "damaged", "not disclosed",
    "undisclosed", "misrepresented", "misrepresentation", "accident",
    "accident history", "wrecked", "repainted", "overspray", "bondo",
    "panel gap", "paint match", "does not line up", "hidden damage",
    # photos
    "duplicate", "same photo", "same photos", "stock photo", "reused photo",
    "old listing", "previous listing", "different car", "not this car",
    # history / documentation
    "carfax", "autocheck", "service record", "service history", "no records",
    "history report", "inconsistent", "doesn't add up", "does not add up",
    "discrepancy", "discrepancies", "incorrect", "inaccurate", "lied",
    "lying", "scam", "fraud", "fake", "questionable", "red flag",
    "raises questions", "something's off", "something is off",
]

MIN_WORDS_FOR_AUTO_REVIEW = 25


def should_review(comment_text: str) -> bool:
    """Broad, recall-favoring prefilter for whether a comment is worth a Claude call.

    Send to Claude if EITHER: a keyword hits, OR the comment is long enough
    (>25 words) that it likely contains a substantive claim regardless of its
    exact wording. Only discard when BOTH checks fail -- short and unmatched.
    """
    if not comment_text:
        return False

    text_lower = comment_text.lower()
    if any(keyword in text_lower for keyword in KEYWORDS):
        return True

    word_count = len(comment_text.split())
    if word_count > MIN_WORDS_FOR_AUTO_REVIEW:
        return True

    return False


# --- Data model ---
class CommentClassification(BaseModel):
    is_confirmed_discrepancy: bool
    flag_category: Literal[
        "VIN_SPEC_MISMATCH", "ODOMETER_DISCREPANCY", "DUPLICATE_PHOTO",
        "MISSING_PHOTO_ANGLE", "UNDISCLOSED_DAMAGE", "OTHER", "NOT_A_DISCREPANCY",
    ]
    confidence: float
    reasoning: str


# --- Instructor-wrapped Anthropic client ---
raw_client = anthropic.Anthropic()
client = instructor.from_anthropic(raw_client)


# --- Classification function ---
def _build_prompt(comment_text: str) -> str:
    return f"""You are reviewing a comment from a Cars & Bids auction thread to decide
whether it confirms a real, evidence-backed discrepancy between the listing
and the actual car -- not just speculation or opinion.

CONFIRM (is_confirmed_discrepancy=True) only when the comment shows the
LISTING'S OWN stated claim -- its spec, drivetrain, title/location, history,
mileage continuity, or photos -- is contradicted by an outside, checkable
source: a prior auction/listing of the same car, VIN/spec data, an auction
house's own record, a title document, or a plainly wrong stated fact (wrong
model part, wrong drivetrain, wrong location). The car having some flaw is
not enough by itself -- the LISTING'S CLAIM has to be the thing that's wrong.

Example CONFIRM (listing's history claim contradicted by an outside record):
"You stated the car has been in the family since new, but Barrett Jackson
shows this car sold at Las Vegas in 2008."
-> is_confirmed_discrepancy=True, flag_category=VIN_SPEC_MISMATCH

Example CONFIRM (listing's spec is just wrong):
"The listing says this is RWD but it's actually AWD -- check the badge and
the VIN decode."
-> is_confirmed_discrepancy=True, flag_category=VIN_SPEC_MISMATCH

DENY (is_confirmed_discrepancy=False) when the comment is speculation, a
guess, an opinion, uses a trigger word while actually denying there's a
problem, OR -- importantly -- when it's the seller/owner (or anyone)
ANSWERING, CLARIFYING, or EXPLAINING a question about the car's condition,
mechanical history, or mileage in the thread. That's active disclosure
happening in real time, not a hidden mismatch between the listing and
reality, even if it mentions damage, a repair, or a mileage figure.

Example DENY (seller disclosure, not a listing contradiction):
"Yes that's correct, the mileage was recorded in km on the title and not
converted to miles -- I didn't catch it until recently, sorry for the
confusion."
-> is_confirmed_discrepancy=False, flag_category=NOT_A_DISCREPANCY

Example DENY (uses a trigger word but isn't flagging anything):
"Checked the mileage and it lines up fine with the service stickers in the
photos, no discrepancy here."
-> is_confirmed_discrepancy=False, flag_category=NOT_A_DISCREPANCY

Example DENY (speculation, no evidence):
"Engine bay looks a little dirty, might have some hidden rust under there,
who knows."
-> is_confirmed_discrepancy=False, flag_category=NOT_A_DISCREPANCY

Now classify this comment:

\"\"\"{comment_text}\"\"\"
"""


def classify_comment(comment_text: str) -> CommentClassification:
    classification, _raw = client.messages.create_with_completion(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": _build_prompt(comment_text)}],
        response_model=CommentClassification,
    )
    return classification


# --- Batch API support ---
# Same prompt and classification schema as classify_comment above, but built
# as a Message Batches request instead of a synchronous call. Batches cost
# 50% less per token and are the right fit for a one-shot corpus mining job
# with no latency requirement -- see agents/run_comment_mining_batch.py.
BATCH_TOOL_NAME = "classify_comment"


def _batch_tool_schema() -> dict:
    schema = CommentClassification.model_json_schema()
    schema.pop("title", None)
    return {
        "name": BATCH_TOOL_NAME,
        "description": "Classify whether a Cars & Bids auction comment confirms a real, evidence-backed discrepancy.",
        "input_schema": schema,
    }


def build_batch_request(custom_id: str, comment_text: str) -> Request:
    return Request(
        custom_id=custom_id,
        params=MessageCreateParamsNonStreaming(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": _build_prompt(comment_text)}],
            tools=[_batch_tool_schema()],
            tool_choice={"type": "tool", "name": BATCH_TOOL_NAME},
        ),
    )


def parse_batch_result(message) -> CommentClassification:
    """message is the anthropic Message from a succeeded batch result
    (result.result.message)."""
    for block in message.content:
        if block.type == "tool_use" and block.name == BATCH_TOOL_NAME:
            return CommentClassification(**block.input)
    raise ValueError("No classify_comment tool_use block found in batch result message")


# --- Mining function ---
def mine_discrepancies(auction_id: str, comments: list) -> list:
    records = []
    for comment in comments:
        if comment.get("type") != 1:
            continue

        text = comment.get("text")
        if not should_review(text):
            continue

        result = classify_comment(text)
        if result.is_confirmed_discrepancy:
            records.append({
                "auction_id": auction_id,
                "comment_id": comment["id"],
                "flag_category": result.flag_category,
                "source_text": text,
                "confidence": result.confidence,
            })

    return records

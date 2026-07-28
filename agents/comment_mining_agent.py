import anthropic
import instructor
from pydantic import BaseModel
from typing import Literal


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
client = instructor.from_anthropic(anthropic.Anthropic())


# --- Classification function ---
def classify_comment(comment_text: str) -> CommentClassification:
    classification, _raw = client.messages.create_with_completion(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""You are reviewing a comment from a Cars & Bids auction thread to decide
whether it confirms a real, evidence-backed discrepancy between the listing
and the actual car -- not just speculation or opinion.

CONFIRM (is_confirmed_discrepancy=True) only when the commenter states
something as verified fact tied to evidence: they checked a record, compared
a photo, called someone, or point to a specific contradiction they can show.

Example CONFIRM:
"Pulled the Carfax myself -- it shows 62,000 miles at last service in 2023,
but this listing says 58,000 now. That's backwards."
-> is_confirmed_discrepancy=True, flag_category=ODOMETER_DISCREPANCY

DENY (is_confirmed_discrepancy=False) when the comment is speculation, a
guess, an opinion, or uses a trigger word while actually denying there's a
problem.

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
""",
            }
        ],
        response_model=CommentClassification,
    )
    return classification


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

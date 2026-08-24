import anthropic
from pydantic import BaseModel
from typing import Literal, Optional
from core.verifier import Flag

from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request


# --- Data Model ---
class ListingReport(BaseModel):
    overall_score: float  # 0.0 to 1.0
    flags: list[Flag]
    summary_paragraph: str
    recommended_action: Literal["approve", "needs_review", "reject"]


# --- Rule-based scoring ---
def compute_score(flags: list[Flag], action: str) -> float:
    score = 1.0
    deductions = {"ERROR": 0.25, "WARNING": 0.10, "INFO": 0.02}
    for flag in flags:
        score -= deductions.get(flag.severity, 0)
    score = max(0.0, score)
    if action == "reject":
        score = min(score, 0.40)
    elif action == "needs_review":
        score = min(score, 0.75)
    return round(score, 2)


# --- Rule-based action ---
def compute_action(flags: list[Flag]) -> Literal["approve", "needs_review", "reject"]:
    # photo_angles' INFO tier fires on nearly every real listing (only
    # ~8-11 photos are sampled against 16 required angles -- see
    # core/verifier.py's check_photo_angles), so it can't be treated as a
    # real signal for the overall action the way every other check's
    # flags can. Its WARNING tier (a whole required category missing,
    # e.g. "mechanical") is a much rarer, real signal and stays counted.
    counted = [f for f in flags if not (f.field_name == "photo_angles" and f.severity == "INFO")]
    error_flags = [f for f in counted if f.severity == "ERROR"]
    warning_flags = [f for f in counted if f.severity == "WARNING"]

    # Reject conditions
    if len(error_flags) >= 2:
        return "reject"
    if any(f.field_name in ["make", "year"] and f.severity == "ERROR" for f in flags):
        # Single ERROR on make or year is a potential fraud signal — reject
        return "reject"

    # Needs review conditions
    if len(error_flags) >= 1:
        return "needs_review"
    if len(warning_flags) >= 1:
        return "needs_review"

    # Approve
    return "approve"


NO_ISSUES_SUMMARY = "No issues were detected. All verified fields match across listing, VIN, and photo data. This listing appears complete and consistent."


def _flags_text(flags: list[Flag]) -> str:
    return "\n".join([
        f"[{f.severity}] {f.field_name}: claimed={f.claimed_value}, verified={f.verified_value} — {f.suggested_fix}"
        for f in flags
    ])


def _summary_prompt(flags: list[Flag]) -> str:
    return f"""You are a Cars & Bids editorial assistant writing a concise internal report summary.

The following flags were detected during verification of a car listing:

{_flags_text(flags)}

Write a 2-3 sentence summary paragraph for an editor. Be direct and specific.
State what was found, what needs attention, and what the editor should do next.
Do not use bullet points. Do not repeat the flag data verbatim — synthesize it."""


# --- LLM summary ---
def generate_summary(flags: list[Flag]) -> tuple[str, int, int]:
    client = anthropic.Anthropic()

    if not flags:
        return NO_ISSUES_SUMMARY, 0, 0

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": _summary_prompt(flags)}],
    )

    return response.content[0].text.strip(), response.usage.input_tokens, response.usage.output_tokens


# --- Batch API support ---
# Same prompt as generate_summary above, submitted as a Message Batches
# request. Returns None for an empty flags list -- that path is already free
# (a canned string, no model call) in generate_summary, so it's never worth
# batching; callers should use NO_ISSUES_SUMMARY directly instead of
# submitting a request for it.
def build_batch_request(custom_id: str, flags: list[Flag]) -> Optional[Request]:
    if not flags:
        return None
    return Request(
        custom_id=custom_id,
        params=MessageCreateParamsNonStreaming(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": _summary_prompt(flags)}],
        ),
    )


def parse_batch_result(message) -> str:
    """message is the anthropic Message from a succeeded batch result
    (result.result.message)."""
    return message.content[0].text.strip()


# --- Main function ---
def synthesize_report(flags: list[Flag]) -> tuple[ListingReport, int, int]:
    # Sort flags by severity
    severity_order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
    sorted_flags = sorted(flags, key=lambda f: severity_order[f.severity])

    action = compute_action(sorted_flags)
    score = compute_score(sorted_flags, action)
    summary, input_tokens, output_tokens = generate_summary(sorted_flags)

    return ListingReport(
        overall_score=score,
        flags=sorted_flags,
        summary_paragraph=summary,
        recommended_action=action,
    ), input_tokens, output_tokens


# --- Quick test ---
if __name__ == "__main__":
    from core.verifier import Flag

    # Simulate the flags from the verifier test
    test_flags = [
        Flag(
            field_name="year",
            claimed_value="2003",
            verified_value="2004",
            source_of_truth="NHTSA",
            confidence=0.95,
            severity="ERROR",
            suggested_fix="Listing says 2003 but VIN decodes to 2004. Correct the listing year."
        ),
        Flag(
            field_name="mileage",
            claimed_value="64200",
            verified_value="70500",
            source_of_truth="seller_description",
            confidence=0.85,
            severity="WARNING",
            suggested_fix="Listed mileage (64200) is lower than a documented service record showing 70500 miles. Verify current mileage."
        ),
        Flag(
            field_name="photo_angles",
            claimed_value=None,
            verified_value=None,
            source_of_truth="photo_agent",
            confidence=0.75,
            severity="WARNING",
            suggested_fix="Standard photo angle missing: 'engine bay'. Request this photo from the seller."
        ),
        Flag(
            field_name="photo_angles",
            claimed_value=None,
            verified_value=None,
            source_of_truth="photo_agent",
            confidence=0.75,
            severity="WARNING",
            suggested_fix="Standard photo angle missing: 'undercarriage'. Request this photo from the seller."
        ),
    ]

    report, _, _ = synthesize_report(test_flags)
    print(f"Overall Score: {report.overall_score}")
    print(f"Recommended Action: {report.recommended_action}")
    print(f"\nSummary:\n{report.summary_paragraph}")
    print(f"\nFlags ({len(report.flags)} total):")
    for flag in report.flags:
        print(f"  [{flag.severity}] {flag.field_name}: {flag.suggested_fix}")
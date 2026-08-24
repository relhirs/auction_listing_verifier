import anthropic
import base64
import concurrent.futures
import httpx
import imagehash
from io import BytesIO
from PIL import Image
from pydantic import BaseModel
from typing import Optional
import json

from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

from core.constants import REQUIRED_PHOTO_ANGLES, DUPLICATE_PHOTO_HASH_DISTANCE


# --- Data Model ---
class PhotoAnalysis(BaseModel):
    image_url: str
    visible_color: Optional[str] = None
    visible_damage: list[str] = []
    missing_angles: list[str] = []
    confidence_score: float  # 0.0 to 1.0
    notes: Optional[str] = None


# --- Fetch image bytes once, shared by both the vision call and the perceptual hash ---
def fetch_image_bytes(url: str) -> tuple[bytes, str]:
    response = httpx.get(url, timeout=15, follow_redirects=True)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "image/jpeg").split(";")[0]
    return response.content, content_type


def _phash_hex(raw_bytes: bytes) -> Optional[str]:
    try:
        return str(imagehash.phash(Image.open(BytesIO(raw_bytes))))
    except Exception:
        return None


def _vision_prompt_text() -> str:
    return f"""You are a vehicle photo inspector. Analyze this car photo and respond ONLY with a JSON object — no preamble, no markdown, no backticks.

                The JSON must have exactly these fields:
                {{
                "visible_color": "the exterior color you can see, or null if not visible",
                "visible_damage": ["list of specific damage observations, empty array if none"],
                "missing_angles": ["list of standard angles not shown in this photo set — only flag if this appears to be the complete photo set"],
                "confidence_score": 0.0 to 1.0 based on image quality and clarity,
                "notes": "any other observations worth flagging, or null"
                }}

                Standard angles to check for: {", ".join(REQUIRED_PHOTO_ANGLES)}.
                Describe visible damage in two parts:
                1. What the damage looks like (type, size, severity)
                2. Where it appears to be located (be conservative —
                if uncertain about the exact component name, describe
                the general area only: front, rear, driver side,
                passenger side, upper, lower)"""


def _parse_vision_json(image_url: str, raw_text: str) -> PhotoAnalysis:
    raw = raw_text.strip()
    # The model sometimes wraps JSON in markdown fences or adds a preamble
    # despite being told not to (same real behavior editorial_agent.py's
    # check_editorial already has to work around) -- extract the first
    # {...} block instead of assuming the whole response is bare JSON, so
    # one non-conforming response doesn't lose an otherwise-successful
    # batch result.
    start, end = raw.find("{"), raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object in photo vision response: {raw!r}")
    parsed = json.loads(raw[start:end])
    return PhotoAnalysis(
        image_url=image_url,
        visible_color=parsed.get("visible_color"),
        visible_damage=[_damage_to_str(d) for d in parsed.get("visible_damage", [])],
        missing_angles=parsed.get("missing_angles", []),
        confidence_score=float(parsed.get("confidence_score", 0.5)),
        notes=parsed.get("notes"),
    )


def _damage_to_str(entry) -> str:
    """visible_damage is documented as a flat list of strings, but the
    model sometimes structures an entry as an object instead (e.g.
    {"observation": "...", "location": "..."}) despite the prompt asking
    for plain strings -- normalize rather than let a single non-conforming
    entry raise a pydantic ValidationError and lose an entire otherwise-good
    photo analysis (or, upstream in a batch, an entire otherwise-good
    batch -- see eval/eval_runner.py's fetch_round1 for why one bad
    response must not be allowed to take down 156 good ones)."""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return " -- ".join(str(v) for v in entry.values() if v)
    return str(entry)


# --- Analyze a single photo ---
def analyze_single_photo(client: anthropic.Anthropic, image_url: str) -> tuple[PhotoAnalysis, int, int, Optional[str]]:
    try:
        raw_bytes, media_type = fetch_image_bytes(image_url)
        b64_data = base64.standard_b64encode(raw_bytes).decode("utf-8")
        phash = _phash_hex(raw_bytes)

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            temperature=0,  # deterministic reads -- vision transcription (color,
            # damage, missing angles) was observed to flip run-to-run on
            # identical input photos with the default (unset, ~1.0) temperature;
            # this is a factual-transcription
            # task, not a creative one, so there's no tradeoff being made here.
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": _vision_prompt_text(),
                        }
                    ],
                }
            ],
        )

        analysis = _parse_vision_json(image_url, response.content[0].text)
        return analysis, response.usage.input_tokens, response.usage.output_tokens, phash

    except Exception as e:
        return PhotoAnalysis(
            image_url=image_url,
            visible_color=None,
            visible_damage=[],
            missing_angles=[],
            confidence_score=0.0,
            notes=f"ERROR: {str(e)}",
        ), 0, 0, None


def detect_duplicate_photos(
    hashes: list[tuple[str, Optional[str]]],
    threshold: int = DUPLICATE_PHOTO_HASH_DISTANCE,
) -> list[tuple[str, str, int]]:
    """hashes is a list of (image_url, phash_hex) pairs, phash_hex may be None
    if that photo's hash couldn't be computed (fetch/decode failure) — those
    are skipped. Returns (url_a, url_b, hamming_distance) for every pair
    whose perceptual hashes are within `threshold` of each other — i.e.
    likely the same or a reused image. O(n^2) pairwise comparison, fine for
    a single listing's photo count (dozens, not thousands)."""
    valid = [(url, imagehash.hex_to_hash(h)) for url, h in hashes if h]
    duplicates = []
    for i in range(len(valid)):
        url_a, hash_a = valid[i]
        for j in range(i + 1, len(valid)):
            url_b, hash_b = valid[j]
            distance = hash_a - hash_b
            if distance <= threshold:
                duplicates.append((url_a, url_b, int(distance)))
    return duplicates


# --- Batch API support ---
# Same vision prompt/schema as analyze_single_photo, submitted as a Message
# Batches request instead of a synchronous call. The image still has to be
# fetched and base64-encoded up front (batch requests are fully self-contained
# — no URL-fetch-at-processing-time option), so build_batch_request does the
# same single fetch-serves-both-purposes work as analyze_single_photo: one
# fetch yields both the base64 payload and the phash used for duplicate
# detection, so the caller doesn't need a second fetch later just to hash.
def build_batch_request(custom_id: str, image_url: str) -> tuple[Request, Optional[str]]:
    raw_bytes, media_type = fetch_image_bytes(image_url)
    b64_data = base64.standard_b64encode(raw_bytes).decode("utf-8")
    phash = _phash_hex(raw_bytes)

    request = Request(
        custom_id=custom_id,
        params=MessageCreateParamsNonStreaming(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            temperature=0,  # see analyze_single_photo -- same determinism fix,
            # kept identical between the sync and batch paths since they share
            # this vision prompt/schema.
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": _vision_prompt_text(),
                        },
                    ],
                }
            ],
        ),
    )
    return request, phash


def parse_batch_result(image_url: str, message) -> PhotoAnalysis:
    """message is the anthropic Message from a succeeded batch result
    (result.result.message)."""
    return _parse_vision_json(image_url, message.content[0].text)


# --- Main function ---
def analyze_photos(image_urls: list[str]) -> tuple[list[PhotoAnalysis], int, int, list[tuple[str, str, int]]]:
    client = anthropic.Anthropic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(analyze_single_photo, client, url): i
                   for i, url in enumerate(image_urls)}
        results = [None] * len(image_urls)
        hashes = [None] * len(image_urls)
        total_input_tokens = 0
        total_output_tokens = 0
        for future in concurrent.futures.as_completed(futures):
            photo, in_tok, out_tok, phash = future.result()
            idx = futures[future]
            results[idx] = photo
            hashes[idx] = (photo.image_url, phash)
            total_input_tokens += in_tok
            total_output_tokens += out_tok
    duplicate_pairs = detect_duplicate_photos(hashes)
    return results, total_input_tokens, total_output_tokens, duplicate_pairs


# --- Quick test ---
if __name__ == "__main__":
    # BMW M3 listing photos — replace with real Cars and Bids image URLs
    test_urls = [
        "https://media.carsandbids.com/cdn-cgi/image/width=2080,quality=70/ee7f173e46ec801a48d1673c50f9cebaa1bf2854/photos/MazdaRX71994029/edit/VBq1U.jpg?t=177825450138",
        "https://media.carsandbids.com/cdn-cgi/image/width=2080,quality=80/ee7f173e46ec801a48d1673c50f9cebaa1bf2854/photos/MazdaRX71994053/edit/KyQuW.jpg?t=177825052559",
        "https://media.carsandbids.com/cdn-cgi/image/width=2080,quality=80/ee7f173e46ec801a48d1673c50f9cebaa1bf2854/photos/MazdaRX71994056/edit/qn97N.jpg?t=177825046478",
        "https://media.carsandbids.com/cdn-cgi/image/width=2080,quality=80/ce30254657d59f325f1440063f3e2676eaa1a645/photos/MazdaRX71994065.jpg?t=177816378895",
        "https://media.carsandbids.com/cdn-cgi/image/width=2080,quality=80/ce30254657d59f325f1440063f3e2676eaa1a645/photos/MazdaRX71994057.jpg?t=177816378895",
    ]

    results, in_tok, out_tok, duplicates = analyze_photos(test_urls)
    for r in results:
        print(r.model_dump_json(indent=2))
    print(f"\ntokens: {in_tok} in / {out_tok} out")
    print(f"duplicate pairs: {duplicates}")

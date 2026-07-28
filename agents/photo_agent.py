import anthropic
import base64
import concurrent.futures
import httpx
from pydantic import BaseModel
from typing import Optional
import json


# --- Data Model ---
class PhotoAnalysis(BaseModel):
    image_url: str
    visible_color: Optional[str] = None
    visible_damage: list[str] = []
    missing_angles: list[str] = []
    confidence_score: float  # 0.0 to 1.0
    notes: Optional[str] = None


# --- Fetch image and convert to base64 ---
def fetch_image_base64(url: str) -> tuple[str, str]:
    response = httpx.get(url, timeout=15, follow_redirects=True)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "image/jpeg").split(";")[0]
    b64 = base64.standard_b64encode(response.content).decode("utf-8")
    return b64, content_type


# --- Analyze a single photo ---
def analyze_single_photo(client: anthropic.Anthropic, image_url: str) -> tuple[PhotoAnalysis, int, int]:
    try:
        b64_data, media_type = fetch_image_base64(image_url)

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
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
                            "text": """You are a vehicle photo inspector. Analyze this car photo and respond ONLY with a JSON object — no preamble, no markdown, no backticks.

                The JSON must have exactly these fields:
                {
                "visible_color": "the exterior color you can see, or null if not visible",
                "visible_damage": ["list of specific damage observations, empty array if none"],
                "missing_angles": ["list of standard angles not shown in this photo set — only flag if this appears to be the complete photo set"],
                "confidence_score": 0.0 to 1.0 based on image quality and clarity,
                "notes": "any other observations worth flagging, or null"
                }

                Standard angles to check for: front, rear, driver side, passenger side, interior, engine bay, odometer, undercarriage.
                Describe visible damage in two parts:
                1. What the damage looks like (type, size, severity)
                2. Where it appears to be located (be conservative — 
                if uncertain about the exact component name, describe 
                the general area only: front, rear, driver side, 
                passenger side, upper, lower)"""
                        }
                    ],
                }
            ],
        )

        raw = response.content[0].text.strip()
        parsed = json.loads(raw)

        return PhotoAnalysis(
            image_url=image_url,
            visible_color=parsed.get("visible_color"),
            visible_damage=parsed.get("visible_damage", []),
            missing_angles=parsed.get("missing_angles", []),
            confidence_score=float(parsed.get("confidence_score", 0.5)),
            notes=parsed.get("notes"),
        ), response.usage.input_tokens, response.usage.output_tokens

    except Exception as e:
        return PhotoAnalysis(
            image_url=image_url,
            visible_color=None,
            visible_damage=[],
            missing_angles=[],
            confidence_score=0.0,
            notes=f"ERROR: {str(e)}",
        ), 0, 0


# --- Main function ---
def analyze_photos(image_urls: list[str]) -> tuple[list[PhotoAnalysis], int, int]:
    client = anthropic.Anthropic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(analyze_single_photo, client, url): i
                   for i, url in enumerate(image_urls)}
        results = [None] * len(image_urls)
        total_input_tokens = 0
        total_output_tokens = 0
        for future in concurrent.futures.as_completed(futures):
            photo, in_tok, out_tok = future.result()
            results[futures[future]] = photo
            total_input_tokens += in_tok
            total_output_tokens += out_tok
    return results, total_input_tokens, total_output_tokens


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

    results = analyze_photos(test_urls)
    for r in results:
        print(r.model_dump_json(indent=2))
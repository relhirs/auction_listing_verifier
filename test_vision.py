import base64
from anthropic import Anthropic
from dotenv import load_dotenv
load_dotenv()

client = Anthropic()
# Load and encode your image
with open("test_car.png", "rb") as image_file:
    base64_image = base64.b64encode(image_file.read()).decode("utf-8")

message = client.messages.create(
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
                        "media_type": "image/png",
                        "data": base64_image,
                    },
                },
{"type": "text", "text": "You are an expert automotive inspector reviewing a car listing photo. Analyze this image and provide a structured condition report covering: (1) Paint condition — look for scratches, chips, swirl marks, mismatched color, or respray evidence like overspray or uneven texture. (2) Body panels — check for dents, creases, ripples, or misaligned panel gaps. (3) Trim and emblems — missing, broken, or aftermarket pieces. (4) Lights — cracks, condensation, or damage. (5) Any other visible inconsistencies a buyer should know about. For each category, state clearly: what you see, your confidence level, and any flags. End with an overall condition rating: Excellent / Good / Fair / Poor."}            ],
        }
    ],
)
print(message.content[0].text)
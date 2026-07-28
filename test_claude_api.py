import os
from anthropic import Anthropic
from dotenv import load_dotenv
load_dotenv()

client = Anthropic(
    # This is the default and can be omitted
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)

message = client.messages.create(
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": "Hello, Claude",
        }
    ],
    model="claude-sonnet-4-6",
)
print(message.content[0].text)

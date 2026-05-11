import os
from pathlib import Path
from openai import OpenAI

# Load .env.local from project root
env_file = Path(__file__).parent.parent / ".env.local"
for line in env_file.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY", "VIRTUAL_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL", "http://pluto/v1/"),
)

response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "Du bist ein hilfreicher Assistent. Antworte auf Deutsch."
        },
        {
            "role": "user",
            "content": "Was könnte ich heute essen?",
        }
    ],
    model="GPT-OSS-120B",
    max_completion_tokens=256,
)

print(response.choices[0].message.content)

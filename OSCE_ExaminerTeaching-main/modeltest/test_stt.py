import os
from pathlib import Path
from openai import OpenAI

# Load .env.local from project root
env_file = Path(__file__).parent.parent / ".env.local"
for line in env_file.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

# Place an audio file (e.g. test.mp3, test.wav, test.webm) in the datafiles/ folder
AUDIO_FILE = r"datafiles\Anamnese Feedback 1.m4a"

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY", "VIRTUAL_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL", "http://pluto/v1/"),
)

with open(AUDIO_FILE, "rb") as f:
    response = client.audio.transcriptions.create(
        model="voxtral-small-2507",
        file=f,
        language="de",
    )

print(response.text)

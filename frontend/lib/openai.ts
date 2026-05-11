const BASE_URL = (process.env.OPENAI_BASE_URL ?? "https://api.openai.com/v1").replace(/\/$/, "");

const DEFAULT_PROMPT = `Du bist ein strenger, aber fairer OSCE-Feedback-Assistent.
Bewerte das gegebene Transcript anhand klinischer Kommunikationskompetenzen.
Gib strukturiertes Feedback mit klaren Punkten und konkreten Verbesserungsvorschlaegen.
Antworte auf Deutsch in klaren Abschnitten:
1) Starke Punkte
2) Verbesserungsfelder
3) Konkrete naechste Schritte
4) Gesamteindruck (1-5)`;

async function fetchWithTimeout(input: RequestInfo, init: RequestInit, timeoutMs = 25000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

export async function transcribeAudio(buffer: Buffer, contentType: string) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("Missing OPENAI_API_KEY.");
  }

  const form = new FormData();
  form.append("model", "voxtral-small-2507"); 
  form.append("file", new Blob([buffer], { type: contentType }), "audio.webm");

  const response = await fetchWithTimeout(`${BASE_URL}/audio/transcriptions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`
    },
    body: form
  });

  if (!response.ok) {
    throw new Error(`Transcription failed: ${response.status}`);
  }

  const data = await response.json();
  return String(data.text || "");
}

export async function evaluateTranscript(transcript: string) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("Missing OPENAI_API_KEY.");
  }

  const prompt = process.env.EVAL_PROMPT || DEFAULT_PROMPT;

  const response = await fetchWithTimeout(`${BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model: "GPT-OSS-120B",
      messages: [
        { role: "system", content: prompt },
        { role: "user", content: `Transcript:\n${transcript}` }
      ],
      temperature: 0.2
    })
  }, 25000);

  if (!response.ok) {
    throw new Error(`Evaluation failed: ${response.status}`);
  }

  const data = await response.json();
  return String(data.choices?.[0]?.message?.content || "");
}

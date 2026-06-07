# OSCE Feedback Web App (MVP)

Minimalistische Web-App fuer OSCE-Feedback ohne externe Dienste (ausser OpenAI). Videos liegen lokal in `public/videos/`, Metadaten in `data/videos.json`, Audio und Submissions in `data/`.

## Setup

### 0) Zugangscode
- Alle Teilnehmenden verwenden denselben universellen Zugangscode: **`OSCE2026SS`**
- Dieser ist in `data/users.json` hinterlegt und muss nicht geändert werden.
- Beim Login geben Teilnehmende zusätzlich ihren Vor- und Nachnamen ein — dieser wird pro Session eindeutig gespeichert und erscheint auf der Teilnahmebescheinigung.
- Jede Session erhält automatisch eine eindeutige ID, sodass Einreichungen und Evaluationen pro Person getrennt gespeichert werden.

### 1) Videos herunterladen und ablegen
- Videos sind **nicht** im Repo enthalten (zu groß für GitHub).
- Lade alle Videodateien aus dem institutionellen Cloud-Speicher herunter:
  **https://caruscloud.uniklinikum-dresden.de/index.php/s/oSyfRbQzEF3kyPd**
- Lege die heruntergeladenen Dateien in `public/videos/` ab.
- Trage die Videos in `data/videos.json` ein, z.B.:
  ```json
  [
    {
      "id": "osce-1",
      "title": "OSCE Station 1",
      "order_index": 1,
      "storage_key": "osce-1.mp4"
    }
  ]
  ```

### 2) Umgebungsvariablen
- `.env.local.example` kopieren nach `.env.local` und Werte setzen:
  - `OPENAI_API_KEY`
  - `EVAL_PROMPT` (optional)

### 3) Installation & Start
```bash
npm install
npm run dev
```

## API Verhalten (MVP)
- Verarbeitung ist synchron, mit Timeout (25s) pro Request.
- Bei Timeout liefert `/api/submissions/[id]/process` Status `processing`.
- In diesem Fall kann der Client erneut `process` aufrufen oder weiter pollen.

## Manuelle E2E Tests (Akzeptanztest)
1. `/login` laden, Zugangscode eingeben.
2. `/app` laden: Video-Liste erscheint, Video wird geladen.
3. Audio aufnehmen, Upload starten, Auswertung starten.
4. Feedback erscheint, Transcript optional einblendbar.

## Sicherheitsannahmen (konservativ)
- OpenAI Key bleibt serverseitig und wird nie an den Client ausgeliefert.
- Zugriffsschutz basiert auf lokal gepflegten Zugangscodes in `data/users.json`.

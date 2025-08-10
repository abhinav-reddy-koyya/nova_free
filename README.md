Here’s the cleaned-up **README.md** (no Git stuff), covering everything we built so far:

```md
# Nova (Free) — General Chat + SEO / Research / Article Writing

A minimal, fast stack for a free-tier assistant:
- **Frontend:** Next.js (React, JSX UI, dark theme, animations)
- **Backend:** Flask API calling OpenAI (with offline echo fallback)

Nova Free handles friendly chat, research summaries, and SEO tasks (keyword clusters, outlines, briefs, meta, articles).  
**Coding/debugging is intentionally disabled** here—those live in the premium models (Main/Power) and **GWEN**.

---

## Features

- **General conversation** (hello/hi works like normal chat)
- **SEO tools** without a dropdown:
  - Keyword clusters, outlines, content briefs, meta titles & descriptions, full articles
  - Auto intent detection from your prompt
- **Research summaries** with concise takeaways
- **No-code guard**: politely blocks code/debug/“write Python/JS …” requests (premium only)
- **Markdown rendering** (headings, lists, tables)
- **CSV export** when a Markdown table is detected
- **Typing animation** + smooth UI animations
- **Enter to send**; **Shift+Enter** for newline; IME-safe (composition aware)
- **Auto-resize** textarea + “Copied!” / “CSV downloaded” toasts
- **Model badge** pulled from `/api/health`
- **.env config**; CORS enabled for `/api/*`
- **Offline mode** (no API key): UI still works with echo replies

---

## Architecture

```

nova\_free/
├─ backend/                 # Flask API
│  ├─ nova\_free.py          # /api/health, /api/chat + guards
│  ├─ requirements.txt
│  └─ .env                  # your real keys (not committed)
└─ frontend/                # Next.js UI (pages router)
├─ pages/
│  ├─ \_app.jsx           # imports global CSS (or app.jsx + per-page import)
│  └─ index.jsx          # chat UI
├─ styles/
│  └─ globals.css        # theme + animations
├─ package.json
├─ next.config.js
└─ jsconfig.json

````

**Backend endpoints**
- `GET /api/health` → `{ ok, model }`
- `POST /api/chat` → `{ reply, usage?, mode }`
  - Blocks coding/debugging with a friendly message
  - Returns normal chat/SEO/research responses

---

## Prerequisites

- **Python** 3.10+ (3.11 recommended)
- **Node.js** 18+ (LTS recommended) and `npm`
- **OpenAI API key**

---

## Quick Start

### 1) Backend

```powershell
cd nova_free\backend

# Windows (PowerShell)
py -m venv venv
.\venv\Scripts\Activate.ps1

# macOS/Linux
# python3 -m venv venv
# source venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
````

Create `backend/.env`:

```env
FLASK_SECRET=change-me
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.6
OPENAI_MAX_TOKENS=900
```

Run the API:

```powershell
python nova_free.py
# http://127.0.0.1:5000/api/health
```

### 2) Frontend

```powershell
cd ..\frontend
npm install
# If your backend runs elsewhere:
# set NEXT_PUBLIC_API_BASE=http://127.0.0.1:5000
npm run dev
# http://localhost:3000
```

**Production build**

```bash
npm run build
npm start
```

---

## Environment Variables

**Backend (`backend/.env`)**

* `FLASK_SECRET` — any random string
* `OPENAI_API_KEY` — your key
* `OPENAI_MODEL` — e.g., `gpt-3.5-turbo`
* `OPENAI_TEMPERATURE` — default `0.6`
* `OPENAI_MAX_TOKENS` — default `900`

**Frontend (optional)**

* `NEXT_PUBLIC_API_BASE` — defaults to `http://127.0.0.1:5000`

---

## Usage

* Type anything (“hello”, “explain zero-trust security”, “keyword clusters for camping stoves”) and press **Enter** to send.
* **Shift+Enter** adds a newline.
* When answers include Markdown tables, a **Download CSV** button appears.
* If you ask for code/debugging, Nova Free will **politely refuse** and suggest upgrading (Main/Power or **GWEN**).

**Examples**

* “Keyword clusters for electric scooters”
* “Outline: benefits of standing desks”
* “Write an article about remote team rituals”
* “Research summary: zero-trust security”
* “Meta titles & descriptions for gluten-free bread”

---

## API Reference

### `GET /api/health`

Returns:

```json
{ "ok": true, "model": "gpt-3.5-turbo" }
```

### `POST /api/chat`

Request:

```json
{
  "messages": [
    {"role":"user","content":"hello"}
  ]
}
```

Response:

```json
{
  "reply": "...",
  "usage": { "prompt_tokens": 123, "completion_tokens": 456, "total_tokens": 579 },
  "mode": "general"   // auto-detected: general/keywords/outline/brief/article/meta/research or "blocked"
}
```

**Notes**

* If a coding/debug intent is detected, response contains a polite refusal and `mode: "blocked"`.
* If no API key is set, reply is an **offline echo** of the user prompt.

---

## Troubleshooting

* **Blank styling / no theme:** ensure `frontend/pages/_app.jsx` imports `../styles/globals.css`.
  If you renamed to `app.jsx`, import CSS in **every** page.
* **CORS/network errors:** confirm the backend is running and `NEXT_PUBLIC_API_BASE` points to it.
* **`Model error: ...`:** check `OPENAI_API_KEY`, model name, and rate limits.
* **Windows venv issues:** use `py -m venv venv`, `.\venv\Scripts\Activate.ps1`, then `python -m ensurepip --upgrade`.
* **Port in use:** change dev ports: `npm run dev -- -p 3001` or run Flask on another port.

---

## Roadmap

* Saved sessions (localStorage) + session switcher
* Token/usage badge in UI
* Optional citations + link previews
* Export to Markdown/HTML
* Premium variants: **Main**, **Power**, **GWEN** (hologram), **Nova Engine** (workspace)

---

## License

Choose a license for your repo (MIT recommended).

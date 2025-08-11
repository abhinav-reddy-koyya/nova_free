import os, re
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET", "dev-secret")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ---------------------------
# OpenAI helpers
# ---------------------------
def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None
    return OpenAI(api_key=api_key)

def get_params():
    return {
        "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.6")),
        "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "900")),
    }

# -------------------------------------------------------
# INPUT: Block coding/debugging requests (Free)
# (Allow theory like "define python", "what is Java")
# -------------------------------------------------------
# Triggers when a "code action verb" appears with code-y nouns,
# or explicit “show X code/query/html”.
DISALLOWED_INTENT = re.compile(
    r"(?is)\b("
    r"(write|generate|show|give|make|create|produce|draft|provide|print|output|"
    r"debug|fix|patch|refactor|optimi[sz]e|run|execute|compile|build|"
    r"test|unit[-\s]*test)\s+"
    r".{0,80}?"
    r"(code|script|snippet|example|implementation|program|function|class|"
    r"sql\s*query|migration|endpoint|api\s*route|dockerfile|yaml|"
    r"regex|pattern|schema|table|trigger|stored\s*procedure)"
    r"|pseudocode|algorithm\s*steps"
    r"|(?:html|css|js|javascript|typescript|sql)\s+(?:code|snippet|example|template)"
    r")\b"
)

# -------------------------------------------------------
# OUTPUT: Block code-like content from the model (Free)
# -------------------------------------------------------
CODE_PATTERNS = [
    re.compile(r"```|~~~"),  # fenced code
    re.compile(r"(?mi)^\s*(import |from |def |class |function |const |let |var |#include|using |package|public |private|template|SELECT |INSERT |UPDATE |CREATE TABLE|<!DOCTYPE|<html|<script|<style|BEGIN )"),
    re.compile(r"(?m)(;|\{|\})\s*$"),  # many line terminators
    re.compile(r"(?mi)^\s*\w+\s*=\s*.+$"),  # repeated assignments
    re.compile(r"(?i)\b(int main|#!/|pip install|npm install|conda |apt-get |curl .* \| bash)\b"),
    re.compile(r"(?m)^\s*<[^>]+>\s*$"),  # bare HTML/XML tags
    re.compile(r"`[^`]+`.*`[^`]+`.*`[^`]+`"),  # dense inline code spans
]

def looks_like_code(text: str) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    if any(p.search(text) for p in CODE_PATTERNS):
        return True
    lines = [l.rstrip() for l in text.splitlines()]
    enders = sum(1 for l in lines if l.endswith((';','{','}')))
    assigns = sum(1 for l in lines if re.search(r"^\s*\w+\s*=\s*.+$", l))
    tags = sum(1 for l in lines if re.match(r"^\s*<[^>]+>\s*$", l))
    blocks = text.count("```") + text.count("~~~")
    return (enders >= 3) or (assigns >= 3) or (tags >= 3) or (blocks > 0)

REFUSAL = ("I can explain the concepts at a high level, but I can’t provide code "
           "or implementation steps on the Free plan. To get runnable examples, "
           "please use the premium models (Main/Power or GWEN).")

def enforce_theory_only_output(reply_text: str) -> str:
    return REFUSAL if looks_like_code(reply_text) else reply_text

# -------------------------------------------------------
# Mode detection & prompts
# -------------------------------------------------------
def detect_mode(text: str) -> str:
    t = (text or "").lower()
    if "keyword" in t or "cluster" in t:
        return "keywords"
    if "outline" in t or "h1" in t or "h2" in t:
        return "outline"
    if "brief" in t or "content brief" in t:
        return "brief"
    if "meta" in t or "title tag" in t or "meta description" in t:
        return "meta"
    if "research" in t or "sources" in t or "summary" in t:
        return "research"
    if "article" in t or "blog post" in t or "write about" in t:
        return "article"
    return "general"

# Extra free-tier guard appended to every mode
EXTRA_GUARD_PROMPT = (
    "You are Nova (Free). Provide conceptual/theoretical explanations only. "
    "Do NOT provide source code, shell/SQL commands, configuration blocks, pseudocode, payloads, or "
    "step-by-step implementations. Never use fenced code blocks. "
    "If the user asks for code or implementation, reply ONLY with: "
    "\"I can explain the concepts at a high level, but I can’t provide code or implementation steps on the Free plan. "
    "To get runnable examples, please use the premium models (Main/Power or GWEN).\""
)

TASK_PROMPTS = {
    "general": (
        "You are Nova (Free), a friendly assistant for general conversation, research, and SEO/content help. "
        "Answer clearly and concisely. Avoid fluff."
    ),
    "keywords": (
        "Act as an SEO specialist. Given a topic, produce keyword clusters with head terms, long-tails, "
        "search intent, and suggested internal links in a compact Markdown table."
    ),
    "outline": (
        "Act as an SEO content strategist. Create an H1–H3 outline with compelling headings, FAQs (People Also Ask), "
        "and rich snippet opportunities."
    ),
    "brief": (
        "Create a content brief: audience, angle, goals, target keywords, intent, competitor notes, H2/H3 headings, "
        "internal links, and a clear CTA."
    ),
    "article": (
        "Write a well-structured article with H2/H3 sections, short paragraphs, scannable lists, and a brief intro & conclusion. "
        "Neutral, informative tone."
    ),
    "meta": (
        "Generate 5 SEO titles (<=60 chars) and 5 meta descriptions (<=155 chars) for the given topic. "
        "Include the primary keyword naturally."
    ),
    "research": (
        "Summarize credible sources into a brief: key findings, quick stats, caveats, and suggested further reading. "
        "Avoid hallucination; say when evidence is lacking."
    ),
}

# ---------------------------
# Health/config
# ---------------------------
@app.get("/api/health")
def health():
    p = get_params()
    return jsonify({"ok": True, "model": p["model"]})

@app.get("/api/config")
def config():
    p = get_params()
    return jsonify({"model": p["model"], "temperature": p["temperature"], "max_tokens": p["max_tokens"]})

# ---------------------------
# Chat endpoint
# ---------------------------
@app.post("/api/chat")
def api_chat():
    """
    Request: { "messages": [{role, content}, ...] }
    Response: { "reply": "...", "usage": {...}, "mode": "<chosen>" }
    """
    data = request.get_json(silent=True) or {}
    messages = data.get("messages") or []
    if not isinstance(messages, list) or not messages:
        return jsonify({"error": "messages[] required"}), 400

    # last user message
    last_user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")

    # INPUT guard: block coding/debugging requests (but allow theory like “define python”)
    if DISALLOWED_INTENT.search(last_user or ""):
        reply = (
            "This free version doesn’t provide coding or debugging. "
            "For code generation and developer tools, please use the premium models (Main/Power or GWEN). "
            "If you’d like, I can outline the approach at a high level."
        )
        return jsonify({"reply": reply, "usage": {"blocked": True, "reason": "coding_request"}, "mode": "blocked"})

    mode = detect_mode(last_user)
    base_prompt = TASK_PROMPTS.get(mode, TASK_PROMPTS["general"])
    system_prompt = EXTRA_GUARD_PROMPT + "\n\n" + base_prompt

    # truncate overly long inputs (safety)
    if isinstance(last_user, str) and len(last_user) > 6000:
        last_user = last_user[:6000] + " [...]"

    client = get_client()
    params = get_params()

    # Offline fallback (no API key or client not available)
    if client is None:
        return jsonify({
            "reply": f"[Nova Free • offline {mode}] {last_user}",
            "usage": {"mode": "offline"},
            "mode": mode
        })

    try:
        result = client.chat.completions.create(
            model=params["model"],
            temperature=params["temperature"],
            max_tokens=params["max_tokens"],
            messages=[{"role": "system", "content": system_prompt}, *messages],
        )
        reply = result.choices[0].message.content

        # OUTPUT guard: block code-like model output
        reply = enforce_theory_only_output(reply)

        usage = None
        if getattr(result, "usage", None):
            try:
                usage = result.usage.model_dump()
            except Exception:
                usage = {
                    "prompt_tokens": getattr(result.usage, "prompt_tokens", None),
                    "completion_tokens": getattr(result.usage, "completion_tokens", None),
                    "total_tokens": getattr(result.usage, "total_tokens", None),
                }

        return jsonify({"reply": reply, "usage": usage, "mode": mode})
    except Exception as e:
        return jsonify({"reply": f"Model error: {e}", "usage": {"error": True}, "mode": mode})

if __name__ == "__main__":
    # For local dev; use gunicorn/pm2 in production
    app.run(host="127.0.0.1", port=5000, debug=True)

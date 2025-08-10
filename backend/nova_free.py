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

# Block coding / debugging in Nova Free
DISALLOWED_INTENT = re.compile(
    r"\b(code|coding|program|script|python|javascript|java|c\+\+|c#|golang|go\s+lang|rust|typescript|sql|regex|"
    r"write\s+code|debug|compile|run\s+(this|a)\s*(code|script)|unit\s+test|class\s+\w+|function\s+\w+)\b",
    flags=re.IGNORECASE,
)

# Light intent routing (no dropdown): pick a style when it helps
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

TASK_PROMPTS = {
    "general": (
        "You are Nova (Free), a friendly assistant for general conversation, research, and SEO/content help. "
        "Answer clearly and concisely. Do NOT provide source code, shell commands, or debugging. "
        "If the user asks for coding/debugging, politely explain that coding is available in premium models "
        "(Main/Power or GWEN) and offer a high-level plan instead."
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
        "Neutral, informative tone. Avoid fluff."
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

@app.get("/api/health")
def health():
    p = get_params()
    return jsonify({"ok": True, "model": p["model"]})

@app.get("/api/config")
def config():
    p = get_params()
    return jsonify({"model": p["model"], "temperature": p["temperature"], "max_tokens": p["max_tokens"]})

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

    # block coding/debugging in free tier
    if DISALLOWED_INTENT.search(last_user or ""):
        reply = (
            "This free version doesn’t provide coding or debugging. "
            "For code generation and developer tools, please use the premium models (Main/Power or GWEN). "
            "If you’d like, I can outline the approach at a high level."
        )
        return jsonify({"reply": reply, "usage": {"blocked": True, "reason": "coding_request"}, "mode": "blocked"})

    mode = detect_mode(last_user)
    system_prompt = TASK_PROMPTS.get(mode, TASK_PROMPTS["general"])

    # truncate overly long inputs (safety)
    if isinstance(last_user, str) and len(last_user) > 6000:
        last_user = last_user[:6000] + " [...]"

    client = get_client()
    params = get_params()

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
    app.run(host="127.0.0.1", port=5000, debug=True)

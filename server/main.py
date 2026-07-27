"""
Minimal web service for the Second Brain Seed.

This is a thin deployment wrapper around the repo. It does NOT replace the
agent-operated markdown workflow described in SEED.md — it just gives the
project a live surface on Railway:

  GET  /         -> landing page describing the second brain
  GET  /health   -> health check (used by Railway)
  GET  /skills   -> lists the example skills shipped in .claude/skills
  POST /generate -> generates an image via the nano-banana Gemini skill
                    (requires GEMINI_API_KEY; returns 503 if unset)

Run locally:  python main.py   (serves on $PORT, default 8000)
"""
import base64
import io
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# Load .env from repo root if present (Railway injects real env vars directly).
REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

app = FastAPI(title="Second Brain Seed", version="0.1.0")


def _skills():
    skills_dir = REPO_ROOT / ".claude" / "skills"
    if skills_dir.exists():
        found = sorted(p.name for p in skills_dir.iterdir() if p.is_dir())
        if found:
            return found
    # Fallback for deploys whose build context doesn't include .claude/skills.
    return ["nano-banana-flash", "nano-banana-pro"]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "second-brain-seed",
        "gemini_key_configured": bool(os.environ.get("GEMINI_API_KEY")),
    }


@app.get("/skills")
def skills():
    return {"skills": _skills()}


@app.get("/", response_class=HTMLResponse)
def index():
    key_ok = bool(os.environ.get("GEMINI_API_KEY"))
    badge = (
        '<span class="pill ok">GEMINI_API_KEY set</span>'
        if key_ok
        else '<span class="pill warn">GEMINI_API_KEY missing</span>'
    )
    skill_items = "".join(f"<li><code>/{s}</code></li>" for s in _skills()) or "<li>none</li>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Second Brain Seed</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; min-height: 100vh; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    background: radial-gradient(1200px 600px at 20% -10%, #1e3a8a33, transparent),
                radial-gradient(900px 500px at 100% 0%, #7c3aed33, transparent), #0b0f1a;
    color: #e5e7eb; display: flex; align-items: center; justify-content: center; padding: 32px;
  }}
  .card {{
    max-width: 720px; width: 100%; background: #0f172acc; border: 1px solid #1f2937;
    border-radius: 20px; padding: 40px; box-shadow: 0 20px 60px #0008; backdrop-filter: blur(6px);
  }}
  h1 {{ margin: 0 0 4px; font-size: 34px; letter-spacing: -0.02em; }}
  .sub {{ color: #9ca3af; margin: 0 0 24px; font-size: 15px; }}
  p {{ line-height: 1.6; color: #cbd5e1; }}
  code {{ background: #111827; border: 1px solid #1f2937; padding: 2px 6px; border-radius: 6px; font-size: 13px; }}
  ul {{ line-height: 1.9; }}
  .pill {{ display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }}
  .ok {{ background: #064e3b; color: #6ee7b7; border: 1px solid #065f46; }}
  .warn {{ background: #4a2410; color: #fdba74; border: 1px solid #7c2d12; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 20px; }}
  .box {{ background: #0b1220; border: 1px solid #1f2937; border-radius: 12px; padding: 16px; }}
  .box h3 {{ margin: 0 0 8px; font-size: 13px; text-transform: uppercase; letter-spacing: 0.06em; color: #7dd3fc; }}
  a {{ color: #93c5fd; }}
  footer {{ margin-top: 24px; color: #64748b; font-size: 12px; }}
</style>
</head>
<body>
  <div class="card">
    <h1>Second Brain Seed</h1>
    <p class="sub">A prompt-grown personal knowledge base — now live on Railway. {badge}</p>
    <p>This service is a thin deployment surface for the repo. The real product is the
       agent-operated markdown brain described in <code>SEED.md</code>. This page confirms the
       project is deployed and its example image-generation skills are wired up.</p>
    <div class="grid">
      <div class="box">
        <h3>Endpoints</h3>
        <ul>
          <li><code>GET /health</code></li>
          <li><code>GET /skills</code></li>
          <li><code>POST /generate</code></li>
        </ul>
      </div>
      <div class="box">
        <h3>Example skills</h3>
        <ul>{skill_items}</ul>
      </div>
    </div>
    <footer>Deployed from the second-brain seed · POST a JSON <code>{{"prompt": "..."}}</code> to <code>/generate</code>.</footer>
  </div>
</body>
</html>"""


class GenerateRequest(BaseModel):
    prompt: str
    aspect_ratio: str = "1:1"


@app.post("/generate")
def generate(req: GenerateRequest):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return JSONResponse(
            status_code=503,
            content={
                "error": "GEMINI_API_KEY not configured",
                "hint": "Set GEMINI_API_KEY as a Railway variable (or in .env locally) to enable image generation.",
            },
        )

    # Uses the same code path as the nano-banana-flash skill.
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    cfg_kwargs = {"response_modalities": ["IMAGE"]}
    if hasattr(types, "ImageConfig"):
        cfg_kwargs["image_config"] = types.ImageConfig(aspect_ratio=req.aspect_ratio)

    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=req.prompt,
        config=types.GenerateContentConfig(**cfg_kwargs),
    )

    for part in response.parts:
        if part.inline_data:
            img = part.as_image()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return {"prompt": req.prompt, "mime": "image/png", "image_base64": b64}

    return JSONResponse(status_code=502, content={"error": "no image returned by model"})


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

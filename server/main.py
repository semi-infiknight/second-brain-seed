"""
Minimal web service for the Second Brain Seed.

This is a thin deployment wrapper around the repo. It does NOT replace the
agent-operated markdown workflow described in SEED.md — it just gives the
project a live surface on Railway:

  GET  /         -> landing page describing the second brain
  GET  /health   -> health check (used by Railway)
  GET  /skills   -> lists the example skills shipped in .claude/skills
  POST /generate -> generates an image. Defaults to a free, keyless provider
                    (pollinations.ai) so it works with no secret; uses the
                    nano-banana Gemini skill instead when GEMINI_API_KEY is set.

Run locally:  python main.py   (serves on $PORT, default 8000)
"""
import base64
import io
import os
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# Aspect ratio -> (width, height) for the free provider.
_ASPECT_DIMS = {
    "1:1": (1024, 1024),
    "16:9": (1024, 576),
    "9:16": (576, 1024),
    "4:3": (1024, 768),
    "3:4": (768, 1024),
}

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


def _default_provider():
    return "gemini" if os.environ.get("GEMINI_API_KEY") else "pollinations"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "second-brain-seed",
        "gemini_key_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "default_image_provider": _default_provider(),
    }


@app.get("/skills")
def skills():
    return {"skills": _skills()}


@app.get("/", response_class=HTMLResponse)
def index():
    provider = _default_provider()
    badge = (
        '<span class="pill ok">image provider: Gemini</span>'
        if provider == "gemini"
        else '<span class="pill ok">image provider: Pollinations (free, no key)</span>'
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
       agent-operated markdown brain described in <code>SEED.md</code>. Image generation works out of
       the box via a free, keyless provider (<code>pollinations.ai</code>); set
       <code>GEMINI_API_KEY</code> to switch to the nano-banana Gemini skill.</p>
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
    <div class="box" style="margin-top:16px;">
      <h3>Try image generation (free, no key)</h3>
      <div style="display:flex; gap:8px; margin-top:8px;">
        <input id="prompt" type="text" value="a friendly robot planting a glowing brain seed, flat vector art"
               style="flex:1; padding:10px; border-radius:8px; border:1px solid #1f2937; background:#0b1220; color:#e5e7eb;" />
        <button id="go" style="padding:10px 16px; border:0; border-radius:8px; background:#2563eb; color:#fff; font-weight:600; cursor:pointer;">Generate</button>
      </div>
      <p id="status" style="color:#94a3b8; font-size:13px; margin:10px 0 0;"></p>
      <img id="out" alt="generated image" style="display:none; width:100%; border-radius:12px; margin-top:12px; border:1px solid #1f2937;" />
    </div>
    <footer>Deployed from the second-brain seed · POST a JSON <code>{{"prompt": "..."}}</code> to <code>/generate</code>.</footer>
  </div>
  <script>
    const btn = document.getElementById('go');
    const status = document.getElementById('status');
    const out = document.getElementById('out');
    btn.addEventListener('click', async () => {{
      const prompt = document.getElementById('prompt').value.trim();
      if (!prompt) return;
      btn.disabled = true; status.textContent = 'Generating…'; out.style.display = 'none';
      try {{
        const r = await fetch('/generate', {{
          method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ prompt, aspect_ratio: '1:1' }})
        }});
        const d = await r.json();
        if (d.image_base64) {{
          out.src = 'data:' + (d.mime || 'image/jpeg') + ';base64,' + d.image_base64;
          out.style.display = 'block';
          status.textContent = 'Done · provider: ' + d.provider;
        }} else {{
          status.textContent = 'Error: ' + (d.error || 'unknown');
        }}
      }} catch (e) {{ status.textContent = 'Error: ' + e; }}
      finally {{ btn.disabled = false; }}
    }});
  </script>
</body>
</html>"""


class GenerateRequest(BaseModel):
    prompt: str
    aspect_ratio: str = "1:1"
    # "auto" -> Gemini if GEMINI_API_KEY is set, else the free Pollinations provider.
    provider: str = "auto"


def _generate_pollinations(prompt: str, aspect_ratio: str):
    """Free, keyless text-to-image via pollinations.ai."""
    width, height = _ASPECT_DIMS.get(aspect_ratio, (1024, 1024))
    encoded = urllib.parse.quote(prompt, safe="")
    query = urllib.parse.urlencode(
        {"width": width, "height": height, "nologo": "true", "model": "flux"}
    )
    url = f"https://image.pollinations.ai/prompt/{encoded}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "second-brain-seed/0.1"})
    with urllib.request.urlopen(request, timeout=120) as resp:
        data = resp.read()
        mime = resp.headers.get("Content-Type", "image/jpeg")
    b64 = base64.b64encode(data).decode("ascii")
    return {"prompt": prompt, "provider": "pollinations", "mime": mime, "image_base64": b64}


def _generate_gemini(prompt: str, aspect_ratio: str):
    """Uses the same code path as the nano-banana-flash skill."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    cfg_kwargs = {"response_modalities": ["IMAGE"]}
    if hasattr(types, "ImageConfig"):
        cfg_kwargs["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)

    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
        config=types.GenerateContentConfig(**cfg_kwargs),
    )

    for part in response.parts:
        if part.inline_data:
            img = part.as_image()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return {"prompt": prompt, "provider": "gemini", "mime": "image/png", "image_base64": b64}

    return None


@app.post("/generate")
def generate(req: GenerateRequest):
    provider = req.provider if req.provider != "auto" else _default_provider()

    try:
        if provider == "gemini":
            if not os.environ.get("GEMINI_API_KEY"):
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "GEMINI_API_KEY not configured",
                        "hint": "Use provider 'pollinations' (free, keyless) or set GEMINI_API_KEY.",
                    },
                )
            result = _generate_gemini(req.prompt, req.aspect_ratio)
            if result is None:
                return JSONResponse(status_code=502, content={"error": "no image returned by model"})
            return result

        if provider == "pollinations":
            return _generate_pollinations(req.prompt, req.aspect_ratio)

        return JSONResponse(status_code=400, content={"error": f"unknown provider: {provider}"})
    except Exception as e:  # surface upstream failures without crashing the service
        return JSONResponse(
            status_code=502,
            content={"error": "image generation failed", "provider": provider, "detail": str(e)[:300]},
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

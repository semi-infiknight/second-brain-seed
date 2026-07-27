# For non-Claude agents (Codex, Cursor, etc.)

This repo's brief lives in `SEED.md`. Read it in full, then begin — it tells you how to grow a
second brain shaped to the person you're talking to. Nothing here auto-loads on your platform, so
read `SEED.md` (and any file it names) yourself before acting.

## Cursor Cloud specific instructions

This repo is a **prompt/seed**, not a traditional application. There is no server, build step, lint
config, or test suite — the "product" is an agent-operated markdown knowledge base grown by following
`SEED.md`. Don't look for `package.json`/`requirements.txt`; there are none.

The only runnable code is the example image-generation skill pair in `.claude/skills/`
(`nano-banana-flash`, `nano-banana-pro`). They are Python snippets embedded in each `SKILL.md`, run
inline (there's no wrapper script). Notes:

- Deps (`google-genai`, `Pillow`, `python-dotenv`) are installed by the startup update script. On this
  Ubuntu image, `pip install` requires `--break-system-packages`.
- These skills call the live Gemini API and require a valid `GEMINI_API_KEY`. Provide it as a Cursor
  secret (injected as an env var) or in a local gitignored `.env` (`cp .env.example .env`). The
  snippets read it via `load_dotenv()` + `os.environ.get('GEMINI_API_KEY')`; since `load_dotenv()`
  does not override existing env vars, an injected secret works even without a `.env`.
- The `SKILL.md` snippets use macOS `open` to preview the result — on this Linux VM use `xdg-open`
  (or just reference the saved path).

### Railway deployment (`server/`)

- `server/` holds a small FastAPI web surface for the project (landing page, `/health`, `/skills`,
  `/generate`). It's a deployment wrapper only — the real product is still the `SEED.md` markdown brain.
- It deploys to the Railway `second-brain` project via the `RAILWAY_TOKEN` **project token** (env var).
  Deploy from `server/`: `railway up --service second-brain-web --ci` (Railway auto-detects Python).
  The Railway CLI is not part of the update script; install it on demand with
  `sudo env "PATH=$PATH" npm install -g @railway/cli` (sudo is passwordless on this VM, but `npm`
  isn't on root's PATH, hence the `env PATH` wrapper).
- `railway status` shows "Linked service: None" because a project token isn't tied to a local link —
  that's expected; pass `--service second-brain-web` to CLI commands.
- Live URL: `https://second-brain-web-production-c8eb.up.railway.app`.
- `/generate` works with **no API key** by default via the free, keyless `pollinations.ai` provider.
  If `GEMINI_API_KEY` is set it uses the nano-banana Gemini skill instead; per-request override with
  `{"provider": "pollinations" | "gemini" | "auto"}`.

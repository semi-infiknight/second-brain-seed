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

# Second Brain Seed — deployment service

A thin web surface that gives the repo a live presence on Railway. It does **not** replace the
agent-operated markdown workflow in [`SEED.md`](../SEED.md); it just exposes a landing page, a health
check, and the example Gemini image-generation skill as an HTTP endpoint.

## Endpoints

| Method | Path        | Description                                              |
|--------|-------------|----------------------------------------------------------|
| GET    | `/`         | Landing page                                             |
| GET    | `/health`   | Health check (reports whether `GEMINI_API_KEY` is set)   |
| GET    | `/skills`   | Lists the example skills                                  |
| POST   | `/generate` | `{ "prompt": "...", "aspect_ratio": "1:1" }` → PNG (base64). Needs `GEMINI_API_KEY`. |

## Run locally

```bash
pip install -r requirements.txt
python main.py            # serves on $PORT (default 8000)
```

## Deploy on Railway

The repo's `RAILWAY_TOKEN` (a project token for the `second-brain` project) is used by the Railway
CLI. From this directory:

```bash
railway up                # builds & deploys this directory (Nixpacks: Python)
railway domain            # generates a public URL
```

Set `GEMINI_API_KEY` as a Railway variable to enable `/generate`:

```bash
railway variables --set GEMINI_API_KEY=your_key
```

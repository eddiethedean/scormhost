# FastAPI Cloud example

Deployable SCORM host with **bundled demo courses** built using [LXPack](https://github.com/eddiethedean/lxpack).

## Bundled courses

On startup (default), the app ingests SCORM ZIPs from `bundled/`:

- **`security-awareness`** (SCORM 1.2) — built from `course/`
- **`branching-demo`** (SCORM 2004) — built from `courses/branching-demo/`
- **`xapi-awareness`** (SCORM 1.2) — built from `courses/xapi-awareness/`

Disable seeding with `SCORMHOST_SEED_BUNDLED_COURSE=false`.

## Local run

```bash
cd examples/cloud
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 — the demo course should appear on the catalog.

## Rebuild the SCORM ZIP (LXPack)

Source lives in `course/` (from [lxpack/examples/security-awareness](https://github.com/eddiethedean/lxpack/tree/main/examples/security-awareness)).

```bash
cd examples/cloud
npm install
npm run build:all
```

This runs `lxpack build` via the local `node_modules` CLI (not `npx`, which can pull an unexpected runtime). Requires **@lxpack/cli 0.3.5+** with a self-contained runtime bundle (no `import … from "@lxpack/validators"` in `lxpack-runtime.js`).

If you already seeded an older bundle locally, remove `data/packages/security-awareness` and restart so the app re-ingests the updated ZIP.

## Deploy to FastAPI Cloud

```bash
cd examples/cloud
pip install -r requirements.txt
fastapi login
fastapi deploy
```

Set in the dashboard:

- `SCORMHOST_DATA_DIR` — persistent storage for uploads and progress
- `SCORMHOST_SECRET_KEY` — stable JWT secret
- `SCORMHOST_COOKIE_SECURE=true`

# FastAPI Cloud example

Deployable SCORM host with a **bundled demo course** built using [LXPack](https://github.com/eddiethedean/lxpack).

## Bundled course

On startup (default), the app ingests `bundled/security-awareness-scorm12.zip` — a SCORM 1.2 package built from the LXPack **Security Awareness** sample in `course/`.

- **Package id:** `security-awareness`
- **Launch:** `/launch/security-awareness` or from the catalog at `/`

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
npm run build:course
```

This runs `lxpack build --target scorm12` via the local `node_modules` CLI (not `npx`, which can pull an older runtime). Requires **@lxpack/cli 0.3.5+** with a self-contained runtime bundle (no `import … from "@lxpack/validators"` in `lxpack-runtime.js`). After upgrading LXPack, copy a rebuilt `@lxpack/runtime` `dist/client.js` into `node_modules` if needed, then run `npm run build:course`.

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

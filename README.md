# scormhost

Turn [FastAPI](https://fastapi.tiangolo.com/) into a small **SCORM 1.2 / 2004 hosting app** you can run locally or deploy to [FastAPI Cloud](https://fastapicloud.com/).

Works with packages built by [LXPack](https://github.com/eddiethedean/lxpack) (`lxpack build --target scorm12` / `scorm2004`) and other compliant SCORM ZIPs.

## Features

- Upload SCORM ZIPs via web UI or `POST /api/packages`
- Launch courses in an iframe with a **parent-frame SCORM API** (`window.API` / `window.API_1484_11`) synced to the server
- Persist learner CMI (suspend data, scores, completion) as JSON on disk
- Multi-SCO SCORM 2004: activity picker when the manifest lists multiple items
- Path-safe static serving of package files

## Quick start

```bash
git clone https://github.com/eddiethedean/scormhost.git
cd scormhost
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

fastapi dev
```

Or use the factory explicitly:

```python
from scormhost import create_scorm_app

app = create_scorm_app(data_dir="./data", title="My SCORM Host")
```

Open http://127.0.0.1:8000 — upload a `.zip`, then **Launch**.

### Mount on an existing FastAPI app

```python
from fastapi import FastAPI
from scormhost import ScormHost

app = FastAPI()
ScormHost(data_dir="./data", title="Training").mount(app)
```

## Deploy to FastAPI Cloud

```bash
cd examples/cloud
pip install -r requirements.txt
fastapi login
fastapi deploy
```

Configure in the cloud dashboard:

| Variable | Purpose |
|----------|---------|
| `SCORMHOST_DATA_DIR` | Persistent volume path for uploaded packages (required for uploads to survive redeploys) |
| `SCORMHOST_TITLE` | Catalog page title |
| `SCORMHOST_ALLOW_UPLOAD` | Set `false` to make the host read-only |

The example entrypoint is `main:app` (see `examples/cloud/pyproject.toml` → `[tool.fastapi]`).

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCORMHOST_DATA_DIR` | `./data` | Root for `packages/` and `sessions/` |
| `SCORMHOST_TITLE` | `SCORM Host` | Home page heading |
| `SCORMHOST_ALLOW_UPLOAD` | `true` | Enable ZIP uploads |
| `SCORMHOST_MAX_UPLOAD_MB` | `100` | Max upload size |
| `SCORMHOST_DEFAULT_LEARNER` | `demo-learner` | Learner id when not passed in query |

Pass `?learner_id=...` on launch URLs to separate progress per user.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Package catalog (HTML) |
| `GET` | `/launch/{package_id}` | SCORM player (iframe + API shim) |
| `GET` | `/content/{package_id}/{path}` | Package static files |
| `POST` | `/api/packages` | Upload SCORM ZIP (`multipart/form-data`, field `file`) |
| `GET` | `/api/packages` | List packages (JSON) |
| `DELETE` | `/api/packages/{id}` | Remove package |
| `GET/PUT` | `/api/scorm/{id}/cmi` | Learner CMI state |

## Limits (v0.1)

- File-based storage only (no database)
- No authentication — use a reverse proxy or disable uploads in production
- cmi5 / xAPI packages are not launched (upload may work if they include `imsmanifest.xml`, but runtime expects SCORM APIs)
- SCORM 2004 sequencing rules are not enforced server-side; each SCO is launched independently

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

Apache-2.0 — see [LICENSE](LICENSE).

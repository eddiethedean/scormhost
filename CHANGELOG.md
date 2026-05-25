# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - 2026-05-25

First public release.

### Added

- FastAPI app factory (`create_scorm_app`) and `ScormHost` router mount helper
- SCORM 1.2 and 2004 package hosting (ZIP upload, manifest parsing, launch player)
- JWT auth with roles (`learner`, `instructor`, `admin`), refresh tokens, and HTML admin UI
- Public course catalog with optional login; guest progress via browser cookie
- SQLite + Alembic migrations (bundled in the `scormhost` package)
- SCORM API shims (`scorm12-api.js`, `scorm2004-api.js`) with server-side CMI persistence
- FastAPI Cloud example under `examples/cloud`

### Security

- Package ID and zip extract path-traversal hardening
- Validated guest learner cookies; login password length limits
- Refresh token rotation with reuse detection; revoke-all on password change
- Safe launch URL allowlist; improved SCORM 2004 schema detection

[0.1.0]: https://github.com/eddiethedean/scormhost/releases/tag/v0.1.0

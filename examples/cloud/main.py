"""
Deploy this app to FastAPI Cloud::

    cd examples/cloud
    pip install -r requirements.txt
    fastapi login
    fastapi deploy

Set ``SCORMHOST_DATA_DIR`` in the cloud dashboard for persistent uploads.
"""

import os

from scormhost import create_scorm_app

app = create_scorm_app(
    data_dir=os.environ.get("SCORMHOST_DATA_DIR", "./data"),
    title=os.environ.get("SCORMHOST_TITLE", "SCORM Host"),
    allow_upload=os.environ.get("SCORMHOST_ALLOW_UPLOAD", "true").lower()
    not in ("0", "false", "no"),
)

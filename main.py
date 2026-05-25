"""Local entrypoint: ``fastapi dev`` or ``uvicorn main:app --reload``."""

from scormhost import create_scorm_app

app = create_scorm_app()

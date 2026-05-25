"""Host SCORM packages on FastAPI."""

from scormhost.app import create_scorm_app
from scormhost.host import ScormHost
from scormhost.config import HostSettings

__all__ = ["create_scorm_app", "ScormHost", "HostSettings"]
__version__ = "0.1.0"

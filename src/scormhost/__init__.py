"""Host SCORM packages on FastAPI."""

from scormhost.app import create_scorm_app
from scormhost.config import HostSettings
from scormhost.host import ScormHost

try:
    from importlib.metadata import version

    __version__ = version("scormhost")
except Exception:
    __version__ = "0.1.0"

__all__ = ["create_scorm_app", "ScormHost", "HostSettings", "__version__"]

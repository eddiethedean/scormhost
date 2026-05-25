from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scormhost.config import HostSettings
from scormhost.manifest import PackageManifest, parse_imsmanifest, slugify_package_id


@dataclass
class PackageRecord:
    id: str
    title: str
    schema_version: str
    uploaded_at: str
    launch_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PackageStore:
    def __init__(self, settings: HostSettings) -> None:
        self.settings = settings
        self.settings.packages_dir.mkdir(parents=True, exist_ok=True)
        self.settings.sessions_dir.mkdir(parents=True, exist_ok=True)

    def package_root(self, package_id: str) -> Path:
        safe = re.sub(r"[^a-zA-Z0-9._-]+", "", package_id)
        if not safe or safe != package_id:
            raise ValueError("Invalid package id")
        return self.settings.packages_dir / safe

    def meta_path(self, package_id: str) -> Path:
        return self.package_root(package_id) / ".scormhost.json"

    def load_meta(self, package_id: str) -> dict[str, Any]:
        path = self.meta_path(package_id)
        if not path.is_file():
            raise FileNotFoundError(package_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def save_meta(self, package_id: str, meta: dict[str, Any]) -> None:
        path = self.meta_path(package_id)
        path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def list_packages(self) -> list[PackageRecord]:
        records: list[PackageRecord] = []
        if not self.settings.packages_dir.is_dir():
            return records
        for entry in sorted(self.settings.packages_dir.iterdir()):
            if not entry.is_dir():
                continue
            meta_file = entry / ".scormhost.json"
            if not meta_file.is_file():
                continue
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            manifest = meta.get("manifest", {})
            records.append(
                PackageRecord(
                    id=meta["id"],
                    title=manifest.get("title", meta["id"]),
                    schema_version=manifest.get("schema_version", "1.2"),
                    uploaded_at=meta.get("uploaded_at", ""),
                    launch_count=len(manifest.get("launches", [])),
                ),
            )
        return records

    def register_package(
        self,
        package_id: str,
        manifest: PackageManifest,
        original_filename: str,
        *,
        uploaded_by_id: int | None = None,
    ) -> None:
        self.save_meta(
            package_id,
            {
                "id": package_id,
                "original_filename": original_filename,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "uploaded_by_id": uploaded_by_id,
                "manifest": {
                    "title": manifest.title,
                    "identifier": manifest.identifier,
                    "schema_version": manifest.schema_version,
                    "launches": [
                        {
                            "identifier": item.identifier,
                            "title": item.title,
                            "href": item.href,
                        }
                        for item in manifest.launches
                    ],
                },
            },
        )

    def ingest_extracted(
        self,
        extract_dir: Path,
        original_filename: str,
        preferred_id: str | None = None,
        uploaded_by_id: int | None = None,
    ) -> str:
        manifest_path = extract_dir / "imsmanifest.xml"
        if not manifest_path.is_file():
            raise ValueError("Package must contain imsmanifest.xml")

        parsed = parse_imsmanifest(manifest_path)
        base_id = preferred_id or slugify_package_id(
            Path(original_filename).stem or parsed.title,
        )
        package_id = base_id
        suffix = 1
        while self.package_root(package_id).exists():
            package_id = f"{base_id}-{suffix}"
            suffix += 1

        dest = self.package_root(package_id)
        shutil.copytree(extract_dir, dest, dirs_exist_ok=False)

        self.register_package(
            package_id,
            parsed,
            original_filename,
            uploaded_by_id=uploaded_by_id,
        )
        return package_id


class SessionStore:
    def __init__(self, settings: HostSettings) -> None:
        self.settings = settings
        self.settings.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(
        self,
        package_id: str,
        learner_id: str,
        launch_href: str,
    ) -> Path:
        safe_learner = re.sub(r"[^a-zA-Z0-9._@-]+", "_", learner_id)[:128]
        safe_launch = re.sub(r"[^a-zA-Z0-9._/-]+", "_", launch_href)[:200]
        folder = self.settings.sessions_dir / package_id
        folder.mkdir(parents=True, exist_ok=True)
        name = f"{safe_learner}__{safe_launch.replace('/', '_')}.json"
        return folder / name

    def load_cmi(
        self,
        package_id: str,
        learner_id: str,
        launch_href: str,
    ) -> dict[str, str]:
        path = self._session_path(package_id, learner_id, launch_href)
        if not path.is_file():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        elements = data.get("elements", {})
        return {str(k): str(v) for k, v in elements.items()}

    def save_cmi(
        self,
        package_id: str,
        learner_id: str,
        launch_href: str,
        elements: dict[str, str],
    ) -> None:
        path = self._session_path(package_id, learner_id, launch_href)
        path.write_text(
            json.dumps(
                {
                    "package_id": package_id,
                    "learner_id": learner_id,
                    "launch_href": launch_href,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "elements": elements,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LaunchItem:
    identifier: str
    title: str
    href: str


@dataclass(frozen=True)
class PackageManifest:
    schema_version: str
    title: str
    identifier: str
    launches: tuple[LaunchItem, ...]

    @property
    def is_scorm_2004(self) -> bool:
        return "2004" in self.schema_version

    @property
    def primary_launch(self) -> LaunchItem | None:
        return self.launches[0] if self.launches else None


def _local_tag(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _text(elem: ET.Element | None) -> str:
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def _find_children(parent: ET.Element, local_name: str) -> list[ET.Element]:
    return [c for c in parent if _local_tag(c.tag) == local_name]


def _find_first(parent: ET.Element, local_name: str) -> ET.Element | None:
    for child in parent:
        if _local_tag(child.tag) == local_name:
            return child
    return None


def parse_imsmanifest(manifest_path: Path) -> PackageManifest:
    tree = ET.parse(manifest_path)
    root = tree.getroot()

    schema_version = "1.2"
    for elem in root.iter():
        if _local_tag(elem.tag) == "schemaversion" and elem.text:
            schema_version = elem.text.strip()
            break

    identifier = root.attrib.get("identifier", "course")

    resources: dict[str, str] = {}
    resource_titles: dict[str, str] = {}
    for elem in root.iter():
        if _local_tag(elem.tag) != "resource":
            continue
        rid = elem.attrib.get("identifier")
        href = elem.attrib.get("href")
        if rid and href:
            resources[rid] = href.replace("\\", "/")
            title_elem = _find_first(elem, "title")
            if title_elem is not None:
                resource_titles[rid] = _text(title_elem)

    org_title = "Course"
    launches: list[LaunchItem] = []

    organizations = [
        e for e in root.iter() if _local_tag(e.tag) == "organization"
    ]
    org = organizations[0] if organizations else None
    if org is not None:
        org_title_elem = _find_first(org, "title")
        if org_title_elem is not None:
            org_title = _text(org_title_elem) or org_title

        for item in _find_children(org, "item"):
            item_id = item.attrib.get("identifier", "")
            title_elem = _find_first(item, "title")
            item_title = _text(title_elem) if title_elem is not None else item_id
            ref = item.attrib.get("identifierref")
            if ref and ref in resources:
                launches.append(
                    LaunchItem(
                        identifier=item_id or ref,
                        title=item_title or ref,
                        href=resources[ref],
                    ),
                )

    if not launches:
        for rid, href in resources.items():
            if href.endswith(".html") or href == "index.html":
                launches.append(
                    LaunchItem(
                        identifier=rid,
                        title=resource_titles.get(rid, rid),
                        href=href,
                    ),
                )

    if not launches:
        index = resources.get("resource_1")
        if index:
            launches.append(LaunchItem("default", org_title, index))

    return PackageManifest(
        schema_version=schema_version,
        title=org_title,
        identifier=identifier,
        launches=tuple(launches),
    )


def slugify_package_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "package"

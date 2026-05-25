from pathlib import Path

from scormhost.manifest import is_scorm_2004_schema, parse_imsmanifest

FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="security-awareness" version="1.0.0"
  xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
  xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2">
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>1.2</schemaversion>
  </metadata>
  <organizations default="security-awareness-org">
    <organization identifier="security-awareness-org">
      <title>Security Awareness</title>
      <item identifier="item_1" identifierref="resource_1">
        <title>Security Awareness</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="resource_1" type="webcontent" adlcp:scormtype="sco" href="index.html">
      <file href="index.html"/>
    </resource>
  </resources>
</manifest>
"""


def test_is_scorm_2004_schema() -> None:
    assert is_scorm_2004_schema("1.3") is True
    assert is_scorm_2004_schema("1.3.1") is True
    assert is_scorm_2004_schema("CAM 1.3") is True
    assert is_scorm_2004_schema("1.2") is False


def test_parse_scorm12_manifest(tmp_path: Path) -> None:
    path = tmp_path / "imsmanifest.xml"
    path.write_text(FIXTURE, encoding="utf-8")
    parsed = parse_imsmanifest(path)
    assert parsed.schema_version == "1.2"
    assert parsed.title == "Security Awareness"
    assert len(parsed.launches) == 1
    assert parsed.launches[0].href == "index.html"

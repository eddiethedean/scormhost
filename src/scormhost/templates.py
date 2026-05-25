from __future__ import annotations

import html
import json
from typing import Any


def catalog_page(title: str, packages: list[dict[str, Any]], allow_upload: bool) -> str:
    rows = []
    for pkg in packages:
        pid = html.escape(pkg["id"])
        ptitle = html.escape(pkg["title"])
        schema = html.escape(pkg.get("schema_version", "1.2"))
        launch_count = pkg.get("launch_count", 1)
        if launch_count > 1:
            link = f'<a href="/packages/{pid}">Open ({launch_count} activities)</a>'
        else:
            link = f'<a href="/launch/{pid}">Launch</a>'
        rows.append(
            f"<tr><td>{ptitle}</td><td><code>{pid}</code></td>"
            f"<td>{schema}</td><td>{link}</td></tr>",
        )

    table_body = "\n".join(rows) if rows else (
        "<tr><td colspan='4'>No packages yet. Upload a SCORM ZIP below.</td></tr>"
    )

    upload_form = ""
    if allow_upload:
        upload_form = """
    <section class="upload">
      <h2>Upload SCORM package</h2>
      <form action="/api/packages" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".zip" required />
        <button type="submit">Upload</button>
      </form>
    </section>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 960px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: left; }}
    th {{ background: #f4f4f5; }}
    .upload {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ddd; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p>SCORM 1.2 and 2004 packages built with <a href="https://lxpack.readthedocs.io/">LXPack</a> or any compliant authoring tool.</p>
  <table>
    <thead><tr><th>Title</th><th>Id</th><th>Schema</th><th></th></tr></thead>
    <tbody>{table_body}</tbody>
  </table>
  {upload_form}
</body>
</html>"""


def package_detail_page(
    title: str,
    package_id: str,
    launches: list[dict[str, str]],
) -> str:
    items = []
    for launch in launches:
        href = html.escape(launch["href"])
        label = html.escape(launch.get("title") or launch["href"])
        lid = html.escape(launch.get("identifier", ""))
        url = f"/launch/{html.escape(package_id)}?launch={html.escape(launch['href'])}"
        items.append(f'<li><a href="{url}">{label}</a> <code>{href}</code></li>')

    list_html = "\n".join(items)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(title)} — activities</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 720px; }}
    a {{ color: #2563eb; }}
  </style>
</head>
<body>
  <p><a href="/">← Catalog</a></p>
  <h1>{html.escape(title)}</h1>
  <p>Package <code>{html.escape(package_id)}</code> — choose an activity:</p>
  <ul>{list_html}</ul>
</body>
</html>"""


def launcher_page(
    *,
    package_title: str,
    package_id: str,
    launch_href: str,
    is_scorm_2004: bool,
    scorm_config: dict[str, Any],
    api_script: str,
) -> str:
    config_json = json.dumps(scorm_config).replace("<", "\\u003c")
    global_name = "__SCORMHOST_SCORM2004__" if is_scorm_2004 else "__SCORMHOST_SCORM12__"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(package_title)} — launch</title>
  <style>
    html, body {{ margin: 0; height: 100%; }}
    iframe {{ border: 0; width: 100%; height: 100vh; display: block; }}
  </style>
</head>
<body>
  <iframe id="scormhost-content" title="{html.escape(package_title)}"></iframe>
  <script>window.{global_name} = {config_json};</script>
  <script src="{html.escape(api_script)}"></script>
</body>
</html>"""

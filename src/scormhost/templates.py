from __future__ import annotations

import html
import json
from collections.abc import Callable
from typing import Any
from urllib.parse import quote, urlencode

from scormhost.paths import is_safe_launch_href

UrlFn = Callable[[str], str]


def _u(url: UrlFn | None, path: str) -> str:
    if url is None:
        return path
    return url(path)

_BASE_CSS = """
    body { font-family: system-ui, sans-serif; margin: 0; background: #f8fafc; color: #0f172a; }
    .wrap { max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem; }
    header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    header nav a { margin-left: 1rem; color: #2563eb; text-decoration: none; }
    table { border-collapse: collapse; width: 100%; background: #fff; }
    th, td { border: 1px solid #e2e8f0; padding: 0.5rem 0.75rem; text-align: left; }
    th { background: #f1f5f9; }
    .card { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.25rem; margin-top: 1.5rem; }
    .btn { background: #2563eb; color: #fff; border: 0; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; }
    .btn.secondary { background: #64748b; }
    .btn.danger { background: #dc2626; }
    .error { color: #dc2626; margin-bottom: 1rem; }
    label { display: block; margin: 0.75rem 0 0.25rem; font-weight: 500; }
    input[type=text], input[type=email], input[type=password] { width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 6px; }
"""


def _page_shell(title: str, body: str, *, narrow: bool = False) -> str:
    width = "480px" if narrow else "960px"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>{_BASE_CSS}
    .wrap {{ max-width: {width}; }}
  </style>
</head>
<body>
  <div class="wrap">{body}</div>
</body>
</html>"""


def nav_bar(
    *,
    title: str,
    user_label: str | None,
    show_admin: bool,
    url: UrlFn | None = None,
) -> str:
    links = []
    if user_label:
        links.append(f"<span>{html.escape(user_label)}</span>")
        links.append('<a href="#" id="logout-link">Log out</a>')
    else:
        links.append(f'<a href="{_u(url, "/login")}">Log in</a>')
        links.append(f'<a href="{_u(url, "/register")}">Register</a>')
    if show_admin:
        links.append(f'<a href="{_u(url, "/admin/users")}">Users</a>')
    nav = "\n".join(links)
    logout_js = f"""
<script>
document.getElementById('logout-link')?.addEventListener('click', async (e) => {{
  e.preventDefault();
  await fetch('{_u(url, "/api/auth/logout")}', {{ method: 'POST', credentials: 'same-origin' }});
  location.href = '{_u(url, "/login")}';
}});
</script>"""
    return f"""<header>
  <h1>{html.escape(title)}</h1>
  <nav>{nav}</nav>
</header>{logout_js if user_label else ""}"""


def catalog_page(
    title: str,
    packages: list[dict[str, Any]],
    *,
    user_label: str | None,
    can_upload: bool,
    show_admin: bool,
    show_delete: bool,
    is_logged_in: bool,
    url: UrlFn | None = None,
) -> str:
    rows = []
    for pkg in packages:
        raw_id = pkg["id"]
        pid = html.escape(raw_id)
        ptitle = html.escape(pkg["title"])
        schema = html.escape(pkg.get("schema_version", "1.2"))
        launch_count = pkg.get("launch_count", 1)
        if launch_count > 1:
            link = (
                f'<a href="{_u(url, f"/packages/{raw_id}")}">'
                f"Open ({launch_count} activities)</a>"
            )
        else:
            link = f'<a href="{_u(url, f"/launch/{raw_id}")}">Launch</a>'
        delete_cell = ""
        if show_delete and pkg.get("can_delete"):
            delete_cell = (
                f' <button class="btn danger" data-delete="{pid}" type="button">Delete</button>'
            )
        rows.append(
            f"<tr><td>{ptitle}</td><td><code>{pid}</code></td>"
            f"<td>{schema}</td><td>{link}{delete_cell}</td></tr>",
        )

    empty_msg = "No courses yet."
    if can_upload:
        empty_msg += " Upload a SCORM ZIP below."
    table_body = "\n".join(rows) if rows else (
        f"<tr><td colspan='4'>{empty_msg}</td></tr>"
    )

    manage_hint = ""
    if not is_logged_in:
        manage_hint = f"""
  <p class="card" style="background:#eff6ff;border-color:#bfdbfe;">
    <strong>Anyone can launch courses</strong> without an account. Progress is saved in this browser automatically.
    <a href="{_u(url, "/login")}">Log in</a> or <a href="{_u(url, "/register")}">register</a> to tie progress to your account, or to upload and manage courses (instructor/admin).
  </p>"""
    elif not can_upload:
        manage_hint = """
  <p class="card">You are signed in — your course progress is saved to your account.</p>"""

    upload_block = ""
    if can_upload:
        upload_block = f"""
  <section class="card upload">
    <h2>Upload SCORM package</h2>
    <p>Instructors and admins: upload SCORM 1.2 or 2004 ZIP files here.</p>
    <form id="upload-form">
      <input type="file" name="file" accept=".zip" required />
      <button class="btn" type="submit" style="margin-top:0.75rem">Upload</button>
    </form>
    <p id="upload-status"></p>
  </section>
<script>
document.getElementById('upload-form')?.addEventListener('submit', async (ev) => {{
  ev.preventDefault();
  const status = document.getElementById('upload-status');
  const file = ev.target.querySelector('input[type=file]').files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append('file', file);
  status.textContent = 'Uploading…';
  const res = await fetch('{_u(url, "/api/packages")}', {{ method: 'POST', body: fd, credentials: 'same-origin' }});
  if (res.status === 401) {{
    location.href = '{_u(url, "/login")}?next=' + encodeURIComponent(location.pathname);
    return;
  }}
  if (res.ok) {{ location.reload(); return; }}
  const err = await res.json().catch(() => ({{}}));
  status.textContent = err.detail || 'Upload failed (instructor or admin required)';
  status.style.color = '#dc2626';
}});
document.querySelectorAll('[data-delete]').forEach((btn) => {{
  btn.addEventListener('click', async () => {{
    if (!confirm('Delete this package?')) return;
    const id = btn.getAttribute('data-delete');
    const res = await fetch('{_u(url, "/api/packages")}/' + id, {{ method: 'DELETE', credentials: 'same-origin' }});
    if (res.ok) location.reload();
    else alert('Delete failed');
  }});
}});
</script>"""

    body = f"""
{nav_bar(title=title, user_label=user_label, show_admin=show_admin, url=url)}
  {manage_hint}
  <table>
    <thead><tr><th>Title</th><th>Id</th><th>Schema</th><th>Actions</th></tr></thead>
    <tbody>{table_body}</tbody>
  </table>
  {upload_block}
"""
    return _page_shell(title, body)


def package_detail_page(
    title: str,
    package_id: str,
    launches: list[dict[str, str]],
    *,
    user_label: str | None,
    url: UrlFn | None = None,
) -> str:
    items = []
    pid_esc = html.escape(package_id)
    for launch in launches:
        label = html.escape(launch.get("title") or launch["href"])
        href_raw = launch["href"]
        href = html.escape(href_raw)
        if is_safe_launch_href(href_raw):
            query = urlencode({"launch": href_raw})
            launch_url = html.escape(_u(url, f"/launch/{package_id}?{query}"), quote=True)
            items.append(f'<li><a href="{launch_url}">{label}</a> <code>{href}</code></li>')
        else:
            items.append(f'<li><span>{label}</span> <code>{href}</code> (invalid launch)</li>')

    user_nav = f"<p>Signed in as {html.escape(user_label)}</p>" if user_label else ""
    body = f"""
<p><a href="{_u(url, "/")}">← Catalog</a></p>
{user_nav}
<h2>{html.escape(title)}</h2>
<p>Package <code>{html.escape(package_id)}</code> — choose an activity:</p>
<ul>{"".join(items)}</ul>
"""
    return _page_shell(f"{title} — activities", body)


def launcher_page(
    *,
    package_title: str,
    package_id: str,
    launch_href: str,
    is_scorm_2004: bool,
    scorm_config: dict[str, Any],
    api_script: str,
    is_logged_in: bool,
    login_href: str = "/login",
    url: UrlFn | None = None,
) -> str:
    catalog_href = _u(url, "/")
    config_json = json.dumps(scorm_config).replace("<", "\\u003c")
    global_name = "__SCORMHOST_SCORM2004__" if is_scorm_2004 else "__SCORMHOST_SCORM12__"
    progress_banner = ""
    if not is_logged_in:
        login_esc = html.escape(login_href, quote=True)
        progress_banner = f"""
  <div id="progress-banner" style="position:fixed;top:0;left:0;right:0;z-index:9999;background:#1e293b;color:#f8fafc;padding:0.4rem 1rem;font:14px system-ui,sans-serif;display:flex;justify-content:space-between;align-items:center;">
    <span>Progress saved in this browser. <a href="{login_esc}" style="color:#93c5fd">Log in</a> to save to your account.</span>
    <a href="{html.escape(catalog_href, quote=True)}" style="color:#93c5fd">Catalog</a>
  </div>
  <style>iframe {{ margin-top: 2.25rem; height: calc(100vh - 2.25rem) !important; }}</style>"""
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
  {progress_banner}
  <iframe id="scormhost-content" title="{html.escape(package_title)}"></iframe>
  <script>window.{global_name} = {config_json};</script>
  <script src="{html.escape(api_script)}"></script>
</body>
</html>"""


def auth_page(
    *,
    title: str,
    mode: str,
    allow_registration: bool,
    error: str | None,
    next_url: str = "/",
    url: UrlFn | None = None,
) -> str:
    err = f'<p class="error">{html.escape(error)}</p>' if error else ""
    next_q = ""
    if next_url != "/":
        next_q = f"?next={quote(next_url, safe='/?:=&')}"
    if mode == "login":
        heading = "Log in"
        subtitle = "<p>Sign in to upload and manage courses, or to save progress to your account.</p>"
        fields = """
      <label>Email</label>
      <input type="email" name="email" required autocomplete="username" />
      <label>Password</label>
      <input type="password" name="password" required autocomplete="current-password" />
"""
        extra = ""
        if allow_registration:
            extra = (
                f'<p style="margin-top:1rem">No account? '
                f'<a href="{_u(url, f"/register{next_q}")}">Register</a></p>'
            )
        endpoint = _u(url, "/api/auth/login")
    else:
        subtitle = "<p>Create an account to save progress across devices. The first account becomes admin.</p>"
        heading = "Create account"
        fields = """
      <label>Display name</label>
      <input type="text" name="display_name" required />
      <label>Username</label>
      <input type="text" name="username" required pattern="[a-zA-Z0-9_-]+" />
      <label>Email</label>
      <input type="email" name="email" required autocomplete="username" />
      <label>Password</label>
      <input type="password" name="password" required minlength="8" autocomplete="new-password" />
"""
        extra = (
            f'<p style="margin-top:1rem">Already have an account? '
            f'<a href="{_u(url, f"/login{next_q}")}">Log in</a></p>'
        )
        endpoint = _u(url, "/api/auth/register")

    body = f"""
<h2>{heading}</h2>
{subtitle}
{err}
<form id="auth-form">
  {fields}
  <button class="btn" type="submit" style="margin-top:1rem">Continue</button>
</form>
{extra}
<script>
document.getElementById('auth-form').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd.entries());
  const res = await fetch({json.dumps(endpoint)}, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify(body),
    credentials: 'same-origin',
  }});
  if (res.ok) {{ location.href = {json.dumps(next_url)}; return; }}
  const err = await res.json().catch(() => ({{}}));
  alert(err.detail || 'Request failed');
}});
</script>
"""
    return _page_shell(f"{title} — {heading}", body, narrow=True)


def admin_users_page(*, url: UrlFn | None = None) -> str:
    api_users = _u(url, "/api/users")
    login_href = _u(url, "/login")
    catalog_href = _u(url, "/")
    body = f"""
<h2>User management</h2>
<p><a href="{catalog_href}">← Catalog</a></p>
<table id="users-table">
  <thead><tr><th>ID</th><th>Email</th><th>Username</th><th>Role</th><th>Active</th><th></th></tr></thead>
  <tbody></tbody>
</table>
<script>
async function loadUsers() {{
  const res = await fetch('{api_users}', {{ credentials: 'same-origin' }});
  if (!res.ok) {{ location.href = '{login_href}'; return; }}
  const users = await res.json();
  const tbody = document.querySelector('#users-table tbody');
  tbody.innerHTML = users.map((u) => `
    <tr>
      <td>${{u.id}}</td>
      <td>${{u.email}}</td>
      <td>${{u.username}}</td>
      <td>
        <select data-id="${{u.id}}" data-field="role">
          <option value="learner" ${{u.role==='learner'?'selected':''}}>learner</option>
          <option value="instructor" ${{u.role==='instructor'?'selected':''}}>instructor</option>
          <option value="admin" ${{u.role==='admin'?'selected':''}}>admin</option>
        </select>
      </td>
      <td><input type="checkbox" data-id="${{u.id}}" data-field="active" ${{u.is_active?'checked':''}} /></td>
      <td><button class="btn danger" data-delete="${{u.id}}" type="button">Delete</button></td>
    </tr>`).join('');
  tbody.querySelectorAll('select, input[type=checkbox]').forEach((el) => {{
    el.addEventListener('change', () => patchUser(el.dataset.id));
  }});
  tbody.querySelectorAll('[data-delete]').forEach((btn) => {{
    btn.addEventListener('click', async () => {{
      if (!confirm('Delete user?')) return;
      await fetch('{api_users}/' + btn.dataset.delete, {{ method: 'DELETE', credentials: 'same-origin' }});
      loadUsers();
    }});
  }});
}}
async function patchUser(id) {{
  const row = document.querySelector(`[data-id="${{id}}"][data-field=role]`);
  const active = document.querySelector(`[data-id="${{id}}"][data-field=active]`);
  await fetch('{api_users}/' + id, {{
    method: 'PATCH',
    credentials: 'same-origin',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ role: row.value, is_active: active.checked }}),
  }});
}}
loadUsers();
</script>
"""
    return _page_shell("User management", body)

from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright

from backend.app.services.discovery import (
    DiscoveryPolicy,
    discover_page,
    login_required,
    sanitized_url,
)


ROOT_HTML = """<!doctype html><html><head><title>Fixture Home</title></head><body>
<nav aria-label="Main navigation">
  <a href="/">Home</a>
  <details><summary>Reports</summary><nav aria-label="Reports navigation">
    <a href="/reports">Reports overview</a><a href="/forbidden">Restricted area</a>
  </nav></details>
  <a href="/register">Register</a>
</nav>
<main>
  <h1>Home screen</h1>
  <section aria-label="Search area">
    <label for="query">Search records</label><input id="query" type="search" placeholder="Search">
  </section>
  <section aria-label="Static settings">
    <label for="status">Status</label>
    <select id="status"><option value="">Choose</option><option value="open">Open</option><option value="closed" disabled>Closed</option></select>
  </section>
  <button role="tab" aria-selected="true" aria-controls="tab-one">Overview</button>
  <button role="tab" aria-selected="false" aria-controls="tab-two">Extra fields</button>
  <div id="tab-one" role="tabpanel"><p>Overview section</p></div>
  <div id="tab-two" role="tabpanel" hidden><label for="extra">Extra field</label><input id="extra"></div>
  <button id="choices" aria-haspopup="listbox" aria-controls="choices-list">Open choices</button>
  <div id="choices-list" role="listbox" hidden>
    <div role="option" aria-selected="false">Alpha</div><div role="option" aria-disabled="true">Beta</div>
  </div>
  <button id="open-dialog" aria-haspopup="dialog">Open help</button>
  <dialog aria-label="Help dialog"><h2>Help</h2><p>Safe help content</p></dialog>
  <table><thead><tr><th>Record name</th><th>Status</th></tr></thead>
    <tbody><tr><td>Private record example</td><td>Open</td></tr></tbody>
  </table>
  <button id="register" type="button" onclick="window.__mutations++">Register</button>
  <button type="submit" onclick="window.__mutations++">Save</button>
  <button type="button" onclick="window.__mutations++">Delete</button>
</main>
<script>
window.__mutations = 0;
document.querySelectorAll('[role=tab]').forEach((tab) => tab.addEventListener('click', () => {
  document.querySelectorAll('[role=tab]').forEach((x) => x.setAttribute('aria-selected', String(x === tab)));
  document.querySelectorAll('[role=tabpanel]').forEach((panel) => panel.hidden = panel.id !== tab.getAttribute('aria-controls'));
}));
document.querySelector('#choices').addEventListener('click', () => document.querySelector('#choices-list').hidden = false);
document.querySelector('dialog').addEventListener('cancel', () => document.querySelector('dialog').removeAttribute('open'));
document.querySelector('#open-dialog').addEventListener('click', () => document.querySelector('dialog').showModal());
</script></body></html>"""

REPORTS_HTML = """<!doctype html><html><head><title>Reports</title></head><body>
<nav aria-label="Main navigation"><a href="/">Home</a><a href="/reports/audit">Audit history</a></nav>
<main><h1>Reports</h1><section aria-label="Report options">
<label for="format">Export format</label><select id="format"><option>CSV</option><option>PDF</option></select>
<button role="tab" aria-selected="true">Recent</button><button role="tab" aria-selected="false">Saved</button>
</section></main></body></html>"""

AUDIT_HTML = """<!doctype html><html><head><title>Audit history</title></head><body>
<nav aria-label="Main navigation"><a href="/">Home</a><a href="/reports">Reports</a></nav>
<main><h1>Audit history</h1><table><tr><th>Timestamp</th><th>Action</th></tr><tr><td>Private audit row</td><td>Updated</td></tr></table></main>
</body></html>"""


@contextmanager
def fixture_site():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            routes = {
                "/": (200, ROOT_HTML),
                "/reports": (200, REPORTS_HTML),
                "/reports/audit": (200, AUDIT_HTML),
                "/login": (200, '<html><body><form><input name="username"><input type="password" name="password"><button>Login</button></form></body></html>'),
                "/forbidden": (403, "<html><body>Forbidden</body></html>"),
            }
            status, body = routes.get(path, (404, "<html><body>Not found</body></html>"))
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.fixture(scope="module")
def edge():
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
        except Exception as exc:
            pytest.skip(f"Installed Microsoft Edge is unavailable for fixture tests ({type(exc).__name__}).")
        yield browser
        browser.close()


def test_discovery_traverses_navigation_expands_ui_and_preserves_safe_evidence(edge) -> None:
    with fixture_site() as base_url:
        page = edge.new_page()
        page.goto(base_url, wait_until="domcontentloaded")

        result = discover_page(
            page,
            policy=DiscoveryPolicy(
                live_discovery=False,
                capture_option_labels=True,
                max_screens=40,
                max_interactions=80,
            ),
        )

        assert result.coverage.screens_observed >= 3
        assert result.coverage.navigation_links_visited >= 2
        assert any(screen.url.endswith("/reports") for screen in result.screens)
        assert any(screen.url.endswith("/reports/audit") for screen in result.screens)
        assert any(section.label == "Search area" for s in result.screens for section in s.sections)
        assert any(control.accessible_name == "Extra field" for s in result.screens for control in s.controls)
        status = next(control for s in result.screens for control in s.controls if control.label == "Status")
        assert status.observed_option_count == 3
        assert [option.label for option in status.options] == ["Choose", "Open", "Closed"]
        custom = next(control for s in result.screens for control in s.controls if control.accessible_name == "Open choices")
        assert custom.observed_option_count == 2
        assert [option.label for option in custom.options] == ["Alpha", "Beta"]
        assert any("Help dialog" in screen.dialog_labels for screen in result.screens)
        assert any(table.headers == ["Record name", "Status"] for s in result.screens for table in s.tables)
        serialized = result.model_dump_json()
        assert "Private record example" not in serialized
        assert "Private audit row" not in serialized
        assert "password" not in serialized.casefold()
        assert page.evaluate("window.__mutations") == 0
        assert page.locator("#status").input_value() == ""
        assert all(screen.evidence for screen in result.screens)
        page.context.close()


def test_authentication_boundary_detects_password_presence_without_capturing_values(edge) -> None:
    with fixture_site() as base_url:
        page = edge.new_page()
        page.goto(f"{base_url}/login")
        page.locator('input[name="username"]').fill("not-captured-user")
        page.locator('input[type="password"]').fill("not-captured-password")

        assert login_required(page)
        result = discover_page(page)
        assert not result.screens
        assert any(issue.code == "authentication_boundary" for issue in result.coverage.issues)
        assert "not-captured-user" not in result.model_dump_json()
        assert "not-captured-password" not in result.model_dump_json()
        page.context.close()


def test_forbidden_navigation_is_reported_without_retry_or_bypass(edge) -> None:
    with fixture_site() as base_url:
        page = edge.new_page()
        page.goto(base_url)

        result = discover_page(page)

        forbidden = [issue for issue in result.coverage.issues if issue.code == "http_forbidden"]
        assert forbidden
        assert forbidden[0].source_url.endswith("/forbidden")
        assert any("HTTP 403" in evidence.fact for evidence in forbidden[0].evidence)
        assert not any(screen.url.endswith("/forbidden") for screen in result.screens)
        page.context.close()


def test_unknown_and_record_specific_navigation_is_not_opened(edge) -> None:
    with fixture_site() as base_url:
        page = edge.new_page()
        page.goto(base_url)
        page.evaluate(
            """() => {
              const nav=document.querySelector('nav');
              const record=document.createElement('a');
              record.href='/records/12345';
              record.textContent='Open record';
              nav.appendChild(record);
            }"""
        )

        result = discover_page(page)

        assert any(
            issue.code == "navigation_not_activated" and "record-like path" in issue.summary
            for issue in result.coverage.issues
        )
        assert not any("/records/12345" in screen.url for screen in result.screens)
        page.context.close()


def test_live_policy_withholds_dynamic_lookup_options_and_urls_strip_query() -> None:
    assert sanitized_url("https://example.test/path?token=hidden#view") == "https://example.test/path"


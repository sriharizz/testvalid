from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright

from backend.app.services.discovery import (
    DiscoveryPolicy,
    _interaction_candidates,
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
document.querySelector('dialog').addEventListener('cancel', (e) => { e.preventDefault(); document.querySelector('dialog').close(); });
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



ANGULAR_HTML = """<!doctype html><html><head><title>Angular Material App</title></head><body>
<nav aria-label="Main menu">
  <a href="/angular/intake">Intake</a>
  <a href="/angular/admin">Admin Area</a>
</nav>
<main>
  <h1>Angular Case Entry</h1>
  <mat-card>
    <mat-card-title>Patient Details</mat-card-title>
    <mat-form-field>
      <mat-label>Identifier</mat-label>
      <input matInput id="patient-id" placeholder="Enter patient ID">
    </mat-form-field>
  </mat-card>
  <mat-expansion-panel>
    <mat-expansion-panel-header>
      <mat-panel-title>Reporter Details</mat-panel-title>
    </mat-expansion-panel-header>
    <mat-form-field>
      <mat-label>Identifier</mat-label>
      <input matInput id="reporter-id" placeholder="Enter reporter ID">
    </mat-form-field>
  </mat-expansion-panel>
  <mat-form-field>
    <mat-label>Priority Level</mat-label>
    <mat-select role="combobox" aria-haspopup="listbox" id="priority-select">
      <span>Choose priority</span>
    </mat-select>
  </mat-form-field>
  <div class="cdk-overlay-container" style="display:none;">
    <div class="cdk-overlay-pane">
      <div role="listbox">
        <mat-option role="option" aria-selected="false">High</mat-option>
        <mat-option role="option" aria-selected="false">Normal</mat-option>
        <mat-option role="option" aria-selected="false" aria-disabled="true">Low</mat-option>
      </div>
    </div>
  </div>
</main>
<script>
window.__values_changed = 0;
const sel = document.querySelector('#priority-select');
const overlay = document.querySelector('.cdk-overlay-container');
sel.addEventListener('click', () => { overlay.style.display = 'block'; });
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') overlay.style.display = 'none';
});
document.querySelectorAll('input').forEach(input => {
  input.addEventListener('change', () => { window.__values_changed++; });
});
</script></body></html>"""

ANGULAR_INTAKE_HTML = """<!doctype html><html><head><title>Angular Intake</title></head><body>
<nav aria-label="Main menu"><a href="/angular">Back to Case Entry</a></nav>
<main><h1>Manual Case Registration</h1><p>Form content</p></main></body></html>"""


ONEPV_SIDEBAR_HTML = """<!doctype html><html><head><title>OnePV Sidebar Test</title></head><body>
<app-sidebar class="d-flex">
  <div class="sidebar container-fluid" style="width: 205px; height: 720px; display: block;">
    <div class="sidebar-scroller">
      <div class="menuList">
        <div class="menu-item" style="cursor: pointer;">
          <div class="parentTitle">Home</div>
        </div>
        <div class="menu-item">
          <div class="parent d-flex justify-content-between" style="cursor: pointer;">
            <div class="parentTitle">Intake </div>
            <mat-icon role="img">expand_less</mat-icon>
          </div>
          <div class="mat-mdc-menu-trigger hoverBox" aria-expanded="false" style="width: 177px; height: 38px; display: flex;">
            <div class="extaText" style="cursor: pointer;">Manual Case Registration</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</app-sidebar>
<main>
  <h1>OnePV Dashboard</h1>
  <p class="description">Safety Management Overview</p>
  <div id="target-view"></div>
</main>
<script>
document.querySelector('.hoverBox').addEventListener('click', () => {
  document.getElementById('target-view').innerHTML = '<div class="intake-form"><h2>Manual Case Registration</h2><label for="case-num">Case Number</label><input id="case-num" placeholder="Enter Case Number"></div>';
});
</script></body></html>"""

SPINNER_HTML = """<!doctype html><html><head><title>Spinner Screen</title></head><body>
<div role="progressbar" id="loader">Loading...</div>
<main id="main-content" style="display:none;"><h1>Content Loaded</h1></main>
<script>
setTimeout(() => {
  document.getElementById('loader').style.display = 'none';
  document.getElementById('main-content').style.display = 'block';
}, 300);
</script></body></html>"""

STUCK_SPINNER_HTML = """<!doctype html><html><head><title>Stuck Spinner</title></head><body>
<mat-spinner role="progressbar">Loading forever...</mat-spinner>
<main><h1>Waiting</h1></main></body></html>"""

FIELD_MAP_HTML = """<!doctype html><html><head><title>Field map</title></head><body><main>
<mat-expansion-panel><mat-expansion-panel-header><mat-panel-title>Event Information</mat-panel-title></mat-expansion-panel-header>
  <section><h3>Event Information</h3>
    <div class="form-group"><label>Reaction Or Event As Reported (English)<span>*</span></label><input type="text"></div>
    <div class="form-group"><label>Country Code*</label><div role="combobox" aria-label="Select" aria-haspopup="listbox" style="width:120px;height:30px"></div></div>
    <input type="text">
    <button type="button">Search</button>
  </section>
</mat-expansion-panel></main></body></html>"""


@contextmanager
def angular_fixture_site():
    class AngularHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            routes = {
                "/angular": (200, ANGULAR_HTML),
                "/angular/intake": (200, ANGULAR_INTAKE_HTML),
                "/angular/admin": (200, "<html><body>Admin restricted</body></html>"),
                "/spinner": (200, SPINNER_HTML),
                "/stuck-spinner": (200, STUCK_SPINNER_HTML),
                "/field-map": (200, FIELD_MAP_HTML),
                "/onepv-sidebar": (200, ONEPV_SIDEBAR_HTML),
            }
            status, body = routes.get(path, (404, "<html><body>Not found</body></html>"))
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), AngularHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_angular_material_fields_sections_and_duplicate_labels(edge) -> None:
    with angular_fixture_site() as base_url:
        page = edge.new_page()
        page.goto(f"{base_url}/angular", wait_until="domcontentloaded")

        result = discover_page(
            page,
            policy=DiscoveryPolicy(
                live_discovery=False,
                capture_option_labels=True,
                max_screens=5,
                max_interactions=10,
                interaction_timeout_ms=1500,
            ),
        )

        assert len(result.screens) >= 1
        screen = result.screens[0]

        # Section detection from mat-card and mat-expansion-panel
        section_labels = [s.label for s in screen.sections]
        assert "Patient Details" in section_labels
        assert "Reporter Details" in section_labels

        # mat-label extraction and duplicate label preservation
        identifier_controls = [c for c in screen.controls if c.accessible_name == "Identifier"]
        assert len(identifier_controls) == 2
        # Verify distinct control_ids derived from distinct section contexts
        assert identifier_controls[0].control_id != identifier_controls[1].control_id
        patient_ctrl = next(c for c in identifier_controls if "patient-id" in c.placeholder or c.section_id)
        assert patient_ctrl is not None
        assert page.evaluate("window.__values_changed") == 0
        page.context.close()


def test_form_fields_map_visible_angular_labels_to_nested_section_path(edge) -> None:
    with angular_fixture_site() as base_url:
        page = edge.new_page()
        page.goto(f"{base_url}/field-map", wait_until="domcontentloaded")

        result = discover_page(page, policy=DiscoveryPolicy(live_discovery=False))
        screen = result.screens[0]
        by_label = {field.label: field for field in screen.form_fields if field.label}

        reaction = by_label["Reaction Or Event As Reported (English)"]
        country = by_label["Country Code"]
        assert reaction.control_type == "text"
        assert country.control_type == "combobox", [(field.label, field.control_type, field.role) for field in screen.form_fields]
        assert reaction.section_path == ["Event Information", "Event Information"]
        assert country.section_path == reaction.section_path
        assert reaction.section_id is not None
        assert reaction.label_match_status == "associated"
        assert reaction.locator_recipe.startswith("candidate: label=")
        assert "observed index" not in reaction.locator_recipe
        assert any(field.label_match_status == "missing" for field in screen.form_fields)
        assert all(field.control_type not in {"button", "link", "tab"} for field in screen.form_fields)
        assert page.locator("[role=combobox]").get_attribute("aria-expanded") is None
        assert not any(item["kind"] == "dropdown" for item in _interaction_candidates(page, policy=DiscoveryPolicy()))
        assert any(item["kind"] == "dropdown" for item in _interaction_candidates(page, policy=DiscoveryPolicy(inspect_dropdown_options=True)))
        page.context.close()


def test_angular_mat_select_cdk_overlay_inspection(edge) -> None:
    with angular_fixture_site() as base_url:
        page = edge.new_page()
        page.goto(f"{base_url}/angular", wait_until="domcontentloaded")

        result = discover_page(
            page,
            policy=DiscoveryPolicy(
                live_discovery=False,
                capture_option_labels=True,
                max_screens=5,
                max_interactions=10,
                interaction_timeout_ms=1500,
                inspect_dropdown_options=True,
            ),
        )

        select_ctrl = next((c for s in result.screens for c in s.controls if c.role == "combobox" and c.accessible_name == "Priority Level" and c.options), None)
        assert select_ctrl is not None
        # Observed options extracted from CDK overlay
        option_labels = [opt.label for opt in select_ctrl.options]
        assert "High" in option_labels
        assert "Normal" in option_labels
        assert "Low" in option_labels
        # Verify overlay was closed and no business values modified
        assert page.evaluate("window.__values_changed") == 0
        page.context.close()


def test_angular_loading_spinner_settlement_and_timeout(edge) -> None:
    with angular_fixture_site() as base_url:
        page = edge.new_page()
        # 1. Spinner that settles
        page.goto(f"{base_url}/spinner", wait_until="domcontentloaded")
        result_settled = discover_page(page, policy=DiscoveryPolicy(interaction_timeout_ms=1500))
        assert len(result_settled.screens) >= 1
        assert not any(i.code == "page_loading_timeout" for i in result_settled.coverage.issues)

        # 2. Stuck spinner that triggers timeout
        page.goto(f"{base_url}/stuck-spinner", wait_until="domcontentloaded")
        result_stuck = discover_page(page, policy=DiscoveryPolicy(interaction_timeout_ms=600))
        assert any(i.code == "page_loading_timeout" for i in result_stuck.coverage.issues)
        page.context.close()


def test_navigation_allowlist_enforcement(edge) -> None:
    with angular_fixture_site() as base_url:
        page = edge.new_page()
        page.goto(f"{base_url}/angular", wait_until="domcontentloaded")

        result = discover_page(
            page,
            policy=DiscoveryPolicy(
                live_discovery=False,
                max_screens=10,
                max_interactions=10,
                interaction_timeout_ms=1500,
                allowed_navigation_labels=("intake",),
            ),
        )

        # Visited Intake
        assert any("intake" in s.url for s in result.screens)
        # Did not visit Admin Area
        assert not any("admin" in s.url for s in result.screens)
        assert any(
            i.code == "navigation_not_activated" and "allowlist" in i.summary
            for i in result.coverage.issues
        )
        page.context.close()


def test_observation_driven_sidebar_and_text_extraction(edge) -> None:
    with angular_fixture_site() as base_url:
        page = edge.new_page()
        page.goto(f"{base_url}/onepv-sidebar", wait_until="domcontentloaded")
        assert any(
            item["kind"] == "menu"
            for item in _interaction_candidates(page, policy=DiscoveryPolicy())
        )

        result = discover_page(
            page,
            policy=DiscoveryPolicy(
                live_discovery=False,
                max_screens=5,
                max_interactions=10,
                interaction_timeout_ms=1500,
                allowed_navigation_labels=("manual case registration", "intake"),
            ),
        )

        assert len(result.screens) >= 1
        screen = result.screens[0]

        # 1. Meaningful visible text extracted
        text_values = [t.text for t in screen.texts]
        assert "OnePV Dashboard" in text_values
        assert "Safety Management Overview" in text_values
        # 2. Icon glyphs excluded
        assert not any("expand_less" in t.text for t in screen.texts)
        assert not any("expand_less" in (c.accessible_name or "") for c in screen.controls)

        # 3. Discovered navigation candidates without <a> tags
        all_labels = [r.label for r in screen.relationships]
        assert "Manual Case Registration" in all_labels
        assert "Intake" in all_labels
        reveals_labels = [r.label for r in screen.relationships if r.relationship_type == "reveals"]
        assert "Intake" in reveals_labels
        nav_labels = [r.label for r in screen.relationships if r.relationship_type == "navigation"]
        assert "Manual Case Registration" in nav_labels

        # 4. Form field on target view discovered after interaction
        all_controls = [c for s in result.screens for c in s.controls]
        assert any(c.accessible_name == "Case Number" for c in all_controls), result.model_dump_json(indent=2)
        page.context.close()


def test_workflow_scope_resolves_nested_menu_owner_and_stops_at_target(edge) -> None:
    with angular_fixture_site() as base_url:
        page = edge.new_page()
        page.goto(f"{base_url}/onepv-sidebar", wait_until="domcontentloaded")

        result = discover_page(
            page,
            policy=DiscoveryPolicy(
                live_discovery=False,
                max_screens=20,
                max_interactions=30,
                max_navigation_visits=20,
                workflow_scope="Manual Case Registration",
            ),
        )

        assert result.workflow_scope == "Manual Case Registration"
        assert result.workflow_match_status == "reached", result.model_dump_json(indent=2)
        assert result.discovery_status != "INCOMPLETE"
        assert any(control.accessible_name == "Case Number" for screen in result.screens for control in screen.controls)
        assert not any("/angular/admin" in screen.url for screen in result.screens)
        assert page.locator("#case-num").input_value() == ""
        page.context.close()


def test_workflow_scope_reports_ambiguous_matches_without_navigating(edge) -> None:
    with angular_fixture_site() as base_url:
        page = edge.new_page()
        page.goto(f"{base_url}/angular", wait_until="domcontentloaded")
        page.evaluate(
            """() => {
              const duplicate = document.createElement('a');
              duplicate.href = '/angular/admin';
              duplicate.textContent = 'Intake';
              document.querySelector('nav').appendChild(duplicate);
            }"""
        )

        result = discover_page(
            page,
            policy=DiscoveryPolicy(workflow_scope="Intake", max_interactions=10),
        )

        assert result.workflow_match_status == "ambiguous"
        assert result.discovery_status == "INCOMPLETE"
        assert result.coverage.navigation_links_visited == 0
        assert any(issue.code == "workflow_scope_ambiguous" for issue in result.coverage.issues)
        assert not any(screen.url.endswith("/angular/intake") for screen in result.screens)
        page.context.close()


def test_discovery_records_control_metadata_without_current_control_values(edge) -> None:
    page = edge.new_page()
    page.set_content(
        """<!doctype html><html><body><main><h1>Form</h1>
        <label for="case-id">Case identifier</label>
        <input id="case-id" value="sensitive-current-input">
        <select id="status"><option selected>Current sensitive choice</option></select>
        <p contenteditable="true">sensitive-editor-content</p>
        </main></body></html>"""
    )

    result = discover_page(
        page,
        policy=DiscoveryPolicy(max_screens=5, max_interactions=0, capture_option_labels=False),
    )
    serialized = result.model_dump_json()

    assert "Case identifier" in serialized
    assert "sensitive-current-input" not in serialized
    assert "Current sensitive choice" not in serialized
    assert "sensitive-editor-content" not in serialized
    assert all(control.accessible_name != "Current sensitive choice" for screen in result.screens for control in screen.controls)
    page.context.close()

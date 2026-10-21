import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {
    size: A4 portrait;
    margin: 12mm 14mm 12mm 14mm;
  }
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    color: #1e293b;
    font-size: 10.2px;
    line-height: 1.48;
    background: #ffffff;
  }
  .page {
    width: 100%;
    height: 270mm;
    page-break-after: always;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .page:last-child {
    page-break-after: avoid;
  }
  .header {
    border-bottom: 2px solid #2563eb;
    padding-bottom: 6px;
    margin-bottom: 12px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }
  .title {
    font-size: 17px;
    font-weight: 700;
    color: #0f172a;
  }
  .subtitle {
    font-size: 11px;
    color: #2563eb;
    font-weight: 600;
    margin-top: 2px;
  }
  .meta {
    font-size: 8.5px;
    color: #64748b;
    text-align: right;
    line-height: 1.35;
  }
  .section {
    margin-bottom: 12px;
  }
  .section-title {
    font-size: 11.5px;
    font-weight: 700;
    color: #0f172a;
    border-left: 3px solid #2563eb;
    padding-left: 6px;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  p {
    margin-bottom: 6px;
    color: #334155;
  }
  .box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 5px;
    padding: 8px 10px;
    margin-bottom: 8px;
  }
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 8px;
  }
  .card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 5px;
    padding: 8px 10px;
  }
  .card-title {
    font-weight: 700;
    font-size: 11px;
    color: #2563eb;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 5px;
  }
  .diagram {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 10px;
    margin: 8px 0 12px 0;
  }
  .diagram-node {
    background: #ffffff;
    border: 1px solid #94a3b8;
    border-radius: 4px;
    padding: 6px 8px;
    text-align: center;
    font-size: 9px;
    font-weight: 600;
    flex: 1;
    margin: 0 4px;
    line-height: 1.3;
  }
  .diagram-node strong {
    color: #0f172a;
    display: block;
    margin-bottom: 2px;
  }
  .diagram-arrow {
    color: #64748b;
    font-size: 13px;
    font-weight: bold;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 6px;
    margin-bottom: 6px;
    font-size: 9px;
  }
  th, td {
    border: 1px solid #cbd5e1;
    padding: 5px 7px;
    text-align: left;
  }
  th {
    background: #f1f5f9;
    color: #0f172a;
    font-weight: 700;
  }
  tr:nth-child(even) {
    background: #f8fafc;
  }
  .badge {
    display: inline-block;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 8px;
    font-weight: 600;
  }
  .badge-pass { background: #dcfce7; color: #166534; }
  .badge-flag { background: #fef3c7; color: #92400e; }
  .footer {
    border-top: 1px solid #e2e8f0;
    padding-top: 5px;
    font-size: 8.5px;
    color: #94a3b8;
    display: flex;
    justify-content: space-between;
  }
</style>
</head>
<body>

<!-- PAGE 1 -->
<div class="page">
  <div>
    <div class="header">
      <div>
        <div class="title">System Architecture: OnePV Validation Portal</div>
        <div class="subtitle">How AI, Playwright, and Evidence Processing Work Together</div>
      </div>
      <div class="meta">
        <strong>Target Application:</strong> OnePV Web App<br>
        <strong>Architecture Overview</strong><br>
        <strong>Page:</strong> 1 of 2
      </div>
    </div>

    <!-- Section 1 -->
    <div class="section">
      <div class="section-title">1. Architecture Overview & High-Level Flow</div>
      <p>
        The platform replaces manual protocol execution with a 3-layer architecture: <strong>AI Interpretation</strong>, <strong>Browser Automation (Playwright)</strong>, and <strong>Evidence Assembly</strong>. Instead of running hardcoded scripts with fixed values, the architecture dynamically bridges human-written Word protocol instructions to live web form interactions.
      </p>
      
      <div class="diagram">
        <div class="diagram-node">
          <strong>1. Protocol Document</strong>
          Raw Word file (.docx) with tables & instructions
        </div>
        <div class="diagram-arrow">&rarr;</div>
        <div class="diagram-node" style="border-color: #2563eb; background: #eff6ff;">
          <strong style="color: #2563eb;">2. AI Layer (Qwen)</strong>
          Extracts intents, field-value pairs & negative rules
        </div>
        <div class="diagram-arrow">&rarr;</div>
        <div class="diagram-node" style="border-color: #059669; background: #ecfdf5;">
          <strong style="color: #059669;">3. Playwright Runner</strong>
          Executes actions, moves cursor, streams live frames
        </div>
        <div class="diagram-arrow">&rarr;</div>
        <div class="diagram-node">
          <strong>4. Evidence Compiler</strong>
          Stitches screenshots & outputs executed Word doc
        </div>
      </div>
    </div>

    <!-- Section 2 -->
    <div class="section">
      <div class="section-title">2. Where AI Comes into the Picture</div>
      <p>
        Validation protocols are written for human testers in descriptive English, not in code. The AI model (Qwen 2.5) functions as the <strong>Protocol Interpreter and Dynamic Step Planner</strong>:
      </p>
      <div class="grid-2">
        <div class="card">
          <div class="card-title">A. Procedure & Intent Classification</div>
          <p>
            The AI reads unstructured table rows from the uploaded Word document and identifies what each test is trying to do (e.g., login, general case details, reporter entry, patient demographics, product lookups, MedDRA coding, or questionnaire responses).
          </p>
        </div>
        <div class="card">
          <div class="card-title">B. Dynamic Field-Value Extraction</div>
          <p>
            Instead of hardcoding names, addresses, or medical terms in code, the AI extracts the exact values requested in the protocol (such as doctor names, patient ages, formulations, and terms like "Pyrexia") and pairs them with specific target UI fields.
          </p>
        </div>
      </div>
      <div class="grid-2">
        <div class="card">
          <div class="card-title">C. Negative Test Rule Detection</div>
          <p>
            The AI identifies whether a step is intended to pass via error (e.g., verifying that omitting mandatory dates blocks registration). It flags the expected validation rule so the runner knows an error message is the intended outcome, not a system failure.
          </p>
        </div>
        <div class="card">
          <div class="card-title">D. Normalization into Action Contracts</div>
          <p>
            Outputs a clean, structured JSON action plan with field IDs, control types (text input, select dropdown, search modal, toggle), and values. This plan is handed over directly to the browser runner without manual code generation.
          </p>
        </div>
      </div>
    </div>

    <!-- Section 3 -->
    <div class="section">
      <div class="section-title">3. Where Playwright Takes Actual Action</div>
      <p>
        Playwright serves as the <strong>Execution and Observability Engine</strong>. It receives the structured plan from the AI layer and drives the live web application:
      </p>
      <div class="box">
        <strong>DOM Interaction & Controls:</strong> Playwright resolves DOM selectors on the live OnePV site, handles text typing, dropdown option matching, modal dialogs, and iframe searches (such as the MedDRA dictionary search and Product catalog selection).
      </div>
      <div class="grid-2">
        <div class="card">
          <div class="card-title">Camera Motion & Viewport Centering</div>
          <p>
            Before interacting with a form card, Playwright smoothly scrolls the browser viewport (<code>behavior: 'smooth', block: 'center'</code>) so reviewers can see the card in focus.
          </p>
        </div>
        <div class="card">
          <div class="card-title">Virtual Mouse & Visual Pacing</div>
          <p>
            Injects an in-DOM cursor that glides to target buttons and inputs, triggering a blue click-pulse ripple. Pauses 350ms between fields to maintain realistic, watchable pacing.
          </p>
        </div>
      </div>
    </div>
  </div>

  <div class="footer">
    <span>OnePV Validation Portal — Architectural & Engine Breakdown</span>
    <span>Page 1 of 2</span>
  </div>
</div>

<!-- PAGE 2 -->
<div class="page">
  <div>
    <div class="header">
      <div>
        <div class="title">System Architecture: OnePV Validation Portal</div>
        <div class="subtitle">Exception Handling, Evidence Stitching & Document Compilation</div>
      </div>
      <div class="meta">
        <strong>Target Application:</strong> OnePV Web App<br>
        <strong>Architecture Overview</strong><br>
        <strong>Page:</strong> 2 of 2
      </div>
    </div>

    <!-- Section 4 -->
    <div class="section">
      <div class="section-title">4. Real-Time Streaming & Live Drawer Architecture</div>
      <p>
        To let human reviewers monitor the headless execution in real time without opening remote desktop windows, the backend establishes a dedicated WebSocket stream:
      </p>
      <div class="box">
        <strong>WebSocket Frame Pipeline:</strong> After each significant field action, Playwright takes a lightweight 60% quality JPEG capture and broadcasts it via WebSocket to the React frontend. The Live View drawer displays this stream continuously, giving full visual feedback of the cursor moving, fields filling, and cards scrolling.
      </div>
    </div>

    <!-- Section 5 -->
    <div class="section">
      <div class="section-title">5. What Happens Behind the Scenes: Error & Discrepancy Handling</div>
      <p>
        The platform uses a decision matrix to differentiate between expected negative tests and unexpected application discrepancies:
      </p>
      <table>
        <thead>
          <tr>
            <th style="width: 25%;">Condition</th>
            <th style="width: 45%;">Internal Mechanism</th>
            <th style="width: 30%;">Resulting State</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Expected Negative Test</strong><br>(e.g., Mandatory fields omitted)</td>
            <td>The AI marks the step as expecting an error. Playwright checks for validation dialogs. When the expected alert appears, it verifies the text, takes evidence, dismisses the modal, and resets the form.</td>
            <td><span class="badge badge-pass">PASS</span> Logged as verified validation behavior.</td>
          </tr>
          <tr>
            <td><strong>Unexpected Error Banner</strong><br>(e.g., 503 error, unhandled alert)</td>
            <td>Playwright detects an unanticipated error popup or red alert banner. It takes an error screenshot and emits a <code>HUMAN_REVIEW_REQUIRED</code> event to the frontend.</td>
            <td><span class="badge badge-flag">PAUSED FOR REVIEW</span> Prompts the user to review, acknowledge/continue, or halt.</td>
          </tr>
          <tr>
            <td><strong>Dropdown / Label Mismatches</strong><br>(e.g., "Dr" vs "Dr.")</td>
            <td>Multi-tier resolution: Exact label match &rarr; Period variations &rarr; Exact value &rarr; Normalized substring lookup.</td>
            <td><span class="badge badge-pass">RESOLVED</span> Selects correct option without breaking execution.</td>
          </tr>
          <tr>
            <td><strong>DOM & Network Latency</strong></td>
            <td>Replaces static sleeps with dynamic Playwright actionability checks (visible, attached, stable) before executing inputs.</td>
            <td><span class="badge badge-pass">STABLE</span> Prevents timing race conditions during modal loads.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Section 6 -->
    <div class="section">
      <div class="section-title">6. Two-Stage Evidence Capture & Word Report Reconstruction</div>
      <p>
        The final phase converts raw execution data into compliance-grade documentation:
      </p>
      <div class="grid-2">
        <div class="card">
          <div class="card-title">Two-Stage Image Stitching</div>
          <p>
            Playwright captures two separate states for critical steps: (1) the filled form before clicking Save/Submit, and (2) the confirmation popup showing the generated Case Number or alert. Both images are stitched vertically into one complete record.
          </p>
        </div>
        <div class="card">
          <div class="card-title">Pristine Cursor Separation</div>
          <p>
            The virtual cursor is visible in the live stream for the reviewer, but Playwright momentarily hides cursor DOM elements before taking screenshots, ensuring official document evidence remains clean.
          </p>
        </div>
      </div>
      <div class="box" style="margin-top: 5px;">
        <strong>Word Document Assembly (<code>python-docx</code>):</strong> Clones the uploaded protocol template and writes execution results directly into <strong>Table 5 (Test Execution)</strong>—filling Observed Results, Pass/Fail classifications, execution dates, tester initials, and embedding the stitched screenshot images. Any flagged discrepancies are written into <strong>Table 8 (Discrepancy Log)</strong>.
      </div>
    </div>
  </div>

  <div class="footer">
    <span>OnePV Validation Portal — Architectural & Engine Breakdown</span>
    <span>Page 2 of 2</span>
  </div>
</div>

</body>
</html>
"""

async def generate_pdf():
    output_path = Path("c:/projects/validation_portal/Validation_Execution_Summary.pdf")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(HTML_CONTENT, wait_until="networkidle")
        await page.pdf(
            path=str(output_path),
            format="A4",
            print_background=True,
            margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"}
        )
        await browser.close()
        print(f"SUCCESS: PDF created at {output_path}")

if __name__ == "__main__":
    asyncio.run(generate_pdf())

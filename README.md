# Clinevo Validation Automation Platform (v2)

Automated Computerized Systems Validation (CSV) execution engine and evidence collection platform for pharmacovigilance applications (OnePV, Signal Detection, and related web interfaces).

---

## 1. Overview

The platform automates the execution of formal qualification protocols (OQ/PQ) against web-based safety applications:

- **Protocol Parsing:** Extracts test steps, procedures, and expected results directly from protocol documents (`.docx`).
- **Dynamic Interaction:** Interacts with application forms using semantic selectors, accessible names, ARIA roles, and labels rather than static element IDs.
- **Result Verification:** Evaluates step outcomes against the live DOM (verifying status indicators, auto-populated fields, table records, and message dialogs).
- **Evidence & Reporting:** Captures watermarked screenshots, populates executed protocol documents (including Table 6 sign-off records), and provides an execution summary with root-cause observations.

---

## 2. System Components

```
[ Protocol Document (.docx) ]
             │
             ▼
      [ Extractor ]
             │
             ▼
      [ Step Planner ] ── (Batched Plan Mapping)
             │
             ▼
    [ Playwright Runner ]
      ├── Semantic Control Resolution (ARIA, Labels, Placeholders)
      ├── Section & Dialog Scoping
      └── Result Verification Engine
             │
             ▼
   [ Evidence & Summary ]
      ├── Watermarked Screenshot Capture
      ├── Executed Protocol Generation (.docx Table 6)
      └── Executive Summary & Root Cause Analysis
```

### Core Features

- **Semantic Field Matching:** Uses `find_semantic_control` to find inputs, dropdowns, and buttons by their associated text, role, or placeholder.
- **Modal & Section Scoping:** Scopes actions to active section cards or topmost modal dialogs to prevent unintentional interactions with background elements.
- **DOM Verification:**
  - `STATUS_BADGE`: Checks for visual status indicators or coding badges (e.g., MedDRA).
  - `FIELD_VALUE`: Verifies that auto-populated or input fields contain the expected values in the DOM.
  - `TABLE_DATA`: Checks for row addition or deletion in data tables.
  - `MESSAGE_DISPLAYED` / `ERROR_MESSAGE`: Confirms expected confirmation messages or validation error dialogs.
- **Executive Summary:** Summarizes test results, identifies discrepancies, and provides root-cause explanations and suggested remediation steps.

---

## 3. Environment & UI Considerations

| Parameter | Recommended Setting | Description |
| :--- | :--- | :--- |
| **Viewport** | `1366 x 768` | Standard desktop viewport for clinical safety systems. |
| **Target Application** | Configured in `backend/.env` | Target web application under test. |
| **Simulation Mode** | `PASS` (`?simMode=pass`) | Target mock environment mode. |
| **Browser** | Chromium | Headless or headed execution via Playwright. |

### Application Notes (Mock Environment)
When executing protocols against a mock testing environment (such as `https://mpv-two.vercel.app`):
- **Validation Discrepancies:** If the mock application does not enforce certain validations (e.g., mandatory field checks on save/submit), the engine reports the observed discrepancy rather than assuming a pass.
- **Auto-Populated Fields:** Fields expected to populate from reference dictionaries must be rendered with values in the DOM for verification to pass.
- **Dialog Flow:** Certain operations (e.g. deletion confirmation) may require reason input before confirming; the runner handles these standard multi-step prompts.

---

## 4. Setup and Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- npm

---

### Backend Setup

```bash
cd backend

# 1. Create and activate virtual environment
python -m venv venv

# Windows:
.\venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright browser binaries
playwright install chromium

# 4. Configure environment
cp .env.example .env
```

#### Configuration (`backend/.env`)
```ini
# LLM Provider: "GROQ" or "DGX"
LLM_PROVIDER="GROQ"

# Groq Configuration (for plan mapping & root cause analysis)
GROQ_API_KEY="your_groq_api_key_here"
GROQ_MODEL="qwen/qwen3.8-27b"

# DGX Configuration (optional fallback)
QWEN_BASE_URL="https://dgx.one-aipv.com/qwen/v1"
QWEN_API_KEY="your_api_key_here"
QWEN_MODEL_NAME="qwen38-27b"

# Target Application URL
TARGET_APP_URL="https://mpv-two.vercel.app"
```

#### Run Backend Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir .
```
Backend API documentation is available at `http://localhost:8000/docs`.

---

### Frontend Setup

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Start development server
npm run dev
```
Frontend interface will be available at `http://localhost:5173`.

---

## 5. Usage

1. Open `http://localhost:5173`.
2. Select the product (e.g. **OnePV**) from the dropdown.
3. Select an existing sample protocol (such as `CLIN-EU-VAL-OPV-1-1-OQ-036`) or upload a new `.docx` protocol.
4. Click **Run Protocol Execution** to begin execution.
5. Review the execution in the live viewer.
6. Upon completion:
   - View the **Executive Summary** modal for step pass/fail metrics and root-cause analyses.
   - Download the executed `.docx` with populated actual results and Table 6 sign-offs.
   - Download the companion evidence dossier.

---

## 6. Directory Structure

```
.
├── backend/
│   ├── agents.py              # Planning agent, assertion synthesis, LLM client
│   ├── check_coverage.py      # Protocol-to-plan coverage verification
│   ├── docx_writer.py         # Executed Word document and Table 6 generator
│   ├── dom_inspector.py       # Playwright DOM inspection helpers
│   ├── extractor.py           # Protocol table extractor (.docx)
│   ├── main.py                # FastAPI routes and WebSocket handler
│   ├── playwright_runner.py   # Test execution engine and DOM assertions
│   ├── products.py            # Product definitions
│   ├── protocol_generator.py  # Protocol authoring helper
│   ├── requirements.txt       # Python dependencies
│   ├── schemas.py             # Data models and assertion types
│   ├── .env.example           # Environment template
│   └── uploads/               # Sample protocol documents
├── frontend/
│   ├── src/                   # React application source
│   ├── package.json           # Frontend dependencies
│   └── vite.config.ts         # Vite configuration
└── README.md                  # Project documentation
```

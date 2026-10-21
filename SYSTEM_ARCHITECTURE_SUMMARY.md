# System Architecture: OnePV Validation Portal
## How AI, Playwright, and Evidence Processing Work Together

---

### 1. High-Level Architectural Flow

The portal operates through a clean multi-layer pipeline rather than static, hardcoded scripts:

```text
[1. Word Protocol (.docx)]
       ↓
[2. AI Layer (Qwen 2.5 Interpreter)]
       ↓ (Structured Action Contract)
[3. Browser Automation (Playwright Runner)]
       ↓ (Real-time Actions & WebSocket Frames)
[4. Live Reviewer Drawer & Error Evaluator]
       ↓ (Two-Stage Stitched Screenshots)
[5. Word Report Compiler (Table 5 & Table 8)]
```

---

### 2. Where AI Comes into the Picture

Validation protocols are written in natural English tables for human reviewers, not in executable test code. The AI model (Qwen 2.5) functions as the **Protocol Interpreter and Dynamic Step Planner**:

1. **Procedure & Intent Classification:**  
   The AI reads the raw procedure text in the protocol and classifies the underlying action intent (e.g., login, general case details, reporter entry, patient demographics, product search, MedDRA coding, or questionnaire response).
2. **Dynamic Field-Value Extraction:**  
   Instead of hardcoding names, addresses, or medical terms, the AI extracts the exact values requested in the protocol tables (such as doctor names, patient ages, formulations, and terms like "Pyrexia") and maps them to the respective form inputs.
3. **Negative Test Rule Detection:**  
   The AI analyzes whether a step is intended to pass via an error condition (e.g., verifying that omitting mandatory dates triggers a validation popup). It flags the expected validation rule so the runner knows an error message is the intended outcome, not a system failure.
4. **Normalized Action Contract:**  
   The AI translates human-written requirements into a structured JSON execution plan containing field IDs, control types (text input, select dropdown, search modal, toggle), and target values.

---

### 3. Where Playwright Takes Actual Action

Playwright serves as the **Execution and Observability Engine**. It consumes the structured action plan from the AI layer and drives the live web application:

1. **DOM Interaction & Control Execution:**  
   Playwright resolves DOM elements on the live OnePV site, handles text typing, dropdown option matching, modal dialogs, and iframe searches (such as the MedDRA dictionary search and Product catalog selection).
2. **Smooth Viewport Centering:**  
   Before interacting with any form section, Playwright smoothly scrolls the browser viewport (`behavior: 'smooth', block: 'center'`) to center the target card (Reporter, Patient, Product, or Event) so viewers can see the active form area.
3. **Virtual Mouse Pointer & Visual Pacing:**  
   An in-DOM virtual cursor glides to target buttons and inputs, triggering a visible click-pulse ripple. Playwright introduces a natural ~350ms cadence between interactions so that typing and dropdown selections are clearly watchable in real time.

---

### 4. Real-Time Streaming & Observability

To allow human reviewers to observe headless browser execution without remote desktop tools:
* **WebSocket Frame Pipeline:** After each field interaction, Playwright captures a lightweight JPEG frame and streams it over WebSockets directly to the React frontend's Live View drawer.
* Reviewers can watch the virtual cursor move, fields get filled, and modals open in real time.

---

### 5. What Happens Behind the Scenes: Error & Discrepancy Handling

The system evaluates runtime events using a grounded decision logic:

| Condition | Internal Mechanism | Resulting State |
| :--- | :--- | :--- |
| **Expected Negative Test** *(e.g., Mandatory fields omitted)* | The AI flags the step as expecting an error. Playwright checks for the validation dialog. When the expected alert appears, it verifies the text, captures evidence, dismisses the modal, and resets the form. | **PASS** — Logged as verified validation behavior. |
| **Unexpected Error Banner** *(e.g., 503 error, unhandled alert)* | Playwright detects an unanticipated error popup or alert banner. It captures an error screenshot and emits a `HUMAN_REVIEW_REQUIRED` event to the frontend. | **PAUSED FOR REVIEW** — Prompts the reviewer to inspect the issue and choose to continue or halt safely. |
| **Dropdown / Label Mismatches** *(e.g., "Dr" vs "Dr.")* | Multi-tier resolution: Exact label match → Period variations → Exact value → Normalized substring lookup. | **RESOLVED** — Selects the correct option without breaking execution. |
| **DOM & Network Latency** | Replaces static sleep timers with dynamic Playwright actionability checks (visible, attached, stable) before executing inputs. | **STABLE** — Prevents race conditions during modal and network loads. |

---

### 6. Two-Stage Evidence Capture & Word Report Reconstruction

The final layer converts execution results into audit-ready documentation:
* **Two-Stage Image Stitching:** Playwright captures two distinct states for critical steps: (1) the filled form before clicking Save/Submit, and (2) the confirmation popup showing the generated Case Number or alert. Both images are stitched vertically into one complete record.
* **Pristine Screenshot Separation:** The virtual cursor is visible in the live stream for the reviewer, but Playwright momentarily hides cursor DOM elements before taking screenshots, ensuring official document evidence remains clean.
* **Word Document Assembly (`python-docx`):** Clones the uploaded protocol template and writes execution results directly into **Table 5 (Test Execution)**—filling Observed Results, Pass/Fail classifications, execution dates, tester initials, and embedding the stitched screenshot images. Any flagged discrepancies are written into **Table 8 (Discrepancy Log)**.

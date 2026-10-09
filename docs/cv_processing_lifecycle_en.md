# CV Processing Lifecycle: From Raw Upload to Tailored PDF

This document provides a comprehensive breakdown of the internal pipeline triggered when a user supplies a CV: what operations execute, how data transforms across each phase, and which security and audit invariants activate.

---

## 1. High-Level Pipeline Architecture

```
[ Candidate Provides CV ] (PDF / DOCX / Text)
            |
            v
[ STEP 1: Text Extraction & Atomization (Evidence Extraction) ]
   - Raw text parsing (PdfReader / text extraction)
   - Disintegration into atomic units (CandidateEvidence)
   - Binding immutable source_quote anchors
            |
            v
[ STEP 2: Profile Normalization (profile.json) ]
   - Schema structuring into CandidateProfile
   - Mapping required facts (FactRequirement -> evidence_ids)
   - Assigning confidence levels (uncertainty: low/medium, status: document_verified)
            |
            v
[ STEP 3: Schema Validation & Immutability Lock (Confirmation Gate) ]
   - Command: `mocnghe profile confirm-file`
   - Integrity audit: every fact must map to existing evidence
   - Stamping confirmed_at in UTC
   - Computing SHA-256 fingerprint (profile_content_hash)
   - Persisting to SQLite `profiles` table (Immutable record)
            |
            v
[ STEP 4: Target-Specific Tailoring (CV Tailoring) ]
   - Command: `mocnghe cv create --job-id <id> --evidence <ev1> --evidence <ev2>...`
   - Formulating structured Claims bound to job_id and profile_version
   - Two operational modes:
       * extractive: text strictly identical to source_quote
       * proposed: rephrased or translated claims (flagged for review)
            |
            v
[ STEP 5: Cryptographic Approval Gate ]
   - Command: `mocnghe cv review <cv_id>` -> extract content_hash
   - Command: `mocnghe cv approve <cv_id> --hash <content_hash>`
   - Any content modification invalidates previous approval state
            |
            v
[ STEP 6: Publication-Grade PDF Compilation (ReportLab Engine) ]
   - Command: `mocnghe cv export <cv_id> --output cv.pdf --max-pages 2`
   - XML escaping against canvas crashes or code injection
   - Enforcing strict page-budget limits (rejects trailing page overflow)
   - Emitting dual bundle: `cv.pdf` (for recruiters) + `cv.json` (for ATS/Audit)
```

---

## 2. Step-by-Step Breakdown

### Step 1: Text Extraction & Atomization (Evidence Extraction)
- **Operation:** When a CV is supplied (e.g. `cv-nguyen-minh-thai.pdf`), the system or AI agent extracts text layers.
- **Transformation:** Freeform text is disintegrated into atomic `CandidateEvidence` records. Each evidence captures:
  - `evidence_id`: Unique identifier (e.g., `ev_exp_steam_camera`).
  - `source_quote`: Verbatim excerpt from the source document. Acts as an **unalterable grounding anchor** preventing LLM hallucination.
  - `status`: Verification badge (e.g., `document_verified`).

### Step 2: Profile Normalization (`profile.json`)
- **Operation:** Evidence items are aggregated under the Pydantic `CandidateProfile` contract.
- **Security Check:** Establishes `FactRequirement` citations. If an assertion states *"Enrolled CS Student"*, it must cite valid `evidence_ids: ["ev_edu_phenikaa"]`.

### Step 3: Schema Validation & Immutability Lock (`profile confirm-file`)
- **Operation:** Executed via CLI:
  ```bash
  uv run mocnghe profile confirm-file
  ```
- **Under the Hood:**
  1. Executes JSON decoding and Pydantic validation.
  2. Integrity audit: Prohibits duplicate `evidence_id` keys and rejects facts citing missing evidence.
  3. Stamps canonical UTC timestamp (`confirmed_at = datetime.now(UTC)`).
  4. Calculates SHA-256 fingerprint over the payload.
  5. Inserts into the `profiles` table in SQLite (`careerviet.sqlite3`).
  - **Invariant:** The confirmed version becomes strictly **immutable**. Subsequent updates require incrementing the version string.

### Step 4: Target-Specific Tailoring (`cv create` & `cv revise`)
- **Operation:** The candidate or agent selects evidence aligned with target job requirements:
  ```bash
  uv run mocnghe cv create --profile-version 1.0 --language en --job-id job_123 \
    --identity full_name --identity email --identity linkedin \
    --evidence ev_edu --evidence ev_exp_steam_camera --evidence ev_skills_backend
  ```
- **Under the Hood:**
  - Initializes a revision entry in the `cv_revisions` table.
  - Converts evidence items into structured `Claim` objects.
  - If phrasing is adapted for the role or translated into English, claims receive `mode: "proposed"`. The system enforces explicit warnings: *Proposed rephrasings require human review and cannot be assumed true without consent.*

### Step 5: Cryptographic Approval Gate (`cv approve`)
- **Operation:** The candidate reviews content and authorizes publication:
  ```bash
  uv run mocnghe cv review <cv_id>   # Outputs claims and content_hash
  uv run mocnghe cv approve <cv_id> --hash <content_hash>
  ```
- **Under the Hood:**
  - The runtime independently computes `digest(cv)`.
  - Matches the computed digest against the user's explicit `--hash` parameter. Persists to `cv_approvals` only on exact match.
  - Any external modification to database records changes the digest, immediately voiding approval state.

### Step 6: Publication-Grade PDF Compilation (`cv export`)
- **Operation:** Emitting publication materials:
  ```bash
  uv run mocnghe cv export <cv_id> --output cv_final.pdf --max-pages 2
  ```
- **Under the Hood:**
  1. Verifies `svc.approved(cv_id)`: Unapproved revisions fail immediately with permission errors.
  2. XML-escapes text to prevent injection or formatting corruption.
  3. Monitors ReportLab canvas dimensions. If content exceeds `--max-pages` (default: 2), the renderer halts with `CV exceeds page budget`, forcing concise editing rather than messy overflow.
  4. Emits publication `cv.pdf` alongside machine-readable `cv.json`.

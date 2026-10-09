# Local Database & Storage Subsystem

The storage subsystem of Mốc Nghề is encapsulated within `CareerRepository` (`storage/repository.py`), providing an isolated, local-first **SQLite 3** persistence layer (`careerviet.sqlite3`) for each workspace directory. All interactions prioritize cryptographic auditability, SHA-256 integrity checks, and self-contained disaster recovery.

---

## 1. Relational Schema Architecture

```
+---------------------------------------------------------------------------------------------------+
|                                      careerviet.sqlite3 (SQLite)                                   |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [ jobs ]                                        [ profiles ]                                     |
|  - job_id (PK, text)                             - profile_id (PK, text)                          |
|  - source_id (text)                              - version (PK, text)                             |
|  - title, employer, location (text)              - payload_json (text)                            |
|  - description, requirements, benefits (text)    - content_hash (text, SHA-256)                   |
|  - freeform_text (text)                          - confirmed_at (text, ISO UTC)                   |
|  - content_hash (text, SHA-256)                  |                                                |
|  - applied (boolean)                             |                                                |
|                                                  |                                                |
|  [ profile_drafts ]                              [ evaluation_reports ]                           |
|  - draft_id (PK, text)                           - report_id (PK, text)                           |
|  - payload_json (text)                           - profile_version, job_id (text)                 |
|  - updated_at (text)                             - jd_content_hash (text)                         |
|                                                  - runtime, model, payload_json (text)            |
|                                                                                                   |
|  [ cv_revisions ]                                [ cv_approvals ]                                 |
|  - id (PK, text)                                 - id (PK, FK -> cv_revisions.id)                 |
|  - payload (text, JSON)                          - hash (text, SHA-256)                           |
|  - hash (text, SHA-256)                                                                           |
|                                                                                                   |
|  [ application_drafts ]                          [ application_draft_approvals ]                  |
|  - id (PK, text)                                 - id (PK, FK -> application_drafts.id)           |
|  - payload (text, JSON)                          - hash (text, SHA-256)                           |
|  - hash (text, SHA-256)                                                                           |
|                                                                                                   |
|  [ applications ]                                [ application_events ]                           |
|  - application_id (PK, int auto)                 - event_id (PK, int auto)                        |
|  - job_id (FK -> jobs.job_id)                    - application_id (FK -> applications)            |
|  - state (text, CHECK state IN (...))            - from_state, to_state (text)                    |
|  - cv_version (text)                             - created_at, note (text)                        |
|  - submission_json (text, snapshot)             - submission_hash (text)                         |
|  - submission_hash (text, SHA-256)                                                                |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Storage Compatibility & Filename Retention

- **Retained SQLite Filename (`careerviet.sqlite3`):**
  Even after the project rebranding from `careerViet.ai` to **Mốc Nghề** (`mocnghe`), the underlying database filename intentionally remains `careerviet.sqlite3`.
  - **Rationale:** Prevents upgrades from silently initializing an empty, unlinked database file, preserving all previously archived career history and audit logs.
- **Self-Contained Workspaces:**
  Every workspace directory (default: `data/`, or customized via `--workspace <path>`) contains an autonomous SQLite database. Backing up, migrating, or archiving an entire job search campaign requires only copying the workspace directory.

---

## 3. Cryptographic Tamper Detection & Integrity Verification

### 3.1. Read-Time Digest Validation
Whenever a CV draft is read from `cv_revisions`:
```python
row = db.execute("SELECT payload, hash FROM cv_revisions WHERE id=?", (cv_id,)).fetchone()
cv = CV.model_validate_json(row["payload"])
if digest(cv) != row["hash"]:
    raise ValueError("CV content hash mismatch")
```
If any external process directly modifies the `payload` column in SQLite, the recomputed `digest(cv)` diverges from the recorded `hash`, immediately aborting execution with a tamper warning.

### 3.2. Immutability of Confirmed Profile Versions (`profiles`)
When persisting a confirmed candidate profile via `save_confirmed_profile()`:
- Duplicate versions trigger an immediate exception: `confirmed profile versions are immutable`.
- Historical application materials remain verifiable against the exact profile state active at the time of submission.

### 3.3. Self-Diagnostic Health Checks (`mocnghe doctor`)
The `doctor()` routine inspects:
- Database physical integrity via `PRAGMA integrity_check`.
- Foreign key relation consistency via `PRAGMA foreign_key_check`.
- Live counts of stored jobs, drafts, and profile revisions.

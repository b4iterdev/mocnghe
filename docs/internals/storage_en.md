# Local Storage Subsystem

The storage subsystem of Mốc Nghề is encapsulated within `CareerRepository` (`storage/repository.py`), providing an isolated, local-first **Pure File-Based Storage** layer for each workspace directory (default: `data/`). All data is stored in human-readable Markdown and structured YAML, utilizing SHA-256 integrity verification, OS file locking (`fcntl.flock`), and full Git compatibility.

---

## 1. Workspace Layout

```
workspace/
├── .lock                          # Concurrency lock file (fcntl.flock)
├── pipeline.md                    # Human-readable Kanban board
├── profile.json                   # Source candidate profile
├── profiles/                      # Immutable profile snapshots
│   ├── {version}.md               # Readable Markdown summary
│   └── {version}.yaml             # Pydantic schema with _hash fingerprint
├── jobs/                          # Ingested job postings
│   └── {job_id}.md                # YAML frontmatter + JD description
├── applications/                  # Application tracking and audit trail
│   └── {job_id}.yaml              # State, CV version, snapshot, event history
├── cvs/                           # Tailored CV revisions and approvals
│   ├── {cv_id}.md                 # Rendered Markdown view
│   ├── {cv_id}.yaml               # Structured claims with _hash
│   └── {cv_id}.approval.yaml      # Candidate approval token (SHA-256)
├── cover_letters/                 # Cover letters
│   ├── {cl_id}.yaml               # Cover letter schema with _hash
│   └── {cl_id}.approval.yaml      # Approval token
├── drafts/                        # Application email and form drafts
│   ├── {draft_id}.yaml            # Form/email draft
│   └── {draft_id}.approval.yaml   # Draft approval
├── reports/                       # Triage & matching reports
│   ├── {report_id}.md             # Report Markdown summary
│   └── {report_id}.yaml           # Structured report payload
└── observations/                  # Raw ingestion observations
    └── {job_id}.json              # Original URLs and raw contents
```

---

## 2. Git-friendly & Local Storage Philosophy

- **No Binary Database Lock-in:**
  Previously, Mốc Nghề maintained a legacy `careerviet.sqlite3` database. This has been fully removed in favor of plain text files (`.md`, `.yaml`, `.json`).
  - **Benefits:** Clean Git tracking (`git diff`, `git log`), straightforward cloud backups, zero risk of SQLite binary corruption.
- **Autonomous Workspaces:**
  Every workspace directory (default: `data/`, or customized via `--workspace <path>`) is completely self-contained. Moving or archiving an entire search campaign only requires copying the workspace folder.

---

## 3. Audit & Tamper Detection

### 3.1. Read-Time Hash Verification (`digest` check)
When loading a tailored CV from `cvs/{cv_id}.yaml`:
```python
data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
stored_hash = data.pop("_hash", None)
cv = CV.model_validate(data)
if stored_hash is not None and digest(cv) != stored_hash:
    raise ValueError("CV content hash mismatch")
```
Any external manual tampering with claims without going through `mocnghe cv approve` causes the recomputed `digest(cv)` to diverge from `stored_hash`, immediately rejecting execution.

### 3.2. Immutability of Confirmed Profiles
When saving an immutable profile version:
- The repository checks if `profiles/{version}.yaml` exists. If the version is already present, it raises `ValueError("confirmed profile versions are immutable")`.

### 3.3. OS File-Level Concurrency Locking
Concurrency between multiple agent processes or CLI commands is managed via `fcntl.flock` on `.lock`:
```python
@contextmanager
def lock(self):
    self.initialize()
    with open(self.lock_file, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
```

### 3.4. Diagnostics (`mocnghe doctor`)
`CareerRepository.doctor()` verifies directory structures and reports active counts of jobs, profiles, drafts, and evaluation reports directly from disk.

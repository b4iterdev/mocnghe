# Application Lifecycle: From Triage to Submission Tracking

This document explains the complete progression from having a stored job posting to evaluating alignment, drafting tailored application materials, capturing cryptographic audit snapshots, and confirming manual submissions.

---

## 1. High-Level Pipeline Architecture

```
[ Stored Job Posting ] + [ Confirmed Candidate Profile ]
            |
            v
[ STEP 1: Offline Alignment Screening (Local Triage) ]
   - Command: `mocnghe evaluate triage <job_id>`
   - Extracts structured requirements from JD bullets
   - Evaluates hard policy gates:
       * Salary floor / industry exclusion breach -> `not_fit`
       * Unspecified role parameters -> `evaluate_with_unknowns`
       * Requirements satisfied -> `practical_fit`
            |
            v
[ STEP 2: Pipeline Enrollment (Shortlisting) ]
   - Command: `mocnghe track <job_id> --state shortlisted`
   - Enrolls application record in `applications` table
   - Logs state event to `application_events` (discovered -> shortlisted)
            |
            v
[ STEP 3: Material Preparation (Drafting) ]
   - Command: `mocnghe track <job_id> --state drafting`
   - CV Tailoring:
       * `mocnghe cv create` -> `mocnghe cv revise` -> `mocnghe cv approve`
   - Form Question Mapping (Application Draft):
       * `mocnghe draft create <cv_id> --questions questions.json`
       * Question answers strictly cite approved CV evidence items
            |
            v
[ STEP 4: Package Finalization & Audit Snapshot (Ready State) ]
   - Command: `mocnghe track <job_id> --state ready --cv <cv_id>`
   - Invariant Check: Attached CV must be cryptographically approved
   - Generates immutable audit snapshot (`submission_json`):
       * Full CV payload + Job content hash + Profile version
   - Calculates cryptographic digest: `submission_hash = SHA-256(snapshot)`
            |
            v
[ STEP 5: Manual Submission & Confirmation (Apply Gate) ]
   - Candidate manually submits materials via employer ATS portal
   - Audited user confirmation:
       `mocnghe apply <job_id> --cv <cv_id> --confirm`
   - Database flags: `applied = True`, stamps canonical `applied_at` in UTC
   - Downstream tracking: `interviewing` -> `offer` / `rejected`
```

---

## 2. Step-by-Step Breakdown

### Step 1: Offline Alignment Screening
- Executes `triage_job(profile, job)` deterministically on the local CPU.
- Incurs zero external token costs and transmits zero personal data.
- Quickly filters out roles below compensation thresholds or outside target industries.

### Steps 2 & 3: Shortlisting & Drafting
- Moves linearly: `discovered` ➔ `shortlisted` ➔ `drafting`.
- **Targeted CV Tailoring:** Connects only candidate evidence directly relevant to the posting's specific bullets.
- **Form Question Mapping (`draft`):** Maps ATS questions (e.g., *"How many years of SQL experience do you have?"*) directly to approved evidence in the CV, preventing contradictory claims across submission channels.

### Step 4: Package Finalization (`ready`)
- Command: `mocnghe track <job_id> --state ready --cv <cv_id>`.
- **Safety Gate:** Rejects progression if the attached CV lacks verified approval status (`cv approve`).
- **Forensic Audit Snapshot (`submission_json`):** Freezes the exact CV revision, job description state, and profile version, generating a verifiable `submission_hash`. Candidates maintain a 100% reproducible historical record of their application.

### Step 5: Manual Submission Confirmation (`apply`)
- **Core Principle:** Mốc Nghề **never auto-submits or spams employer portals**.
- Once the user completes the external submission, they record the action:
  ```bash
  uv run mocnghe apply <job_id> --cv <cv_id> --confirm
  ```
- Keeps the job search fully human-controlled and intentional.

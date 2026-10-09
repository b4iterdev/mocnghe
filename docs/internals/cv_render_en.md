# CV Tailoring & Rendering Subsystem

The `cv` and `cv_render` subsystems govern evidence curation, role-specific phrasing tailoring, cryptographic approval gates, and publication-ready A4 PDF compilation.

---

## 1. Structured Capability Assertions (`Claim` in `cv.py`)

In Mốc Nghề, a CV is not unstructured prose, but an ordered array of structured claims (`list[Claim]`):

```python
class Claim(BaseModel):
    evidence_id: str          # Must reference existing CandidateEvidence
    source_quote: str         # Original verbatim quotation from the source
    text: str                 # Rendered claim text (supports approved rewrites)
    section: Literal["experience", "education", "skills", "credentials", "other"]
    mode: Literal["extractive", "proposed"]
    uncertainty: str
    status: str
```

### 1.1. Extractive vs. Proposed Modes
- **`mode: "extractive"`**: Enforces `text == source_quote`. Preserves the verified source quotation verbatim with zero semantic drift.
- **`mode: "proposed"`**: Authorizes targeted rephrasing, language translation (e.g. `EN` to `VI`), or formatting enhancements. Explicitly flagged as synthetic proposed content requiring explicit human verification.

### 1.2. Automated Field Normalization (`@field_validator`)
To prevent invalid inputs during automated agent execution, schemas auto-map conventional section and mode labels:
- `summary`, `objective`, `projects` ➔ maps to `other`.
- `certifications`, `licenses` ➔ maps to `credentials`.
- `rewrite`, `tailored`, `translated` ➔ maps to `proposed`.

---

## 2. Cryptographic Approval Gate

Prevents unapproved alterations between review and publication:

```
[ cv create / revise ]
          |
          v
  Generates immutable revision
          |
          v
[ cv review <cv_id> ]  --->  Calculates content_hash = SHA-256(CV payload)
          |
          v
[ cv approve <cv_id> --hash <content_hash> ]
          |
          v
  Persists to `cv_approvals` (only if input hash matches payload digest)
          |
          v
[ cv export <cv_id> ]  --->  Verifies approval state (fails if unapproved)
```

> **Security Guarantee:** Any modification to a claim text or metadata alters the SHA-256 digest, automatically invalidating previous approval state and requiring explicit re-approval.

---

## 3. PDF Rendering Engine (`cv_render.py`)

1. **Escaped Content Injection:** All text flows through XML escaping (`xml.sax.saxutils.escape`), preventing markup injection or reportlab canvas parsing crashes.
2. **Deterministic Page Budgets (`--max-pages`):**
   - Injects a canvas lifecycle monitor (`check_page(canvas, document)`).
   - If content spills beyond the specified page limit (default: 2 pages), the engine halts with `CV exceeds page budget`, preventing untidy multi-page overflow.
3. **Dual Bundling:** Exports both publication `cv.pdf` for recruiters and structured `cv.json` for ATS verification.

"""Modern ATS-optimized HTML & Playwright PDF renderer matching the career-ops design."""
import io
import re
from html import escape
from typing import Any

from pypdf import PdfReader

MODERN_CSS = """
  :root {
    --accent-color: hsl(187 74% 32%);
    --font-family: "Liberation Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, 'Helvetica Neue', Arial, sans-serif;
    --font-size: 10.5px;
    --page-margin: 0.4in;
  }
  @page {
    margin: var(--page-margin);
    size: A4;
  }
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-variant-ligatures: none;
    font-feature-settings: "liga" 0, "clig" 0, "dlig" 0;
  }
  html {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  body {
    font-family: var(--font-family);
    font-size: var(--font-size);
    line-height: 1.45;
    color: #1a1a2e;
    background: #ffffff;
    padding: 0;
    margin: 0;
  }
  .page {
    width: 100%;
    max-width: 210mm;
    margin: 0 auto;
    padding: 0;
  }
  /* === HEADER === */
  .header {
    margin-bottom: 10px;
  }
  .header h1 {
    font-size: 24px;
    font-weight: 700;
    color: #1a1a2e;
    letter-spacing: -0.02em;
    margin-bottom: 4px;
    line-height: 1.1;
  }
  .header-gradient {
    height: 2px;
    background: linear-gradient(to right, var(--accent-color), hsl(270, 70%, 45%));
    border-radius: 1px;
    margin-bottom: 6px;
  }
  .contact-row {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 10px;
    font-size: 10px;
    line-height: 1.3;
    color: #555;
  }
  .contact-row a {
    color: #555;
    text-decoration: none;
  }
  .contact-row .separator {
    color: #ccc;
  }
  /* === SECTIONS === */
  .section {
    margin-bottom: 9px;
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .section-title {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--accent-color);
    border-bottom: 1.5px solid #e2e2e2;
    padding-bottom: 2px;
    margin-bottom: 6px;
    line-height: 1.2;
  }
  .summary-text {
    font-size: var(--font-size);
    line-height: 1.5;
    color: #2f2f2f;
  }
  /* === COMPETENCIES === */
  .competencies-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }
  .competency-tag {
    font-size: 9.5px;
    font-weight: 500;
    color: hsl(187, 74%, 28%);
    background: hsl(187, 40%, 95%);
    padding: 2.5px 7px;
    border-radius: 3px;
    border: 1px solid hsl(187, 40%, 88%);
  }
  /* === WORK / EXPERIENCE === */
  .job {
    margin-bottom: 7px;
  }
  .job-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 10px;
    margin-bottom: 1px;
  }
  .job-company {
    font-size: 11.5px;
    font-weight: 600;
    color: hsl(270, 70%, 45%);
  }
  .job-period {
    font-size: 9.5px;
    color: #777;
    white-space: nowrap;
  }
  .job-role {
    font-size: 10.5px;
    font-weight: 600;
    color: #333;
    margin-bottom: 1px;
  }
  .job-location {
    font-size: 9px;
    color: #888;
    margin-bottom: 2px;
  }
  ul.claim-list, .job ul {
    padding-left: 15px;
    margin-top: 2px;
  }
  ul.claim-list li, .job li {
    font-size: 10px;
    line-height: 1.45;
    color: #333;
    margin-bottom: 2px;
  }
  /* === PROJECTS === */
  .project {
    margin-bottom: 6px;
  }
  .project-title {
    font-size: 11px;
    font-weight: 600;
    color: hsl(270, 70%, 45%);
  }
  .project-badge {
    font-size: 8.5px;
    font-weight: 500;
    color: var(--accent-color);
    background: hsl(187, 40%, 95%);
    padding: 1px 5px;
    border-radius: 2px;
    margin-left: 5px;
  }
  .project-desc {
    font-size: 10px;
    color: #444;
    margin-top: 1px;
    line-height: 1.45;
  }
  .project-tech {
    font-size: 9px;
    color: #888;
    margin-top: 1px;
  }
  /* === EDUCATION === */
  .edu-item {
    margin-bottom: 4px;
  }
  .edu-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 10px;
  }
  .edu-title {
    font-weight: 600;
    font-size: 10.5px;
    color: #333;
  }
  .edu-org {
    color: hsl(270, 70%, 45%);
    font-weight: 500;
    margin-left: 4px;
  }
  .edu-year {
    font-size: 9.5px;
    color: #777;
    white-space: nowrap;
  }
  .edu-desc {
    font-size: 9.5px;
    color: #666;
    margin-top: 1px;
    line-height: 1.4;
  }
  /* === CERTIFICATIONS === */
  .cert-table {
    display: table;
    width: 100%;
  }
  .cert-item {
    display: table-row;
  }
  .cert-item > * {
    display: table-cell;
    vertical-align: baseline;
    padding-bottom: 3px;
  }
  .cert-title {
    font-size: 10px;
    font-weight: 500;
    color: #333;
  }
  .cert-org {
    color: hsl(270, 70%, 45%);
    white-space: nowrap;
    padding-left: 10px;
    font-size: 9.5px;
  }
  .cert-year {
    font-size: 9.5px;
    color: #777;
    white-space: nowrap;
    text-align: right;
    width: 40px;
  }
  /* === SKILLS === */
  .skills-grid {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .skill-item {
    font-size: 10px;
    color: #444;
    line-height: 1.4;
  }
  .skill-category {
    font-weight: 600;
    color: #333;
  }
"""


def _format_contact_item(key: str, value: str) -> str:
    val = escape(value.strip())
    if "email" in key or "@" in val:
        email = val.replace("mailto:", "")
        return f'<a href="mailto:{email}">{email}</a>'
    if "phone" in key or re.match(r"^\+?[0-9\*\s\-]{7,}$", val):
        return f'<a href="tel:{val}">{val}</a>'
    if "linkedin" in key or "linkedin.com" in val:
        url = val if val.startswith("http") else f"https://{val}"
        label = re.sub(r"^https?://(www\.)?", "", val).rstrip("/")
        return f'<a href="{url}">{label}</a>'
    if "github" in key or "github.com" in val:
        url = val if val.startswith("http") else f"https://{val}"
        label = re.sub(r"^https?://(www\.)?", "", val).rstrip("/")
        return f'<a href="{url}">{label}</a>'
    if "website" in key or val.startswith(("http://", "https://")):
        url = val if val.startswith("http") else f"https://{val}"
        label = re.sub(r"^https?://(www\.)?", "", val).rstrip("/")
        return f'<a href="{url}">{label}</a>'
    return f"<span>{val}</span>"


def _format_date(d: str) -> str:
    if not d:
        return ""
    if d.lower() == "present":
        return "Present"
    if d == "2026-03":
        return "Early 2026"
    m = re.match(r"^(\d{4})-(\d{2})$", d)
    if m:
        months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return f"{months[int(m.group(2))]} {m.group(1)}"
    return d


def render_modern_html(cv: Any, profile: Any = None) -> str:
    """Generate clean semantic HTML matching career-ops template."""
    identity = dict(getattr(cv, "identity", {}) or {})
    if profile and hasattr(profile, "identity") and profile.identity:
        for k, v in profile.identity.items():
            if k not in identity:
                identity[k] = v

    name = escape(identity.get("name") or identity.get("full_name") or "Curriculum Vitae")
    contacts = [
        _format_contact_item(k, v)
        for k, v in identity.items()
        if k not in {"name", "full_name"} and v and str(v).strip()
    ]
    contact_html = ' <span class="separator">|</span> '.join(contacts)

    sections_html: list[str] = []

    is_vi = getattr(cv, "language", "en") == "vi"
    labels = {
        "summary": "Tóm tắt chuyên môn" if is_vi else "Professional Summary",
        "competencies": "Năng lực cốt lõi" if is_vi else "Core Competencies",
        "experience": "Kinh nghiệm làm việc" if is_vi else "Engineering Experience",
        "projects": "Dự án & Đóng góp" if is_vi else "Projects & Open Source",
        "education": "Học vấn" if is_vi else "Education",
        "credentials": "Chứng chỉ & Giải thưởng" if is_vi else "Certifications",
        "skills": "Kỹ năng chuyên môn" if is_vi else "Technical Skills",
    }

    claims = list(getattr(cv, "claims", []))
    claims_by_id = {getattr(c, "evidence_id", ""): c for c in claims}

    # 1. Summary
    summary_claim = next(
        (c for c in claims if getattr(c, "evidence_id", "") == "ev_summary" or "summary" in getattr(c, "evidence_id", "")),
        None,
    )
    if summary_claim:
        sections_html.append(f"""
        <div class="section">
          <div class="section-title">{labels['summary']}</div>
          <div class="summary-text">{escape(summary_claim.text)}</div>
        </div>""")

    # 2. Competencies (pills)
    competencies_list = [
        "Object-Oriented Programming (OOP)",
        "Backend & RESTful APIs",
        "Distributed Systems & Streaming",
        "PostgreSQL & Database Design",
        "C++ & Python Systems",
        "Docker & CI/CD Automation",
        "Git & Code Review Discipline",
    ]
    comp_tags = "".join(f'<span class="competency-tag">{escape(t)}</span>' for t in competencies_list)
    sections_html.append(f"""
    <div class="section">
      <div class="section-title">{labels['competencies']}</div>
      <div class="competencies-grid">{comp_tags}</div>
    </div>""")

    # 3. Experience
    exp_jobs = getattr(profile, "experience", []) if profile else []
    exp_html_items = []

    for exp in exp_jobs:
        title_raw = getattr(exp, "title", "")
        m = re.match(r"^(.*?)\s*\((.*?)\)$", title_raw)
        if m:
            role, comp = m.groups()
        else:
            role, comp = title_raw, ""

        start = getattr(exp, "start", "") or ""
        end = getattr(exp, "end", "") or ""
        period = f"{_format_date(start)} - {_format_date(end)}" if start or end else ""

        bullets = []
        for evid in getattr(exp, "evidence_ids", []):
            if evid in claims_by_id:
                bullets.append(f"<li>{escape(claims_by_id[evid].text)}</li>")

        if bullets:
            exp_html_items.append(f"""
            <div class="job">
              <div class="job-header">
                <span class="job-company">{escape(comp.strip())}</span>
                <span class="job-period">{escape(period.strip())}</span>
              </div>
              <div class="job-role">{escape(role.strip())}</div>
              <div class="job-location">Remote</div>
              <ul class="claim-list">
                {''.join(bullets)}
              </ul>
            </div>""")

    # Fallback if no structured experience from profile
    if not exp_html_items:
        exp_claims = [c for c in claims if getattr(c, "section", "") == "experience" and getattr(c, "evidence_id", "") != "ev_summary"]
        for c in exp_claims:
            exp_html_items.append(f"""
            <div class="job">
              <ul class="claim-list">
                <li>{escape(c.text)}</li>
              </ul>
            </div>""")

    if exp_html_items:
        sections_html.append(f"""
        <div class="section">
          <div class="section-title">{labels['experience']}</div>
          {''.join(exp_html_items)}
        </div>""")

    # 4. Projects & Contributions
    proj_claims = [
        c for c in claims
        if getattr(c, "evidence_id", "").startswith("ev_proj_")
        or (
            getattr(c, "section", "") == "other"
            and not getattr(c, "evidence_id", "").startswith(("ev_summary", "ev_exp_", "ev_edu_", "ev_skills_", "ev_cert_"))
        )
    ]
    proj_meta = {
        "ev_proj_valo_map_veto": ("Valorant Map Veto Helper", "Open Source"),
        "ev_proj_xashds_arm64": ("XashDS ARM64 Server", "Open Source"),
        "ev_proj_valospectra_hud": ("ValoSpectra Tournament HUD", "Contributor"),
        "ev_proj_nrc_camera": ("NRCCameraService", "Open Source"),
        "ev_proj_fire_detection": ("FireDetection_YOLOv26", "AI Project"),
        "ev_proj_phenikaa_calendar": ("PhenikaaCalendarExporter", "Open Source"),
    }
    proj_html_items = []
    for pc in proj_claims:
        evid = getattr(pc, "evidence_id", "")
        pname, badge = proj_meta.get(evid, (evid.replace("ev_proj_", "").replace("_", " ").title(), "Project"))
        text = getattr(pc, "text", "")
        parts = text.rsplit(". ", 1)
        if len(parts) == 2 and ("," in parts[1] or len(parts[1].split()) <= 6):
            desc, tech = parts[0] + ".", parts[1]
        else:
            desc, tech = text, ""

        tech_html = f'<div class="project-tech">{escape(tech)}</div>' if tech else ""
        proj_html_items.append(f"""
        <div class="project">
          <div class="project-title">{escape(pname)} <span class="project-badge">{escape(badge)}</span></div>
          <div class="project-desc">{escape(desc)}</div>
          {tech_html}
        </div>""")

    if proj_html_items:
        sections_html.append(f"""
        <div class="section">
          <div class="section-title">{labels['projects']}</div>
          {''.join(proj_html_items)}
        </div>""")

    # 5. Education
    edu_claims = [c for c in claims if getattr(c, "section", "") == "education" or getattr(c, "evidence_id", "").startswith("ev_edu_")]
    edu_html_items = []
    for ec in edu_claims:
        text = getattr(ec, "text", "")
        m = re.match(
            r"^(Bachelor\s+of\s+Computer\s+Science|Bachelor\s+of\s+[^,]+?|Master\s+of\s+[^,]+?|B\.S\.[^,]*?)\s+([A-Z][A-Za-z\s]+?(?:University|College|Institute))\s+(Expected\s+\d{4}|\d{4})\s*(.*)$",
            text,
            re.IGNORECASE,
        )
        if m:
            degree, school, year, desc = m.groups()
            desc_html = f'<div class="edu-desc">{escape(desc)}</div>' if desc else ""
            edu_html_items.append(f"""
            <div class="edu-item">
              <div class="edu-header">
                <div class="edu-title">{escape(degree)} <span class="edu-org">{escape(school)}</span></div>
                <div class="edu-year">{escape(year)}</div>
              </div>
              {desc_html}
            </div>""")
        else:
            edu_html_items.append(f"""
            <div class="edu-item">
              <div class="edu-desc">{escape(text)}</div>
            </div>""")

    if edu_html_items:
        sections_html.append(f"""
        <div class="section">
          <div class="section-title">{labels['education']}</div>
          {''.join(edu_html_items)}
        </div>""")

    # 6. Certifications
    cert_claims = [c for c in claims if getattr(c, "section", "") == "credentials" or getattr(c, "evidence_id", "").startswith("ev_cert_")]
    cert_html_items = []
    for cc in cert_claims:
        text = getattr(cc, "text", "")
        m = re.match(r"^(.*?)(?:\s+(\d{4})\s+(.*?)|(?:\s+\((\d{4})(?:,\s*(.*?))?\)))$", text)
        if m:
            groups = m.groups()
            ctitle = (groups[0] or "").strip()
            cyear = groups[1] or groups[3] or ""
            corg = groups[2] or groups[4] or ""
            cert_html_items.append(f"""
            <div class="cert-item">
              <span class="cert-title">{escape(ctitle)}</span>
              <span class="cert-org">{escape(corg)}</span>
              <span class="cert-year">{escape(cyear)}</span>
            </div>""")
        else:
            cert_html_items.append(f"""
            <div class="cert-item">
              <span class="cert-title">{escape(text)}</span>
              <span class="cert-org"></span>
              <span class="cert-year"></span>
            </div>""")

    if cert_html_items:
        sections_html.append(f"""
        <div class="section">
          <div class="section-title">{labels['credentials']}</div>
          <div class="cert-table">
            {''.join(cert_html_items)}
          </div>
        </div>""")

    # 7. Technical Skills
    skill_claims = [c for c in claims if getattr(c, "section", "") == "skills" or getattr(c, "evidence_id", "").startswith("ev_skills_")]
    skill_html_items = []
    for sc in skill_claims:
        text = getattr(sc, "text", "")
        if ":" in text:
            cat, rest = text.split(":", 1)
            skill_html_items.append(
                f'<div class="skill-item"><span class="skill-category">{escape(cat.strip())}: </span>{escape(rest.strip())}</div>'
            )
        else:
            skill_html_items.append(f'<div class="skill-item">{escape(text)}</div>')

    if skill_html_items:
        sections_html.append(f"""
        <div class="section">
          <div class="section-title">{labels['skills']}</div>
          <div class="skills-grid">
            {''.join(skill_html_items)}
          </div>
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="{getattr(cv, 'language', 'en')}">
<head>
<meta charset="UTF-8">
<title>{name} — CV</title>
<style>
{MODERN_CSS}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <h1>{name}</h1>
    <div class="header-gradient"></div>
    <div class="contact-row">
      {contact_html}
    </div>
  </div>
  {''.join(sections_html)}
</div>
</body>
</html>"""


def render_modern_pdf(cv: Any, max_pages: int = 2, *, template: str = "modern", profile: Any = None) -> bytes:
    """Render CV via Playwright Chromium into PDF; fall back to ReportLab if Playwright fails."""
    from .cv_templates import render_template_html

    html_content = render_template_html(cv, template_name=template, profile=profile)
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html_content, wait_until="load")
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "0.4in", "bottom": "0.4in", "left": "0.4in", "right": "0.4in"},
            )
            browser.close()

        # Check page count
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if len(reader.pages) > max_pages:
            raise ValueError(f"CV exceeds {max_pages} page budget (actual: {len(reader.pages)})")
        return pdf_bytes
    except (OSError, RuntimeError, ValueError):
        # Fallback to reportlab
        from .cv_render import render_pdf
        return render_pdf(cv, max_pages=max_pages)

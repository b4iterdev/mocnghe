"""Modern ATS-optimized HTML & Playwright PDF renderer matching the career-ops design."""
import re
from html import escape
from typing import Any

from pypdf import PdfReader

MODERN_CSS = """
  :root {
    --accent-color: hsl(187 74% 32%);
    --font-family: "Liberation Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, 'Helvetica Neue', Arial, sans-serif;
    --font-size: 11px;
    --page-margin: 0.5in;
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
    line-height: 1.5;
    color: #1a1a2e;
    background: #ffffff;
    padding: 0;
    margin: 0;
  }
  .page {
    width: 100%;
    max-width: 210mm;
    margin: 0 auto;
    padding: 2px 0;
  }
  /* === HEADER === */
  .header {
    margin-bottom: 16px;
  }
  .header h1 {
    font-size: 26px;
    font-weight: 700;
    color: #1a1a2e;
    letter-spacing: -0.02em;
    margin-bottom: 5px;
    line-height: 1.15;
  }
  .header-gradient {
    height: 2px;
    background: linear-gradient(to right, var(--accent-color), hsl(270, 70%, 45%));
    border-radius: 1px;
    margin-bottom: 8px;
  }
  .contact-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 12px;
    font-size: 10.5px;
    line-height: 1.4;
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
    margin-bottom: 14px;
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .section-title {
    font-size: 11.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--accent-color);
    border-bottom: 1.5px solid #e2e2e2;
    padding-bottom: 3px;
    margin-bottom: 8px;
    line-height: 1.2;
  }
  .summary-text {
    font-size: var(--font-size);
    line-height: 1.6;
    color: #2f2f2f;
  }
  /* === COMPETENCIES === */
  .competencies-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .competency-tag {
    font-size: 10px;
    font-weight: 500;
    color: hsl(187, 74%, 28%);
    background: hsl(187, 40%, 95%);
    padding: 3px 8px;
    border-radius: 3px;
    border: 1px solid hsl(187, 40%, 88%);
  }
  /* === WORK / EXPERIENCE === */
  .job {
    margin-bottom: 10px;
  }
  .job-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 2px;
  }
  .job-company {
    font-size: 12px;
    font-weight: 600;
    color: hsl(270, 70%, 45%);
  }
  .job-period {
    font-size: 10px;
    color: #777;
    white-space: nowrap;
  }
  .job-role {
    font-size: 11px;
    font-weight: 600;
    color: #333;
    margin-bottom: 4px;
  }
  ul.claim-list {
    padding-left: 16px;
    margin-top: 4px;
  }
  ul.claim-list li {
    font-size: 10.5px;
    line-height: 1.55;
    color: #333;
    margin-bottom: 3px;
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
    return f"<span>{val}</span>"


def render_modern_html(cv: Any) -> str:
    """Generate clean semantic HTML matching career-ops template."""
    name = escape(cv.identity.get("name", "Curriculum Vitae"))
    contacts = [
        _format_contact_item(k, v)
        for k, v in cv.identity.items()
        if k != "name" and v and v.strip()
    ]
    contact_html = ' <span class="separator">|</span> '.join(contacts)

    sections_html: list[str] = []

    # Map labels
    is_vi = getattr(cv, "language", "en") == "vi"
    labels = {
        "summary": "Tóm tắt chuyên môn" if is_vi else "Professional Summary",
        "skills": "Kỹ năng cốt lõi" if is_vi else "Core Competencies",
        "experience": "Kinh nghiệm làm việc" if is_vi else "Engineering Experience",
        "education": "Học vấn" if is_vi else "Education",
        "credentials": "Chứng chỉ & Giải thưởng" if is_vi else "Certifications",
        "other": "Dự án & Đóng góp" if is_vi else "Projects & Contributions",
    }

    # Group claims
    grouped: dict[str, list[Any]] = {
        "experience": [],
        "education": [],
        "skills": [],
        "credentials": [],
        "other": [],
    }
    for claim in getattr(cv, "claims", []):
        sec = claim.section if claim.section in grouped else "other"
        grouped[sec].append(claim)

    # 1. Experience
    if grouped["experience"]:
        items_html = []
        for claim in grouped["experience"]:
            text = escape(claim.text)
            # Try splitting into Role/Org and bullets if format matches "Company — Role, Dates. Text"
            match = re.match(r"^([^—\–]+)[—\–]\s*([^,\.]+),\s*([^.]+)\.\s*(.*)$", text)
            if match:
                org, role, dates, body = match.groups()
                items_html.append(f"""
                <div class="job">
                  <div class="job-header">
                    <span class="job-company">{org.strip()}</span>
                    <span class="job-period">{dates.strip()}</span>
                  </div>
                  <div class="job-role">{role.strip()}</div>
                  <ul class="claim-list">
                    <li>{body.strip()}</li>
                  </ul>
                </div>""")
            else:
                items_html.append(f"""
                <div class="job">
                  <ul class="claim-list">
                    <li>{text}</li>
                  </ul>
                </div>""")
        sections_html.append(f"""
        <div class="section">
          <div class="section-title">{labels['experience']}</div>
          {''.join(items_html)}
        </div>""")

    # 2. Projects & Contributions
    if grouped["other"]:
        items_html = []
        for claim in grouped["other"]:
            text = escape(claim.text)
            match = re.match(r"^([^:]+):\s*(.*)$", text)
            if match:
                title, desc = match.groups()
                items_html.append(f"""
                <div class="job">
                  <div class="job-header">
                    <span class="job-company">{title.strip()}</span>
                  </div>
                  <ul class="claim-list">
                    <li>{desc.strip()}</li>
                  </ul>
                </div>""")
            else:
                items_html.append(f"""
                <div class="job">
                  <ul class="claim-list">
                    <li>{text}</li>
                  </ul>
                </div>""")
        sections_html.append(f"""
        <div class="section">
          <div class="section-title">{labels['other']}</div>
          {''.join(items_html)}
        </div>""")

    # 3. Education
    if grouped["education"]:
        items_html = []
        for claim in grouped["education"]:
            items_html.append(f"""
            <div class="job">
              <ul class="claim-list">
                <li>{escape(claim.text)}</li>
              </ul>
            </div>""")
        sections_html.append(f"""
        <div class="section">
          <div class="section-title">{labels['education']}</div>
          {''.join(items_html)}
        </div>""")

    # 4. Skills / Competencies
    if grouped["skills"]:
        tags_html = "".join(
            f'<span class="competency-tag">{escape(c.text)}</span>'
            for c in grouped["skills"]
        )
        sections_html.append(f"""
        <div class="section">
          <div class="section-title">{labels['skills']}</div>
          <div class="competencies-grid">{tags_html}</div>
        </div>""")

    # 5. Credentials
    if grouped["credentials"]:
        items_html = "".join(
            f'<li>{escape(c.text)}</li>' for c in grouped["credentials"]
        )
        sections_html.append(f"""
        <div class="section">
          <div class="section-title">{labels['credentials']}</div>
          <ul class="claim-list">{items_html}</ul>
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


def render_modern_pdf(cv: Any, max_pages: int = 2) -> bytes:
    """Render CV via Playwright Chromium into PDF; fall back to ReportLab if Playwright fails."""
    html_content = render_modern_html(cv)
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html_content, wait_until="load")
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "0.45in", "bottom": "0.45in", "left": "0.45in", "right": "0.45in"},
            )
            browser.close()

        # Check page count
        import io
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if len(reader.pages) > max_pages:
            raise ValueError(f"CV exceeds {max_pages} page budget (actual: {len(reader.pages)})")
        return pdf_bytes
    except (OSError, RuntimeError, ValueError):
        # Fallback to reportlab
        from .cv_render import render_pdf
        return render_pdf(cv, max_pages=max_pages)

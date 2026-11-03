from html import escape
from pathlib import Path
from typing import Any

from .cv_modern_render import render_modern_html

BUILTIN_TEMPLATES = ["modern", "classic", "minimal"]


def list_templates() -> list[str]:
    return list(BUILTIN_TEMPLATES)


def _format_contact(key: str, val: str) -> str:
    key_lower = key.lower()
    val_clean = val.strip()
    if "@" in val_clean:
        return f'<a href="mailto:{escape(val_clean)}">{escape(val_clean)}</a>'
    if key_lower in ("linkedin", "github", "portfolio", "website") or val_clean.startswith("http"):
        url = val_clean if val_clean.startswith("http") else f"https://{val_clean}"
        return f'<a href="{escape(url)}" target="_blank" rel="noopener">{escape(val_clean)}</a>'
    return f"<span>{escape(val_clean)}</span>"


def _render_classic_html(cv: Any) -> str:
    name = escape(cv.identity.get("name") or cv.identity.get("full_name") or "Curriculum Vitae")
    contacts = [
        _format_contact(k, v)
        for k, v in cv.identity.items()
        if k not in {"name", "full_name"} and v and v.strip()
    ]
    contact_bar = " &bull; ".join(contacts)

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

    is_vi = getattr(cv, "language", "en") == "vi"
    labels = {
        "skills": "KỸ NĂNG CHUYÊN MÔN" if is_vi else "TECHNICAL SKILLS",
        "experience": "KINH NGHIỆM LÀM VIỆC" if is_vi else "PROFESSIONAL EXPERIENCE",
        "education": "HỌC VẤN" if is_vi else "EDUCATION",
        "credentials": "CHỨNG CHỈ" if is_vi else "CREDENTIALS & CERTIFICATIONS",
        "other": "DỰ ÁN TIÊU BIỂU" if is_vi else "SELECTED PROJECTS",
    }

    sections_html = []

    # Skills section
    if grouped["skills"]:
        skill_items = [f"<li>{escape(c.text)}</li>" for c in grouped["skills"]]
        sections_html.append(f"""
        <div class="section">
          <h2>{labels['skills']}</h2>
          <ul>{''.join(skill_items)}</ul>
        </div>
        """)

    # Experience section
    if grouped["experience"]:
        exp_items = [f"<li>{escape(c.text)}</li>" for c in grouped["experience"]]
        sections_html.append(f"""
        <div class="section">
          <h2>{labels['experience']}</h2>
          <ul>{''.join(exp_items)}</ul>
        </div>
        """)

    # Projects
    if grouped["other"]:
        proj_items = [f"<li>{escape(c.text)}</li>" for c in grouped["other"]]
        sections_html.append(f"""
        <div class="section">
          <h2>{labels['other']}</h2>
          <ul>{''.join(proj_items)}</ul>
        </div>
        """)

    # Education
    if grouped["education"]:
        edu_items = [f"<li>{escape(c.text)}</li>" for c in grouped["education"]]
        sections_html.append(f"""
        <div class="section">
          <h2>{labels['education']}</h2>
          <ul>{''.join(edu_items)}</ul>
        </div>
        """)

    # Credentials
    if grouped["credentials"]:
        cred_items = [f"<li>{escape(c.text)}</li>" for c in grouped["credentials"]]
        sections_html.append(f"""
        <div class="section">
          <h2>{labels['credentials']}</h2>
          <ul>{''.join(cred_items)}</ul>
        </div>
        """)

    return f"""<!DOCTYPE html>
<html lang="{getattr(cv, 'language', 'en')}">
<head>
<meta charset="utf-8">
<title>{name} — CV</title>
<style>
  @page {{
    size: A4;
    margin: 18mm 18mm 18mm 18mm;
  }}
  body {{
    font-family: "Times New Roman", Times, Georgia, serif;
    color: #111;
    line-height: 1.4;
    font-size: 10.5pt;
    margin: 0;
    padding: 0;
  }}
  .template-classic {{
    max-width: 800px;
    margin: 0 auto;
  }}
  header {{
    text-align: center;
    border-bottom: 2px solid #222;
    padding-bottom: 8px;
    margin-bottom: 14px;
  }}
  h1 {{
    font-size: 20pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 0 0 6px 0;
  }}
  .contact-bar {{
    font-size: 9.5pt;
    color: #444;
  }}
  .contact-bar a {{
    color: #111;
    text-decoration: none;
  }}
  .section {{
    margin-bottom: 12px;
  }}
  h2 {{
    font-size: 11pt;
    font-weight: bold;
    letter-spacing: 0.5px;
    border-bottom: 1px solid #777;
    padding-bottom: 2px;
    margin: 10px 0 6px 0;
  }}
  ul {{
    margin: 4px 0 6px 18px;
    padding: 0;
  }}
  li {{
    margin-bottom: 4px;
  }}
</style>
</head>
<body class="template-classic">
  <header>
    <h1>{name}</h1>
    <div class="contact-bar">{contact_bar}</div>
  </header>
  {''.join(sections_html)}
</body>
</html>"""


def _render_minimal_html(cv: Any) -> str:
    name = escape(cv.identity.get("name") or cv.identity.get("full_name") or "Curriculum Vitae")
    contacts = [
        _format_contact(k, v)
        for k, v in cv.identity.items()
        if k not in {"name", "full_name"} and v and v.strip()
    ]
    contact_bar = " / ".join(contacts)

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

    sections_html = []
    for sec_name, items in grouped.items():
        if not items:
            continue
        items_li = [f"<li>{escape(c.text)}</li>" for c in items]
        sections_html.append(f"""
        <div class="min-sec">
          <div class="sec-title">{sec_name.upper()}</div>
          <ul class="sec-list">{''.join(items_li)}</ul>
        </div>
        """)

    return f"""<!DOCTYPE html>
<html lang="{getattr(cv, 'language', 'en')}">
<head>
<meta charset="utf-8">
<title>{name}</title>
<style>
  @page {{
    size: A4;
    margin: 12mm 15mm;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #1a1a1a;
    font-size: 10pt;
    line-height: 1.35;
    margin: 0;
  }}
  .template-minimal {{
    max-width: 800px;
    margin: 0 auto;
  }}
  .min-header {{
    margin-bottom: 14px;
  }}
  .min-name {{
    font-size: 18pt;
    font-weight: 700;
    margin: 0;
  }}
  .min-contacts {{
    font-size: 9pt;
    color: #666;
    margin-top: 4px;
  }}
  .min-contacts a {{
    color: #000;
    text-decoration: underline;
  }}
  .min-sec {{
    margin-bottom: 10px;
  }}
  .sec-title {{
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: #555;
    margin-bottom: 4px;
  }}
  .sec-list {{
    margin: 0 0 0 16px;
    padding: 0;
  }}
  li {{
    margin-bottom: 3px;
  }}
</style>
</head>
<body class="template-minimal">
  <div class="min-header">
    <div class="min-name">{name}</div>
    <div class="min-contacts">{contact_bar}</div>
  </div>
  {''.join(sections_html)}
</body>
</html>"""


def render_template_html(cv: Any, template_name: str = "modern", custom_path: Path | None = None, profile: Any = None) -> str:
    if custom_path is not None and custom_path.exists():
        raw_tmpl = custom_path.read_text(encoding="utf-8")
        name = escape(cv.identity.get("name") or cv.identity.get("full_name") or "")
        skills = ", ".join([c.text for c in getattr(cv, "claims", []) if c.section == "skills"])
        rendered = raw_tmpl.replace("{{ name }}", name).replace("{{ skills }}", skills)
        return rendered

    normalized = template_name.lower().strip()
    if normalized == "classic":
        return _render_classic_html(cv)
    if normalized == "minimal":
        return _render_minimal_html(cv)
    return render_modern_html(cv, profile=profile)

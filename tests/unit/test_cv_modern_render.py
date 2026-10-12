from pypdf import PdfReader

from mocnghe.cv import CVService
from mocnghe.cv_modern_render import render_modern_html, render_modern_pdf
from mocnghe.cv_render import export_cv


def test_render_modern_html_and_pdf(repo, tmp_path):
    s = CVService(repo)
    cv = s.create(
        "v1",
        ["ev1"],
        language="vi",
        identity_keys=["name"],
    )
    s.approve(cv.id, s.content_hash(cv))

    # HTML generation
    html = render_modern_html(cv)
    assert "header-gradient" in html
    assert "Ứng viên mẫu" in html
    assert "contact-row" in html

    # PDF generation via Playwright (or fallback)
    pdf_bytes = render_modern_pdf(cv, max_pages=1)
    assert len(pdf_bytes) > 0
    import io

    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert "Ứng viên mẫu" in text

    # Export bundle with modern engine
    target = tmp_path / "modern_bundle"
    export_cv(s, cv.id, target, engine="modern", max_pages=1)
    assert (target / "cv.pdf").exists()
    assert (target / "cv.html").exists()
    assert (target / "cv.json").exists()

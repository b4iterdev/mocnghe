import pytest
from PIL import Image

from mocnghe.cv import CVService
from mocnghe.cv_render import render_pdf
from mocnghe.cv_visual import compare_images, pdf_to_images, verify_pdf_visual


def test_pdf_to_images_and_compare(repo):
    s = CVService(repo)
    cv = s.create("v1", ["ev1"], language="vi")
    pdf_bytes = render_pdf(cv)
    images = pdf_to_images(pdf_bytes, dpi=72)
    assert len(images) == 1
    assert images[0].size[0] > 0 and images[0].size[1] > 0

    # Identical image comparison
    passed, diff_ratio, diff_img = compare_images(images[0], images[0], tolerance=0.0)
    assert passed
    assert diff_ratio == 0.0
    assert diff_img is None


def test_compare_images_with_differences():
    img1 = Image.new("RGB", (100, 100), color=(255, 255, 255))
    img2 = Image.new("RGB", (100, 100), color=(255, 255, 255))
    # Change 1 pixel
    img2.putpixel((50, 50), (0, 0, 0))

    passed, diff_ratio, diff_img = compare_images(img1, img2, tolerance=0.0)
    assert not passed
    assert diff_ratio == 1 / 10000
    assert diff_img is not None

    # Within tolerance
    passed_tol, _, _ = compare_images(img1, img2, tolerance=0.001)
    assert passed_tol


def test_verify_pdf_visual_snapshot_workflow(repo, tmp_path):
    s = CVService(repo)
    cv = s.create("v1", ["ev1"], language="vi")
    pdf_bytes = render_pdf(cv)
    snapshot_path = tmp_path / "baseline.png"

    # First run creates baseline
    res = verify_pdf_visual(pdf_bytes, snapshot_path, dpi=72)
    assert res["status"] == "baseline_updated"
    assert res["passed"]
    assert snapshot_path.exists()

    # Second run compares against baseline
    res2 = verify_pdf_visual(pdf_bytes, snapshot_path, dpi=72)
    assert res2["status"] == "matched"
    assert res2["passed"]
    assert res2["diff_ratio"] == 0.0


def test_invalid_pdf_bytes_raises():
    with pytest.raises(ValueError, match="empty"):
        pdf_to_images(b"")

"""
UI smoke tests dùng Streamlit AppTest.

Mục tiêu: đảm bảo app render không exception và flow chính
upload -> detect -> confirm -> perspective -> enhance chạy được end-to-end.
"""

import cv2
import numpy as np
import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "smartscan" / "ui" / "app.py"


def _make_document_jpeg() -> bytes:
    """Tạo ảnh tài liệu giả: nền sáng + khung đen + vài dòng text giả."""
    img = np.full((700, 900, 3), 235, dtype=np.uint8)
    cv2.rectangle(img, (120, 90), (780, 610), (40, 40, 40), 4)
    for y in range(160, 560, 45):
        x0 = 180 + (y % 90)
        cv2.line(img, (x0, y), (x0 + 480 - (y % 120), y), (60, 60, 60), 6)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


def _state(at, key):
    return at.session_state[key] if key in at.session_state else None


def test_ui_renders_without_exception():
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    assert not at.exception


def test_ui_end_to_end_smoke():
    at = AppTest.from_file(str(APP_PATH), default_timeout=180)
    at.run()
    assert not at.exception

    # Step 1: upload
    at.file_uploader[0].upload("doc.jpg", _make_document_jpeg(), "image/jpeg")
    at.run()
    assert not at.exception
    assert _state(at, "source_image") is not None

    # Step 2: detect
    at.button(key="btn_detect").click()
    at.run()
    assert not at.exception
    det = _state(at, "detection_result")
    assert det is not None and det["success"], det and det.get("message")
    assert _state(at, "detected_corners") is not None

    # Step 2: confirm corners
    at.button(key="btn_confirm_corners").click()
    at.run()
    assert not at.exception
    assert _state(at, "corners_confirmed") is True

    # Step 3: perspective
    at.button(key="btn_perspective").click()
    at.run()
    assert not at.exception
    assert _state(at, "scanned_image") is not None

    # Step 4: enhancement
    at.button(key="btn_enhance").click()
    at.run()
    assert not at.exception
    assert _state(at, "enhanced_image") is not None


def test_ui_invalid_upload_shows_error():
    at = AppTest.from_file(str(APP_PATH), default_timeout=120)
    at.run()
    at.file_uploader[0].upload("bad.jpg", b"not an image", "image/jpeg")
    at.run()
    assert not at.exception
    assert _state(at, "source_image") is None

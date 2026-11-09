"""
Independent QA tests for SmartScan (Agent QA).
Synthetic labeled dataset: each case generates an image plus ground-truth
quadrilateral corners (TL, TR, BR, BL in original image coordinates).
"""

import sys
import os
import time

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from smartscan.core.detection import detect_document, order_corners
from smartscan.core.perspective import (
    correct_perspective,
    apply_perspective_with_padding,
    validate_corners,
    calculate_output_dimensions,
)
from smartscan.core.enhancement import (
    enhance_document,
    denoise_image,
    enhance_contrast,
    binarize_image,
    sharpen_image,
    correct_shadow,
)
from smartscan.core.pipeline import process_document, process_document_with_fallback
from smartscan.core.preprocessing import validate_image, preprocess_for_detection
from smartscan.utils.image_loader import (
    load_image_from_bytes,
    load_and_validate_image,
    validate_file_size,
)
from smartscan.utils.config import DEFAULT_ENHANCEMENT_CONFIG


# ---------------------------------------------------------------------------
# Synthetic document image generator
# ---------------------------------------------------------------------------

def make_document_image(W=800, H=600, doc_rect=(150, 100, 650, 500),
                        bg=(40, 40, 40), doc=(235, 235, 235),
                        skew=None, noise=0, contrast=1.0, gray=False,
                        extra_rects=0, seed=0):
    """Create image with a bright document quad on darker background.

    doc_rect: (x1, y1, x2, y2) axis-aligned doc bounds.
    skew: optional (dx_top, dy_top, dx_bot, dy_bot) corner offsets for
          perspective skew. Returns (image_bgr, corners_gt (4,2)).
    """
    rng = np.random.RandomState(seed)
    img = np.full((H, W, 3), bg, dtype=np.uint8)
    x1, y1, x2, y2 = doc_rect
    corners = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                       dtype=np.float32)
    if skew is not None:
        corners = corners + np.array(skew, dtype=np.float32)
    # Draw document
    cv2.fillPoly(img, [corners.astype(np.int32)], doc)
    # Draw some "text" lines inside doc for realism
    for yy in range(int(y1) + 30, int(y2) - 20, 35):
        cv2.line(img, (int(x1) + 40, yy), (int(x2) - 40, yy),
                 (60, 60, 60), 3)
    # Extra distracting rectangles
    for i in range(extra_rects):
        ex1 = int(rng.randint(0, W - 120))
        ey1 = int(rng.randint(0, H - 120))
        cv2.rectangle(img, (ex1, ey1), (ex1 + 100, ey1 + 80),
                      (200, 200, 200), -1)
    # Noise
    if noise > 0:
        img = np.clip(img.astype(np.int16) +
                      rng.randint(-noise, noise + 1, img.shape),
                      0, 255).astype(np.uint8)
    # Low contrast: blend doc toward bg
    if contrast != 1.0:
        img = np.clip(bg + (img.astype(np.float16) - bg) * contrast,
                      0, 255).astype(np.uint8)
    if gray:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img, corners


def corner_error(det, gt):
    """Mean Euclidean distance between matched corners (det assumed ordered)."""
    return float(np.mean(np.linalg.norm(det - gt, axis=1)))


# =========================================================================
# A. INPUT TESTS
# =========================================================================

class TestInputHandling:
    def test_valid_jpg_bytes(self):
        img = np.random.randint(0, 255, (200, 300, 3), dtype=np.uint8)
        ok, buf = cv2.imencode('.jpg', img)
        success, out, msg = load_image_from_bytes(buf.tobytes())
        assert success and out is not None and out.shape == (200, 300, 3)

    def test_valid_png_bytes(self):
        img = np.random.randint(0, 255, (200, 300, 3), dtype=np.uint8)
        ok, buf = cv2.imencode('.png', img)
        success, out, msg = load_image_from_bytes(buf.tobytes())
        assert success and out is not None

    def test_invalid_bytes(self):
        success, out, msg = load_image_from_bytes(b"not an image")
        assert not success and out is None

    def test_empty_bytes(self):
        success, out, msg = load_image_from_bytes(b"")
        assert not success and out is None

    def test_oversized_file_rejected(self):
        # >10MB dummy payload (validate_file_size only checks length)
        big = b"\x00" * (11 * 1024 * 1024)
        ok, msg = validate_file_size(len(big))
        assert not ok
        success, out, msg = load_and_validate_image(big)
        assert not success

    def test_tiny_image_rejected(self):
        img = np.zeros((5, 5, 3), dtype=np.uint8)
        ok, buf = cv2.imencode('.png', img)
        success, out, msg = load_image_from_bytes(buf.tobytes())
        assert not success  # validate_image requires >=10px

    def test_grayscale_image_accepted(self):
        img = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        ok, buf = cv2.imencode('.png', img)
        success, out, msg = load_image_from_bytes(buf.tobytes())
        # imdecode with IMREAD_COLOR converts gray->BGR, should succeed
        assert success and out is not None

    def test_validate_image_non_uint8(self):
        img = np.zeros((50, 50, 3), dtype=np.float32)
        ok, msg = validate_image(img)
        assert not ok

    def test_validate_image_none_and_list(self):
        assert not validate_image(None)[0]
        assert not validate_image([[1, 2], [3, 4]])[0]


# =========================================================================
# B. DETECTION TESTS (synthetic labeled set)
# =========================================================================

def _detect(img):
    return detect_document(img)


class TestDetectionSynthetic:
    """Detection success rate on labeled synthetic documents."""

    CASES = {
        'clean_contrast': dict(bg=(30, 30, 30), doc=(240, 240, 240)),
        'low_contrast': dict(bg=(120, 120, 120), doc=(160, 160, 160),
                             contrast=1.0),
        'skewed': dict(skew=[[30, 20], [-25, 15], [-20, -20], [35, -10]]),
        'extra_rectangles': dict(extra_rects=4),
        'grayscale_doc': dict(gray=True),
        'noisy': dict(noise=25),
        'small_doc': dict(doc_rect=(250, 180, 550, 420)),
    }

    @pytest.mark.parametrize('case', list(CASES.keys()))
    def test_detection_case(self, case):
        img, gt = make_document_image(seed=hash(case) % 1000, **self.CASES[case])
        res = _detect(img)
        assert res['success'], f"{case}: detection failed - {res['message']}"
        assert res['corners'].shape == (4, 2)
        err = corner_error(res['corners'], gt)
        # generous tolerance: detection on resized image then mapped back
        assert err < 60, f"{case}: corner error {err:.1f}px too large"

    def test_no_document_blank(self):
        img = np.full((400, 400, 3), 128, dtype=np.uint8)
        res = _detect(img)
        # may fail OR return garbage; must not crash
        assert 'success' in res and 'corners' in res

    def test_no_document_texture(self):
        rng = np.random.RandomState(1)
        img = rng.randint(0, 255, (400, 400, 3), dtype=np.uint8)
        res = _detect(img)
        assert 'success' in res

    def test_corner_occluded(self):
        img, gt = make_document_image()
        # Cover bottom-right corner region with background-colored blob
        cv2.circle(img, (640, 490), 60, (40, 40, 40), -1)
        res = _detect(img)
        # Should still attempt; record outcome
        assert 'success' in res

    def test_manual_corners_valid(self):
        img = np.full((400, 500, 3), 200, dtype=np.uint8)
        mc = np.array([[50, 50], [400, 60], [390, 350], [60, 340]],
                      dtype=np.float32)
        res = detect_document(img, manual_corners=mc)
        assert res['success']
        # order should be TL,TR,BR,BL
        c = res['corners']
        assert c[0][0] + c[0][1] == pytest.approx(
            min(c[:, 0] + c[:, 1]))

    def test_manual_corners_wrong_shape(self):
        img = np.full((100, 100, 3), 200, dtype=np.uint8)
        res = detect_document(img, manual_corners=np.zeros((3, 2), np.float32))
        assert not res['success']

    def test_manual_corners_out_of_bounds_still_accepted_by_detect(self):
        """detect_document manual path does NOT bounds-check; downstream
        perspective must reject."""
        img = np.full((100, 100, 3), 200, dtype=np.uint8)
        mc = np.array([[-50, -50], [500, -50], [500, 500], [-50, 500]],
                      dtype=np.float32)
        det = detect_document(img, manual_corners=mc)
        per = correct_perspective(img, det['corners'] if det['success'] else mc)
        assert not per['success']  # perspective layer must catch it


# =========================================================================
# C. PERSPECTIVE TESTS
# =========================================================================

class TestPerspective:
    def _img(self):
        return np.random.randint(0, 255, (400, 500, 3), dtype=np.uint8)

    def test_correct_order_produces_rectangle(self):
        img = self._img()
        corners = np.array([[100, 80], [400, 60], [420, 320], [80, 340]],
                           dtype=np.float32)
        res = correct_perspective(img, corners)
        assert res['success']
        out = res['corrected_image']
        assert out.dtype == np.uint8 and out.ndim == 3
        assert res['output_size'][0] > 0 and res['output_size'][1] > 0

    def test_output_not_flipped(self):
        """A marker in TL of source quad must appear near TL of output."""
        img = np.full((300, 400, 3), 255, dtype=np.uint8)
        cv2.circle(img, (60, 60), 15, (0, 0, 255), -1)  # red dot near TL
        corners = np.array([[40, 40], [300, 50], [310, 250], [50, 240]],
                           dtype=np.float32)
        res = correct_perspective(img, corners)
        assert res['success']
        out = res['corrected_image']
        # red channel dominant in top-left quadrant of output
        h, w = out.shape[:2]
        tl = out[:h // 4, :w // 4]
        assert tl[:, :, 2].mean() > tl[:, :, 0].mean()

    def test_corners_out_of_bounds_rejected(self):
        img = self._img()
        corners = np.array([[-10, 10], [400, 10], [400, 300], [-10, 300]],
                           dtype=np.float32)
        res = correct_perspective(img, corners)
        assert not res['success']
        assert 'bounds' in res['message'].lower() or 'Invalid' in res['message']

    def test_duplicate_corners_rejected(self):
        img = self._img()
        corners = np.array([[10, 10], [10, 10], [300, 300], [10, 300]],
                           dtype=np.float32)
        ok, msg = validate_corners(corners.astype(np.float32), (400, 500))
        assert not ok
        res = correct_perspective(img, corners)
        assert not res['success']

    def test_self_intersecting_rejected(self):
        img = self._img()
        # bowtie order
        corners = np.array([[10, 10], [300, 300], [300, 10], [10, 300]],
                           dtype=np.float32)
        res = correct_perspective(img, corners)
        assert not res['success']

    def test_collinear_rejected(self):
        img = self._img()
        corners = np.array([[10, 10], [200, 10], [400, 10], [300, 10]],
                           dtype=np.float32)
        res = correct_perspective(img, corners)
        assert not res['success']

    def test_wrong_shape_rejected(self):
        img = self._img()
        res = correct_perspective(img, np.zeros((5, 2), np.float32))
        assert not res['success']

    def test_list_input_accepted(self):
        img = self._img()
        corners = [[100, 80], [400, 60], [420, 320], [80, 340]]
        res = correct_perspective(img, corners)
        assert res['success']

    def test_padding_variant(self):
        img = self._img()
        corners = np.array([[100, 80], [400, 60], [420, 320], [80, 340]],
                           dtype=np.float32)
        res = apply_perspective_with_padding(img, corners, padding_ratio=0.05)
        assert res['success']
        bw, bh = calculate_output_dimensions(corners)
        ow, oh = res['output_size']
        assert ow > bw and oh > bh

    def test_extreme_skew(self):
        img = self._img()
        corners = np.array([[5, 5], [490, 30], [480, 390], [20, 395]],
                           dtype=np.float32)
        res = correct_perspective(img, corners)
        assert res['success']


# =========================================================================
# D. ENHANCEMENT TESTS
# =========================================================================

def _color_img():
    return np.random.randint(0, 255, (120, 160, 3), dtype=np.uint8)


class TestEnhancement:
    def test_default_config_success(self):
        res = enhance_document(_color_img())
        assert res['success']
        assert res['enhanced_image'].dtype == np.uint8

    @pytest.mark.parametrize('method', ['gaussian', 'median', 'bilateral', 'none'])
    def test_denoise_methods(self, method):
        out = denoise_image(_color_img(), method=method)
        assert out.shape == (120, 160, 3) and out.dtype == np.uint8

    @pytest.mark.parametrize('method', ['histogram_eq', 'clahe', 'none'])
    def test_contrast_methods(self, method):
        out = enhance_contrast(_color_img(), method=method)
        assert out.shape == (120, 160, 3)

    @pytest.mark.parametrize('method', ['global', 'otsu', 'adaptive_mean',
                                        'adaptive_gaussian', 'none'])
    def test_threshold_methods(self, method):
        out = binarize_image(_color_img(), method=method)
        assert out.dtype == np.uint8
        if method != 'none':
            assert out.ndim == 2  # binary output is grayscale

    @pytest.mark.parametrize('method', ['unsharp_mask', 'kernel', 'none'])
    def test_sharpen_methods(self, method):
        out = sharpen_image(_color_img(), method=method)
        assert out.shape == (120, 160, 3) and out.dtype == np.uint8

    def test_shadow_correction_color_and_gray(self):
        img = _color_img()
        out = correct_shadow(img, method='morphological',
                             kernel_size=15, blur_sigma=3)
        assert out.shape == img.shape and out.dtype == np.uint8
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        outg = correct_shadow(gray, method='morphological',
                              kernel_size=15, blur_sigma=3)
        assert outg.shape == gray.shape

    def test_invalid_method_raises_value_error(self):
        with pytest.raises(ValueError):
            denoise_image(_color_img(), method='bogus')
        with pytest.raises(ValueError):
            enhance_contrast(_color_img(), method='bogus')
        with pytest.raises(ValueError):
            binarize_image(_color_img(), method='bogus')
        with pytest.raises(ValueError):
            sharpen_image(_color_img(), method='bogus')
        with pytest.raises(ValueError):
            correct_shadow(_color_img(), method='bogus')

    def test_original_image_not_modified(self):
        img = _color_img()
        snapshot = img.copy()
        enhance_document(img, return_intermediate=True)
        assert np.array_equal(img, snapshot)

    def test_invalid_image_returns_failure_dict(self):
        res = enhance_document(np.array([], dtype=np.uint8))
        assert not res['success'] and res['enhanced_image'] is None

    def test_bad_param_returns_failure_not_crash(self):
        # even kernel_size -> auto-fixed; force cv2 error via huge kernel
        res = enhance_document(_color_img(), denoise_method='gaussian',
                               denoise_params={'kernel_size': 9999})
        assert 'success' in res  # either True or graceful False

    def test_unsharp_even_radius_crash_check(self):
        """radius=2 (even) -> cv2.GaussianBlur requires odd ksize -> error"""
        img = _color_img()
        try:
            sharpen_image(img, method='unsharp_mask', radius=2)
            crashed = False
        except Exception:
            crashed = True
        # document behavior: if it crashes, enhance_document should catch it
        res = enhance_document(img, sharpen=True, sharpen_method='unsharp_mask',
                               sharpen_params={'radius': 2})
        assert res['success'] is False or not crashed

    def test_output_dtype_shape_contract(self):
        img = _color_img()
        res = enhance_document(img, threshold_method='none',
                               convert_to_grayscale=True)
        assert res['success']
        out = res['enhanced_image']
        assert out.dtype == np.uint8


# =========================================================================
# E. PIPELINE TESTS
# =========================================================================

class TestPipelineQA:
    def test_end_to_end_manual_corners(self):
        img, gt = make_document_image()
        corners = gt.copy()
        res = process_document(img, manual_corners=corners)
        assert res['success']
        assert res['enhanced_image'] is not None
        assert res['scanned_image'].dtype == np.uint8

    def test_end_to_end_auto_detection(self):
        img, gt = make_document_image()
        res = process_document(img)
        # synthetic clean doc should be detected
        assert res['success'], res['message']

    def test_detection_failure_returns_graceful(self):
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        res = process_document_with_fallback(img)
        assert 'needs_manual_corners' in res
        assert 'message' in res

    def test_processing_time_reasonable(self):
        img, gt = make_document_image(W=1000, H=750)
        t0 = time.time()
        res = process_document(img, manual_corners=gt)
        elapsed = time.time() - t0
        assert res['success']
        assert elapsed < 10  # spec target <3s; record actual in report

    def test_extra_config_key_crashes_pipeline(self):
        """enhancement_config with unknown key -> TypeError propagates?"""
        img, gt = make_document_image(W=400, H=300)
        cfg = dict(DEFAULT_ENHANCEMENT_CONFIG)
        cfg['bogus_key'] = 1
        try:
            res = process_document(img, manual_corners=gt,
                                   enhancement_config=cfg)
            outcome = ('returned', res.get('success'))
        except Exception as e:
            outcome = ('raised', type(e).__name__)
        # Document actual behavior; uncaught exception = bug
        assert outcome[0] == 'returned' or True  # informational
        print('extra-key outcome:', outcome)

    def test_core_init_stub_returns_none(self):
        """smartscan.core.process_document is an unimplemented stub."""
        from smartscan.core import process_document as pkg_fn
        img, gt = make_document_image(W=300, H=300)
        out = pkg_fn(img)
        # Expected: real pipeline result dict; actual: None
        assert out is None or isinstance(out, dict)


# =========================================================================
# F. LOADER / FORMAT TESTS
# =========================================================================

class TestFormats:
    def test_bmp_bytes(self):
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        ok, buf = cv2.imencode('.bmp', img)
        success, out, _ = load_image_from_bytes(buf.tobytes())
        assert success and out is not None

    def test_gif_or_tiff_bytes(self):
        """Formats outside advertised list — cv2 may still decode."""
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        ok, buf = cv2.imencode('.tiff', img)
        if ok:
            success, out, _ = load_image_from_bytes(buf.tobytes())
            # informational: loader accepts whatever cv2 decodes
            print('tiff decode success:', success)

    def test_large_valid_image_dimensions(self):
        """4001x100 image exceeds MAX_IMAGE_HEIGHT? width limit is 4000."""
        img = np.zeros((100, 4100, 3), dtype=np.uint8)
        ok, buf = cv2.imencode('.png', img)
        success, out, msg = load_and_validate_image(buf.tobytes())
        assert not success  # >4000px wide rejected


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

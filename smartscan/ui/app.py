"""
SmartScan - Intelligent Document Scanner
Streamlit Web Application

Luồng 5 bước:
    1. Upload Document
    2. Detect & Review (góc tài liệu, cho phép chỉnh thủ công)
    3. Perspective Correction
    4. Image Enhancement
    5. Preview & Export
"""

import streamlit as st
import cv2
import numpy as np
import time
import hashlib
import copy
import sys
import os
from typing import Optional, Dict, Any

# Add project root (parent of the smartscan package) to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from smartscan.core.detection import detect_document
from smartscan.core.perspective import apply_perspective_with_padding, validate_corners
from smartscan.core.pipeline import (
    update_enhancement,
    get_default_enhancement_presets
)
from smartscan.core.preprocessing import rotate_image, rotate_90
from smartscan.utils.image_loader import load_and_validate_image
from smartscan.utils.utils import (
    encode_image_to_bytes,
    draw_corners_on_image,
    create_comparison_image,
    format_processing_time,
    get_image_info
)
from smartscan.utils.config import (
    DENOISE_METHODS,
    CONTRAST_METHODS,
    THRESHOLD_METHODS,
    SHARPEN_METHODS,
    SHADOW_CORRECTION_METHODS
)
from smartscan.ui.state import (
    init_session_state,
    reset_session,
    reset_downstream,
    reset_perspective_and_enhancement,
    reset_enhancement_result,
    set_stage_error,
    clear_stage_error,
    get_stage_error
)


# Page config
st.set_page_config(
    page_title="SmartScan - Intelligent Document Scanner",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)


_ROTATE_90_MAP = {"0°": 0, "90° CW": 1, "90° CCW": 3, "180°": 2}
_CORNER_LABELS = ['TL', 'TR', 'BR', 'BL']


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def apply_user_rotation(image: np.ndarray, quarter: str, angle: float) -> np.ndarray:
    """Áp dụng góc xoay 90° + góc tự do lên ảnh BGR."""
    turns = _ROTATE_90_MAP.get(quarter, 0)
    if turns:
        image = rotate_90(image, turns)
    if abs(angle) > 1e-6:
        image = rotate_image(image, angle, expand=True)
    return image


def to_display(image: np.ndarray) -> np.ndarray:
    """Convert ảnh BGR/grayscale sang RGB để hiển thị trên Streamlit."""
    if image is None:
        return None
    if len(image.shape) == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def stage_icon(done: bool) -> str:
    return "✅" if done else "⬜"


# ---------------------------------------------------------------------------
# Step handlers (gọi core API, không chứa thuật toán)
# ---------------------------------------------------------------------------

def run_detection() -> None:
    """Chạy auto-detection trên source_image và cập nhật session state."""
    src = st.session_state.source_image
    start = time.time()
    result = detect_document(src, debug=True)
    result['elapsed'] = time.time() - start

    st.session_state.detection_result = result
    clear_stage_error('detect')
    clear_stage_error('review')
    st.session_state.corners_confirmed = False
    st.session_state.corner_source = None

    if result['success']:
        st.session_state.detected_corners = result['corners']
        st.session_state.corner_draft = result['corners'].copy()
    else:
        st.session_state.detected_corners = None
        h, w = src.shape[:2]
        st.session_state.corner_draft = np.array([
            [0.08 * w, 0.08 * h],
            [0.92 * w, 0.08 * h],
            [0.92 * w, 0.92 * h],
            [0.08 * w, 0.92 * h],
        ], dtype=np.float32)
        set_stage_error('detect', result['message'])

    st.session_state.corner_edit_version += 1


def confirm_corners(corners: np.ndarray) -> None:
    """Validate + xác nhận 4 góc, sau đó reset perspective/enhancement."""
    src = st.session_state.source_image

    det = detect_document(src, manual_corners=corners)
    if not det['success']:
        set_stage_error('review', det['message'])
        return

    is_valid, msg = validate_corners(det['corners'], src.shape[:2])
    if not is_valid:
        set_stage_error('review', msg)
        return

    prev = st.session_state.detected_corners
    det_result = st.session_state.detection_result
    auto_ok = (
        prev is not None
        and det_result is not None
        and det_result.get('success', False)
        and np.allclose(det['corners'], prev, atol=1.5)
    )

    st.session_state.detected_corners = det['corners']
    st.session_state.corners_confirmed = True
    st.session_state.corner_source = 'auto' if auto_ok else (
        'manual' if (det_result is None or not det_result.get('success', False)) else 'reviewed'
    )
    reset_perspective_and_enhancement()
    clear_stage_error('review')


def run_perspective() -> None:
    """Chạy perspective correction với corners đã confirm."""
    src = st.session_state.source_image
    corners = st.session_state.detected_corners
    start = time.time()
    result = apply_perspective_with_padding(src, corners, padding_ratio=0.05)
    elapsed = time.time() - start

    if result['success']:
        st.session_state.scanned_image = result['corrected_image']
        st.session_state.perspective_meta = {
            'output_size': result['output_size'],
            'time': elapsed,
            'message': result['message'],
        }
        st.session_state.enhanced_image = None
        st.session_state.enhancement_meta = None
        clear_stage_error('perspective')
    else:
        set_stage_error('perspective', result['message'])


def run_enhancement() -> None:
    """Chạy enhancement trên scanned_image với config hiện tại."""
    scanned = st.session_state.scanned_image
    config = st.session_state.enhancement_config
    result = update_enhancement(scanned, config)

    if result['success']:
        st.session_state.enhanced_image = result['enhanced_image']
        st.session_state.enhancement_meta = {
            'time': result['processing_time'],
            'message': result['message'],
        }
        clear_stage_error('enhancement')
    else:
        set_stage_error('enhancement', result['message'])


# ---------------------------------------------------------------------------
# UI sections
# ---------------------------------------------------------------------------

def render_upload_section() -> None:
    """Bước 1: Upload + rotation."""
    st.subheader(f"{stage_icon(st.session_state.source_image is not None)} 1. Upload Document")

    nonce = st.session_state.upload_nonce
    uploaded_file = st.file_uploader(
        "Chọn ảnh tài liệu (JPG, JPEG, PNG)",
        type=['jpg', 'jpeg', 'png'],
        key=f"file_uploader_{nonce}",
        help="Tối đa 10MB, ảnh sẽ được validate trước khi xử lý"
    )

    quarter = st.radio(
        "Xoay 90°",
        options=["0°", "90° CW", "90° CCW", "180°"],
        horizontal=True,
        key="rot_quarter",
        help="Xoay nhanh theo bước 90 độ"
    )
    angle = st.slider(
        "Góc xoay tinh chỉnh (độ)",
        min_value=-45.0, max_value=45.0, value=0.0, step=0.5,
        key="rot_angle",
        help="Xoay nghiêng để chỉnh đường chân trời hoặc mép tài liệu bị lệch"
    )

    if uploaded_file is None:
        if st.session_state.source_image is not None or st.session_state.base_image is not None:
            st.session_state.base_image = None
            st.session_state.source_image = None
            st.session_state.file_signature = None
            reset_downstream()
        return

    # Đọc bytes + signature để chỉ decode khi file/rotation thực sự đổi
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    file_sig = (
        uploaded_file.name,
        uploaded_file.size,
        hashlib.md5(file_bytes).hexdigest(),
        quarter,
        angle,
    )

    if file_sig != st.session_state.file_signature:
        success, image_bgr, message = load_and_validate_image(file_bytes)
        if not success:
            st.session_state.base_image = None
            st.session_state.source_image = None
            st.session_state.file_signature = None
            reset_downstream()
            set_stage_error('upload', message)
            st.error(f"❌ {message}")
            return

        clear_stage_error('upload')
        st.session_state.base_image = image_bgr
        st.session_state.source_image = apply_user_rotation(image_bgr, quarter, angle)
        st.session_state.file_signature = file_sig
        reset_downstream()

    src = st.session_state.source_image
    if src is None:
        return

    col_img, col_info = st.columns([3, 1])
    with col_img:
        st.image(to_display(src), use_container_width=True)
    with col_info:
        info = get_image_info(src)
        st.json({
            "Kích thước": f"{info['width']}x{info['height']}",
            "Kênh màu": info['channels'],
            "Dung lượng": f"{info['size_mb']:.2f}MB",
            "Loại": "Màu" if info['is_color'] else "Grayscale",
            "File": uploaded_file.name,
        })

    if st.button("🗑️ Xóa ảnh và reset", key="clear_upload"):
        reset_session()
        st.session_state.upload_nonce += 1
        st.rerun()


def render_corner_editor(w: int, h: int) -> np.ndarray:
    """8 number input cho 4 góc TL/TR/BR/BL. Trả về mảng (4,2)."""
    draft = st.session_state.corner_draft
    if draft is None:
        draft = np.array([
            [0.1 * w, 0.1 * h], [0.9 * w, 0.1 * h],
            [0.9 * w, 0.9 * h], [0.1 * w, 0.9 * h],
        ], dtype=np.float32)

    version = st.session_state.corner_edit_version
    cols = st.columns(4)
    points = []
    for i, label in enumerate(_CORNER_LABELS):
        x, y = draft[i]
        xi = int(np.clip(round(float(x)), 0, max(w - 1, 0)))
        yi = int(np.clip(round(float(y)), 0, max(h - 1, 0)))
        with cols[i]:
            st.markdown(f"**{label}**")
            xv = st.number_input(
                f"{label} X", min_value=0, max_value=max(w - 1, 0),
                value=xi, step=1, key=f"corner_x_{version}_{i}"
            )
            yv = st.number_input(
                f"{label} Y", min_value=0, max_value=max(h - 1, 0),
                value=yi, step=1, key=f"corner_y_{version}_{i}"
            )
            points.append([xv, yv])
    return np.array(points, dtype=np.float32)


def render_review_section() -> None:
    """Bước 2: Detect & Review corners."""
    has_src = st.session_state.source_image is not None
    st.subheader(f"{stage_icon(st.session_state.corners_confirmed)} 2. Detect & Review Corners")

    if not has_src:
        st.info("Upload ảnh ở bước 1 trước.")
        return

    src = st.session_state.source_image
    h, w = src.shape[:2]
    det = st.session_state.detection_result

    col_btn, col_status = st.columns([1, 2])
    with col_btn:
        detect_label = "🔁 Detect lại" if det is not None else "🔍 Detect document"
        if st.button(detect_label, key="btn_detect", use_container_width=True):
            with st.spinner("Đang detect document..."):
                run_detection()
    with col_status:
        if det is not None:
            if det['success']:
                st.success(f"Detected — confidence {det['confidence']:.2f} ({format_processing_time(det.get('elapsed', 0))})")
            else:
                st.warning("Auto-detection thất bại — hãy chỉnh 4 góc thủ công rồi Confirm.")

    err = get_stage_error('detect')
    if err:
        st.error(f"Detection: {err}")

    # Hiển thị overlay corners sau khi detect (kể cả fail để user thấy draft)
    show_corners = (
        st.session_state.detected_corners
        if st.session_state.corners_confirmed
        else st.session_state.corner_draft
    )
    if det is not None or show_corners is not None:
        if show_corners is not None:
            overlay = draw_corners_on_image(src, show_corners.astype(np.float32))
            st.image(to_display(overlay), use_container_width=True)

        st.markdown("**Chỉnh 4 góc** (TL, TR, BR, BL) nếu detection chưa chính xác:")
        corners_input = render_corner_editor(w, h)

        col_confirm, col_hint = st.columns([1, 2])
        with col_confirm:
            if st.button("✅ Confirm corners", key="btn_confirm_corners",
                         type="primary", use_container_width=True):
                with st.spinner("Đang validate corners..."):
                    confirm_corners(corners_input)
        with col_hint:
            st.caption("Confirm sẽ kiểm tra hình học (bounds, trùng điểm, tự giao) trước khi sang bước perspective.")

    err = get_stage_error('review')
    if err:
        st.error(f"Corners không hợp lệ: {err}")

    if st.session_state.corners_confirmed:
        st.success(
            f"Corners đã xác nhận ({st.session_state.corner_source}) — "
            "có thể sang bước 3. Đổi corners sẽ reset perspective/enhancement."
        )


def render_perspective_section() -> None:
    """Bước 3: Perspective correction."""
    done = st.session_state.scanned_image is not None
    st.subheader(f"{stage_icon(done)} 3. Perspective Correction")

    if not st.session_state.corners_confirmed:
        st.info("Cần detect và confirm 4 góc ở bước 2 trước.")
        return

    col_btn, col_back = st.columns([1, 1])
    with col_btn:
        if st.button("✂️ Correct perspective", key="btn_perspective",
                     type="primary", use_container_width=True):
            with st.spinner("Đang hiệu chỉnh phối cảnh..."):
                run_perspective()
    with col_back:
        if st.button("← Quay lại review corners", key="btn_back_review"):
            st.session_state.corners_confirmed = False
            reset_perspective_and_enhancement()
            st.rerun()

    err = get_stage_error('perspective')
    if err:
        st.error(f"Perspective: {err}")

    scanned = st.session_state.scanned_image
    if scanned is not None:
        meta = st.session_state.perspective_meta or {}
        st.success(f"Đã scan — output {meta.get('output_size', '?')} "
                   f"({format_processing_time(meta.get('time', 0))})")
        st.image(to_display(scanned), use_container_width=True)


def _cfg_get(cfg: Dict[str, Any], key: str, default: Any) -> Any:
    return cfg.get(key, default)


def render_enhancement_controls() -> None:
    """Preset + advanced controls, ghi vào st.session_state.enhancement_config."""
    cfg = st.session_state.enhancement_config
    presets = get_default_enhancement_presets()

    col_preset, col_apply = st.columns([3, 1])
    with col_preset:
        preset_name = st.selectbox(
            "Preset",
            list(presets.keys()),
            key="preset_select",
            help="Original/Natural giữ màu tự nhiên; B&W mới binarize; Low Light/Text Enhancement cho ảnh khó."
        )
    with col_apply:
        st.write("")
        if st.button("Áp dụng preset", key="btn_apply_preset", use_container_width=True):
            st.session_state.enhancement_config = copy.deepcopy(presets[preset_name])
            reset_enhancement_result()
            st.session_state.config_snapshot = copy.deepcopy(st.session_state.enhancement_config)
            st.success(f"Đã áp dụng preset: {preset_name}")

    with st.expander("⚙️ Cấu hình nâng cao"):
        # Brightness / Contrast
        st.subheader("Brightness / Contrast")
        new_brightness = st.slider(
            "Brightness", min_value=-100, max_value=100,
            value=int(_cfg_get(cfg, 'brightness', 0)), step=1, key="sl_brightness"
        )
        new_contrast = st.slider(
            "Contrast", min_value=0.5, max_value=2.0,
            value=float(_cfg_get(cfg, 'contrast', 1.0)), step=0.05, key="sl_contrast"
        )
        cfg['brightness'] = new_brightness
        cfg['contrast'] = new_contrast

        # Denoise
        st.subheader("Denoising")
        denoise_method = st.selectbox(
            "Phương pháp",
            DENOISE_METHODS,
            index=DENOISE_METHODS.index(_cfg_get(cfg, 'denoise_method', 'bilateral'))
            if _cfg_get(cfg, 'denoise_method', 'bilateral') in DENOISE_METHODS else 0,
            key="sel_denoise"
        )
        cfg['denoise_method'] = denoise_method
        denoise_params = cfg.setdefault('denoise_params', {})
        if denoise_method in ('gaussian', 'median', 'bilateral'):
            k = st.slider(
                "Kernel size", min_value=3, max_value=15, step=2,
                value=int(denoise_params.get('kernel_size', 9 if denoise_method == 'bilateral' else 5)),
                key="sl_denoise_kernel"
            )
            denoise_params['kernel_size'] = k

        # Contrast enhancement (CLAHE / histogram)
        st.subheader("Contrast Enhancement")
        contrast_method = st.selectbox(
            "Phương pháp",
            CONTRAST_METHODS,
            index=CONTRAST_METHODS.index(_cfg_get(cfg, 'contrast_method', 'clahe'))
            if _cfg_get(cfg, 'contrast_method', 'clahe') in CONTRAST_METHODS else 0,
            key="sel_contrast"
        )
        cfg['contrast_method'] = contrast_method
        contrast_params = cfg.setdefault('contrast_params', {})
        if contrast_method == 'clahe':
            contrast_params['clip_limit'] = st.slider(
                "CLAHE clip limit", min_value=0.5, max_value=10.0,
                value=float(contrast_params.get('clip_limit', 2.0)),
                step=0.5, key="sl_clahe_clip"
            )

        # Binarization
        st.subheader("Binarization")
        threshold_method = st.selectbox(
            "Phương pháp",
            THRESHOLD_METHODS,
            index=THRESHOLD_METHODS.index(_cfg_get(cfg, 'threshold_method', 'none'))
            if _cfg_get(cfg, 'threshold_method', 'none') in THRESHOLD_METHODS else 0,
            key="sel_threshold"
        )
        cfg['threshold_method'] = threshold_method
        threshold_params = cfg.setdefault('threshold_params', {})
        if threshold_method in ('adaptive_mean', 'adaptive_gaussian'):
            threshold_params['block_size'] = st.slider(
                "Block size", min_value=3, max_value=51, step=2,
                value=int(threshold_params.get('block_size', 11)), key="sl_thresh_block"
            )
            threshold_params['C'] = st.slider(
                "Hằng số C", min_value=-10, max_value=10,
                value=int(threshold_params.get('C', 2)), key="sl_thresh_c"
            )
        elif threshold_method == 'global':
            threshold_params['threshold'] = st.slider(
                "Ngưỡng global", min_value=0, max_value=255,
                value=int(threshold_params.get('threshold', 127)), key="sl_thresh_global"
            )

        # Sharpening
        st.subheader("Sharpening")
        sharpen = st.checkbox("Bật sharpening", value=bool(_cfg_get(cfg, 'sharpen', True)), key="chk_sharpen")
        cfg['sharpen'] = sharpen
        if sharpen:
            sharpen_method = st.selectbox(
                "Phương pháp",
                SHARPEN_METHODS,
                index=SHARPEN_METHODS.index(_cfg_get(cfg, 'sharpen_method', 'unsharp_mask'))
                if _cfg_get(cfg, 'sharpen_method', 'unsharp_mask') in SHARPEN_METHODS else 0,
                key="sel_sharpen"
            )
            cfg['sharpen_method'] = sharpen_method
            if sharpen_method == 'unsharp_mask':
                sharpen_params = cfg.setdefault('sharpen_params', {})
                sharpen_params['strength'] = st.slider(
                    "Strength", min_value=0.0, max_value=3.0,
                    value=float(sharpen_params.get('strength', 1.5)),
                    step=0.1, key="sl_sharpen_strength"
                )
                sharpen_params['radius'] = st.slider(
                    "Radius", min_value=3, max_value=15, step=2,
                    value=int(sharpen_params.get('radius', 3)), key="sl_sharpen_radius"
                )

        # Shadow correction
        st.subheader("Shadow Correction")
        shadow = st.checkbox(
            "Bật shadow correction",
            value=bool(_cfg_get(cfg, 'shadow_correction', False)), key="chk_shadow"
        )
        cfg['shadow_correction'] = shadow
        if shadow:
            shadow_method = st.selectbox(
                "Phương pháp",
                SHADOW_CORRECTION_METHODS,
                index=SHADOW_CORRECTION_METHODS.index(_cfg_get(cfg, 'shadow_correction_method', 'morphological'))
                if _cfg_get(cfg, 'shadow_correction_method', 'morphological') in SHADOW_CORRECTION_METHODS else 0,
                key="sel_shadow"
            )
            cfg['shadow_correction_method'] = shadow_method

        # Output
        st.subheader("Output")
        cfg['convert_to_grayscale'] = st.checkbox(
            "Chuyển sang grayscale",
            value=bool(_cfg_get(cfg, 'convert_to_grayscale', False)), key="chk_grayscale"
        )

    # Nếu config đổi so với snapshot -> chỉ cần chạy lại enhancement
    snapshot = st.session_state.get('config_snapshot')
    current = copy.deepcopy(cfg)
    if snapshot is not None and current != snapshot:
        reset_enhancement_result()
    st.session_state.config_snapshot = current


def render_enhancement_section() -> None:
    """Bước 4: Enhancement."""
    done = st.session_state.enhanced_image is not None
    st.subheader(f"{stage_icon(done)} 4. Image Enhancement")

    if st.session_state.scanned_image is None:
        st.info("Cần hoàn thành perspective correction ở bước 3 trước.")
        return

    render_enhancement_controls()

    col_run, col_note = st.columns([1, 2])
    with col_run:
        if st.button("✨ Run enhancement", key="btn_enhance",
                     type="primary", use_container_width=True):
            with st.spinner("Đang enhance..."):
                run_enhancement()
    with col_note:
        st.caption("Đổi config chỉ cần Run enhancement lại — không cần detect/perspective lại. "
                   "Nếu enhance lỗi, ảnh scanned vẫn được giữ để export.")

    err = get_stage_error('enhancement')
    if err:
        st.error(f"Enhancement: {err}")
        if st.session_state.scanned_image is not None:
            st.info("Ảnh scanned (chưa enhance) vẫn khả dụng ở bước 5.")

    enhanced = st.session_state.enhanced_image
    if enhanced is not None:
        meta = st.session_state.enhancement_meta or {}
        st.success(f"Enhanced — {format_processing_time(meta.get('time', 0))}")
        st.image(to_display(enhanced), use_container_width=True)


def render_export_section() -> None:
    """Bước 5: Preview & Export."""
    has_scanned = st.session_state.scanned_image is not None
    has_enhanced = st.session_state.enhanced_image is not None
    st.subheader(f"{stage_icon(has_scanned or has_enhanced)} 5. Preview & Export")

    if not has_scanned:
        st.info("Chưa có kết quả để export. Hoàn thành các bước trước.")
        return

    src = st.session_state.source_image
    scanned = st.session_state.scanned_image
    enhanced = st.session_state.enhanced_image

    # Preview 3 ảnh
    cols = st.columns(3)
    with cols[0]:
        st.markdown("**Original**")
        st.image(to_display(src), use_container_width=True)
    with cols[1]:
        st.markdown("**Scanned**")
        st.image(to_display(scanned), use_container_width=True)
    with cols[2]:
        st.markdown("**Enhanced**" if has_enhanced else "**Enhanced** (chưa có)")
        if has_enhanced:
            st.image(to_display(enhanced), use_container_width=True)
        else:
            st.caption("Chạy enhancement ở bước 4, hoặc export scanned bên dưới.")

    # So sánh
    if has_enhanced:
        with st.expander("🔍 So sánh Scanned vs Enhanced"):
            comparison = create_comparison_image(scanned, enhanced, ("Scanned", "Enhanced"))
            st.image(to_display(comparison), use_container_width=True)

    # Export
    st.markdown("**Export**")
    col_fmt, col_q, col_dl1, col_dl2 = st.columns([1, 1, 1, 1])
    with col_fmt:
        fmt = st.selectbox("Định dạng", ["JPG", "PNG"], key="export_format")
    ext = '.jpg' if fmt == 'JPG' else '.png'
    with col_q:
        quality = st.slider("JPEG quality", 50, 100, 95, key="export_quality") if fmt == 'JPG' else 95

    with col_dl1:
        scanned_bytes = encode_image_to_bytes(scanned, ext, quality)
        st.download_button(
            f"📥 Scanned ({fmt})",
            data=scanned_bytes,
            file_name=f"smartscan_scanned{ext}",
            mime="image/jpeg" if ext == '.jpg' else "image/png",
            use_container_width=True,
        )
    with col_dl2:
        if has_enhanced:
            enhanced_bytes = encode_image_to_bytes(enhanced, ext, quality)
            st.download_button(
                f"📥 Enhanced ({fmt})",
                data=enhanced_bytes,
                file_name=f"smartscan_enhanced{ext}",
                mime="image/jpeg" if ext == '.jpg' else "image/png",
                use_container_width=True,
            )
        else:
            st.caption("Enhanced chưa sẵn sàng")

    # Chi tiết xử lý
    with st.expander("📊 Chi tiết xử lý"):
        det = st.session_state.detection_result
        if det is not None:
            status = "✅" if det['success'] else "❌"
            conf = f", confidence {det['confidence']:.2f}" if det['success'] else ""
            st.write(f"{status} **Detection**: {det['message']}{conf} "
                     f"({format_processing_time(det.get('elapsed', 0))})")
        pmeta = st.session_state.perspective_meta
        if pmeta:
            st.write(f"✅ **Perspective**: {pmeta.get('message', '')} "
                     f"({format_processing_time(pmeta.get('time', 0))})")
        emeta = st.session_state.enhancement_meta
        if emeta:
            st.write(f"✅ **Enhancement**: {format_processing_time(emeta.get('time', 0))}")
        err = get_stage_error('enhancement')
        if err:
            st.write(f"❌ **Enhancement**: {err} (scanned vẫn export được)")


def render_sidebar() -> None:
    with st.sidebar:
        st.header("ℹ️ SmartScan")
        st.markdown("""
        **Quy trình:**
        1. Upload → 2. Detect & Review → 3. Perspective →
        4. Enhancement → 5. Preview & Export
        """)
        st.caption("Ảnh gốc luôn được giữ nguyên; mọi xử lý làm việc trên bản copy.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    init_session_state()

    st.title("📄 SmartScan - Intelligent Document Scanner")
    st.caption("Upload → Detect → Review → Perspective Correction → Enhancement → Preview → Export")

    render_sidebar()

    with st.container(border=True):
        render_upload_section()

    if st.session_state.source_image is not None:
        with st.container(border=True):
            render_review_section()
        with st.container(border=True):
            render_perspective_section()
        with st.container(border=True):
            render_enhancement_section()
        with st.container(border=True):
            render_export_section()
    else:
        st.info("👆 Upload ảnh tài liệu ở bước 1 để bắt đầu.")


if __name__ == "__main__":
    main()

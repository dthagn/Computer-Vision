"""
Session state management cho SmartScan UI.

Tập trung toàn bộ schema và quy tắc reset để app.py chỉ lo render.
Quy tắc reset:
- Upload mới / đổi rotation -> reset toàn bộ downstream (corners, scanned, enhanced).
- Đổi/xác nhận corners -> reset perspective + enhancement.
- Đổi enhancement config -> chỉ reset enhanced_image (user chủ động chạy lại).
"""

import streamlit as st
import numpy as np
from typing import Any, Dict, Optional

from smartscan.core.pipeline import get_default_enhancement_presets


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

def _default_state() -> Dict[str, Any]:
    return {
        # Nguồn ảnh
        'base_image': None,          # Ảnh gốc decode từ file (BGR), chưa xoay
        'source_image': None,        # Ảnh sau rotation do user chọn (BGR)
        'file_signature': None,      # (name, size, md5, quarter, angle)
        # Detection / review
        'detection_result': None,    # dict trả về từ detect_document
        'detected_corners': None,    # np.ndarray (4,2) đã order TL,TR,BR,BL
        'corner_draft': None,        # np.ndarray (4,2) dùng để init editor
        'corners_confirmed': False,  # user đã xác nhận corners chưa
        'corner_source': None,       # 'auto' | 'manual' | 'reviewed'
        'corner_edit_version': 0,    # tăng để reset number_input widgets
        'upload_nonce': 0,           # đổi key file_uploader để clear file
        # Perspective
        'scanned_image': None,       # ảnh sau perspective correction
        'perspective_meta': None,    # {'output_size':..., 'time':...}
        # Enhancement
        'enhanced_image': None,
        'enhancement_meta': None,    # {'time':..., 'message':...}
        'enhancement_config': get_default_enhancement_presets()['default'],
        # Lỗi theo stage
        'stage_errors': {},
    }


def init_session_state() -> None:
    """Khởi tạo session state nếu chưa có."""
    for key, value in _default_state().items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session() -> None:
    """Reset toàn bộ state về mặc định (nút reset thủ công)."""
    for key, value in _default_state().items():
        st.session_state[key] = value


def reset_downstream() -> None:
    """Reset mọi thứ phụ thuộc vào source_image (corners trở đi)."""
    st.session_state.detection_result = None
    st.session_state.detected_corners = None
    st.session_state.corner_draft = None
    st.session_state.corners_confirmed = False
    st.session_state.corner_source = None
    st.session_state.corner_edit_version = 0
    st.session_state.stage_errors = {}
    reset_perspective_and_enhancement()


def reset_perspective_and_enhancement() -> None:
    """Reset perspective + enhancement khi corners thay đổi."""
    st.session_state.scanned_image = None
    st.session_state.perspective_meta = None
    st.session_state.enhanced_image = None
    st.session_state.enhancement_meta = None
    st.session_state.stage_errors.pop('perspective', None)
    st.session_state.stage_errors.pop('enhancement', None)


def reset_enhancement_result() -> None:
    """Chỉ reset kết quả enhancement (khi đổi config)."""
    st.session_state.enhanced_image = None
    st.session_state.enhancement_meta = None
    st.session_state.stage_errors.pop('enhancement', None)


def set_stage_error(stage: str, message: str) -> None:
    st.session_state.stage_errors[stage] = message


def clear_stage_error(stage: str) -> None:
    st.session_state.stage_errors.pop(stage, None)


def get_stage_error(stage: str) -> Optional[str]:
    return st.session_state.stage_errors.get(stage)

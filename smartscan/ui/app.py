"""
SmartScan - Intelligent Document Scanner
Streamlit Web Application
"""

import streamlit as st
import cv2
import numpy as np
import time
from typing import Optional, Dict, Any
import sys
import os

# Add project root (parent of the smartscan package) to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from smartscan.core.pipeline import (
    process_document,
    process_document_with_fallback,
    update_enhancement,
    get_default_enhancement_presets
)
from smartscan.core.preprocessing import rotate_image, rotate_90
from smartscan.utils.image_loader import (
    load_and_validate_image,
    convert_rgb_to_bgr,
    convert_bgr_to_rgb
)
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


# Page config
st.set_page_config(
    page_title="SmartScan - Intelligent Document Scanner",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)


def initialize_session_state():
    """Initialize session state variables"""
    if 'original_image' not in st.session_state:
        st.session_state.original_image = None
    if 'scanned_image' not in st.session_state:
        st.session_state.scanned_image = None
    if 'enhanced_image' not in st.session_state:
        st.session_state.enhanced_image = None
    if 'detected_corners' not in st.session_state:
        st.session_state.detected_corners = None
    if 'processing_result' not in st.session_state:
        st.session_state.processing_result = None
    if 'needs_manual_corners' not in st.session_state:
        st.session_state.needs_manual_corners = False
    if 'manual_corners' not in st.session_state:
        st.session_state.manual_corners = None
    if 'enhancement_config' not in st.session_state:
        st.session_state.enhancement_config = get_default_enhancement_presets()['default']
    if 'processing_history' not in st.session_state:
        st.session_state.processing_history = []


def reset_session():
    """Reset session state"""
    st.session_state.original_image = None
    st.session_state.scanned_image = None
    st.session_state.enhanced_image = None
    st.session_state.detected_corners = None
    st.session_state.processing_result = None
    st.session_state.needs_manual_corners = False
    st.session_state.manual_corners = None
    st.session_state.enhancement_config = get_default_enhancement_presets()['default']
    st.session_state.processing_history = []


_ROTATE_90_MAP = {"0°": 0, "90° CW": 1, "90° CCW": 3, "180°": 2}


def apply_user_rotation(image: np.ndarray) -> np.ndarray:
    """Áp dụng góc xoay do người dùng chọn trong sidebar."""
    turns = _ROTATE_90_MAP.get(st.session_state.get("rot_quarter", "0°"), 0)
    if turns:
        image = rotate_90(image, turns)
    angle = st.session_state.get("rot_angle", 0.0)
    if abs(angle) > 1e-6:
        image = rotate_image(image, angle, expand=True)
    return image


def main():
    """Main Streamlit application"""
    initialize_session_state()

    st.title("📄 SmartScan - Intelligent Document Scanner")
    st.markdown("""
    Tự động phát hiện, hiệu chỉnh phối cảnh và nâng cao chất lượng tài liệu giấy
    """)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Cấu hình")

        # Upload section
        st.subheader("📤 Upload ảnh")
        uploaded_file = st.file_uploader(
            "Chọn ảnh tài liệu",
            type=['jpg', 'jpeg', 'png', 'bmp'],
            help="Hỗ trợ JPG, PNG, BMP (max 10MB)"
        )

        if uploaded_file is not None:
            if st.button("🔄 Xử lý ảnh mới", key="reset"):
                reset_session()

        # Rotation section
        st.subheader("🔄 Xoay & hướng ảnh")
        rot_quarter = st.radio(
            "Xoay 90°",
            options=["0°", "90° CW", "90° CCW", "180°"],
            horizontal=True,
            key="rot_quarter",
            help="Xoay nhanh theo bước 90 độ (ví dụ: ảnh chụp ngang cần dựng dọc)"
        )
        st.session_state.rot_quarter = rot_quarter

        rot_angle = st.slider(
            "Góc xoay tinh chỉnh (độ)",
            min_value=-45.0,
            max_value=45.0,
            value=0.0,
            step=0.5,
            key="rot_angle",
            help="Xoay nghiêng để chỉnh đường chân trời hoặc mép tài liệu bị lệch"
        )
        st.session_state.rot_angle = rot_angle

        # Enhancement presets
        st.subheader("🎨 Preset Enhancement")
        presets = get_default_enhancement_presets()
        preset_name = st.selectbox(
            "Chọn preset",
            list(presets.keys()),
            index=0,
            help="Chọn preset phù hợp với loại tài liệu"
        )

        if st.button("Áp dụng preset", key="apply_preset"):
            st.session_state.enhancement_config = presets[preset_name]
            st.success(f"Đã áp dụng preset: {preset_name}")

        # Advanced enhancement settings
        with st.expander("⚡ Cấu hình nâng cao"):
            st.subheader("Denoising")
            denoise_method = st.selectbox(
                "Phương pháp",
                DENOISE_METHODS,
                index=DENOISE_METHODS.index(st.session_state.enhancement_config['denoise_method'])
            )
            st.session_state.enhancement_config['denoise_method'] = denoise_method

            st.subheader("Contrast Enhancement")
            contrast_method = st.selectbox(
                "Phương pháp",
                CONTRAST_METHODS,
                index=CONTRAST_METHODS.index(st.session_state.enhancement_config['contrast_method'])
            )
            st.session_state.enhancement_config['contrast_method'] = contrast_method

            if contrast_method == 'clahe':
                contrast_params = st.session_state.enhancement_config.setdefault('contrast_params', {})
                clip_limit = st.slider(
                    "CLAHE clip limit",
                    min_value=0.5, max_value=10.0,
                    value=float(contrast_params.get('clip_limit', 2.0)),
                    step=0.5, key="clahe_clip"
                )
                contrast_params['clip_limit'] = clip_limit

            st.subheader("Binarization")
            threshold_method = st.selectbox(
                "Phương pháp",
                THRESHOLD_METHODS,
                index=THRESHOLD_METHODS.index(st.session_state.enhancement_config['threshold_method'])
            )
            st.session_state.enhancement_config['threshold_method'] = threshold_method

            if threshold_method in ('adaptive_mean', 'adaptive_gaussian'):
                threshold_params = st.session_state.enhancement_config.setdefault('threshold_params', {})
                block_size = st.slider(
                    "Block size (adaptive)",
                    min_value=3, max_value=51, step=2,
                    value=int(threshold_params.get('block_size', 11)),
                    key="thresh_block",
                    help="Cửa sổ tính ngưỡng cục bộ. Nhỏ hơn = tách chữ/nền tốt hơn trên nền không đều"
                )
                threshold_params['block_size'] = block_size
                thresh_c = st.slider(
                    "Hằng số C",
                    min_value=-10, max_value=10,
                    value=int(threshold_params.get('C', 2)),
                    key="thresh_c",
                    help="Trừ vào trung bình cục bộ. Tăng = ít pixel đen hơn (chữ mảnh hơn)"
                )
                threshold_params['C'] = thresh_c
            elif threshold_method == 'global':
                threshold_params = st.session_state.enhancement_config.setdefault('threshold_params', {})
                threshold_params['threshold'] = st.slider(
                    "Ngưỡng global",
                    min_value=0, max_value=255,
                    value=int(threshold_params.get('threshold', 127)),
                    key="thresh_global"
                )

            st.subheader("Sharpening")
            sharpen = st.checkbox(
                "Bật sharpening",
                value=st.session_state.enhancement_config['sharpen']
            )
            st.session_state.enhancement_config['sharpen'] = sharpen

            if sharpen:
                sharpen_method = st.selectbox(
                    "Phương pháp",
                    SHARPEN_METHODS,
                    index=SHARPEN_METHODS.index(st.session_state.enhancement_config['sharpen_method'])
                )
                st.session_state.enhancement_config['sharpen_method'] = sharpen_method

                if sharpen_method == 'unsharp_mask':
                    sharpen_params = st.session_state.enhancement_config.setdefault('sharpen_params', {})
                    sharpen_params['strength'] = st.slider(
                        "Sharpen strength",
                        min_value=0.0, max_value=3.0,
                        value=float(sharpen_params.get('strength', 1.5)),
                        step=0.1, key="sharpen_strength"
                    )
                    sharpen_params['radius'] = st.slider(
                        "Sharpen radius (kernel)",
                        min_value=3, max_value=15, step=2,
                        value=int(sharpen_params.get('radius', 3)),
                        key="sharpen_radius",
                        help="Kernel blur cho unsharp mask. Quá nhỏ gây nhiễu/viền sáng quanh chữ"
                    )

            st.subheader("Shadow Correction")
            shadow_correction = st.checkbox(
                "Bật shadow correction",
                value=st.session_state.enhancement_config['shadow_correction']
            )
            st.session_state.enhancement_config['shadow_correction'] = shadow_correction

            if shadow_correction:
                shadow_method = st.selectbox(
                    "Phương pháp",
                    SHADOW_CORRECTION_METHODS,
                    index=SHADOW_CORRECTION_METHODS.index(st.session_state.enhancement_config['shadow_correction_method'])
                )
                st.session_state.enhancement_config['shadow_correction_method'] = shadow_method

            st.subheader("Output")
            convert_to_grayscale = st.checkbox(
                "Chuyển sang grayscale",
                value=st.session_state.enhancement_config['convert_to_grayscale']
            )
            st.session_state.enhancement_config['convert_to_grayscale'] = convert_to_grayscale

    # Main content
    if uploaded_file is not None:
        # Load image
        file_bytes = uploaded_file.read()
        success, image_bgr, message = load_and_validate_image(file_bytes)

        if not success:
            st.error(f"❌ {message}")
            return

        # Áp dụng xoay thủ công do người dùng chọn
        image_bgr = apply_user_rotation(image_bgr)

        # Convert to RGB for display
        image_rgb = convert_bgr_to_rgb(image_bgr)
        st.session_state.original_image = image_bgr

        # Display original image
        st.subheader("📷 Ảnh đầu vào (sau xoay)")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.image(image_rgb, use_column_width=True)
        with col2:
            info = get_image_info(image_bgr)
            st.json({
                "Kích thước": f"{info['width']}x{info['height']}",
                "Kênh màu": info['channels'],
                "Dung lượng": f"{info['size_mb']:.2f}MB",
                "Loại": "Màu" if info['is_color'] else "Grayscale"
            })

        # Process button
        st.subheader("🚀 Xử lý")
        if st.button("Bắt đầu xử lý", type="primary", use_container_width=True):
            with st.spinner("Đang xử lý ảnh..."):
                # Process document
                result = process_document_with_fallback(
                    image_bgr,
                    enhancement_config=st.session_state.enhancement_config,
                    use_padding=True,
                    debug=False
                )

                st.session_state.processing_result = result
                st.session_state.needs_manual_corners = result['needs_manual_corners']

                if result['success']:
                    st.session_state.detected_corners = result['detected_corners']
                    st.session_state.scanned_image = result['scanned_image']
                    st.session_state.enhanced_image = result['enhanced_image']

                    # Add to history
                    st.session_state.processing_history.append({
                        'timestamp': time.time(),
                        'result': result
                    })

        # Display results
        if st.session_state.processing_result is not None:
            result = st.session_state.processing_result

            # Check if needs manual corners
            if st.session_state.needs_manual_corners:
                st.warning("⚠️ Không thể phát hiện tự động 4 góc tài liệu. Vui lòng nhập thủ công.")

                st.subheader("🎯 Nhập 4 góc thủ công")
                st.info("Nhập tọa độ 4 góc theo thứ tự: Top-Left, Top-Right, Bottom-Right, Bottom-Left")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    tl_x = st.number_input("TL X", min_value=0, max_value=image_bgr.shape[1], value=100)
                    tl_y = st.number_input("TL Y", min_value=0, max_value=image_bgr.shape[0], value=100)
                with col2:
                    tr_x = st.number_input("TR X", min_value=0, max_value=image_bgr.shape[1], value=image_bgr.shape[1]-100)
                    tr_y = st.number_input("TR Y", min_value=0, max_value=image_bgr.shape[0], value=100)
                with col3:
                    br_x = st.number_input("BR X", min_value=0, max_value=image_bgr.shape[1], value=image_bgr.shape[1]-100)
                    br_y = st.number_input("BR Y", min_value=0, max_value=image_bgr.shape[0], value=image_bgr.shape[0]-100)
                with col4:
                    bl_x = st.number_input("BL X", min_value=0, max_value=image_bgr.shape[1], value=100)
                    bl_y = st.number_input("BL Y", min_value=0, max_value=image_bgr.shape[0], value=image_bgr.shape[0]-100)

                if st.button("Áp dụng manual corners", type="primary"):
                    manual_corners = np.array([
                        [tl_x, tl_y],
                        [tr_x, tr_y],
                        [br_x, br_y],
                        [bl_x, bl_y]
                    ], dtype=np.float32)

                    with st.spinner("Đang xử lý với manual corners..."):
                        result = process_document(
                            image_bgr,
                            manual_corners=manual_corners,
                            enhancement_config=st.session_state.enhancement_config,
                            use_padding=True,
                            debug=False
                        )

                        st.session_state.processing_result = result
                        st.session_state.needs_manual_corners = False

                        if result['success']:
                            st.session_state.detected_corners = result['detected_corners']
                            st.session_state.scanned_image = result['scanned_image']
                            st.session_state.enhanced_image = result['enhanced_image']
                            st.success("✅ Xử lý thành công với manual corners!")
                        else:
                            st.error(f"❌ {result['message']}")

            # Display processing results
            if result['success'] and not st.session_state.needs_manual_corners:
                st.success(f"✅ {result['message']}")

                # Display processing steps
                with st.expander("📊 Chi tiết xử lý"):
                    steps = result['steps']
                    for step_name, step_info in steps.items():
                        step_label = step_name.capitalize()
                        status = "✅" if step_info['success'] else "❌"
                        st.write(f"{status} {step_label}: {step_info['message']}")
                        if 'time' in step_info:
                            st.write(f"   ⏱️ Thời gian: {format_processing_time(step_info['time'])}")

                    st.write(f"⏱️ **Tổng thời gian:** {format_processing_time(result['processing_time'])}")

                # Display scanned image
                if st.session_state.scanned_image is not None:
                    st.subheader("📐 Ảnh sau khi hiệu chỉnh phối cảnh")
                    scanned_rgb = convert_bgr_to_rgb(st.session_state.scanned_image)
                    st.image(scanned_rgb, use_column_width=True)

                # Display enhanced image
                if st.session_state.enhanced_image is not None:
                    st.subheader("✨ Ảnh sau khi nâng cao chất lượng")
                    enhanced_rgb = convert_bgr_to_rgb(st.session_state.enhanced_image)
                    st.image(enhanced_rgb, use_column_width=True)

                    # Download buttons
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if st.session_state.scanned_image is not None:
                            scanned_bytes = encode_image_to_bytes(st.session_state.scanned_image, '.jpg', 95)
                            st.download_button(
                                label="📥 Tải ảnh scanned (JPG)",
                                data=scanned_bytes,
                                file_name="smartscan_scanned.jpg",
                                mime="image/jpeg"
                            )

                    with col2:
                        if st.session_state.enhanced_image is not None:
                            enhanced_bytes = encode_image_to_bytes(st.session_state.enhanced_image, '.jpg', 95)
                            st.download_button(
                                label="📥 Tải ảnh enhanced (JPG)",
                                data=enhanced_bytes,
                                file_name="smartscan_enhanced.jpg",
                                mime="image/jpeg"
                            )

                    with col3:
                        if st.session_state.enhanced_image is not None:
                            enhanced_png_bytes = encode_image_to_bytes(st.session_state.enhanced_image, '.png')
                            st.download_button(
                                label="📥 Tải ảnh enhanced (PNG)",
                                data=enhanced_png_bytes,
                                file_name="smartscan_enhanced.png",
                                mime="image/png"
                            )

                    # Re-enhance button
                    if st.button("🔄 Áp dụng enhancement mới", use_container_width=True):
                        if st.session_state.scanned_image is not None:
                            with st.spinner("Đang áp dụng enhancement mới..."):
                                update_result = update_enhancement(
                                    st.session_state.scanned_image,
                                    st.session_state.enhancement_config
                                )

                                if update_result['success']:
                                    st.session_state.enhanced_image = update_result['enhanced_image']
                                    st.success("✅ Enhancement đã được cập nhật!")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {update_result['message']}")

                # Comparison view
                if st.session_state.scanned_image is not None and st.session_state.enhanced_image is not None:
                    with st.expander("🔍 So sánh ảnh"):
                        comparison = create_comparison_image(
                            st.session_state.scanned_image,
                            st.session_state.enhanced_image,
                            ("Scanned", "Enhanced")
                        )
                        comparison_rgb = convert_bgr_to_rgb(comparison)
                        st.image(comparison_rgb, use_column_width=True)

            else:
                st.error(f"❌ {result['message']}")

    else:
        st.info("👆 Vui lòng upload ảnh để bắt đầu xử lý")

        # Display instructions
        with st.expander("📖 Hướng dẫn sử dụng"):
            st.markdown("""
            ### Các bước sử dụng:

            1. **Upload ảnh**: Chọn ảnh tài liệu từ máy tính (JPG, PNG, BMP, max 10MB)
            2. **Chọn preset**: Chọn preset phù hợp với loại tài liệu của bạn
            3. **Cấu hình nâng cao**: Tùy chỉnh các tham số enhancement nếu cần
            4. **Xử lý**: Nhấn nút "Bắt đầu xử lý"
            5. **Kết quả**: Xem và tải ảnh đã xử lý

            ### Các preset có sẵn:
            - **default**: Cấu hình mặc định, phù hợp cho hầu hết các tài liệu
            - **bw_document**: Tài liệu đen trắng (text), chuyển sang grayscale và binarization
            - **color_document**: Tài liệu màu, preserve màu sắc
            - **light_enhancement**: Enhancement nhẹ, chỉ tăng tương phản và giảm nhiễu

            ### Tips:
            - Nếu detection thất bại, bạn có thể nhập 4 góc thủ công
            - Có thể thay đổi enhancement và bấm "Áp dụng enhancement mới" để xem kết quả khác
            - Xuất ảnh JPG cho dung lượng nhỏ, PNG cho chất lượng cao
            """)


if __name__ == "__main__":
    main()

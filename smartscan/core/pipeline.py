"""
Pipeline Module for SmartScan
Kết nối các module: detection, perspective, enhancement thành pipeline thống nhất
"""

import cv2
import numpy as np
import time
import copy
from typing import Tuple, Optional, Dict, Any
from .detection import detect_document
from .perspective import correct_perspective, apply_perspective_with_padding
from .enhancement import (
    enhance_document,
    sanitize_enhancement_config,
    DEFAULT_ENHANCEMENT_CONFIG,
)
from .preprocessing import validate_image


def process_document(
    image: np.ndarray,
    manual_corners: Optional[np.ndarray] = None,
    enhancement_config: Optional[Dict[str, Any]] = None,
    use_padding: bool = True,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Pipeline xử lý tài liệu hoàn chỉnh: detect → perspective → enhance

    Args:
        image: NumPy array (BGR, uint8)
        manual_corners: Optional - 4 góc thủ công shape (4, 2) nếu detection thất bại
        enhancement_config: Dict chứa các tham số enhancement. Nếu None, dùng mặc định
        use_padding: Có dùng padding khi perspective correction không
        debug: Có trả về debug images không

    Returns:
        Dictionary:
            - 'success': bool - Pipeline thành công không
            - 'original_image': np.ndarray - Ảnh gốc
            - 'detected_corners': np.ndarray or None - 4 góc đã phát hiện
            - 'scanned_image': np.ndarray or None - Ảnh sau perspective correction
            - 'enhanced_image': np.ndarray or None - Ảnh sau enhancement
            - 'debug_images': Dict[str, np.ndarray] - Các debug images (nếu debug=True)
            - 'message': str - Thông báo kết quả
            - 'steps': Dict[str, Any] - Chi tiết từng bước xử lý
            - 'processing_time': float - Tổng thời gian xử lý (giây)
    """
    start_time = time.time()
    steps = {}
    debug_images = {}

    # Validate ảnh
    is_valid, error_msg = validate_image(image)
    if not is_valid:
        return {
            'success': False,
            'original_image': None,
            'detected_corners': None,
            'scanned_image': None,
            'enhanced_image': None,
            'debug_images': {},
            'message': f"Invalid image: {error_msg}",
            'steps': {},
            'processing_time': time.time() - start_time
        }

    original_image = image.copy()

    # Step 1: Detection
    detection_start = time.time()
    detection_result = detect_document(image, manual_corners=manual_corners, debug=debug)
    detection_time = time.time() - detection_start

    steps['detection'] = {
        'success': detection_result['success'],
        'message': detection_result['message'],
        'confidence': detection_result['confidence'],
        'time': detection_time
    }

    if debug and detection_result['debug_image'] is not None:
        debug_images['detection'] = detection_result['debug_image']

    if not detection_result['success']:
        return {
            'success': False,
            'original_image': original_image,
            'detected_corners': None,
            'scanned_image': None,
            'enhanced_image': None,
            'debug_images': debug_images,
            'message': f"Detection failed: {detection_result['message']}",
            'steps': steps,
            'processing_time': time.time() - start_time
        }

    corners = detection_result['corners']
    steps['detection']['corners'] = corners.tolist()

    # Step 2: Perspective Correction
    perspective_start = time.time()
    if use_padding:
        perspective_result = apply_perspective_with_padding(image, corners, padding_ratio=0.05)
    else:
        perspective_result = correct_perspective(image, corners)
    perspective_time = time.time() - perspective_start

    steps['perspective'] = {
        'success': perspective_result['success'],
        'message': perspective_result['message'],
        'output_size': perspective_result['output_size'],
        'time': perspective_time
    }

    if not perspective_result['success']:
        return {
            'success': False,
            'original_image': original_image,
            'detected_corners': corners,
            'scanned_image': None,
            'enhanced_image': None,
            'debug_images': debug_images,
            'message': f"Perspective correction failed: {perspective_result['message']}",
            'steps': steps,
            'processing_time': time.time() - start_time
        }

    scanned_image = perspective_result['corrected_image']

    # Step 3: Enhancement
    enhancement_start = time.time()

    # Chuẩn hóa config: điền mặc định và loại bỏ khóa không hợp lệ
    enhancement_config = sanitize_enhancement_config(enhancement_config)

    try:
        enhancement_result = enhance_document(
            scanned_image,
            return_intermediate=debug,
            **enhancement_config
        )
    except Exception as e:
        steps['enhancement'] = {
            'success': False,
            'message': str(e),
            'time': time.time() - enhancement_start
        }
        return {
            'success': False,
            'original_image': original_image,
            'detected_corners': corners,
            'scanned_image': scanned_image,
            'enhanced_image': None,
            'debug_images': debug_images,
            'message': f"Enhancement failed: {str(e)}",
            'steps': steps,
            'processing_time': time.time() - start_time
        }
    enhancement_time = time.time() - enhancement_start

    steps['enhancement'] = {
        'success': enhancement_result['success'],
        'message': enhancement_result['message'],
        'time': enhancement_time
    }

    if debug and 'intermediate' in enhancement_result:
        debug_images['enhancement_intermediate'] = enhancement_result['intermediate']

    if not enhancement_result['success']:
        # Enhancement thất bại nhưng vẫn trả về scanned_image
        return {
            'success': True,  # Partial success
            'original_image': original_image,
            'detected_corners': corners,
            'scanned_image': scanned_image,
            'enhanced_image': None,
            'debug_images': debug_images,
            'message': f"Enhancement failed: {enhancement_result['message']}. Scanned image available.",
            'steps': steps,
            'processing_time': time.time() - start_time
        }

    enhanced_image = enhancement_result['enhanced_image']

    total_time = time.time() - start_time

    return {
        'success': True,
        'original_image': original_image,
        'detected_corners': corners,
        'scanned_image': scanned_image,
        'enhanced_image': enhanced_image,
        'debug_images': debug_images,
        'message': "Document processed successfully",
        'steps': steps,
        'processing_time': total_time
    }


def process_document_with_fallback(
    image: np.ndarray,
    manual_corners: Optional[np.ndarray] = None,
    enhancement_config: Optional[Dict[str, Any]] = None,
    use_padding: bool = True,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Pipeline với fallback mechanism: thử auto detection, nếu thất bại cho phép manual corners

    Args:
        image: NumPy array (BGR, uint8)
        manual_corners: Optional - 4 góc thủ công shape (4, 2)
        enhancement_config: Dict chứa các tham số enhancement
        use_padding: Có dùng padding khi perspective correction không
        debug: Có trả về debug images không

    Returns:
        Dictionary tương tự process_document() với thêm field:
            - 'needs_manual_corners': bool - Cần nhập manual corners không
    """
    # Thử auto detection trước
    result = process_document(
        image,
        manual_corners=manual_corners,
        enhancement_config=enhancement_config,
        use_padding=use_padding,
        debug=debug
    )

    # Nếu detection thất bại, đánh dấu cần manual corners
    if not result['success'] and 'Detection failed' in result['message']:
        result['needs_manual_corners'] = True
        result['original_image'] = image.copy()
    else:
        result['needs_manual_corners'] = False

    return result


def update_enhancement(
    scanned_image: np.ndarray,
    enhancement_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Cập nhật enhancement cho ảnh đã scan (đã perspective correction)

    Args:
        scanned_image: NumPy array (BGR, uint8) - Ảnh sau perspective correction
        enhancement_config: Dict chứa các tham số enhancement mới

    Returns:
        Dictionary:
            - 'success': bool - Enhancement thành công không
            - 'enhanced_image': np.ndarray or None - Ảnh đã enhance
            - 'message': str - Thông báo kết quả
            - 'processing_time': float - Thời gian xử lý
    """
    start_time = time.time()

    sanitized_config = sanitize_enhancement_config(enhancement_config)

    try:
        enhancement_result = enhance_document(scanned_image, **sanitized_config)
    except Exception as e:
        return {
            'success': False,
            'enhanced_image': None,
            'message': f"Enhancement failed: {str(e)}",
            'processing_time': time.time() - start_time
        }

    processing_time = time.time() - start_time

    return {
        'success': enhancement_result['success'],
        'enhanced_image': enhancement_result['enhanced_image'],
        'message': enhancement_result['message'],
        'processing_time': processing_time
    }


def validate_and_load_image(image_path: str) -> Tuple[bool, np.ndarray, str]:
    """
    Load và validate ảnh từ file

    Args:
        image_path: Đường dẫn đến file ảnh

    Returns:
        Tuple (success, image, message):
            - success: bool - Load thành công không
            - image: np.ndarray or None - Ảnh đã load (BGR)
            - message: str - Thông báo kết quả
    """
    try:
        image = cv2.imread(image_path)
        if image is None:
            return False, None, f"Failed to load image from {image_path}"

        is_valid, error_msg = validate_image(image)
        if not is_valid:
            return False, None, f"Invalid image: {error_msg}"

        return True, image, "Image loaded successfully"
    except Exception as e:
        return False, None, f"Error loading image: {str(e)}"


def _preset_config(**overrides: Any) -> Dict[str, Any]:
    """Tạo enhancement config từ DEFAULT_ENHANCEMENT_CONFIG + overrides."""
    config = copy.deepcopy(DEFAULT_ENHANCEMENT_CONFIG)
    config.update(overrides)
    return config


def get_default_enhancement_presets() -> Dict[str, Dict[str, Any]]:
    """
    Lấy các preset enhancement cho các loại tài liệu khác nhau.

    Các preset chính:
        - original / natural: giữ màu tự nhiên, không binarize
        - color_document: tài liệu có màu, giữ màu
        - bw_document: tài liệu đen trắng (có threshold)
        - low_light: tài liệu thiếu sáng
        - text_enhancement: làm rõ chữ và đường nét

    Returns:
        Dict mapping preset name → enhancement config
    """
    bilateral = {'kernel_size': 9, 'sigma_color': 75, 'sigma_space': 75}
    clahe = {'clip_limit': 2.0, 'tile_grid_size': (8, 8)}
    shadow = {'kernel_size': 25, 'blur_sigma': 5}

    return {
        'default': _preset_config(),
        'original': _preset_config(
            denoise_method='none', denoise_params={},
            contrast_method='none', contrast_params={},
            threshold_method='none', threshold_params={},
            sharpen=False, sharpen_method='none', sharpen_params={},
            shadow_correction=False, shadow_correction_method='none',
            shadow_correction_params={},
            convert_to_grayscale=False,
            brightness=0, contrast=1.0,
        ),
        'natural': _preset_config(),
        'color_document': _preset_config(
            denoise_params=bilateral,
            contrast_params=clahe,
            threshold_method='none', threshold_params={},
            sharpen=True, sharpen_params={'strength': 1.0, 'radius': 3},
            shadow_correction=True, shadow_correction_params=shadow,
            convert_to_grayscale=False,
            brightness=5, contrast=1.05,
        ),
        'bw_document': _preset_config(
            denoise_params=bilateral,
            contrast_params=clahe,
            threshold_method='adaptive_gaussian',
            threshold_params={'block_size': 11, 'C': 2},
            sharpen=True, sharpen_params={'strength': 1.0, 'radius': 3},
            shadow_correction=False,
            convert_to_grayscale=True,
            brightness=10, contrast=1.1,
        ),
        'low_light': _preset_config(
            denoise_params=bilateral,
            contrast_params={'clip_limit': 3.0, 'tile_grid_size': (8, 8)},
            threshold_method='none', threshold_params={},
            sharpen=False, sharpen_method='none', sharpen_params={},
            shadow_correction=True, shadow_correction_params=shadow,
            convert_to_grayscale=False,
            brightness=25, contrast=1.15,
        ),
        'text_enhancement': _preset_config(
            denoise_params=bilateral,
            contrast_params={'clip_limit': 3.0, 'tile_grid_size': (8, 8)},
            threshold_method='none', threshold_params={},
            sharpen=True, sharpen_params={'strength': 2.0, 'radius': 3},
            shadow_correction=False,
            convert_to_grayscale=True,
            brightness=5, contrast=1.1,
        ),
        'light_enhancement': _preset_config(
            denoise_params={'kernel_size': 9, 'sigma_color': 50, 'sigma_space': 50},
            contrast_params={'clip_limit': 3.0, 'tile_grid_size': (8, 8)},
            threshold_method='none', threshold_params={},
            sharpen=False, sharpen_method='none', sharpen_params={},
            shadow_correction=True, shadow_correction_params=shadow,
            convert_to_grayscale=False,
            brightness=15, contrast=1.1,
        ),
    }

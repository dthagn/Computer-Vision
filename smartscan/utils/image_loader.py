"""
Image Loader Module for SmartScan
Load và validate ảnh từ file hoặc byte stream
"""

import cv2
import numpy as np
from typing import Tuple, Optional
from ..core.preprocessing import validate_image


# Giới hạn kích thước upload (MB)
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Giới hạn kích thước ảnh (pixels)
MAX_IMAGE_WIDTH = 4000
MAX_IMAGE_HEIGHT = 4000


def load_image_from_file(file_path: str) -> Tuple[bool, np.ndarray, str]:
    """
    Load ảnh từ file path

    Args:
        file_path: Đường dẫn đến file ảnh

    Returns:
        Tuple (success, image, message):
            - success: bool - Load thành công không
            - image: np.ndarray or None - Ảnh đã load (BGR)
            - message: str - Thông báo kết quả
    """
    try:
        image = cv2.imread(file_path)
        if image is None:
            return False, None, f"Failed to load image from {file_path}"

        is_valid, error_msg = validate_image(image)
        if not is_valid:
            return False, None, f"Invalid image: {error_msg}"

        return True, image, "Image loaded successfully"
    except Exception as e:
        return False, None, f"Error loading image: {str(e)}"


def load_image_from_bytes(file_bytes: bytes) -> Tuple[bool, np.ndarray, str]:
    """
    Load ảnh từ byte stream (cho Streamlit upload)

    Args:
        file_bytes: Bytes của file ảnh

    Returns:
        Tuple (success, image, message):
            - success: bool - Load thành công không
            - image: np.ndarray or None - Ảnh đã load (BGR)
            - message: str - Thông báo kết quả
    """
    try:
        # Convert bytes to numpy array
        nparr = np.frombuffer(file_bytes, np.uint8)

        # Decode image
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            return False, None, "Failed to decode image from bytes"

        is_valid, error_msg = validate_image(image)
        if not is_valid:
            return False, None, f"Invalid image: {error_msg}"

        return True, image, "Image loaded successfully"
    except Exception as e:
        return False, None, f"Error loading image from bytes: {str(e)}"


def validate_file_size(file_size: int) -> Tuple[bool, str]:
    """
    Validate kích thước file

    Args:
        file_size: Kích thước file (bytes)

    Returns:
        Tuple (is_valid, message)
    """
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        return False, f"File too large: {size_mb:.2f}MB (max: {MAX_FILE_SIZE_MB}MB)"

    return True, "File size OK"


def validate_image_dimensions(image: np.ndarray) -> Tuple[bool, str]:
    """
    Validate kích thước ảnh

    Args:
        image: NumPy array (BGR)

    Returns:
        Tuple (is_valid, message)
    """
    h, w = image.shape[:2]

    if w > MAX_IMAGE_WIDTH or h > MAX_IMAGE_HEIGHT:
        return False, f"Image too large: {w}x{h} (max: {MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT})"

    return True, "Image dimensions OK"


def load_and_validate_image(file_bytes: bytes) -> Tuple[bool, np.ndarray, str]:
    """
    Load và validate ảnh từ bytes với đầy đủ checks

    Args:
        file_bytes: Bytes của file ảnh

    Returns:
        Tuple (success, image, message):
            - success: bool - Load thành công không
            - image: np.ndarray or None - Ảnh đã load (BGR)
            - message: str - Thông báo kết quả
    """
    # Check file size
    is_valid, message = validate_file_size(len(file_bytes))
    if not is_valid:
        return False, None, message

    # Load image
    success, image, message = load_image_from_bytes(file_bytes)
    if not success:
        return False, None, message

    # Check dimensions
    is_valid, message = validate_image_dimensions(image)
    if not is_valid:
        return False, None, message

    return True, image, "Image loaded and validated successfully"


def convert_rgb_to_bgr(image: np.ndarray) -> np.ndarray:
    """
    Convert RGB image to BGR format for OpenCV

    Args:
        image: NumPy array (RGB, uint8)

    Returns:
        NumPy array (BGR, uint8)
    """
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)


def convert_bgr_to_rgb(image: np.ndarray) -> np.ndarray:
    """
    Convert BGR image to RGB format for Streamlit

    Args:
        image: NumPy array (BGR, uint8)

    Returns:
        NumPy array (RGB, uint8)
    """
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

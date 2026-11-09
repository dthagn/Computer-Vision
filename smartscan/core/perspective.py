"""
Perspective Correction Module for SmartScan
Hiệu chỉnh phối cảnh để làm thẳng tài liệu
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any
from .preprocessing import validate_image


def calculate_output_dimensions(corners: np.ndarray) -> Tuple[int, int]:
    """
    Tính toán kích thước đầu ra dựa trên chiều dài cạnh của tứ giác.

    Args:
        corners: NumPy array shape (4, 2) với thứ tự TL, TR, BR, BL

    Returns:
        Tuple (width, height) cho ảnh đầu ra
    """
    tl, tr, br, bl = corners

    # Tính chiều rộng: trung bình của top edge và bottom edge
    top_width = np.linalg.norm(tr - tl)
    bottom_width = np.linalg.norm(br - bl)
    width = int(max(top_width, bottom_width))

    # Tính chiều cao: trung bình của left edge và right edge
    left_height = np.linalg.norm(bl - tl)
    right_height = np.linalg.norm(br - tr)
    height = int(max(left_height, right_height))

    return width, height


def validate_corners(corners: np.ndarray, image_shape: Tuple[int, int]) -> Tuple[bool, str]:
    """
    Validate 4 góc đầu vào.

    Args:
        corners: NumPy array shape (4, 2)
        image_shape: Kích thước ảnh (h, w)

    Returns:
        Tuple (is_valid, error_message)
    """
    if corners is None:
        return False, "Corners is None"

    if not isinstance(corners, np.ndarray):
        return False, f"Corners must be numpy array, got {type(corners)}"

    if corners.shape != (4, 2):
        return False, f"Corners must have shape (4, 2), got {corners.shape}"

    if corners.dtype not in [np.float32, np.float64, np.int32, np.int64]:
        return False, f"Corners must be numeric type, got {corners.dtype}"

    h, w = image_shape

    # Kiểm tra tọa độ nằm trong ảnh
    if np.any(corners[:, 0] < 0) or np.any(corners[:, 0] >= w):
        return False, "Corner x-coordinates out of image bounds"

    if np.any(corners[:, 1] < 0) or np.any(corners[:, 1] >= h):
        return False, "Corner y-coordinates out of image bounds"

    # Kiểm tra không có trùng lặp
    unique_corners = np.unique(corners, axis=0)
    if len(unique_corners) < 4:
        return False, "Corners contain duplicate points"

    # Kiểm tra không collinear (tất cả 4 điểm không nằm trên cùng một đường)
    if np.linalg.det(np.cov(corners.T)) < 1e-6:
        return False, "Corners are collinear or nearly collinear"

    return True, ""


def check_self_intersection(corners: np.ndarray) -> bool:
    """
    Kiểm tra xem tứ giác có tự giao nhau không.

    Args:
        corners: NumPy array shape (4, 2) với thứ tự TL, TR, BR, BL

    Returns:
        True nếu tự giao nhau, False nếu không
    """
    tl, tr, br, bl = corners

    def ccw(A, B, C):
        """Counter-clockwise test"""
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    def segments_intersect(p1, p2, p3, p4):
        """Kiểm tra xem đoạn p1-p2 có giao đoạn p3-p4 không"""
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

    # Kiểm tra TL-TR với BL-BR
    if segments_intersect(tl, tr, bl, br):
        return True

    # Kiểm tra TR-BR với TL-BL
    if segments_intersect(tr, br, tl, bl):
        return True

    return False


def compute_homography_matrix(
    src_corners: np.ndarray,
    dst_corners: np.ndarray
) -> np.ndarray:
    """
    Tính ma trận Homography để biến đổi phối cảnh.

    Args:
        src_corners: 4 góc nguồn shape (4, 2)
        dst_corners: 4 góc đích shape (4, 2)

    Returns:
        Ma trận Homography 3x3
    """
    return cv2.getPerspectiveTransform(src_corners, dst_corners)


def correct_perspective(
    image: np.ndarray,
    corners: np.ndarray,
    output_size: Optional[Tuple[int, int]] = None
) -> Dict[str, Any]:
    """
    Hiệu chỉnh phối cảnh để làm thẳng tài liệu.

    Args:
        image: NumPy array (BGR, uint8)
        corners: 4 góc shape (4, 2) với thứ tự TL, TR, BR, BL
        output_size: Optional (width, height) cho ảnh đầu ra.
                     Nếu None, tự động tính dựa trên chiều dài cạnh.

    Returns:
        Dictionary:
            - 'success': bool - Hiệu chỉnh thành công không
            - 'corrected_image': np.ndarray or None - Ảnh đã hiệu chỉnh
            - 'homography_matrix': np.ndarray or None - Ma trận homography
            - 'output_size': Tuple[int, int] or None - Kích thước đầu ra
            - 'message': str - Thông báo kết quả
    """
    # Validate ảnh
    is_valid, error_msg = validate_image(image)
    if not is_valid:
        return {
            'success': False,
            'corrected_image': None,
            'homography_matrix': None,
            'output_size': None,
            'message': f"Invalid image: {error_msg}"
        }

    h, w = image.shape[:2]

    # Validate corners
    corners = np.array(corners, dtype=np.float32)
    is_valid, error_msg = validate_corners(corners, (h, w))
    if not is_valid:
        return {
            'success': False,
            'corrected_image': None,
            'homography_matrix': None,
            'output_size': None,
            'message': f"Invalid corners: {error_msg}"
        }

    # Kiểm tra tự giao nhau
    if check_self_intersection(corners):
        return {
            'success': False,
            'corrected_image': None,
            'homography_matrix': None,
            'output_size': None,
            'message': "Corners form self-intersecting quadrilateral"
        }

    # Tính kích thước đầu ra
    if output_size is None:
        output_size = calculate_output_dimensions(corners)

    output_width, output_height = output_size

    # Tạo đích điểm (hình chữ nhật)
    dst_corners = np.array([
        [0, 0],                           # TL
        [output_width - 1, 0],            # TR
        [output_width - 1, output_height - 1],  # BR
        [0, output_height - 1]            # BL
    ], dtype=np.float32)

    # Tính ma trận homography
    try:
        homography_matrix = compute_homography_matrix(corners, dst_corners)
    except cv2.error as e:
        return {
            'success': False,
            'corrected_image': None,
            'homography_matrix': None,
            'output_size': None,
            'message': f"Failed to compute homography: {str(e)}"
        }

    # Áp dụng perspective transform
    try:
        corrected_image = cv2.warpPerspective(
            image,
            homography_matrix,
            (output_width, output_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)  # White background
        )
    except cv2.error as e:
        return {
            'success': False,
            'corrected_image': None,
            'homography_matrix': None,
            'output_size': None,
            'message': f"Failed to apply perspective transform: {str(e)}"
        }

    return {
        'success': True,
        'corrected_image': corrected_image,
        'homography_matrix': homography_matrix,
        'output_size': output_size,
        'message': f"Perspective corrected to {output_width}x{output_height}"
    }


def apply_perspective_with_padding(
    image: np.ndarray,
    corners: np.ndarray,
    padding_ratio: float = 0.05
) -> Dict[str, Any]:
    """
    Hiệu chỉnh phối cảnh với padding để tránh cắt mất nội dung.

    Args:
        image: NumPy array (BGR, uint8)
        corners: 4 góc shape (4, 2)
        padding_ratio: Tỷ lệ padding (0.05 = 5%)

    Returns:
        Dictionary tương tự correct_perspective
    """
    # Validate trước
    is_valid, error_msg = validate_image(image)
    if not is_valid:
        return {
            'success': False,
            'corrected_image': None,
            'homography_matrix': None,
            'output_size': None,
            'message': f"Invalid image: {error_msg}"
        }

    h, w = image.shape[:2]
    corners = np.array(corners, dtype=np.float32)
    is_valid, error_msg = validate_corners(corners, (h, w))
    if not is_valid:
        return {
            'success': False,
            'corrected_image': None,
            'homography_matrix': None,
            'output_size': None,
            'message': f"Invalid corners: {error_msg}"
        }

    # Tính kích thước cơ bản
    base_width, base_height = calculate_output_dimensions(corners)

    # Thêm padding
    padding_w = int(base_width * padding_ratio)
    padding_h = int(base_height * padding_ratio)

    output_size = (base_width + 2 * padding_w, base_height + 2 * padding_h)

    # Tính đích điểm với padding
    dst_corners = np.array([
        [padding_w, padding_h],
        [base_width + padding_w - 1, padding_h],
        [base_width + padding_w - 1, base_height + padding_h - 1],
        [padding_w, base_height + padding_h - 1]
    ], dtype=np.float32)

    # Tính homography
    try:
        homography_matrix = cv2.getPerspectiveTransform(corners, dst_corners)
    except cv2.error as e:
        return {
            'success': False,
            'corrected_image': None,
            'homography_matrix': None,
            'output_size': None,
            'message': f"Failed to compute homography: {str(e)}"
        }

    # Áp dụng transform
    try:
        corrected_image = cv2.warpPerspective(
            image,
            homography_matrix,
            output_size,
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )
    except cv2.error as e:
        return {
            'success': False,
            'corrected_image': None,
            'homography_matrix': None,
            'output_size': None,
            'message': f"Failed to apply perspective transform: {str(e)}"
        }

    return {
        'success': True,
        'corrected_image': corrected_image,
        'homography_matrix': homography_matrix,
        'output_size': output_size,
        'message': f"Perspective corrected with padding to {output_size[0]}x{output_size[1]}"
    }

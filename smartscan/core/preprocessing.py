"""
Preprocessing Module for SmartScan
Cung cấp các hàm tiền xử lý ảnh cho phát hiện tài liệu và hiệu chỉnh phối cảnh
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any


def validate_image(image: np.ndarray) -> Tuple[bool, str]:
    """
    Kiểm tra tính hợp lệ của ảnh đầu vào.

    Args:
        image: NumPy array (BGR, RGB hoặc grayscale)

    Returns:
        Tuple (is_valid, error_message):
            - is_valid: True nếu ảnh hợp lệ
            - error_message: Thông báo lỗi nếu không hợp lệ
    """
    if image is None:
        return False, "Image is None"

    if not isinstance(image, np.ndarray):
        return False, f"Image must be numpy array, got {type(image)}"

    if len(image.shape) not in [2, 3]:
        return False, f"Image must have 2 or 3 dimensions, got {len(image.shape)}"

    if image.dtype != np.uint8:
        return False, f"Image must be uint8, got {image.dtype}"

    if image.size == 0:
        return False, "Image is empty"

    # Kiểm tra kích thước tối thiểu
    h, w = image.shape[:2]
    if h < 10 or w < 10:
        return False, f"Image too small: {h}x{w}"

    return True, ""


def rotate_image(
    image: np.ndarray,
    angle_deg: float,
    expand: bool = True,
    border_value: int = 255
) -> np.ndarray:
    """
    Xoay ảnh theo góc tùy ý (độ) bằng affine transform.

    Args:
        image: NumPy array (BGR, RGB hoặc grayscale)
        angle_deg: Góc xoay theo độ. Dương = ngược chiều kim đồng hồ
                   (theo hệ tọa độ ảnh, hiển thị như xoay thuận chiều kim đồng hồ).
        expand: True = mở rộng canvas để không cắt góc ảnh; False = giữ nguyên kích thước
        border_value: Giá trị pixel vùng trống (mặc định trắng 255)

    Returns:
        Ảnh đã xoay, cùng số kênh và dtype với ảnh gốc
    """
    if abs(angle_deg) < 1e-6:
        return image.copy()

    h, w = image.shape[:2]
    center = (w / 2.0, h / 2.0)

    M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)

    if expand:
        cos_a = abs(M[0, 0])
        sin_a = abs(M[0, 1])
        new_w = int(h * sin_a + w * cos_a)
        new_h = int(h * cos_a + w * sin_a)
        M[0, 2] += (new_w - w) / 2.0
        M[1, 2] += (new_h - h) / 2.0
        dsize = (new_w, new_h)
    else:
        dsize = (w, h)

    border = border_value if len(image.shape) == 2 else (border_value,) * image.shape[2]

    return cv2.warpAffine(
        image,
        M,
        dsize,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border
    )


def rotate_90(image: np.ndarray, turns: int = 1) -> np.ndarray:
    """
    Xoay ảnh theo bội số 90 độ.

    Args:
        image: NumPy array (BGR, RGB hoặc grayscale)
        turns: Số lần xoay 90° theo chiều kim đồng hồ.
               1 = 90° CW, 2 = 180°, 3 = 90° CCW. Giá trị âm được chuẩn hóa.

    Returns:
        Ảnh đã xoay
    """
    turns = turns % 4
    if turns == 0:
        return image.copy()
    if turns == 1:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if turns == 2:
        return cv2.rotate(image, cv2.ROTATE_180)
    return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)


def resize_with_aspect_ratio(
    image: np.ndarray,
    max_width: int = 1280,
    max_height: int = 720
) -> Tuple[np.ndarray, float, float]:
    """
    Resize ảnh giữ nguyên tỷ lệ khung hình.

    Args:
        image: NumPy array (BGR, RGB hoặc grayscale)
        max_width: Chiều rộng tối đa
        max_height: Chiều cao tối đa

    Returns:
        Tuple (resized_image, scale_x, scale_y):
            - resized_image: Ảnh đã resize
            - scale_x: Tỷ lệ theo chiều ngang (new_width / original_width)
            - scale_y: Tỷ lệ theo chiều dọc (new_height / original_height)
    """
    h, w = image.shape[:2]

    # Tính toán kích thước mới giữ tỷ lệ
    scale = min(max_width / w, max_height / h, 1.0)  # Không zoom up

    new_w = int(w * scale)
    new_h = int(h * scale)

    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    return resized, scale, scale


def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    Chuyển đổi ảnh sang grayscale.

    Args:
        image: NumPy array (BGR hoặc RGB)

    Returns:
        Grayscale image
    """
    if len(image.shape) == 2:
        # Đã là grayscale
        return image

    # Giả định BGR (mặc định OpenCV)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def apply_gaussian_blur(
    image: np.ndarray,
    kernel_size: int = 5,
    sigma: float = 0
) -> np.ndarray:
    """
    Áp dụng Gaussian Blur để giảm nhiễu.

    Args:
        image: NumPy array (grayscale hoặc color)
        kernel_size: Kích thước kernel (phải là số lẻ)
        sigma: Độ lệch chuẩn Gaussian (0 = tự động tính từ kernel_size)

    Returns:
        Blurred image
    """
    if kernel_size % 2 == 0:
        kernel_size += 1  # Đảm bảo số lẻ

    if kernel_size < 3:
        kernel_size = 3

    return cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)


def apply_canny_edge_detection(
    image: np.ndarray,
    threshold1: int = 50,
    threshold2: int = 150,
    aperture_size: int = 3
) -> np.ndarray:
    """
    Áp dụng Canny edge detection.

    Args:
        image: NumPy array (grayscale)
        threshold1: Ngưỡng thấp cho hysteresis
        threshold2: Ngưỡng cao cho hysteresis
        aperture_size: Kích thước aperture cho Sobel operator

    Returns:
        Edge map (binary image)
    """
    if len(image.shape) == 3:
        image = convert_to_grayscale(image)

    return cv2.Canny(image, threshold1, threshold2, apertureSize=aperture_size)


def apply_morphology(
    image: np.ndarray,
    operation: str = 'close',
    kernel_size: int = 5,
    iterations: int = 1
) -> np.ndarray:
    """
    Áp dụng morphological operations để làm sạch edges.

    Args:
        image: Binary image
        operation: Loại operation ('erode', 'dilate', 'open', 'close')
        kernel_size: Kích thước kernel
        iterations: Số lần lặp

    Returns:
        Processed image
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))

    if operation == 'erode':
        return cv2.erode(image, kernel, iterations=iterations)
    elif operation == 'dilate':
        return cv2.dilate(image, kernel, iterations=iterations)
    elif operation == 'open':
        return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel, iterations=iterations)
    elif operation == 'close':
        return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel, iterations=iterations)
    else:
        raise ValueError(f"Unknown morphological operation: {operation}")


def preprocess_for_detection(
    image: np.ndarray,
    max_width: int = 1280,
    max_height: int = 720,
    blur_kernel: int = 5,
    canny_low: int = 50,
    canny_high: int = 150,
    morph_close_kernel: int = 5
) -> Dict[str, Any]:
    """
    Pipeline tiền xử lý hoàn chỉnh cho phát hiện tài liệu.

    Args:
        image: NumPy array (BGR)
        max_width: Chiều rộng tối đa cho resize
        max_height: Chiều cao tối đa cho resize
        blur_kernel: Kích thước kernel cho Gaussian blur
        canny_low: Ngưỡng thấp cho Canny
        canny_high: Ngưỡng cao cho Canny
        morph_close_kernel: Kích thước kernel cho morphological close

    Returns:
        Dictionary chứa:
            - 'processed': Ảnh đã xử lý (edge map)
            - 'scale': Tỷ lệ scale từ resize
            - 'gray': Ảnh grayscale
            - 'blurred': Ảnh sau blur
            - 'original_size': Kích thước gốc (h, w)
            - 'resized_size': Kích thước sau resize (h, w)
    """
    # Validate
    is_valid, error_msg = validate_image(image)
    if not is_valid:
        raise ValueError(f"Invalid image: {error_msg}")

    original_h, original_w = image.shape[:2]

    # Resize giữ tỷ lệ
    resized, scale_x, scale_y = resize_with_aspect_ratio(image, max_width, max_height)
    resized_h, resized_w = resized.shape[:2]

    # Grayscale
    gray = convert_to_grayscale(resized)

    # Gaussian Blur
    blurred = apply_gaussian_blur(gray, kernel_size=blur_kernel)

    # Canny Edge Detection
    edges = apply_canny_edge_detection(blurred, canny_low, canny_high)

    # Morphological Close để nối các edge bị đứt
    edges = apply_morphology(edges, operation='close', kernel_size=morph_close_kernel)

    return {
        'processed': edges,
        'scale': scale_x,  # scale_x == scale_y do giữ tỷ lệ
        'gray': gray,
        'blurred': blurred,
        'original_size': (original_h, original_w),
        'resized_size': (resized_h, resized_w)
    }


def map_coordinates_to_original(
    coordinates: np.ndarray,
    scale: float
) -> np.ndarray:
    """
    Ánh xạ tọa độ từ ảnh resize về ảnh gốc.

    Args:
        coordinates: Tọa độ trong ảnh resize, shape (N, 2)
        scale: Tỷ lệ scale từ resize

    Returns:
        Tọa độ trong ảnh gốc, shape (N, 2)
    """
    if scale == 0:
        raise ValueError("Scale cannot be zero")

    return (coordinates / scale).astype(np.float32)


def create_debug_image(
    original: np.ndarray,
    edges: np.ndarray,
    contours: Optional[list] = None
) -> np.ndarray:
    """
    Tạo debug image để visualize các bước tiền xử lý.

    Args:
        original: Ảnh gốc (BGR)
        edges: Edge map (grayscale)
        contours: List của contours để vẽ (optional)

    Returns:
        Debug image (BGR)
    """
    # Convert edges sang BGR để ghép ảnh
    edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    # Resize edges về kích thước gốc nếu cần
    if edges_bgr.shape[:2] != original.shape[:2]:
        edges_bgr = cv2.resize(edges_bgr, (original.shape[1], original.shape[0]))

    # Ghép ảnh ngang
    debug = np.hstack([original, edges_bgr])

    # Vẽ contours nếu có
    if contours is not None:
        # Vẽ lên ảnh gốc
        debug_contours = original.copy()
        cv2.drawContours(debug_contours, contours, -1, (0, 255, 0), 2)
        debug = np.hstack([debug, debug_contours])

    return debug

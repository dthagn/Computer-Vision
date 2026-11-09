"""
Utility Functions for SmartScan
Các hàm tiện ích cho pipeline và UI
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any


def draw_corners_on_image(
    image: np.ndarray,
    corners: np.ndarray,
    color: Tuple[int, int, int] = (0, 255, 0),
    thickness: int = 3
) -> np.ndarray:
    """
    Vẽ 4 góc lên ảnh

    Args:
        image: NumPy array (BGR)
        corners: NumPy array shape (4, 2)
        color: Màu line (B, G, R)
        thickness: Độ dày line

    Returns:
        Ảnh với corners đã vẽ
    """
    result = image.copy()
    corners_int = corners.astype(np.int32)
    cv2.polylines(result, [corners_int], True, color, thickness)

    # Vẽ các điểm corners
    for i, corner in enumerate(corners_int):
        cv2.circle(result, tuple(corner), 8, (255, 0, 0), -1)

    # Vẽ nhãn
    labels = ['TL', 'TR', 'BR', 'BL']
    for i, (corner, label) in enumerate(zip(corners_int, labels)):
        cv2.putText(result, label, tuple(corner),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    return result


def create_comparison_image(
    original: np.ndarray,
    processed: np.ndarray,
    labels: Tuple[str, str] = ("Original", "Processed")
) -> np.ndarray:
    """
    Tạo ảnh so sánh side-by-side

    Args:
        original: Ảnh gốc (BGR)
        processed: Ảnh đã xử lý (BGR)
        labels: Nhãn cho 2 ảnh

    Returns:
        Ảnh so sánh (BGR)
    """
    # Resize để cùng kích thước
    h1, w1 = original.shape[:2]
    h2, w2 = processed.shape[:2]

    # Resize processed về kích thước original
    if (h1, w1) != (h2, w2):
        processed = cv2.resize(processed, (w1, h1))

    # Convert sang grayscale nếu cần
    if len(processed.shape) == 2:
        processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)

    # Ghép ảnh ngang
    comparison = np.hstack([original, processed])

    # Vẽ text label
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(comparison, labels[0], (10, 30), font, 1, (255, 255, 255), 2)
    cv2.putText(comparison, labels[1], (w1 + 10, 30), font, 1, (255, 255, 255), 2)

    return comparison


def encode_image_to_bytes(
    image: np.ndarray,
    format: str = '.jpg',
    quality: int = 95
) -> bytes:
    """
    Encode ảnh sang bytes cho download

    Args:
        image: NumPy array (BGR)
        format: Format output ('.jpg', '.png')
        quality: Chất lượng cho JPEG (1-100)

    Returns:
        Bytes của ảnh
    """
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality] if format == '.jpg' else []

    _, encoded = cv2.imencode(format, image, encode_param)
    return encoded.tobytes()


def format_processing_time(seconds: float) -> str:
    """
    Format thời gian xử lý cho hiển thị

    Args:
        seconds: Thời gian (giây)

    Returns:
        String đã format
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"


def get_image_info(image: np.ndarray) -> Dict[str, Any]:
    """
    Lấy thông tin về ảnh

    Args:
        image: NumPy array

    Returns:
        Dict với thông tin ảnh
    """
    h, w = image.shape[:2]
    channels = image.shape[2] if len(image.shape) == 3 else 1
    dtype = str(image.dtype)

    return {
        'height': h,
        'width': w,
        'channels': channels,
        'dtype': dtype,
        'size_mb': image.nbytes / (1024 * 1024),
        'is_color': channels == 3,
        'is_grayscale': channels == 1
    }


def resize_image_if_large(
    image: np.ndarray,
    max_width: int = 1920,
    max_height: int = 1080
) -> np.ndarray:
    """
    Resize ảnh nếu quá lớn

    Args:
        image: NumPy array
        max_width: Chiều rộng tối đa
        max_height: Chiều cao tối đa

    Returns:
        Ảnh đã resize hoặc ảnh gốc
    """
    h, w = image.shape[:2]

    if w <= max_width and h <= max_height:
        return image

    scale = min(max_width / w, max_height / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def create_debug_grid(
    images: Dict[str, np.ndarray],
    grid_size: Optional[Tuple[int, int]] = None
) -> np.ndarray:
    """
    Tạo grid debug image từ multiple images

    Args:
        images: Dict mapping label → image
        grid_size: Tuple (rows, cols) cho grid. Nếu None, auto calculate

    Returns:
        Grid image
    """
    num_images = len(images)
    if num_images == 0:
        return np.zeros((100, 100, 3), dtype=np.uint8)

    # Calculate grid size
    if grid_size is None:
        cols = int(np.ceil(np.sqrt(num_images)))
        rows = int(np.ceil(num_images / cols))
    else:
        rows, cols = grid_size

    # Get max dimensions
    max_h = max(img.shape[0] for img in images.values())
    max_w = max(img.shape[1] for img in images.values())

    # Resize all images to same size
    resized_images = []
    for label, img in images.items():
        # Convert grayscale to BGR
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        # Resize
        img_resized = cv2.resize(img, (max_w, max_h))

        # Add label
        cv2.putText(img_resized, label, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        resized_images.append(img_resized)

    # Create grid
    grid = np.zeros((rows * max_h, cols * max_w, 3), dtype=np.uint8)

    for i, img in enumerate(resized_images):
        row = i // cols
        col = i % cols
        grid[row * max_h:(row + 1) * max_h, col * max_w:(col + 1) * max_w] = img

    return grid

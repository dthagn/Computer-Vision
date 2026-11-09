"""
Image Enhancement Module for SmartScan
Cung cấp các thuật toán nâng cao chất lượng ảnh tài liệu
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any, List
from ..utils.config import (
    DENOISE_METHODS,
    CONTRAST_METHODS,
    THRESHOLD_METHODS,
    SHARPEN_METHODS,
    SHADOW_CORRECTION_METHODS,
    DEFAULT_ENHANCEMENT_CONFIG
)
from .preprocessing import validate_image


def apply_gaussian_denoise(
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
        kernel_size += 1

    if kernel_size < 3:
        kernel_size = 3

    return cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)


def apply_median_denoise(
    image: np.ndarray,
    kernel_size: int = 5
) -> np.ndarray:
    """
    Áp dụng Median Filter để giảm nhiễu dạng salt-and-pepper.

    Args:
        image: NumPy array (grayscale hoặc color)
        kernel_size: Kích thước kernel (phải là số lẻ)

    Returns:
        Denoised image
    """
    if kernel_size % 2 == 0:
        kernel_size += 1

    if kernel_size < 3:
        kernel_size = 3

    return cv2.medianBlur(image, kernel_size)


def apply_bilateral_denoise(
    image: np.ndarray,
    d: int = 9,
    sigma_color: float = 75,
    sigma_space: float = 75
) -> np.ndarray:
    """
    Áp dụng Bilateral Filter để giảm nhiễu trong khi giữ lại edge.

    Args:
        image: NumPy array (grayscale hoặc color)
        d: Đường kính vùng lân cận pixel
        sigma_color: Sigma cho không gian màu (giá trị lớn hơn = màu ảnh hưởng nhiều hơn)
        sigma_space: Sigma cho không gian tọa độ (giá trị lớn hơn = pixel xa ảnh hưởng nhiều hơn)

    Returns:
        Denoised image
    """
    return cv2.bilateralFilter(image, d, sigma_color, sigma_space)


def denoise_image(
    image: np.ndarray,
    method: str = 'bilateral',
    **params
) -> np.ndarray:
    """
    Giảm nhiễu ảnh theo phương pháp được chọn.

    Args:
        image: NumPy array (grayscale hoặc color)
        method: Phương pháp ('gaussian', 'median', 'bilateral', 'none')
        **params: Tham số cho từng phương pháp

    Returns:
        Denoised image
    """
    if method == 'none':
        return image.copy()

    if method not in DENOISE_METHODS:
        raise ValueError(f"Unknown denoise method: {method}. Available: {DENOISE_METHODS}")

    if method == 'gaussian':
        kernel_size = params.get('kernel_size', 5)
        sigma = params.get('sigma', 0)
        return apply_gaussian_denoise(image, kernel_size, sigma)

    elif method == 'median':
        kernel_size = params.get('kernel_size', 5)
        return apply_median_denoise(image, kernel_size)

    elif method == 'bilateral':
        d = params.get('kernel_size', 9)
        sigma_color = params.get('sigma_color', 75)
        sigma_space = params.get('sigma_space', 75)
        return apply_bilateral_denoise(image, d, sigma_color, sigma_space)

    return image.copy()


def apply_histogram_equalization(image: np.ndarray) -> np.ndarray:
    """
    Áp dụng Histogram Equalization để tăng tương phản.

    Args:
        image: NumPy array (grayscale)

    Returns:
        Enhanced image
    """
    if len(image.shape) == 3:
        # Nếu ảnh màu, áp dụng trên từng kênh rồi kết hợp
        channels = []
        for i in range(3):
            channels.append(cv2.equalizeHist(image[:, :, i]))
        return cv2.merge(channels)
    else:
        return cv2.equalizeHist(image)


def apply_clahe(
    image: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: Tuple[int, int] = (8, 8)
) -> np.ndarray:
    """
    Áp dụng CLAHE (Contrast Limited Adaptive Histogram Equalization).

    Args:
        image: NumPy array (grayscale hoặc color)
        clip_limit: Giới hạn clip cho contrast enhancement
        tile_grid_size: Kích thước lưới cho adaptive histogram

    Returns:
        Enhanced image
    """
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)

    if len(image.shape) == 3:
        # Chuyển sang Lab color space để chỉ enhance kênh L
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    else:
        return clahe.apply(image)


def enhance_contrast(
    image: np.ndarray,
    method: str = 'clahe',
    **params
) -> np.ndarray:
    """
    Tăng tương phản ảnh theo phương pháp được chọn.

    Args:
        image: NumPy array (grayscale hoặc color)
        method: Phương pháp ('histogram_eq', 'clahe', 'none')
        **params: Tham số cho từng phương pháp

    Returns:
        Enhanced image
    """
    if method == 'none':
        return image.copy()

    if method not in CONTRAST_METHODS:
        raise ValueError(f"Unknown contrast method: {method}. Available: {CONTRAST_METHODS}")

    if method == 'histogram_eq':
        return apply_histogram_equalization(image)

    elif method == 'clahe':
        clip_limit = params.get('clip_limit', 2.0)
        tile_grid_size = params.get('tile_grid_size', (8, 8))
        return apply_clahe(image, clip_limit, tile_grid_size)

    return image.copy()


def apply_global_threshold(
    image: np.ndarray,
    threshold: int = 127,
    max_value: int = 255
) -> np.ndarray:
    """
    Áp dụng Global Threshold.

    Args:
        image: NumPy array (grayscale)
        threshold: Ngưỡng threshold
        max_value: Giá trị tối đa cho pixel vượt ngưỡng

    Returns:
        Binary image
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    _, binary = cv2.threshold(image, threshold, max_value, cv2.THRESH_BINARY)
    return binary


def apply_otsu_threshold(
    image: np.ndarray,
    max_value: int = 255
) -> np.ndarray:
    """
    Áp dụng Otsu's Thresholding (tự động tính ngưỡng tối ưu).

    Args:
        image: NumPy array (grayscale)
        max_value: Giá trị tối đa cho pixel vượt ngưỡng

    Returns:
        Binary image
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    _, binary = cv2.threshold(image, 0, max_value, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def apply_adaptive_mean_threshold(
    image: np.ndarray,
    block_size: int = 11,
    C: int = 2
) -> np.ndarray:
    """
    Áp dụng Adaptive Threshold với Mean.

    Args:
        image: NumPy array (grayscale)
        block_size: Kích thước window (phải là số lẻ)
        C: Hằng số được trừ từ mean

    Returns:
        Binary image
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if block_size % 2 == 0:
        block_size += 1

    if block_size < 3:
        block_size = 3

    binary = cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY, block_size, C
    )
    return binary


def apply_adaptive_gaussian_threshold(
    image: np.ndarray,
    block_size: int = 11,
    C: int = 2
) -> np.ndarray:
    """
    Áp dụng Adaptive Threshold với Gaussian.

    Args:
        image: NumPy array (grayscale)
        block_size: Kích thước window (phải là số lẻ)
        C: Hằng số được trừ từ weighted mean

    Returns:
        Binary image
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if block_size % 2 == 0:
        block_size += 1

    if block_size < 3:
        block_size = 3

    binary = cv2.adaptiveThreshold(
        image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, block_size, C
    )
    return binary


def binarize_image(
    image: np.ndarray,
    method: str = 'adaptive_gaussian',
    **params
) -> np.ndarray:
    """
    Chuyển đổi ảnh sang binary theo phương pháp được chọn.

    Args:
        image: NumPy array (grayscale hoặc color)
        method: Phương pháp ('global', 'otsu', 'adaptive_mean', 'adaptive_gaussian', 'none')
        **params: Tham số cho từng phương pháp

    Returns:
        Binary image (grayscale) hoặc image gốc nếu method='none'
    """
    if method == 'none':
        return image.copy()

    if method not in THRESHOLD_METHODS:
        raise ValueError(f"Unknown threshold method: {method}. Available: {THRESHOLD_METHODS}")

    if method == 'global':
        threshold = params.get('threshold', 127)
        return apply_global_threshold(image, threshold)

    elif method == 'otsu':
        return apply_otsu_threshold(image)

    elif method == 'adaptive_mean':
        block_size = params.get('block_size', 11)
        C = params.get('C', 2)
        return apply_adaptive_mean_threshold(image, block_size, C)

    elif method == 'adaptive_gaussian':
        block_size = params.get('block_size', 11)
        C = params.get('C', 2)
        return apply_adaptive_gaussian_threshold(image, block_size, C)

    return image.copy()


def apply_unsharp_mask(
    image: np.ndarray,
    strength: float = 1.5,
    radius: int = 3
) -> np.ndarray:
    """
    Áp dụng Unsharp Mask để sharpening.

    Args:
        image: NumPy array (grayscale hoặc color)
        strength: Độ mạnh của sharpening
        radius: Kích thước kernel cho Gaussian blur

    Returns:
        Sharpened image
    """
    if radius % 2 == 0:
        radius += 1
    if radius < 3:
        radius = 3

    blurred = cv2.GaussianBlur(image, (radius, radius), 0)
    sharpened = cv2.addWeighted(image, 1.0 + strength, blurred, -strength, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def apply_kernel_sharpen(
    image: np.ndarray,
    kernel: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Áp dụng sharpening kernel.

    Args:
        image: NumPy array (grayscale hoặc color)
        kernel: Kernel sharpening (mặc định là kernel chuẩn)

    Returns:
        Sharpened image
    """
    if kernel is None:
        kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ], dtype=np.float32)

    sharpened = cv2.filter2D(image, -1, kernel)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def sharpen_image(
    image: np.ndarray,
    method: str = 'unsharp_mask',
    **params
) -> np.ndarray:
    """
    Sharpening ảnh theo phương pháp được chọn.

    Args:
        image: NumPy array (grayscale hoặc color)
        method: Phương pháp ('unsharp_mask', 'kernel', 'none')
        **params: Tham số cho từng phương pháp

    Returns:
        Sharpened image
    """
    if method == 'none':
        return image.copy()

    if method not in SHARPEN_METHODS:
        raise ValueError(f"Unknown sharpen method: {method}. Available: {SHARPEN_METHODS}")

    if method == 'unsharp_mask':
        strength = params.get('strength', 1.5)
        radius = params.get('radius', 3)
        return apply_unsharp_mask(image, strength, radius)

    elif method == 'kernel':
        kernel = params.get('kernel', None)
        return apply_kernel_sharpen(image, kernel)

    return image.copy()


def apply_morphological_shadow_correction(
    image: np.ndarray,
    kernel_size: int = 25,
    blur_sigma: int = 5
) -> np.ndarray:
    """
    Xử lý bóng đổ và ánh sáng không đồng đều bằng morphological operations.

    Phương pháp:
    1. Mở rộng (dilate) để tạo bản đồ background
    2. Blur bản đồ background
    3. Chia ảnh gốc cho background để normalize

    Args:
        image: NumPy array (grayscale hoặc color)
        kernel_size: Kích thước kernel cho morphological operation
        blur_sigma: Sigma cho Gaussian blur

    Returns:
        Image đã được correct ánh sáng
    """
    if len(image.shape) == 3:
        # Chuyển sang grayscale để tính background
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Morphological dilation để lấy background
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    background = cv2.dilate(gray, kernel)

    # Blur background để làm mượt
    background = cv2.GaussianBlur(background, (0, 0), blur_sigma)

    # Normalize: chia ảnh cho background, nhân với mean background
    background = background.astype(np.float32)
    gray_float = gray.astype(np.float32)

    # Tránh chia cho 0
    background[background == 0] = 1

    normalized = (gray_float / background) * np.mean(background)
    normalized = np.clip(normalized, 0, 255).astype(np.uint8)

    # Nếu ảnh màu, áp dụng normalized lên từng kênh
    if len(image.shape) == 3:
        # Tính ratio cho grayscale
        ratio = normalized.astype(np.float32) / (gray.astype(np.float32) + 1e-6)

        # Áp dụng ratio lên từng kênh
        result = image.astype(np.float32)
        for i in range(3):
            result[:, :, i] = result[:, :, i] * ratio

        result = np.clip(result, 0, 255).astype(np.uint8)
        return result
    else:
        return normalized


def correct_shadow(
    image: np.ndarray,
    method: str = 'morphological',
    **params
) -> np.ndarray:
    """
    Xử lý bóng đổ và ánh sáng không đồng đều.

    Args:
        image: NumPy array (grayscale hoặc color)
        method: Phương pháp ('morphological', 'none')
        **params: Tham số cho từng phương pháp

    Returns:
        Image đã được correct
    """
    if method == 'none':
        return image.copy()

    if method not in SHADOW_CORRECTION_METHODS:
        raise ValueError(f"Unknown shadow correction method: {method}. Available: {SHADOW_CORRECTION_METHODS}")

    if method == 'morphological':
        kernel_size = params.get('kernel_size', 25)
        blur_sigma = params.get('blur_sigma', 5)
        return apply_morphological_shadow_correction(image, kernel_size, blur_sigma)

    return image.copy()


def enhance_document(
    image: np.ndarray,
    denoise_method: str = 'bilateral',
    contrast_method: str = 'clahe',
    threshold_method: str = 'adaptive_gaussian',
    sharpen: bool = True,
    sharpen_method: str = 'unsharp_mask',
    shadow_correction: bool = False,
    shadow_correction_method: str = 'morphological',
    convert_to_grayscale: bool = False,
    denoise_params: Optional[Dict[str, Any]] = None,
    contrast_params: Optional[Dict[str, Any]] = None,
    threshold_params: Optional[Dict[str, Any]] = None,
    sharpen_params: Optional[Dict[str, Any]] = None,
    shadow_correction_params: Optional[Dict[str, Any]] = None,
    return_intermediate: bool = False
) -> Dict[str, Any]:
    """
    Nâng cao chất lượng ảnh tài liệu với các bước xử lý có thể cấu hình.

    Args:
        image: NumPy array (BGR, uint8)
        denoise_method: Phương pháp giảm nhiễu ('gaussian', 'median', 'bilateral', 'none')
        contrast_method: Phương pháp tăng tương phản ('histogram_eq', 'clahe', 'none')
        threshold_method: Phương pháp binarization ('global', 'otsu', 'adaptive_mean', 'adaptive_gaussian', 'none')
        sharpen: Có áp dụng sharpening không
        sharpen_method: Phương pháp sharpening ('unsharp_mask', 'kernel', 'none')
        shadow_correction: Có xử lý bóng đổ không
        shadow_correction_method: Phương pháp xử lý bóng đổ ('morphological', 'none')
        convert_to_grayscale: Có chuyển sang grayscale không (nếu False, giữ màu khi có thể)
        denoise_params: Tham số cho denoising
        contrast_params: Tham số cho contrast enhancement
        threshold_params: Tham số cho binarization
        sharpen_params: Tham số cho sharpening
        shadow_correction_params: Tham số cho shadow correction
        return_intermediate: Có trả về các ảnh trung gian không

    Returns:
        Dictionary:
            - 'success': bool - Xử lý thành công không
            - 'enhanced_image': np.ndarray or None - Ảnh đã được enhance
            - 'message': str - Thông báo kết quả
            - 'intermediate': Dict[str, np.ndarray] - Các ảnh trung gian (nếu return_intermediate=True)
    """
    # Validate ảnh
    is_valid, error_msg = validate_image(image)
    if not is_valid:
        return {
            'success': False,
            'enhanced_image': None,
            'message': f"Invalid image: {error_msg}",
            'intermediate': {}
        }

    # Khởi tạo tham số mặc định
    if denoise_params is None:
        denoise_params = {}
    if contrast_params is None:
        contrast_params = {}
    if threshold_params is None:
        threshold_params = {}
    if sharpen_params is None:
        sharpen_params = {}
    if shadow_correction_params is None:
        shadow_correction_params = {}

    # Copy ảnh gốc để không thay đổi
    current_image = image.copy()

    # Lưu các ảnh trung gian
    intermediate = {}
    if return_intermediate:
        intermediate['original'] = image.copy()

    # Bước 1: Shadow Correction (nếu được yêu cầu)
    if shadow_correction:
        try:
            current_image = correct_shadow(
                current_image,
                method=shadow_correction_method,
                **shadow_correction_params
            )
            if return_intermediate:
                intermediate['shadow_corrected'] = current_image.copy()
        except Exception as e:
            return {
                'success': False,
                'enhanced_image': None,
                'message': f"Shadow correction failed: {str(e)}",
                'intermediate': intermediate
            }

    # Bước 2: Denoising
    try:
        current_image = denoise_image(
            current_image,
            method=denoise_method,
            **denoise_params
        )
        if return_intermediate:
            intermediate['denoised'] = current_image.copy()
    except Exception as e:
        return {
            'success': False,
            'enhanced_image': None,
            'message': f"Denoising failed: {str(e)}",
            'intermediate': intermediate
        }

    # Bước 3: Contrast Enhancement
    try:
        current_image = enhance_contrast(
            current_image,
            method=contrast_method,
            **contrast_params
        )
        if return_intermediate:
            intermediate['contrast_enhanced'] = current_image.copy()
    except Exception as e:
        return {
            'success': False,
            'enhanced_image': None,
            'message': f"Contrast enhancement failed: {str(e)}",
            'intermediate': intermediate
        }

    # Bước 4: Sharpening (nếu được yêu cầu)
    if sharpen:
        try:
            current_image = sharpen_image(
                current_image,
                method=sharpen_method,
                **sharpen_params
            )
            if return_intermediate:
                intermediate['sharpened'] = current_image.copy()
        except Exception as e:
            return {
                'success': False,
                'enhanced_image': None,
                'message': f"Sharpening failed: {str(e)}",
                'intermediate': intermediate
            }

    # Bước 5: Binarization (nếu được yêu cầu hoặc convert_to_grayscale=True)
    # Lưu ảnh trước binarization nếu người dùng muốn giữ màu
    if return_intermediate and threshold_method != 'none':
        intermediate['before_threshold'] = current_image.copy()

    if threshold_method != 'none':
        try:
            current_image = binarize_image(
                current_image,
                method=threshold_method,
                **threshold_params
            )
            if return_intermediate:
                intermediate['thresholded'] = current_image.copy()
        except Exception as e:
            return {
                'success': False,
                'enhanced_image': None,
                'message': f"Binarization failed: {str(e)}",
                'intermediate': intermediate
            }
    elif convert_to_grayscale and len(current_image.shape) == 3:
        # Chuyển sang grayscale nếu người dùng yêu cầu nhưng không threshold
        current_image = cv2.cvtColor(current_image, cv2.COLOR_BGR2GRAY)
        if return_intermediate:
            intermediate['grayscale'] = current_image.copy()

    # Đảm bảo dtype và shape đúng
    if current_image.dtype != np.uint8:
        current_image = np.clip(current_image, 0, 255).astype(np.uint8)

    return {
        'success': True,
        'enhanced_image': current_image,
        'message': "Document enhanced successfully",
        'intermediate': intermediate
    }

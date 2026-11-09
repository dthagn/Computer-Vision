"""
Configuration Module for SmartScan Enhancement
Chứa các tham số mặc định cho các thuật toán nâng cao chất lượng ảnh
"""

import numpy as np

# Denoising Parameters
DENOISE_METHODS = ['gaussian', 'median', 'bilateral', 'none']

DEFAULT_GAUSSIAN_KERNEL = 5
DEFAULT_GAUSSIAN_SIGMA = 0

DEFAULT_MEDIAN_KERNEL = 5

DEFAULT_BILATERAL_D = 9
DEFAULT_BILATERAL_SIGMA_COLOR = 75
DEFAULT_BILATERAL_SIGMA_SPACE = 75

# Contrast Enhancement Parameters
CONTRAST_METHODS = ['histogram_eq', 'clahe', 'none']

DEFAULT_CLAHE_CLIP_LIMIT = 2.0
DEFAULT_CLAHE_TILE_SIZE = (8, 8)

# Binarization Parameters
THRESHOLD_METHODS = ['global', 'otsu', 'adaptive_mean', 'adaptive_gaussian', 'none']

DEFAULT_GLOBAL_THRESHOLD = 127

DEFAULT_ADAPTIVE_BLOCK_SIZE = 11
DEFAULT_ADAPTIVE_C = 2

# Sharpening Parameters
SHARPEN_METHODS = ['unsharp_mask', 'kernel', 'none']

DEFAULT_UNSHARP_STRENGTH = 1.5
DEFAULT_UNSHARP_RADIUS = 3

DEFAULT_SHARPEN_KERNEL = np.array([
    [0, -1, 0],
    [-1, 5, -1],
    [0, -1, 0]
], dtype=np.float32)

# Shadow/Uneven Illumination Correction Parameters
SHADOW_CORRECTION_METHODS = ['morphological', 'none']

DEFAULT_SHADOW_KERNEL_SIZE = 25
DEFAULT_SHADOW_BLUR_SIGMA = 5

# Default Enhancement Configuration
DEFAULT_ENHANCEMENT_CONFIG = {
    'denoise_method': 'bilateral',
    'denoise_params': {
        'kernel_size': DEFAULT_BILATERAL_D,
        'sigma_color': DEFAULT_BILATERAL_SIGMA_COLOR,
        'sigma_space': DEFAULT_BILATERAL_SIGMA_SPACE
    },
    'contrast_method': 'clahe',
    'contrast_params': {
        'clip_limit': DEFAULT_CLAHE_CLIP_LIMIT,
        'tile_grid_size': DEFAULT_CLAHE_TILE_SIZE
    },
    'threshold_method': 'adaptive_gaussian',
    'threshold_params': {
        'block_size': DEFAULT_ADAPTIVE_BLOCK_SIZE,
        'C': DEFAULT_ADAPTIVE_C
    },
    'sharpen': True,
    'sharpen_method': 'unsharp_mask',
    'sharpen_params': {
        'strength': DEFAULT_UNSHARP_STRENGTH,
        'radius': DEFAULT_UNSHARP_RADIUS
    },
    'shadow_correction': False,
    'shadow_correction_method': 'morphological',
    'shadow_correction_params': {
        'kernel_size': DEFAULT_SHADOW_KERNEL_SIZE,
        'blur_sigma': DEFAULT_SHADOW_BLUR_SIGMA
    },
    'convert_to_grayscale': False  # Giữ màu mặc định
}

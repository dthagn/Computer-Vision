"""
Constants and configuration
"""

# Image processing constants
MIN_DOCUMENT_AREA = 10000  # Minimum area for valid document (pixels)
MAX_DOCUMENT_AREA_RATIO = 0.95  # Max ratio of image area
CANNY_THRESHOLD1 = 50
CANNY_THRESHOLD2 = 150
BLUR_KERNEL_SIZE = 5

# Corner order
CORNER_ORDER = ["TL", "TR", "BR", "BL"]  # Top-Left, Top-Right, Bottom-Right, Bottom-Left

# Enhancement parameters
CONTRAST_ALPHA = 1.2  # Contrast factor
BRIGHTNESS_BETA = 10  # Brightness offset
DENOISE_H = 10  # Denoising strength
THRESHOLD_BINARIZATION = 127

# Supported formats
SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".bmp"]

"""
Image utility functions
"""

import cv2
import numpy as np


def rgb_to_bgr(image):
    """
    Convert RGB image to BGR format for OpenCV.
    
    Args:
        image: NumPy array (RGB, uint8)
        
    Returns:
        NumPy array (BGR, uint8)
    """
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)


def bgr_to_rgb(image):
    """
    Convert BGR image to RGB format for Streamlit.
    
    Args:
        image: NumPy array (BGR, uint8)
        
    Returns:
        NumPy array (RGB, uint8)
    """
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def validate_image(image):
    """
    Validate image format and dimensions.
    
    Args:
        image: NumPy array
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(image, np.ndarray):
        return False
    if len(image.shape) not in [2, 3]:
        return False
    if image.dtype != np.uint8:
        return False
    return True

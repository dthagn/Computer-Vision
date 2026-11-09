"""
Verify imports work correctly
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    import cv2
    print("✅ OpenCV imported successfully")
except Exception as e:
    print(f"❌ OpenCV import failed: {e}")

try:
    import numpy as np
    print("✅ NumPy imported successfully")
except Exception as e:
    print(f"❌ NumPy import failed: {e}")

try:
    from pipeline import process_document, get_default_enhancement_presets
    print("✅ Pipeline module imported successfully")
except Exception as e:
    print(f"❌ Pipeline import failed: {e}")

try:
    from image_loader import load_image_from_bytes, convert_bgr_to_rgb
    print("✅ Image loader module imported successfully")
except Exception as e:
    print(f"❌ Image loader import failed: {e}")

try:
    from utils import draw_corners_on_image, create_comparison_image
    print("✅ Utils module imported successfully")
except Exception as e:
    print(f"❌ Utils import failed: {e}")

try:
    from config import DEFAULT_ENHANCEMENT_CONFIG
    print("✅ Config module imported successfully")
except Exception as e:
    print(f"❌ Config import failed: {e}")

print("\nAll imports verified!")

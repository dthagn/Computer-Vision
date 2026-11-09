"""
Simple test script for pipeline without pytest
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import cv2
import numpy as np
from pipeline import process_document, get_default_enhancement_presets
from image_loader import load_image_from_bytes, convert_bgr_to_rgb, convert_rgb_to_bgr


def test_basic_pipeline():
    """Test basic pipeline"""
    print("Testing basic pipeline...")

    # Create test image
    image = np.ones((500, 700, 3), dtype=np.uint8) * 255
    cv2.rectangle(image, (50, 50), (650, 450), (0, 0, 0), 3)

    # Manual corners
    manual_corners = np.array([
        [50, 50],
        [650, 50],
        [650, 450],
        [50, 450]
    ], dtype=np.float32)

    # Process
    result = process_document(image, manual_corners=manual_corners)

    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")
    print(f"Processing time: {result['processing_time']:.2f}s")

    if result['success']:
        print(f"Original image shape: {result['original_image'].shape}")
        print(f"Scanned image shape: {result['scanned_image'].shape}")
        print(f"Enhanced image shape: {result['enhanced_image'].shape}")
        print("✅ Basic pipeline test PASSED")
    else:
        print("❌ Basic pipeline test FAILED")
        return False

    return True


def test_image_loader():
    """Test image loader"""
    print("\nTesting image loader...")

    # Create test image
    image = np.ones((100, 100, 3), dtype=np.uint8) * 255
    _, buffer = cv2.imencode('.jpg', image)
    bytes_data = buffer.tobytes()

    success, loaded_image, message = load_image_from_bytes(bytes_data)

    print(f"Success: {success}")
    print(f"Message: {message}")

    if success and loaded_image is not None:
        print(f"Loaded image shape: {loaded_image.shape}")
        print("✅ Image loader test PASSED")
    else:
        print("❌ Image loader test FAILED")
        return False

    return True


def test_color_conversion():
    """Test color conversion"""
    print("\nTesting color conversion...")

    original_rgb = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

    bgr = convert_rgb_to_bgr(original_rgb)
    back_to_rgb = convert_bgr_to_rgb(bgr)

    if np.array_equal(original_rgb, back_to_rgb):
        print("✅ Color conversion test PASSED")
        return True
    else:
        print("❌ Color conversion test FAILED")
        return False


def test_presets():
    """Test enhancement presets"""
    print("\nTesting enhancement presets...")

    presets = get_default_enhancement_presets()

    print(f"Number of presets: {len(presets)}")
    print(f"Preset names: {list(presets.keys())}")

    if len(presets) >= 4:
        print("✅ Presets test PASSED")
        return True
    else:
        print("❌ Presets test FAILED")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("SmartScan Pipeline Simple Test")
    print("=" * 50)

    all_passed = True

    all_passed &= test_basic_pipeline()
    all_passed &= test_image_loader()
    all_passed &= test_color_conversion()
    all_passed &= test_presets()

    print("\n" + "=" * 50)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 50)

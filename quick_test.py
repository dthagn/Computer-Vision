import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Testing imports...")

try:
    import cv2
    print("[OK] cv2")
except Exception as e:
    print(f"[FAIL] cv2: {e}")

try:
    import numpy as np
    print("[OK] numpy")
except Exception as e:
    print(f"[FAIL] numpy: {e}")

try:
    import preprocessing
    print("[OK] preprocessing")
except Exception as e:
    print(f"[FAIL] preprocessing: {e}")

try:
    import detection
    print("[OK] detection")
except Exception as e:
    print(f"[FAIL] detection: {e}")

try:
    import perspective
    print("[OK] perspective")
except Exception as e:
    print(f"[FAIL] perspective: {e}")

try:
    import enhancement
    print("[OK] enhancement")
except Exception as e:
    print(f"[FAIL] enhancement: {e}")

try:
    import config
    print("[OK] config")
except Exception as e:
    print(f"[FAIL] config: {e}")

try:
    import pipeline
    print("[OK] pipeline")
except Exception as e:
    print(f"[FAIL] pipeline: {e}")

try:
    import image_loader
    print("[OK] image_loader")
except Exception as e:
    print(f"[FAIL] image_loader: {e}")

try:
    import utils
    print("[OK] utils")
except Exception as e:
    print(f"[FAIL] utils: {e}")

print("\nTesting simple pipeline execution...")

try:
    import cv2
    import numpy as np
    from pipeline import process_document

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

    print(f"Pipeline success: {result['success']}")
    print(f"Pipeline message: {result['message']}")
    print(f"Processing time: {result['processing_time']:.2f}s")

    if result['success']:
        print("[OK] Pipeline execution test PASSED")
    else:
        print("[FAIL] Pipeline execution test FAILED")

except Exception as e:
    print(f"[FAIL] Pipeline execution error: {e}")
    import traceback
    traceback.print_exc()

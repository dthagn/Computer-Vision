import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

print("Testing imports with new structure...")

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
    from smartscan.core.preprocessing import validate_image
    print("[OK] smartscan.core.preprocessing")
except Exception as e:
    print(f"[FAIL] smartscan.core.preprocessing: {e}")

try:
    from smartscan.core.detection import detect_document
    print("[OK] smartscan.core.detection")
except Exception as e:
    print(f"[FAIL] smartscan.core.detection: {e}")

try:
    from smartscan.core.perspective import correct_perspective
    print("[OK] smartscan.core.perspective")
except Exception as e:
    print(f"[FAIL] smartscan.core.perspective: {e}")

try:
    from smartscan.core.enhancement import enhance_document
    print("[OK] smartscan.core.enhancement")
except Exception as e:
    print(f"[FAIL] smartscan.core.enhancement: {e}")

try:
    from smartscan.core.pipeline import process_document
    print("[OK] smartscan.core.pipeline")
except Exception as e:
    print(f"[FAIL] smartscan.core.pipeline: {e}")

try:
    from smartscan.utils.config import DEFAULT_ENHANCEMENT_CONFIG
    print("[OK] smartscan.utils.config")
except Exception as e:
    print(f"[FAIL] smartscan.utils.config: {e}")

try:
    from smartscan.utils.image_loader import load_image_from_bytes
    print("[OK] smartscan.utils.image_loader")
except Exception as e:
    print(f"[FAIL] smartscan.utils.image_loader: {e}")

try:
    from smartscan.utils.utils import draw_corners_on_image
    print("[OK] smartscan.utils.utils")
except Exception as e:
    print(f"[FAIL] smartscan.utils.utils: {e}")

print("\nTesting simple pipeline execution...")

try:
    import cv2
    import numpy as np
    from smartscan.core.pipeline import process_document

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

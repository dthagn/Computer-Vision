"""
Example Usage of SmartScan Modules
Demo cách sử dụng preprocessing, detection, và perspective modules
"""

import cv2
import numpy as np
from src.detection import detect_document
from src.perspective import correct_perspective
from src.preprocessing import preprocess_for_detection


def example_1_basic_pipeline():
    """Ví dụ pipeline cơ bản"""
    print("=== Example 1: Basic Pipeline ===")

    # Tạo ảnh tổng hợp với hình chữ nhật trắng
    image = np.zeros((500, 500, 3), dtype=np.uint8)
    cv2.rectangle(image, (50, 50), (450, 450), (255, 255, 255), -1)
    cv2.putText(image, "DOCUMENT", (150, 250),
                cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)

    # 1. Phát hiện tài liệu
    print("Step 1: Detecting document...")
    detection_result = detect_document(image, debug=True)

    if detection_result['success']:
        print(f"[OK] Detection successful!")
        print(f"  Confidence: {detection_result['confidence']:.2f}")
        print(f"  Corners:\n{detection_result['corners']}")
    else:
        print(f"[FAIL] Detection failed: {detection_result['message']}")
        return

    # 2. Hiệu chỉnh phối cảnh
    print("\nStep 2: Correcting perspective...")
    perspective_result = correct_perspective(image, detection_result['corners'])

    if perspective_result['success']:
        print(f"[OK] Perspective correction successful!")
        print(f"  Output size: {perspective_result['output_size']}")
    else:
        print(f"[FAIL] Perspective correction failed: {perspective_result['message']}")
        return

    # Lưu kết quả
    cv2.imwrite('example1_corrected.jpg', perspective_result['corrected_image'])
    print("\n[OK] Result saved to example1_corrected.jpg")


def example_2_manual_corners():
    """Ví dụ sử dụng manual corners"""
    print("\n=== Example 2: Manual Corners ===")

    # Tạo ảnh
    image = np.zeros((500, 500, 3), dtype=np.uint8)
    cv2.rectangle(image, (100, 100), (400, 400), (255, 255, 255), -1)

    # Manual corners (có thể đến từ UI click)
    manual_corners = np.array([
        [100, 100],  # TL
        [400, 100],  # TR
        [400, 400],  # BR
        [100, 400]   # BL
    ], dtype=np.float32)

    print("Using manual corners:")
    print(manual_corners)

    # Phát hiện với manual corners
    detection_result = detect_document(image, manual_corners=manual_corners)

    if detection_result['success']:
        print(f"[OK] Manual corners accepted")
        print(f"  Ordered corners:\n{detection_result['corners']}")

        # Perspective correction
        perspective_result = correct_perspective(image, detection_result['corners'])

        if perspective_result['success']:
            cv2.imwrite('example2_corrected.jpg', perspective_result['corrected_image'])
            print("[OK] Result saved to example2_corrected.jpg")
    else:
        print(f"[FAIL] Manual corners rejected: {detection_result['message']}")


def example_3_preprocessing_only():
    """Ví dụ chỉ sử dụng preprocessing"""
    print("\n=== Example 3: Preprocessing Only ===")

    # Tạo ảnh
    image = np.random.randint(0, 256, (1000, 1500, 3), dtype=np.uint8)
    cv2.rectangle(image, (100, 100), (1400, 900), (255, 255, 255), -1)

    print(f"Original size: {image.shape}")

    # Preprocess
    result = preprocess_for_detection(
        image,
        max_width=800,
        max_height=600
    )

    print(f"[OK] Preprocessing completed")
    print(f"  Scale factor: {result['scale']:.3f}")
    print(f"  Original size: {result['original_size']}")
    print(f"  Resized size: {result['resized_size']}")
    print(f"  Edge map shape: {result['processed'].shape}")

    # Lưu edge map
    cv2.imwrite('example3_edges.jpg', result['processed'])
    print("[OK] Edge map saved to example3_edges.jpg")


def example_4_debug_mode():
    """Ví dụ sử dụng debug mode"""
    print("\n=== Example 4: Debug Mode ===")

    # Tạo ảnh
    image = np.zeros((500, 500, 3), dtype=np.uint8)
    cv2.rectangle(image, (50, 50), (450, 450), (255, 255, 255), -1)

    # Detect với debug mode
    detection_result = detect_document(image, debug=True)

    if detection_result['success'] and detection_result['debug_image'] is not None:
        cv2.imwrite('example4_debug.jpg', detection_result['debug_image'])
        print("[OK] Debug image saved to example4_debug.jpg")
        print("  Debug image shows: original image + edges + detected contour with labels")


def example_5_perspective_with_padding():
    """Ví dụ perspective correction với padding"""
    print("\n=== Example 5: Perspective with Padding ===")

    # Tạo ảnh
    image = np.zeros((500, 500, 3), dtype=np.uint8)
    cv2.rectangle(image, (100, 100), (400, 400), (255, 255, 255), -1)

    corners = np.array([[100, 100], [400, 100], [400, 400], [100, 400]], dtype=np.float32)

    # Perspective correction thường
    result_normal = correct_perspective(image, corners)
    print(f"Normal output size: {result_normal['output_size']}")

    # Perspective correction với padding
    from src.perspective import apply_perspective_with_padding
    result_padded = apply_perspective_with_padding(image, corners, padding_ratio=0.1)
    print(f"Padded output size: {result_padded['output_size']}")

    if result_normal['success'] and result_padded['success']:
        cv2.imwrite('example5_normal.jpg', result_normal['corrected_image'])
        cv2.imwrite('example5_padded.jpg', result_padded['corrected_image'])
        print("[OK] Results saved to example5_normal.jpg and example5_padded.jpg")


def example_6_error_handling():
    """Ví dụ error handling"""
    print("\n=== Example 6: Error Handling ===")

    # Test 1: Invalid image
    print("Test 1: Invalid image (None)")
    result = detect_document(None)
    print(f"  Success: {result['success']}")
    print(f"  Message: {result['message']}")

    # Test 2: Invalid manual corners
    print("\nTest 2: Invalid manual corners (only 2 points)")
    image = np.zeros((500, 500, 3), dtype=np.uint8)
    bad_corners = np.array([[100, 100], [400, 400]], dtype=np.float32)
    result = detect_document(image, manual_corners=bad_corners)
    print(f"  Success: {result['success']}")
    print(f"  Message: {result['message']}")

    # Test 3: Self-intersecting corners
    print("\nTest 3: Self-intersecting corners (bow-tie)")
    bad_corners = np.array([[0, 0], [100, 100], [0, 100], [100, 0]], dtype=np.float32)
    result = detect_document(image, manual_corners=bad_corners)
    print(f"  Success: {result['success']}")
    print(f"  Message: {result['message']}")

    # Test 4: Invalid perspective corners
    print("\nTest 4: Invalid perspective corners (out of bounds)")
    corners = np.array([[50, 50], [550, 50], [550, 550], [50, 550]], dtype=np.float32)
    result = correct_perspective(image, corners)
    print(f"  Success: {result['success']}")
    print(f"  Message: {result['message']}")


if __name__ == '__main__':
    print("SmartScan Module Usage Examples\n")

    # Chạy các ví dụ
    example_1_basic_pipeline()
    example_2_manual_corners()
    example_3_preprocessing_only()
    example_4_debug_mode()
    example_5_perspective_with_padding()
    example_6_error_handling()

    print("\n=== All Examples Completed ===")
    print("Check the generated .jpg files to see results")

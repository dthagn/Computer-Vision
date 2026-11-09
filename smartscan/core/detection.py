"""
Document Detection Module for SmartScan
Phát hiện vùng tài liệu trong ảnh sử dụng Computer Vision cổ điển
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any, List
from .preprocessing import (
    preprocess_for_detection,
    map_coordinates_to_original,
    validate_image
)


def compute_convexity_score(contour: np.ndarray, hull: np.ndarray) -> float:
    """
    Tính điểm số dựa trên độ lồi của contour.

    Args:
        contour: Contour từ findContours
        hull: Convex hull của contour

    Returns:
        Score từ 0 đến 1 (1 = hoàn toàn lồi)
    """
    contour_area = cv2.contourArea(contour)
    hull_area = cv2.contourArea(hull)

    if hull_area == 0:
        return 0.0

    return contour_area / hull_area


def compute_quadrilateral_score(approx: np.ndarray, image_shape: Tuple[int, int]) -> float:
    """
    Đánh giá độ hợp lý của tứ giác dựa trên hình học.

    Args:
        approx: 4 điểm contour đã được approximate (shape (4, 2) hoặc (4, 1, 2))
        image_shape: Kích thước ảnh (h, w)

    Returns:
        Score từ 0 đến 1 (cao hơn = hợp lý hơn)
    """
    # Reshape nếu cần
    if len(approx.shape) == 3:
        approx = approx.reshape(4, 2)

    h, w = image_shape
    score = 0.0

    # 1. Kiểm tra diện tích tương đối (không quá nhỏ, không quá lớn)
    area = cv2.contourArea(approx.reshape(-1, 1, 2))
    image_area = h * w
    area_ratio = area / image_area

    # Tài liệu nên chiếm 10% - 90% diện tích ảnh
    if 0.1 <= area_ratio <= 0.9:
        score += 0.3
    elif 0.05 <= area_ratio < 0.1 or 0.9 < area_ratio <= 0.95:
        score += 0.15

    # 2. Kiểm tra các góc (tứ giác nên có góc gần 90 độ)
    angles = []
    for i in range(4):
        p1 = approx[i]
        p2 = approx[(i + 1) % 4]
        p3 = approx[(i + 2) % 4]

        # Vector
        v1 = p1 - p2
        v2 = p3 - p2

        # Tính góc bằng dot product
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            continue

        cos_angle = np.dot(v1, v2) / (norm_v1 * norm_v2)
        angle = np.arccos(np.clip(cos_angle, -1, 1))
        angle_deg = np.degrees(angle)
        angles.append(angle_deg)

    # Tài liệu thường có góc 60-120 độ
    if len(angles) == 4:
        good_angles = sum(1 for a in angles if 60 <= a <= 120)
        if good_angles == 4:
            score += 0.4
        elif good_angles >= 3:
            score += 0.2

    # 3. Kiểm tra tỷ lệ cạnh (tài liệu thường có tỷ lệ hợp lý)
    edges = []
    for i in range(4):
        p1 = approx[i]
        p2 = approx[(i + 1) % 4]
        edge_length = np.linalg.norm(p1 - p2)
        edges.append(edge_length)

    edges.sort()
    aspect_ratio = edges[3] / (edges[0] + 1e-6)

    # Tỷ lệ cạnh không nên quá cực đoan (không quá 10:1)
    if aspect_ratio <= 5:
        score += 0.3
    elif aspect_ratio <= 10:
        score += 0.15

    return min(score, 1.0)


def order_corners(corners: np.ndarray) -> np.ndarray:
    """
    Sắp xếp 4 góc theo thứ tự: TL, TR, BR, BL (Top-Left, Top-Right, Bottom-Right, Bottom-Left).

    Args:
        corners: NumPy array shape (4, 2)

    Returns:
        NumPy array shape (4, 2) với thứ tự TL, TR, BR, BL
    """
    # Tính tổng tọa độ x+y
    sum_coords = np.sum(corners, axis=1)

    # TL: có tổng nhỏ nhất
    tl_idx = np.argmin(sum_coords)
    tl = corners[tl_idx]

    # BR: có tổng lớn nhất
    br_idx = np.argmax(sum_coords)
    br = corners[br_idx]

    # Tìm diff = x - y
    diff_coords = (corners[:, 0] - corners[:, 1]).reshape(-1, 1)

    # TR: có diff lớn nhất (x lớn, y nhỏ)
    tr_idx = np.argmax(diff_coords)
    tr = corners[tr_idx]

    # BL: có diff nhỏ nhất (x nhỏ, y lớn)
    bl_idx = np.argmin(diff_coords)
    bl = corners[bl_idx]

    # Kiểm tra xem có trùng lặp index không
    indices = [tl_idx, tr_idx, br_idx, bl_idx]
    if len(set(indices)) != 4:
        # Fallback: sắp xếp theo góc từ tâm
        center = np.mean(corners, axis=0)
        angles = np.arctan2(corners[:, 1] - center[1], corners[:, 0] - center[0])
        sorted_indices = np.argsort(angles)
        # TL sẽ là góc nhỏ nhất (góc trên bên trái)
        corners = corners[sorted_indices]
        return corners

    return np.array([tl, tr, br, bl], dtype=np.float32)


def check_self_intersection(corners: np.ndarray) -> bool:
    """
    Kiểm tra xem tứ giác có tự giao nhau không.

    Args:
        corners: NumPy array shape (4, 2) với thứ tự TL, TR, BR, BL

    Returns:
        True nếu tự giao nhau, False nếu không
    """
    tl, tr, br, bl = corners

    # Kiểm tra giao nhau giữa các cạnh không kề nhau
    # Cạnh 1: TL -> TR
    # Cạnh 3: BL -> BR
    def segments_intersect(p1, p2, p3, p4):
        """Kiểm tra xem đoạn p1-p2 có giao đoạn p3-p4 không"""
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

    # Kiểm tra TL-TR với BL-BR
    if segments_intersect(tl, tr, bl, br):
        return True

    # Kiểm tra TR-BR với TL-BL
    if segments_intersect(tr, br, tl, bl):
        return True

    return False


def find_document_contour(
    edges: np.ndarray,
    min_area_ratio: float = 0.05,
    max_area_ratio: float = 0.95
) -> Optional[np.ndarray]:
    """
    Tìm contour phù hợp nhất cho tài liệu từ edge map.

    Args:
        edges: Binary edge map
        min_area_ratio: Tỷ lệ diện tích tối thiểu so với ảnh
        max_area_ratio: Tỷ lệ diện tích tối đa so với ảnh

    Returns:
        Contour tốt nhất (shape (N, 1, 2)) hoặc None
    """
    h, w = edges.shape
    image_area = h * w
    min_area = image_area * min_area_ratio
    max_area = image_area * max_area_ratio

    # Tìm contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    best_contour = None
    best_score = 0.0

    for contour in contours:
        # Bỏ qua contour quá nhỏ
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue

        # Approximate contour thành đa giác
        perimeter = cv2.arcLength(contour, True)
        epsilon = 0.02 * perimeter  # 2% tolerance
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Cần ít nhất 4 điểm
        if len(approx) < 4:
            continue

        # Nếu có hơn 4 điểm, dùng convex hull
        if len(approx) > 4:
            hull = cv2.convexHull(approx)
            perimeter = cv2.arcLength(hull, True)
            epsilon = 0.02 * perimeter
            approx = cv2.approxPolyDP(hull, epsilon, True)

            if len(approx) != 4:
                continue

        # Tính convexity score
        hull = cv2.convexHull(contour)
        convexity_score = compute_convexity_score(contour, hull)

        # Tính quadrilateral score
        quad_score = compute_quadrilateral_score(approx, (h, w))

        # Tổng hợp score
        total_score = 0.6 * convexity_score + 0.4 * quad_score

        if total_score > best_score:
            best_score = total_score
            best_contour = approx.reshape(4, 2)

    return best_contour


def detect_document(
    image: np.ndarray,
    manual_corners: Optional[np.ndarray] = None,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Phát hiện 4 góc của tài liệu trong ảnh.

    Args:
        image: NumPy array (BGR, uint8)
        manual_corners: Optional - 4 góc thủ công shape (4, 2) nếu phát hiện tự động thất bại
        debug: Có tạo debug image không

    Returns:
        Dictionary:
            - 'success': bool - Phát hiện thành công không
            - 'corners': np.ndarray or None - 4 góc shape (4, 2), thứ tự TL, TR, BR, BL
            - 'debug_image': np.ndarray or None - Debug image nếu debug=True
            - 'message': str - Thông báo kết quả
            - 'confidence': float - Độ tin cậy (0-1)
    """
    # Validate ảnh
    is_valid, error_msg = validate_image(image)
    if not is_valid:
        return {
            'success': False,
            'corners': None,
            'debug_image': None,
            'message': f"Invalid image: {error_msg}",
            'confidence': 0.0
        }

    # Nếu có manual corners, validate và sử dụng
    if manual_corners is not None:
        manual_corners = np.array(manual_corners, dtype=np.float32)
        if manual_corners.shape != (4, 2):
            return {
                'success': False,
                'corners': None,
                'debug_image': None,
                'message': "Manual corners must have shape (4, 2)",
                'confidence': 0.0
            }

        # Sắp xếp corners
        ordered_corners = order_corners(manual_corners)

        # Kiểm tra tự giao nhau
        if check_self_intersection(ordered_corners):
            return {
                'success': False,
                'corners': None,
                'debug_image': None,
                'message': "Manual corners form self-intersecting quadrilateral",
                'confidence': 0.0
            }

        # Tạo debug image nếu cần
        debug_image = None
        if debug:
            debug_image = image.copy()
            corners = ordered_corners.astype(np.int32)
            cv2.polylines(debug_image, [corners], True, (0, 255, 0), 3)

            # Vẽ nhãn các góc
            labels = ['TL', 'TR', 'BR', 'BL']
            for i, (corner, label) in enumerate(zip(corners, labels)):
                cv2.putText(debug_image, label, tuple(corner),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

        return {
            'success': True,
            'corners': ordered_corners,
            'debug_image': debug_image,
            'message': "Using manual corners",
            'confidence': 1.0
        }

    # Tiền xử lý với nhiều bộ tham số Canny
    canny_params = [
        (50, 150),   # Default
        (30, 100),   # More sensitive
        (70, 200),   # Less sensitive
        (20, 80),    # Very sensitive
        (100, 250)   # Very conservative
    ]

    best_result = None
    best_confidence = 0.0

    for canny_low, canny_high in canny_params:
        try:
            # Tiền xử lý
            result = preprocess_for_detection(
                image,
                max_width=1280,
                max_height=720,
                canny_low=canny_low,
                canny_high=canny_high
            )

            edges = result['processed']
            scale = result['scale']

            # Tìm contour
            contour = find_document_contour(edges)

            if contour is not None:
                # Map về tọa độ gốc
                original_contour = map_coordinates_to_original(contour, scale)

                # Sắp xếp corners
                ordered_corners = order_corners(original_contour)

                # Kiểm tra tự giao nhau
                if check_self_intersection(ordered_corners):
                    continue

                # Tính confidence score
                convexity_score = compute_convexity_score(
                    contour.reshape(-1, 1, 2),
                    cv2.convexHull(contour.reshape(-1, 1, 2))
                )
                quad_score = compute_quadrilateral_score(contour, edges.shape)
                confidence = 0.6 * convexity_score + 0.4 * quad_score

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_result = {
                        'corners': ordered_corners,
                        'confidence': confidence,
                        'edges': edges,
                        'scale': scale
                    }

        except Exception as e:
            # Bỏ qua bộ tham số này nếu lỗi
            continue

    # Kiểm tra ngưỡng confidence tối thiểu
    if best_result is None or best_confidence < 0.3:
        return {
            'success': False,
            'corners': None,
            'debug_image': None,
            'message': "Could not detect document with sufficient confidence",
            'confidence': best_confidence if best_result else 0.0
        }

    # Tạo debug image nếu cần
    debug_image = None
    if debug:
        debug_image = image.copy()
        corners = best_result['corners'].astype(np.int32)
        cv2.polylines(debug_image, [corners], True, (0, 255, 0), 3)

        # Vẽ nhãn các góc
        labels = ['TL', 'TR', 'BR', 'BL']
        for i, (corner, label) in enumerate(zip(corners, labels)):
            cv2.putText(debug_image, label, tuple(corner),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

    return {
        'success': True,
        'corners': best_result['corners'],
        'debug_image': debug_image,
        'message': f"Document detected with confidence {best_confidence:.2f}",
        'confidence': best_confidence
    }

"""
Document Detection Module for SmartScan
Phát hiện vùng tài liệu trong ảnh sử dụng Computer Vision cổ điển
"""

import cv2
import numpy as np
from itertools import combinations
from typing import Tuple, Optional, Dict, Any, List
from .preprocessing import (
    preprocess_for_detection,
    map_coordinates_to_original,
    validate_image
)
from .geometry import order_corners, check_self_intersection


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


DETECTION_EPSILON_FACTORS = (0.01, 0.02, 0.03, 0.04, 0.05, 0.08)
DETECTION_MAX_CONTOURS = 4
DETECTION_MAX_HULL_VERTICES = 16
DETECTION_COMBINATION_KEEP = 12
COMBINATION_SEARCH_SCORE_THRESHOLD = 0.72
EDGE_DISTANCE_SAMPLE_STEP = 8.0


def _polygon_area(points: np.ndarray) -> float:
    """Tính diện tích đa giác (4,2) bằng contourArea của OpenCV."""
    return abs(cv2.contourArea(points.reshape(-1, 1, 2).astype(np.float32)))


def _edge_distance_map(edges: np.ndarray) -> np.ndarray:
    """Tạo bản đồ khoảng cách tới pixel edge gần nhất."""
    return cv2.distanceTransform(255 - edges, cv2.DIST_L2, 3)


def _sample_edge_distance(
    points: np.ndarray,
    distance_map: np.ndarray,
    sample_step: float = EDGE_DISTANCE_SAMPLE_STEP
) -> float:
    """
    Đo khoảng cách trung bình từ các cạnh tứ giác tới edge map.

    Điểm càng nằm sát contour gốc thì giá trị càng nhỏ. Hàm này giúp phân biệt
    tứ giác trùng biên tài liệu với tứ giác chỉ bao được một phần contour bị
    nhiễu/protrusion.
    """
    distances = []
    h, w = distance_map.shape

    for i in range(4):
        p1 = points[i].astype(np.float32)
        p2 = points[(i + 1) % 4].astype(np.float32)
        length = float(np.linalg.norm(p2 - p1))
        samples = max(2, int(np.ceil(length / sample_step)) + 1)

        for t in np.linspace(0.0, 1.0, samples):
            point = p1 * (1.0 - t) + p2 * t
            x = int(round(float(point[0])))
            y = int(round(float(point[1])))
            if 0 <= y < h and 0 <= x < w:
                distances.append(float(distance_map[y, x]))

    if not distances:
        return 999.0
    return float(np.mean(distances))


def _make_candidate(
    points: np.ndarray,
    image_shape: Tuple[int, int],
    min_area_ratio: float,
    max_area_ratio: float,
    distance_map: np.ndarray
) -> Optional[Dict[str, Any]]:
    """Chuẩn hóa một candidate tứ giác và tính confidence."""
    points = np.asarray(points, dtype=np.float32).reshape(4, 2)
    ordered = order_corners(points)

    if check_self_intersection(ordered):
        return None

    h, w = image_shape
    image_area = h * w
    area_ratio = _polygon_area(ordered) / image_area if image_area > 0 else 0.0

    if area_ratio < min_area_ratio or area_ratio > max_area_ratio:
        return None

    quad_score = compute_quadrilateral_score(ordered, image_shape)
    edge_distance = _sample_edge_distance(ordered, distance_map)
    edge_score = 1.0 / (1.0 + edge_distance / 4.0)
    score = min(1.0, 0.6 * quad_score + 0.4 * edge_score)

    return {
        'points': ordered.astype(np.float32),
        'score': float(score),
        'quad_score': float(quad_score),
        'edge_score': float(edge_score),
        'edge_distance': float(edge_distance),
        'area_ratio': float(area_ratio)
    }


def _candidate_key(candidate: Dict[str, Any]) -> Tuple[Tuple[int, int], ...]:
    """Tạo key duy nhất để loại candidate trùng nhau."""
    rounded = np.rint(candidate['points']).astype(int)
    return tuple((int(x), int(y)) for x, y in rounded)


def _approx_candidates_from_source(
    source: np.ndarray,
    image_shape: Tuple[int, int],
    min_area_ratio: float,
    max_area_ratio: float,
    distance_map: np.ndarray
) -> List[Dict[str, Any]]:
    """Sinh candidate từ approxPolyDP với nhiều mức epsilon."""
    candidates = []
    perimeter = cv2.arcLength(source, True)
    if perimeter <= 0:
        return candidates

    for factor in DETECTION_EPSILON_FACTORS:
        approx = cv2.approxPolyDP(source, factor * perimeter, True)
        if len(approx) != 4:
            continue
        candidate = _make_candidate(
            approx.reshape(4, 2),
            image_shape,
            min_area_ratio,
            max_area_ratio,
            distance_map
        )
        if candidate is not None:
            candidates.append(candidate)

    return candidates


def _combination_candidates(
    hull: np.ndarray,
    image_shape: Tuple[int, int],
    min_area_ratio: float,
    max_area_ratio: float,
    distance_map: np.ndarray,
    keep: int = DETECTION_COMBINATION_KEEP
) -> List[Dict[str, Any]]:
    """
    Fallback cho contour phức tạp: chọn 4 đỉnh từ convex hull.

    Chỉ chạy khi số đỉnh hull đủ nhỏ để brute-force an toàn. Candidate được
    sàng sơ bộ bằng hình học trước, sau đó mới đo edge support cho top-K.
    """
    perimeter = cv2.arcLength(hull, True)
    if perimeter <= 0:
        return []

    vertices = []
    for factor in (0.005, 0.01, 0.02, 0.03, 0.05):
        approx = cv2.approxPolyDP(hull, factor * perimeter, True).reshape(-1, 2)
        for point in approx:
            point = point.astype(np.float32)
            if not any(np.linalg.norm(point - existing) < 1.5 for existing in vertices):
                vertices.append(point)
        if len(vertices) > DETECTION_MAX_HULL_VERTICES:
            return []

    if len(vertices) < 4:
        return []

    h, w = image_shape
    image_area = h * w
    pre_scored = []

    for indices in combinations(range(len(vertices)), 4):
        points = np.array([vertices[i] for i in indices], dtype=np.float32)
        ordered = order_corners(points)
        if check_self_intersection(ordered):
            continue

        area_ratio = _polygon_area(ordered) / image_area if image_area > 0 else 0.0
        if area_ratio < min_area_ratio or area_ratio > max_area_ratio:
            continue

        quad_score = compute_quadrilateral_score(ordered, image_shape)
        area_fit = 1.0 if 0.15 <= area_ratio <= 0.85 else 0.5
        pre_score = 0.75 * quad_score + 0.25 * area_fit
        pre_scored.append((pre_score, ordered))

    pre_scored.sort(key=lambda item: item[0], reverse=True)

    candidates = []
    for _, points in pre_scored[:keep]:
        candidate = _make_candidate(
            points,
            image_shape,
            min_area_ratio,
            max_area_ratio,
            distance_map
        )
        if candidate is not None:
            candidates.append(candidate)

    return candidates


def find_document_candidates(
    edges: np.ndarray,
    min_area_ratio: float = 0.05,
    max_area_ratio: float = 0.95
) -> List[Dict[str, Any]]:
    """
    Tìm các candidate tứ giác tài liệu từ edge map, sắp xếp theo confidence.

    Args:
        edges: Binary edge map
        min_area_ratio: Tỷ lệ diện tích tối thiểu so với ảnh
        max_area_ratio: Tỷ lệ diện tích tối đa so với ảnh

    Returns:
        List candidate dict, mỗi phần tử gồm 'points' (4,2), 'score',
        'quad_score', 'edge_score', 'edge_distance', 'area_ratio'.
    """
    if edges is None or len(edges.shape) != 2:
        return []

    h, w = edges.shape
    image_area = h * w
    min_area = image_area * min_area_ratio
    max_area = image_area * max_area_ratio
    distance_map = _edge_distance_map(edges)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []

    viable_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if min_area <= area <= max_area:
            viable_contours.append(contour)

    viable_contours.sort(key=cv2.contourArea, reverse=True)
    viable_contours = viable_contours[:DETECTION_MAX_CONTOURS]
    if not viable_contours:
        return []

    candidates_by_key = {}

    def add_candidate(candidate: Optional[Dict[str, Any]]) -> None:
        if candidate is None:
            return
        key = _candidate_key(candidate)
        existing = candidates_by_key.get(key)
        if existing is None or candidate['score'] > existing['score']:
            candidates_by_key[key] = candidate

    contour_sources = []
    for contour in viable_contours:
        hull = cv2.convexHull(contour)
        sources = [contour, hull]

        for source in sources:
            for candidate in _approx_candidates_from_source(
                source,
                (h, w),
                min_area_ratio,
                max_area_ratio,
                distance_map
            ):
                add_candidate(candidate)

        # Minimum-area rectangle là fallback cho tài liệu bị xoay nhưng vẫn
        # có bốn cạnh thẳng; edge support sẽ loại candidate ôm quá nhiều noise.
        try:
            box_points = cv2.boxPoints(cv2.minAreaRect(hull)).astype(np.float32)
            add_candidate(_make_candidate(
                box_points,
                (h, w),
                min_area_ratio,
                max_area_ratio,
                distance_map
            ))
        except cv2.error:
            pass

        contour_sources.append((contour, hull))

    best_score = max((candidate['score'] for candidate in candidates_by_key.values()), default=0.0)
    if best_score < COMBINATION_SEARCH_SCORE_THRESHOLD:
        for contour, hull in contour_sources[:2]:
            for candidate in _combination_candidates(
                hull,
                (h, w),
                min_area_ratio,
                max_area_ratio,
                distance_map
            ):
                add_candidate(candidate)

    candidates = sorted(candidates_by_key.values(), key=lambda item: item['score'], reverse=True)
    return candidates[:20]


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
        Contour tốt nhất (shape (4, 2), thứ tự TL/TR/BR/BL) hoặc None
    """
    candidates = find_document_candidates(edges, min_area_ratio, max_area_ratio)
    if not candidates:
        return None
    return candidates[0]['points'].astype(np.float32)


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

            # Tìm candidate tứ giác từ edge map
            candidates = find_document_candidates(edges)

            if candidates:
                candidate = candidates[0]

                # Map về tọa độ gốc
                original_contour = map_coordinates_to_original(candidate['points'], scale)
                ordered_corners = order_corners(original_contour)

                # Kiểm tra tự giao nhau
                if check_self_intersection(ordered_corners):
                    continue

                confidence = float(np.clip(candidate['score'], 0.0, 1.0))

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

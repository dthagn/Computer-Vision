"""
Geometry helpers for SmartScan corner handling.

Các hàm này là nguồn chuẩn duy nhất cho việc sắp xếp và kiểm tra tính hợp lệ
hình học của bốn góc tài liệu. Detection và perspective cùng sử dụng module này
để tránh hai implementation khác nhau theo thời gian.
"""

import numpy as np
from typing import Tuple


def order_corners(corners: np.ndarray) -> np.ndarray:
    """
    Sắp xếp 4 góc theo thứ tự: TL, TR, BR, BL.

    Args:
        corners: NumPy array shape (4, 2)

    Returns:
        NumPy array shape (4, 2) với thứ tự TL, TR, BR, BL
    """
    sum_coords = np.sum(corners, axis=1)

    tl_idx = np.argmin(sum_coords)
    tl = corners[tl_idx]

    br_idx = np.argmax(sum_coords)
    br = corners[br_idx]

    diff_coords = (corners[:, 0] - corners[:, 1]).reshape(-1, 1)

    tr_idx = np.argmax(diff_coords)
    tr = corners[tr_idx]

    bl_idx = np.argmin(diff_coords)
    bl = corners[bl_idx]

    indices = [tl_idx, tr_idx, br_idx, bl_idx]
    if len(set(indices)) != 4:
        center = np.mean(corners, axis=0)
        angles = np.arctan2(corners[:, 1] - center[1], corners[:, 0] - center[0])
        sorted_indices = np.argsort(angles)
        return corners[sorted_indices]

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

    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    def segments_intersect(p1, p2, p3, p4):
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

    if segments_intersect(tl, tr, bl, br):
        return True

    if segments_intersect(tr, br, tl, bl):
        return True

    return False


def signed_area(corners: np.ndarray) -> float:
    """
    Tính diện tích đại số của tứ giác theo thứ tự điểm hiện tại.

    Quy ước TL -> TR -> BR -> BL trong hệ tọa độ ảnh cho giá trị dương.
    Giá trị âm thường nghĩa là thứ tự điểm bị đảo chiều.
    """
    points = np.asarray(corners, dtype=np.float32).reshape(4, 2)
    x = points[:, 0]
    y = points[:, 1]
    x_next = np.roll(x, -1)
    y_next = np.roll(y, -1)
    return float(0.5 * np.sum(x * y_next - x_next * y))

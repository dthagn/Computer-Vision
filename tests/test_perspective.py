"""
Unit tests for perspective module
"""

import pytest
import numpy as np
import cv2
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from smartscan.core.perspective import (
    calculate_output_dimensions,
    validate_corners,
    check_self_intersection,
    compute_homography_matrix,
    correct_perspective,
    apply_perspective_with_padding
)


class TestCalculateOutputDimensions:
    """Test cases cho calculate_output_dimensions"""

    def test_square_document(self):
        """Test tài liệu hình vuông"""
        corners = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)
        width, height = calculate_output_dimensions(corners)

        assert width == 100
        assert height == 100

    def test_rectangular_document(self):
        """Test tài liệu hình chữ nhật"""
        corners = np.array([[0, 0], [200, 0], [200, 100], [0, 100]], dtype=np.float32)
        width, height = calculate_output_dimensions(corners)

        assert width == 200
        assert height == 100

    def test_irregular_document(self):
        """Test tài liệu có cạnh không đều"""
        corners = np.array([[0, 0], [200, 10], [195, 105], [5, 100]], dtype=np.float32)
        width, height = calculate_output_dimensions(corners)

        # Width nên là max của top và bottom edge
        # Height nên là max của left và right edge
        assert width > 0
        assert height > 0
        assert width > height  # Hợp lý với corners trên

    def test_small_document(self):
        """Test tài liệu nhỏ"""
        corners = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float32)
        width, height = calculate_output_dimensions(corners)

        assert width == 10
        assert height == 10


class TestValidateCorners:
    """Test cases cho validate_corners"""

    def test_valid_corners(self):
        """Test corners hợp lệ"""
        corners = np.array([[50, 50], [450, 50], [450, 450], [50, 450]], dtype=np.float32)
        image_shape = (500, 500)

        is_valid, msg = validate_corners(corners, image_shape)

        assert is_valid is True
        assert msg == ""

    def test_none_corners(self):
        """Test corners = None"""
        image_shape = (500, 500)

        is_valid, msg = validate_corners(None, image_shape)

        assert is_valid is False
        assert "None" in msg

    def test_not_numpy_array(self):
        """Test corners không phải numpy array"""
        corners = [[50, 50], [450, 50], [450, 450], [50, 450]]
        image_shape = (500, 500)

        is_valid, msg = validate_corners(corners, image_shape)

        assert is_valid is False
        assert "numpy array" in msg

    def test_wrong_shape(self):
        """Test sai shape"""
        corners = np.array([[50, 50], [450, 50]], dtype=np.float32)
        image_shape = (500, 500)

        is_valid, msg = validate_corners(corners, image_shape)

        assert is_valid is False
        assert "shape" in msg

    def test_wrong_dtype(self):
        """Test sai dtype"""
        corners = np.array([[50, 50], [450, 50], [450, 450], [50, 450]], dtype=np.str_)
        image_shape = (500, 500)

        is_valid, msg = validate_corners(corners, image_shape)

        assert is_valid is False
        assert "numeric type" in msg

    def test_corners_out_of_bounds_x(self):
        """Test tọa độ x vượt quá kích thước ảnh"""
        corners = np.array([[50, 50], [550, 50], [550, 450], [50, 450]], dtype=np.float32)
        image_shape = (500, 500)

        is_valid, msg = validate_corners(corners, image_shape)

        assert is_valid is False
        assert "out of image bounds" in msg

    def test_corners_out_of_bounds_y(self):
        """Test tọa độ y vượt quá kích thước ảnh"""
        corners = np.array([[50, 50], [450, 50], [450, 550], [50, 550]], dtype=np.float32)
        image_shape = (500, 500)

        is_valid, msg = validate_corners(corners, image_shape)

        assert is_valid is False
        assert "out of image bounds" in msg

    def test_negative_coordinates(self):
        """Test tọa độ âm"""
        corners = np.array([[-50, 50], [450, 50], [450, 450], [50, 450]], dtype=np.float32)
        image_shape = (500, 500)

        is_valid, msg = validate_corners(corners, image_shape)

        assert is_valid is False
        assert "out of image bounds" in msg

    def test_duplicate_corners(self):
        """Test corners trùng lặp"""
        corners = np.array([[50, 50], [50, 50], [450, 450], [50, 450]], dtype=np.float32)
        image_shape = (500, 500)

        is_valid, msg = validate_corners(corners, image_shape)

        assert is_valid is False
        assert "duplicate" in msg

    def test_collinear_corners(self):
        """Test corners collinear"""
        corners = np.array([[0, 0], [100, 0], [200, 0], [300, 0]], dtype=np.float32)
        image_shape = (500, 500)

        is_valid, msg = validate_corners(corners, image_shape)

        assert is_valid is False
        assert "collinear" in msg


class TestCheckSelfIntersection:
    """Test cases cho check_self_intersection"""

    def test_no_intersection(self):
        """Test tứ giác không tự giao nhau"""
        corners = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)
        result = check_self_intersection(corners)

        assert result is False

    def test_self_intersecting_bowtie(self):
        """Test tứ giác tự giao nhau (bow-tie)"""
        corners = np.array([[0, 0], [100, 100], [0, 100], [100, 0]], dtype=np.float32)
        result = check_self_intersection(corners)

        assert result is True

    def test_normal_quadrilateral(self):
        """Test tứ giác bình thường"""
        corners = np.array([[10, 10], [90, 10], [95, 95], [5, 90]], dtype=np.float32)
        result = check_self_intersection(corners)

        assert result is False


class TestComputeHomographyMatrix:
    """Test cases cho compute_homography_matrix"""

    def test_compute_homography(self):
        """Test tính ma trận homography"""
        src = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)
        dst = np.array([[0, 0], [200, 0], [200, 200], [0, 200]], dtype=np.float32)

        matrix = compute_homography_matrix(src, dst)

        assert matrix.shape == (3, 3)
        # OpenCV trả về float64, không phải float32
        assert matrix.dtype in [np.float32, np.float64]

    def test_homography_scaling(self):
        """Test homography cho scaling"""
        src = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.float32)
        dst = np.array([[0, 0], [200, 0], [200, 200], [0, 200]], dtype=np.float32)

        matrix = compute_homography_matrix(src, dst)

        # Kiểm tra scaling factor
        assert matrix[0, 0] == pytest.approx(2.0, rel=0.1)


class TestCorrectPerspective:
    """Test cases cho correct_perspective"""

    def test_correct_perspective_valid(self):
        """Test hiệu chỉnh phối cảnh hợp lệ"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        corners = np.array([[50, 50], [450, 50], [450, 450], [50, 450]], dtype=np.float32)

        result = correct_perspective(image, corners)

        assert result['success'] is True
        assert result['corrected_image'] is not None
        assert result['homography_matrix'] is not None
        assert result['output_size'] is not None
        assert result['corrected_image'].dtype == np.uint8

    def test_correct_perspective_invalid_image(self):
        """Test hiệu chỉnh với ảnh không hợp lệ"""
        corners = np.array([[50, 50], [450, 50], [450, 450], [50, 450]], dtype=np.float32)

        result = correct_perspective(None, corners)

        assert result['success'] is False
        assert result['corrected_image'] is None
        assert "Invalid image" in result['message']

    def test_correct_perspective_invalid_corners(self):
        """Test hiệu chỉnh với corners không hợp lệ"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        corners = np.array([[50, 50], [450, 50]], dtype=np.float32)  # Chỉ 2 điểm

        result = correct_perspective(image, corners)

        assert result['success'] is False
        assert result['corrected_image'] is None
        assert "Invalid corners" in result['message']

    def test_correct_perspective_self_intersecting(self):
        """Test hiệu chỉnh với corners tự giao nhau"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        corners = np.array([[0, 0], [100, 100], [0, 100], [100, 0]], dtype=np.float32)

        result = correct_perspective(image, corners)

        assert result['success'] is False
        assert "self-intersecting" in result['message']

    def test_correct_perspective_custom_output_size(self):
        """Test hiệu chỉnh với kích thước đầu ra tùy chỉnh"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        corners = np.array([[50, 50], [450, 50], [450, 450], [50, 450]], dtype=np.float32)
        output_size = (800, 600)

        result = correct_perspective(image, corners, output_size=output_size)

        assert result['success'] is True
        assert result['output_size'] == output_size
        assert result['corrected_image'].shape == (600, 800, 3)

    def test_correct_perspective_output_dimensions(self):
        """Test kích thước đầu ra được tính tự động"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        corners = np.array([[50, 50], [450, 50], [450, 450], [50, 450]], dtype=np.float32)

        result = correct_perspective(image, corners)

        assert result['success'] is True
        # Kích thước nên xấp xỉ khoảng 400x400
        assert result['output_size'][0] > 350
        assert result['output_size'][1] > 350

    def test_correct_perspective_no_distortion(self):
        """Test không làm biến dạng nội dung quá nhiều"""
        # Tạo ảnh với pattern
        image = np.zeros((500, 500, 3), dtype=np.uint8)
        cv2.rectangle(image, (100, 100), (400, 400), (255, 255, 255), 5)

        corners = np.array([[50, 50], [450, 50], [450, 450], [50, 450]], dtype=np.float32)
        result = correct_perspective(image, corners)

        assert result['success'] is True
        # Ảnh đầu ra nên có nội dung
        assert np.sum(result['corrected_image']) > 0

    def test_correct_perspective_color_image(self):
        """Test hiệu chỉnh ảnh màu"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        corners = np.array([[50, 50], [450, 50], [450, 450], [50, 450]], dtype=np.float32)

        result = correct_perspective(image, corners)

        assert result['success'] is True
        assert len(result['corrected_image'].shape) == 3
        assert result['corrected_image'].shape[2] == 3

    def test_correct_perspective_white_background(self):
        """Test nền trắng cho vùng ngoài transformed region"""
        # Tạo ảnh với vùng màu trắng ở giữa, nền đen
        image = np.zeros((500, 500, 3), dtype=np.uint8)
        cv2.rectangle(image, (100, 100), (400, 400), (255, 255, 255), -1)

        corners = np.array([[100, 100], [400, 100], [400, 400], [100, 400]], dtype=np.float32)

        result = correct_perspective(image, corners)

        assert result['success'] is True
        # Kiểm tra vùng transform có nội dung (không phải toàn đen)
        assert np.sum(result['corrected_image']) > 0


class TestApplyPerspectiveWithPadding:
    """Test cases cho apply_perspective_with_padding"""

    def test_perspective_with_padding(self):
        """Test hiệu chỉnh với padding"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        corners = np.array([[50, 50], [450, 50], [450, 450], [50, 450]], dtype=np.float32)

        result = apply_perspective_with_padding(image, corners, padding_ratio=0.1)

        assert result['success'] is True
        assert result['corrected_image'] is not None
        assert result['output_size'] is not None

    def test_perspective_with_padding_larger_output(self):
        """Test output với padding lớn hơn không có padding"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        corners = np.array([[50, 50], [450, 50], [450, 450], [50, 450]], dtype=np.float32)

        result_no_pad = correct_perspective(image, corners)
        result_with_pad = apply_perspective_with_padding(image, corners, padding_ratio=0.1)

        assert result_with_pad['output_size'][0] > result_no_pad['output_size'][0]
        assert result_with_pad['output_size'][1] > result_no_pad['output_size'][1]

    def test_perspective_with_padding_invalid_image(self):
        """Test padding với ảnh không hợp lệ"""
        corners = np.array([[50, 50], [450, 50], [450, 450], [50, 450]], dtype=np.float32)

        result = apply_perspective_with_padding(None, corners)

        assert result['success'] is False
        assert "Invalid image" in result['message']

    def test_perspective_with_padding_invalid_corners(self):
        """Test padding với corners không hợp lệ"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        corners = np.array([[50, 50], [450, 50]], dtype=np.float32)

        result = apply_perspective_with_padding(image, corners)

        assert result['success'] is False
        assert "Invalid corners" in result['message']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

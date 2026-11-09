"""
Unit tests for preprocessing module
"""

import pytest
import numpy as np
import cv2
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from smartscan.core.preprocessing import (
    validate_image,
    resize_with_aspect_ratio,
    convert_to_grayscale,
    apply_gaussian_blur,
    apply_canny_edge_detection,
    apply_morphology,
    preprocess_for_detection,
    map_coordinates_to_original,
    create_debug_image
)


class TestValidateImage:
    """Test cases cho validate_image"""

    def test_valid_bgr_image(self):
        """Test ảnh BGR hợp lệ"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        is_valid, msg = validate_image(image)
        assert is_valid is True
        assert msg == ""

    def test_valid_grayscale_image(self):
        """Test ảnh grayscale hợp lệ"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        is_valid, msg = validate_image(image)
        assert is_valid is True
        assert msg == ""

    def test_none_image(self):
        """Test ảnh None"""
        is_valid, msg = validate_image(None)
        assert is_valid is False
        assert "None" in msg

    def test_not_numpy_array(self):
        """Test không phải numpy array"""
        is_valid, msg = validate_image([1, 2, 3])
        assert is_valid is False
        assert "numpy array" in msg

    def test_wrong_dimensions(self):
        """Test sai số chiều"""
        image = np.random.randint(0, 256, (100,), dtype=np.uint8)
        is_valid, msg = validate_image(image)
        assert is_valid is False
        assert "dimensions" in msg

    def test_wrong_dtype(self):
        """Test sai dtype"""
        image = np.random.rand(100, 100, 3).astype(np.float32)
        is_valid, msg = validate_image(image)
        assert is_valid is False
        assert "uint8" in msg

    def test_empty_image(self):
        """Test ảnh rỗng"""
        image = np.array([], dtype=np.uint8)
        is_valid, msg = validate_image(image)
        assert is_valid is False
        # Ảnh rỗng có shape (0,) nên sẽ bị lỗi về số chiều
        assert "dimensions" in msg or "empty" in msg

    def test_too_small_image(self):
        """Test ảnh quá nhỏ"""
        image = np.random.randint(0, 256, (5, 5, 3), dtype=np.uint8)
        is_valid, msg = validate_image(image)
        assert is_valid is False
        assert "too small" in msg


class TestResizeWithAspectRatio:
    """Test cases cho resize_with_aspect_ratio"""

    def test_resize_larger_image(self):
        """Test resize ảnh lớn hơn max dimensions"""
        image = np.random.randint(0, 256, (2000, 3000, 3), dtype=np.uint8)
        resized, scale_x, scale_y = resize_with_aspect_ratio(image, max_width=1000, max_height=1000)

        assert resized.shape[0] <= 1000
        assert resized.shape[1] <= 1000
        assert scale_x == scale_y  # Giữ tỷ lệ
        assert scale_x < 1.0  # Scale down

    def test_resize_smaller_image(self):
        """Test resize ảnh nhỏ hơn max dimensions (không zoom up)"""
        image = np.random.randint(0, 256, (100, 200, 3), dtype=np.uint8)
        resized, scale_x, scale_y = resize_with_aspect_ratio(image, max_width=1000, max_height=1000)

        assert resized.shape == image.shape
        assert scale_x == 1.0
        assert scale_y == 1.0

    def test_resize_grayscale(self):
        """Test resize ảnh grayscale"""
        image = np.random.randint(0, 256, (1000, 1500), dtype=np.uint8)
        resized, scale_x, scale_y = resize_with_aspect_ratio(image, max_width=500, max_height=500)

        assert len(resized.shape) == 2
        assert scale_x == scale_y

    def test_aspect_ratio_preserved(self):
        """Test tỷ lệ khung hình được giữ nguyên"""
        image = np.random.randint(0, 256, (1000, 2000, 3), dtype=np.uint8)
        original_ratio = image.shape[1] / image.shape[0]

        resized, _, _ = resize_with_aspect_ratio(image, max_width=500, max_height=500)
        new_ratio = resized.shape[1] / resized.shape[0]

        assert abs(original_ratio - new_ratio) < 0.01


class TestConvertToGrayscale:
    """Test cases cho convert_to_grayscale"""

    def test_bgr_to_grayscale(self):
        """Test chuyển BGR sang grayscale"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        gray = convert_to_grayscale(image)

        assert len(gray.shape) == 2
        assert gray.shape == (100, 100)

    def test_already_grayscale(self):
        """Test ảnh đã là grayscale"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        gray = convert_to_grayscale(image)

        assert np.array_equal(image, gray)


class TestApplyGaussianBlur:
    """Test cases cho apply_gaussian_blur"""

    def test_blur_color_image(self):
        """Test blur ảnh màu"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        blurred = apply_gaussian_blur(image, kernel_size=5)

        assert blurred.shape == image.shape
        assert not np.array_equal(image, blurred)  # Đã bị blur

    def test_blur_grayscale(self):
        """Test blur ảnh grayscale"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        blurred = apply_gaussian_blur(image, kernel_size=5)

        assert blurred.shape == image.shape

    def test_even_kernel_size(self):
        """Test kernel size chẵn được chuyển thành lẻ"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        blurred = apply_gaussian_blur(image, kernel_size=4)

        assert blurred.shape == image.shape

    def test_small_kernel_size(self):
        """Test kernel size nhỏ được đưa về 3"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        blurred = apply_gaussian_blur(image, kernel_size=1)

        assert blurred.shape == image.shape


class TestApplyCannyEdgeDetection:
    """Test cases cho apply_canny_edge_detection"""

    def test_canny_grayscale(self):
        """Test Canny trên grayscale"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        edges = apply_canny_edge_detection(image, threshold1=50, threshold2=150)

        assert edges.shape == image.shape
        assert edges.dtype == np.uint8

    def test_canny_color_auto_convert(self):
        """Test Canny tự động chuyển color sang grayscale"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        edges = apply_canny_edge_detection(image, threshold1=50, threshold2=150)

        assert len(edges.shape) == 2
        assert edges.shape == (100, 100)

    def test_canny_binary_output(self):
        """Test output là binary"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        edges = apply_canny_edge_detection(image, threshold1=50, threshold2=150)

        unique_values = np.unique(edges)
        assert len(unique_values) <= 2  # Chỉ có 0 và 255


class TestApplyMorphology:
    """Test cases cho apply_morphology"""

    def test_morphology_erode(self):
        """Test morphological erode"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_morphology(image, operation='erode', kernel_size=5)

        assert result.shape == image.shape

    def test_morphology_dilate(self):
        """Test morphological dilate"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_morphology(image, operation='dilate', kernel_size=5)

        assert result.shape == image.shape

    def test_morphology_open(self):
        """Test morphological open"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_morphology(image, operation='open', kernel_size=5)

        assert result.shape == image.shape

    def test_morphology_close(self):
        """Test morphological close"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_morphology(image, operation='close', kernel_size=5)

        assert result.shape == image.shape

    def test_invalid_operation(self):
        """Test operation không hợp lệ"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        with pytest.raises(ValueError):
            apply_morphology(image, operation='invalid', kernel_size=5)


class TestPreprocessForDetection:
    """Test cases cho preprocess_for_detection"""

    def test_preprocess_valid_image(self):
        """Test tiền xử lý ảnh hợp lệ"""
        image = np.random.randint(0, 256, (1000, 1500, 3), dtype=np.uint8)
        result = preprocess_for_detection(image)

        assert 'processed' in result
        assert 'scale' in result
        assert 'gray' in result
        assert 'blurred' in result
        assert 'original_size' in result
        assert 'resized_size' in result

        assert result['processed'].dtype == np.uint8
        assert 0 < result['scale'] <= 1.0

    def test_preprocess_invalid_image(self):
        """Test tiền xử lý ảnh không hợp lệ"""
        with pytest.raises(ValueError):
            preprocess_for_detection(None)

    def test_preprocess_small_image(self):
        """Test tiền xử lý ảnh nhỏ"""
        image = np.random.randint(0, 256, (500, 600, 3), dtype=np.uint8)
        result = preprocess_for_detection(image)

        assert result['scale'] == 1.0  # Không resize

    def test_preprocess_large_image(self):
        """Test tiền xử lý ảnh lớn"""
        image = np.random.randint(0, 256, (2000, 3000, 3), dtype=np.uint8)
        result = preprocess_for_detection(image)

        assert result['scale'] < 1.0  # Đã resize


class TestMapCoordinatesToOriginal:
    """Test cases cho map_coordinates_to_original"""

    def test_map_coordinates(self):
        """Test ánh xạ tọa độ"""
        coordinates = np.array([[100, 100], [200, 200]], dtype=np.float32)
        scale = 0.5

        original = map_coordinates_to_original(coordinates, scale)

        assert original.shape == coordinates.shape
        assert np.allclose(original, coordinates / scale)

    def test_map_zero_scale(self):
        """Test scale = 0 gây lỗi"""
        coordinates = np.array([[100, 100]], dtype=np.float32)
        with pytest.raises(ValueError):
            map_coordinates_to_original(coordinates, 0.0)


class TestCreateDebugImage:
    """Test cases cho create_debug_image"""

    def test_create_debug_image_basic(self):
        """Test tạo debug image cơ bản"""
        original = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        edges = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

        debug = create_debug_image(original, edges)

        assert debug.shape[0] == original.shape[0]
        assert debug.shape[2] == 3  # BGR

    def test_create_debug_image_with_contours(self):
        """Test tạo debug image với contours"""
        original = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        edges = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        contours = [np.array([[[10, 10]], [[90, 10]], [[90, 90]], [[10, 90]]], dtype=np.int32)]

        debug = create_debug_image(original, edges, contours)

        assert debug.shape[0] == original.shape[0]
        assert debug.shape[2] == 3

    def test_create_debug_image_resize_edges(self):
        """Test resize edges về kích thước gốc"""
        original = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        edges = np.random.randint(0, 256, (50, 50), dtype=np.uint8)

        debug = create_debug_image(original, edges)

        assert debug.shape[0] == original.shape[0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

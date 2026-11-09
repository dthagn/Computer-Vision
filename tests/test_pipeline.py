"""
Integration Tests for SmartScan Pipeline
Test toàn bộ pipeline: detection → perspective → enhancement
"""

import pytest
import cv2
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from smartscan.core.pipeline import (
    process_document,
    process_document_with_fallback,
    update_enhancement,
    get_default_enhancement_presets,
    validate_and_load_image
)
from smartscan.utils.image_loader import (
    load_image_from_bytes,
    convert_rgb_to_bgr,
    convert_bgr_to_rgb
)
from smartscan.utils.config import DEFAULT_ENHANCEMENT_CONFIG


class TestPipelineBasic:
    """Test cơ bản cho pipeline"""

    def test_process_document_with_valid_image(self):
        """Test pipeline với ảnh hợp lệ"""
        # Tạo ảnh test đơn giản (trắng nền đen chữ)
        image = np.ones((500, 700, 3), dtype=np.uint8) * 255
        cv2.rectangle(image, (50, 50), (650, 450), (0, 0, 0), 3)

        result = process_document(image, debug=False)

        assert result is not None
        assert 'success' in result
        assert 'original_image' in result
        assert 'processing_time' in result
        assert result['processing_time'] > 0

    def test_process_document_with_invalid_image(self):
        """Test pipeline với ảnh không hợp lệ"""
        image = np.array([], dtype=np.uint8)

        result = process_document(image)

        assert result['success'] == False
        assert result['original_image'] is None
        assert 'Invalid image' in result['message']

    def test_process_document_with_none_image(self):
        """Test pipeline với None"""
        result = process_document(None)

        assert result['success'] == False
        assert result['original_image'] is None

    def test_process_document_with_manual_corners(self):
        """Test pipeline với manual corners"""
        image = np.ones((500, 700, 3), dtype=np.uint8) * 255
        manual_corners = np.array([
            [100, 100],
            [600, 100],
            [600, 400],
            [100, 400]
        ], dtype=np.float32)

        result = process_document(image, manual_corners=manual_corners)

        assert result['success'] == True
        assert result['detected_corners'] is not None
        assert result['scanned_image'] is not None

    def test_process_document_with_invalid_manual_corners(self):
        """Test pipeline với manual corners không hợp lệ"""
        image = np.ones((500, 700, 3), dtype=np.uint8) * 255
        manual_corners = np.array([
            [100, 100],
            [100, 100],  # Duplicate
            [600, 400],
            [100, 400]
        ], dtype=np.float32)

        result = process_document(image, manual_corners=manual_corners)

        assert result['success'] == False

    def test_process_document_with_padding(self):
        """Test pipeline với padding"""
        image = np.ones((500, 700, 3), dtype=np.uint8) * 255
        manual_corners = np.array([
            [100, 100],
            [600, 100],
            [600, 400],
            [100, 400]
        ], dtype=np.float32)

        result = process_document(image, manual_corners=manual_corners, use_padding=True)

        assert result['success'] == True
        assert result['scanned_image'] is not None

    def test_process_document_without_padding(self):
        """Test pipeline không có padding"""
        image = np.ones((500, 700, 3), dtype=np.uint8) * 255
        manual_corners = np.array([
            [100, 100],
            [600, 100],
            [600, 400],
            [100, 400]
        ], dtype=np.float32)

        result = process_document(image, manual_corners=manual_corners, use_padding=False)

        assert result['success'] == True
        assert result['scanned_image'] is not None

    def test_process_document_with_debug(self):
        """Test pipeline với debug mode"""
        image = np.ones((500, 700, 3), dtype=np.uint8) * 255
        manual_corners = np.array([
            [100, 100],
            [600, 100],
            [600, 400],
            [100, 400]
        ], dtype=np.float32)

        result = process_document(image, manual_corners=manual_corners, debug=True)

        assert result['success'] == True
        assert 'debug_images' in result
        assert isinstance(result['debug_images'], dict)


class TestPipelineWithFallback:
    """Test pipeline với fallback mechanism"""

    def test_process_document_with_fallback_success(self):
        """Test fallback khi detection thành công"""
        image = np.ones((500, 700, 3), dtype=np.uint8) * 255
        manual_corners = np.array([
            [100, 100],
            [600, 100],
            [600, 400],
            [100, 400]
        ], dtype=np.float32)

        result = process_document_with_fallback(image, manual_corners=manual_corners)

        assert result['success'] == True
        assert result['needs_manual_corners'] == False

    def test_process_document_with_fallback_needs_manual(self):
        """Test fallback khi detection thất bại"""
        # Tạo ảnh quá đơn giản để detection thất bại
        image = np.ones((100, 100, 3), dtype=np.uint8) * 255

        result = process_document_with_fallback(image)

        # Có thể thành công hoặc thất bại tùy vào thuật toán
        assert 'needs_manual_corners' in result
        assert 'original_image' in result


class TestUpdateEnhancement:
    """Test cập nhật enhancement"""

    def test_update_enhancement_valid(self):
        """Test update enhancement với ảnh hợp lệ"""
        # Tạo ảnh test
        scanned_image = np.ones((500, 700, 3), dtype=np.uint8) * 200

        config = DEFAULT_ENHANCEMENT_CONFIG.copy()
        result = update_enhancement(scanned_image, config)

        assert result['success'] == True
        assert result['enhanced_image'] is not None
        assert result['processing_time'] > 0

    def test_update_enhancement_with_different_config(self):
        """Test update enhancement với config khác"""
        scanned_image = np.ones((500, 700, 3), dtype=np.uint8) * 200

        config = {
            'denoise_method': 'none',
            'contrast_method': 'none',
            'threshold_method': 'none',
            'sharpen': False,
            'sharpen_method': 'none',
            'shadow_correction': False,
            'shadow_correction_method': 'none',
            'convert_to_grayscale': False
        }

        result = update_enhancement(scanned_image, config)

        assert result['success'] == True
        assert result['enhanced_image'] is not None

    def test_update_enhancement_invalid_image(self):
        """Test update enhancement với ảnh không hợp lệ"""
        invalid_image = np.array([], dtype=np.uint8)

        config = DEFAULT_ENHANCEMENT_CONFIG.copy()
        result = update_enhancement(invalid_image, config)

        assert result['success'] == False
        assert result['enhanced_image'] is None


class TestEnhancementPresets:
    """Test enhancement presets"""

    def test_get_default_enhancement_presets(self):
        """Test lấy presets"""
        presets = get_default_enhancement_presets()

        assert isinstance(presets, dict)
        assert 'default' in presets
        assert 'bw_document' in presets
        assert 'color_document' in presets
        assert 'light_enhancement' in presets

    def test_preset_structure(self):
        """Test cấu trúc preset"""
        presets = get_default_enhancement_presets()

        for preset_name, config in presets.items():
            assert isinstance(config, dict)
            assert 'denoise_method' in config
            assert 'contrast_method' in config
            assert 'threshold_method' in config
            assert 'sharpen' in config
            assert 'shadow_correction' in config
            assert 'convert_to_grayscale' in config

    def test_bw_document_preset(self):
        """Test preset bw_document"""
        presets = get_default_enhancement_presets()
        bw_config = presets['bw_document']

        assert bw_config['convert_to_grayscale'] == True
        assert bw_config['threshold_method'] != 'none'

    def test_color_document_preset(self):
        """Test preset color_document"""
        presets = get_default_enhancement_presets()
        color_config = presets['color_document']

        assert color_config['convert_to_grayscale'] == False
        assert color_config['threshold_method'] == 'none'


class TestImageLoader:
    """Test image loader"""

    def test_load_image_from_bytes_valid(self):
        """Test load ảnh từ bytes hợp lệ"""
        # Tạo ảnh JPG bytes
        image = np.ones((100, 100, 3), dtype=np.uint8) * 255
        _, buffer = cv2.imencode('.jpg', image)
        bytes_data = buffer.tobytes()

        success, loaded_image, message = load_image_from_bytes(bytes_data)

        assert success == True
        assert loaded_image is not None
        assert loaded_image.shape == (100, 100, 3)

    def test_load_image_from_bytes_invalid(self):
        """Test load ảnh từ bytes không hợp lệ"""
        invalid_bytes = b"invalid image data"

        success, loaded_image, message = load_image_from_bytes(invalid_bytes)

        assert success == False
        assert loaded_image is None

    def test_convert_rgb_to_bgr(self):
        """Test convert RGB to BGR"""
        rgb_image = np.array([[[255, 0, 0]]], dtype=np.uint8)  # Red in RGB
        bgr_image = convert_rgb_to_bgr(rgb_image)

        assert bgr_image.shape == rgb_image.shape
        assert not np.array_equal(rgb_image, bgr_image)

    def test_convert_bgr_to_rgb(self):
        """Test convert BGR to RGB"""
        bgr_image = np.array([[[0, 0, 255]]], dtype=np.uint8)  # Red in BGR
        rgb_image = convert_bgr_to_rgb(bgr_image)

        assert rgb_image.shape == bgr_image.shape
        assert not np.array_equal(bgr_image, rgb_image)

    def test_convert_roundtrip(self):
        """Test convert roundtrip RGB→BGR→RGB"""
        original_rgb = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        bgr = convert_rgb_to_bgr(original_rgb)
        back_to_rgb = convert_bgr_to_rgb(bgr)

        assert np.array_equal(original_rgb, back_to_rgb)


class TestPipelineIntegration:
    """Test integration end-to-end"""

    def test_full_pipeline_with_enhancement(self):
        """Test full pipeline với enhancement"""
        # Tạo ảnh test
        image = np.ones((500, 700, 3), dtype=np.uint8) * 255
        cv2.rectangle(image, (50, 50), (650, 450), (0, 0, 0), 3)

        manual_corners = np.array([
            [50, 50],
            [650, 50],
            [650, 450],
            [50, 450]
        ], dtype=np.float32)

        config = DEFAULT_ENHANCEMENT_CONFIG.copy()
        result = process_document(image, manual_corners=manual_corners, enhancement_config=config)

        assert result['success'] == True
        assert result['original_image'] is not None
        assert result['detected_corners'] is not None
        assert result['scanned_image'] is not None
        assert result['enhanced_image'] is not None
        assert 'steps' in result
        assert 'detection' in result['steps']
        assert 'perspective' in result['steps']
        assert 'enhancement' in result['steps']

    def test_pipeline_steps_info(self):
        """Test thông tin các bước pipeline"""
        image = np.ones((500, 700, 3), dtype=np.uint8) * 255
        manual_corners = np.array([
            [100, 100],
            [600, 100],
            [600, 400],
            [100, 400]
        ], dtype=np.float32)

        result = process_document(image, manual_corners=manual_corners)

        if result['success']:
            steps = result['steps']

            if 'detection' in steps:
                assert 'success' in steps['detection']
                assert 'time' in steps['detection']

            if 'perspective' in steps:
                assert 'success' in steps['perspective']
                assert 'time' in steps['perspective']

            if 'enhancement' in steps:
                assert 'success' in steps['enhancement']
                assert 'time' in steps['enhancement']

    def test_pipeline_preserves_original(self):
        """Test pipeline không làm thay đổi ảnh gốc"""
        image = np.ones((500, 700, 3), dtype=np.uint8) * 255
        original_copy = image.copy()

        manual_corners = np.array([
            [100, 100],
            [600, 100],
            [600, 400],
            [100, 400]
        ], dtype=np.float32)

        result = process_document(image, manual_corners=manual_corners)

        assert np.array_equal(image, original_copy)
        assert np.array_equal(result['original_image'], original_copy)


class TestValidateAndLoadImage:
    """Test validate_and_load_image"""

    def test_validate_and_load_image_valid(self, tmp_path):
        """Test validate và load ảnh hợp lệ"""
        # Tạo file ảnh test
        image = np.ones((100, 100, 3), dtype=np.uint8) * 255
        image_path = str(tmp_path / "test.jpg")
        cv2.imwrite(image_path, image)

        success, loaded_image, message = validate_and_load_image(image_path)

        assert success == True
        assert loaded_image is not None
        assert loaded_image.shape == (100, 100, 3)

    def test_validate_and_load_image_invalid_path(self):
        """Test validate và load với path không tồn tại"""
        success, loaded_image, message = validate_and_load_image("nonexistent.jpg")

        assert success == False
        assert loaded_image is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

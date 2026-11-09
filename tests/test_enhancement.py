"""
Unit tests for enhancement module
"""

import pytest
import numpy as np
import cv2
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from smartscan.core.enhancement import (
    apply_gaussian_denoise,
    apply_median_denoise,
    apply_bilateral_denoise,
    denoise_image,
    apply_histogram_equalization,
    apply_clahe,
    enhance_contrast,
    apply_global_threshold,
    apply_otsu_threshold,
    apply_adaptive_mean_threshold,
    apply_adaptive_gaussian_threshold,
    binarize_image,
    apply_unsharp_mask,
    apply_kernel_sharpen,
    sharpen_image,
    apply_morphological_shadow_correction,
    correct_shadow,
    enhance_document
)


class TestGaussianDenoise:
    """Test cases cho Gaussian denoising"""

    def test_gaussian_denoise_basic(self):
        """Test Gaussian blur cơ bản"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = apply_gaussian_denoise(image, kernel_size=5)

        assert result.shape == image.shape
        assert result.dtype == np.uint8

    def test_gaussian_denoise_grayscale(self):
        """Test Gaussian blur trên grayscale"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_gaussian_denoise(image, kernel_size=5)

        assert result.shape == image.shape
        assert result.dtype == np.uint8

    def test_gaussian_denoise_even_kernel(self):
        """Test kernel chẵn được tự động chuyển thành lẻ"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_gaussian_denoise(image, kernel_size=4)

        assert result.shape == image.shape

    def test_gaussian_denoise_small_kernel(self):
        """Test kernel nhỏ được tự động tăng lên 3"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_gaussian_denoise(image, kernel_size=1)

        assert result.shape == image.shape


class TestMedianDenoise:
    """Test cases cho Median denoising"""

    def test_median_denoise_basic(self):
        """Test median filter cơ bản"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = apply_median_denoise(image, kernel_size=5)

        assert result.shape == image.shape
        assert result.dtype == np.uint8

    def test_median_denoise_grayscale(self):
        """Test median filter trên grayscale"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_median_denoise(image, kernel_size=5)

        assert result.shape == image.shape
        assert result.dtype == np.uint8


class TestBilateralDenoise:
    """Test cases cho Bilateral denoising"""

    def test_bilateral_denoise_basic(self):
        """Test bilateral filter cơ bản"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = apply_bilateral_denoise(image, d=9, sigma_color=75, sigma_space=75)

        assert result.shape == image.shape
        assert result.dtype == np.uint8

    def test_bilateral_denoise_grayscale(self):
        """Test bilateral filter trên grayscale"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_bilateral_denoise(image, d=9, sigma_color=75, sigma_space=75)

        assert result.shape == image.shape
        assert result.dtype == np.uint8


class TestDenoiseImage:
    """Test cases cho denoise_image wrapper"""

    def test_denoise_none(self):
        """Test method='none' trả về copy ảnh"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = denoise_image(image, method='none')

        assert np.array_equal(result, image)
        assert result is not image  # Should be a copy

    def test_denoise_gaussian(self):
        """Test denoise với Gaussian"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = denoise_image(image, method='gaussian', kernel_size=5)

        assert result.shape == image.shape

    def test_denoise_median(self):
        """Test denoise với Median"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = denoise_image(image, method='median', kernel_size=5)

        assert result.shape == image.shape

    def test_denoise_bilateral(self):
        """Test denoise với Bilateral"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = denoise_image(image, method='bilateral', kernel_size=9)

        assert result.shape == image.shape

    def test_denoise_invalid_method(self):
        """Test method không hợp lệ"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

        with pytest.raises(ValueError):
            denoise_image(image, method='invalid')


class TestHistogramEqualization:
    """Test cases cho Histogram Equalization"""

    def test_histogram_eq_grayscale(self):
        """Test histogram equalization trên grayscale"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_histogram_equalization(image)

        assert result.shape == image.shape
        assert result.dtype == np.uint8

    def test_histogram_eq_color(self):
        """Test histogram equalization trên ảnh màu"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = apply_histogram_equalization(image)

        assert result.shape == image.shape
        assert result.dtype == np.uint8


class TestCLAHE:
    """Test cases cho CLAHE"""

    def test_clahe_grayscale(self):
        """Test CLAHE trên grayscale"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_clahe(image, clip_limit=2.0, tile_grid_size=(8, 8))

        assert result.shape == image.shape
        assert result.dtype == np.uint8

    def test_clahe_color(self):
        """Test CLAHE trên ảnh màu (Lab color space)"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = apply_clahe(image, clip_limit=2.0, tile_grid_size=(8, 8))

        assert result.shape == image.shape
        assert result.dtype == np.uint8


class TestEnhanceContrast:
    """Test cases cho enhance_contrast wrapper"""

    def test_contrast_none(self):
        """Test method='none' trả về copy ảnh"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = enhance_contrast(image, method='none')

        assert np.array_equal(result, image)
        assert result is not image

    def test_contrast_histogram_eq(self):
        """Test contrast với histogram equalization"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = enhance_contrast(image, method='histogram_eq')

        assert result.shape == image.shape

    def test_contrast_clahe(self):
        """Test contrast với CLAHE"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = enhance_contrast(image, method='clahe')

        assert result.shape == image.shape

    def test_contrast_invalid_method(self):
        """Test method không hợp lệ"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

        with pytest.raises(ValueError):
            enhance_contrast(image, method='invalid')


class TestGlobalThreshold:
    """Test cases cho Global Threshold"""

    def test_global_threshold_grayscale(self):
        """Test global threshold trên grayscale"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_global_threshold(image, threshold=127)

        assert result.shape == image.shape
        assert result.dtype == np.uint8
        assert np.all((result == 0) | (result == 255))  # Binary

    def test_global_threshold_color(self):
        """Test global threshold tự động chuyển sang grayscale"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = apply_global_threshold(image, threshold=127)

        assert len(result.shape) == 2  # Grayscale
        assert result.dtype == np.uint8


class TestOtsuThreshold:
    """Test cases cho Otsu Threshold"""

    def test_otsu_threshold_grayscale(self):
        """Test Otsu threshold trên grayscale"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_otsu_threshold(image)

        assert result.shape == image.shape
        assert result.dtype == np.uint8
        assert np.all((result == 0) | (result == 255))

    def test_otsu_threshold_color(self):
        """Test Otsu threshold tự động chuyển sang grayscale"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = apply_otsu_threshold(image)

        assert len(result.shape) == 2


class TestAdaptiveThreshold:
    """Test cases cho Adaptive Threshold"""

    def test_adaptive_mean_threshold(self):
        """Test adaptive mean threshold"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_adaptive_mean_threshold(image, block_size=11, C=2)

        assert result.shape == image.shape
        assert result.dtype == np.uint8
        assert np.all((result == 0) | (result == 255))

    def test_adaptive_gaussian_threshold(self):
        """Test adaptive Gaussian threshold"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_adaptive_gaussian_threshold(image, block_size=11, C=2)

        assert result.shape == image.shape
        assert result.dtype == np.uint8
        assert np.all((result == 0) | (result == 255))

    def test_adaptive_even_block_size(self):
        """Test block size chẵn được tự động chuyển thành lẻ"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_adaptive_mean_threshold(image, block_size=10, C=2)

        assert result.shape == image.shape


class TestBinarizeImage:
    """Test cases cho binarize_image wrapper"""

    def test_binarize_none(self):
        """Test method='none' trả về copy ảnh"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = binarize_image(image, method='none')

        assert np.array_equal(result, image)
        assert result is not image

    def test_binarize_global(self):
        """Test binarize với global threshold"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = binarize_image(image, method='global', threshold=127)

        assert result.shape == image.shape

    def test_binarize_otsu(self):
        """Test binarize với Otsu"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = binarize_image(image, method='otsu')

        assert result.shape == image.shape

    def test_binarize_adaptive_mean(self):
        """Test binarize với adaptive mean"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = binarize_image(image, method='adaptive_mean')

        assert result.shape == image.shape

    def test_binarize_adaptive_gaussian(self):
        """Test binarize với adaptive Gaussian"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = binarize_image(image, method='adaptive_gaussian')

        assert result.shape == image.shape

    def test_binarize_invalid_method(self):
        """Test method không hợp lệ"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

        with pytest.raises(ValueError):
            binarize_image(image, method='invalid')


class TestUnsharpMask:
    """Test cases cho Unsharp Mask"""

    def test_unsharp_mask_basic(self):
        """Test unsharp mask cơ bản"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = apply_unsharp_mask(image, strength=1.5, radius=3)

        assert result.shape == image.shape
        assert result.dtype == np.uint8

    def test_unsharp_mask_grayscale(self):
        """Test unsharp mask trên grayscale"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_unsharp_mask(image, strength=1.5, radius=3)

        assert result.shape == image.shape
        assert result.dtype == np.uint8


class TestKernelSharpen:
    """Test cases cho Kernel Sharpening"""

    def test_kernel_sharpen_default(self):
        """Test kernel sharpen mặc định"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = apply_kernel_sharpen(image)

        assert result.shape == image.shape
        assert result.dtype == np.uint8

    def test_kernel_sharpen_custom(self):
        """Test kernel sharpen tùy chỉnh"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        custom_kernel = np.array([
            [-1, -1, -1],
            [-1, 9, -1],
            [-1, -1, -1]
        ], dtype=np.float32)
        result = apply_kernel_sharpen(image, kernel=custom_kernel)

        assert result.shape == image.shape
        assert result.dtype == np.uint8


class TestSharpenImage:
    """Test cases cho sharpen_image wrapper"""

    def test_sharpen_none(self):
        """Test method='none' trả về copy ảnh"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = sharpen_image(image, method='none')

        assert np.array_equal(result, image)
        assert result is not image

    def test_sharpen_unsharp_mask(self):
        """Test sharpen với unsharp mask"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = sharpen_image(image, method='unsharp_mask')

        assert result.shape == image.shape

    def test_sharpen_kernel(self):
        """Test sharpen với kernel"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = sharpen_image(image, method='kernel')

        assert result.shape == image.shape

    def test_sharpen_invalid_method(self):
        """Test method không hợp lệ"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

        with pytest.raises(ValueError):
            sharpen_image(image, method='invalid')


class TestShadowCorrection:
    """Test cases cho Shadow Correction"""

    def test_morphological_shadow_correction_color(self):
        """Test morphological shadow correction trên ảnh màu"""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = apply_morphological_shadow_correction(image, kernel_size=25)

        assert result.shape == image.shape
        assert result.dtype == np.uint8

    def test_morphological_shadow_correction_grayscale(self):
        """Test morphological shadow correction trên grayscale"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = apply_morphological_shadow_correction(image, kernel_size=25)

        assert result.shape == image.shape
        assert result.dtype == np.uint8

    def test_correct_shadow_none(self):
        """Test method='none' trả về copy ảnh"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = correct_shadow(image, method='none')

        assert np.array_equal(result, image)
        assert result is not image

    def test_correct_shadow_morphological(self):
        """Test shadow correction với morphological"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        result = correct_shadow(image, method='morphological')

        assert result.shape == image.shape

    def test_correct_shadow_invalid_method(self):
        """Test method không hợp lệ"""
        image = np.random.randint(0, 256, (100, 100), dtype=np.uint8)

        with pytest.raises(ValueError):
            correct_shadow(image, method='invalid')


class TestEnhanceDocument:
    """Test cases cho enhance_document function"""

    def test_enhance_document_invalid_image(self):
        """Test với ảnh không hợp lệ"""
        result = enhance_document(None)

        assert result['success'] is False
        assert result['enhanced_image'] is None
        assert "Invalid image" in result['message']

    def test_enhance_document_basic(self):
        """Test enhancement cơ bản với tham số mặc định"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        result = enhance_document(image)

        assert result['success'] is True
        assert result['enhanced_image'] is not None
        assert result['enhanced_image'].dtype == np.uint8

    def test_enhance_document_all_none(self):
        """Test khi tất cả các bước đều 'none'"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        result = enhance_document(
            image,
            denoise_method='none',
            contrast_method='none',
            threshold_method='none',
            sharpen=False,
            shadow_correction=False
        )

        assert result['success'] is True
        assert result['enhanced_image'] is not None
        # Nên gần giống ảnh gốc (có thể có sự khác biệt nhỏ do copy)

    def test_enhance_document_with_intermediate(self):
        """Test với return_intermediate=True"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        result = enhance_document(
            image,
            denoise_method='gaussian',
            contrast_method='clahe',
            sharpen=True,
            return_intermediate=True
        )

        assert result['success'] is True
        assert 'intermediate' in result
        assert 'original' in result['intermediate']
        assert 'denoised' in result['intermediate']
        assert 'contrast_enhanced' in result['intermediate']
        assert 'sharpened' in result['intermediate']

    def test_enhance_document_binarization(self):
        """Test với binarization"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        result = enhance_document(
            image,
            threshold_method='adaptive_gaussian',
            return_intermediate=True
        )

        assert result['success'] is True
        assert 'thresholded' in result['intermediate']
        # Kết quả cuối cùng nên là grayscale
        assert len(result['enhanced_image'].shape) == 2

    def test_enhance_document_keep_color(self):
        """Test giữ màu khi không threshold"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        result = enhance_document(
            image,
            threshold_method='none',
            convert_to_grayscale=False
        )

        assert result['success'] is True
        assert len(result['enhanced_image'].shape) == 3  # Color

    def test_enhance_document_convert_grayscale(self):
        """Test chuyển sang grayscale"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        result = enhance_document(
            image,
            threshold_method='none',
            convert_to_grayscale=True
        )

        assert result['success'] is True
        assert len(result['enhanced_image'].shape) == 2  # Grayscale

    def test_enhance_document_shadow_correction(self):
        """Test với shadow correction"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        result = enhance_document(
            image,
            shadow_correction=True,
            shadow_correction_method='morphological',
            return_intermediate=True
        )

        assert result['success'] is True
        assert 'shadow_corrected' in result['intermediate']

    def test_enhance_document_invalid_denoise_method(self):
        """Test với denoise method không hợp lệ"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        result = enhance_document(image, denoise_method='invalid')

        assert result['success'] is False
        assert "Denoising failed" in result['message']

    def test_enhance_document_invalid_contrast_method(self):
        """Test với contrast method không hợp lệ"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        result = enhance_document(image, contrast_method='invalid')

        assert result['success'] is False
        assert "Contrast enhancement failed" in result['message']

    def test_enhance_document_invalid_threshold_method(self):
        """Test với threshold method không hợp lệ"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        result = enhance_document(image, threshold_method='invalid')

        assert result['success'] is False
        assert "Binarization failed" in result['message']

    def test_enhance_document_preserves_shape(self):
        """Test shape được giữ nguyên khi phù hợp"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        result = enhance_document(
            image,
            threshold_method='none',
            convert_to_grayscale=False
        )

        assert result['enhanced_image'].shape == image.shape

    def test_enhance_document_all_methods(self):
        """Test với tất cả các phương pháp"""
        image = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        result = enhance_document(
            image,
            denoise_method='bilateral',
            contrast_method='clahe',
            threshold_method='adaptive_gaussian',
            sharpen=True,
            sharpen_method='unsharp_mask',
            shadow_correction=True,
            return_intermediate=True
        )

        assert result['success'] is True
        assert result['enhanced_image'] is not None
        # Kiểm tra tất cả các bước trung gian
        assert 'shadow_corrected' in result['intermediate']
        assert 'denoised' in result['intermediate']
        assert 'contrast_enhanced' in result['intermediate']
        assert 'sharpened' in result['intermediate']
        assert 'thresholded' in result['intermediate']


class TestSyntheticImages:
    """Test với ảnh tổng hợp có các vấn đề cụ thể"""

    def test_noisy_image(self):
        """Test với ảnh có nhiễu"""
        # Tạo ảnh clean
        clean = np.zeros((200, 200), dtype=np.uint8)
        cv2.rectangle(clean, (50, 50), (150, 150), 255, -1)

        # Thêm nhiễu salt-and-pepper
        noisy = clean.copy()
        noise = np.random.random(clean.shape)
        noisy[noise < 0.05] = 0
        noisy[noise > 0.95] = 255

        result = enhance_document(
            noisy,
            denoise_method='median',
            contrast_method='none',
            threshold_method='none',
            sharpen=False
        )

        assert result['success'] is True

    def test_low_contrast_image(self):
        """Test với ảnh có độ tương phản thấp"""
        # Tạo ảnh với narrow histogram
        image = np.random.randint(100, 150, (200, 200), dtype=np.uint8)

        result = enhance_document(
            image,
            denoise_method='none',
            contrast_method='clahe',
            threshold_method='none',
            sharpen=False
        )

        assert result['success'] is True

    def test_uneven_illumination(self):
        """Test với ánh sáng không đồng đều"""
        # Tạo gradient illumination
        image = np.zeros((200, 200), dtype=np.uint8)
        for i in range(200):
            image[i, :] = int(255 * (i / 200))

        result = enhance_document(
            image,
            denoise_method='none',
            contrast_method='none',
            threshold_method='none',
            sharpen=False,
            shadow_correction=True
        )

        assert result['success'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

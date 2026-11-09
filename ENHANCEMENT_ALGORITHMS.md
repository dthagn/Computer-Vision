# Image Enhancement Algorithms Documentation

## Tổng quan

Module `enhancement.py` cung cấp các thuật toán nâng cao chất lượng ảnh tài liệu cho SmartScan. Các thuật toán được thiết kế để xử lý các vấn đề phổ biến khi số hóa tài liệu: nhiễu, độ tương phản thấp, ánh sáng không đồng bộ, và cần chuyển đổi sang đen trắng.

---

## 1. Denoising (Giảm nhiễu)

### 1.1 Gaussian Blur

**Mô tả:**
- Áp dụng bộ lọc Gaussian để làm mượt ảnh và giảm nhiễu Gaussian.
- Phù hợp cho nhiễu loại "smooth noise" nhưng có thể làm mờ edge.

**Tham số:**
- `kernel_size` (int): Kích thước kernel (phải là số lẻ, mặc định: 5)
  - Giá trị lớn hơn → làm mượt mạnh hơn nhưng làm mờ nhiều hơn
  - Khuyến nghị: 3-11
- `sigma` (float): Độ lệch chuẩn Gaussian (mặc định: 0)
  - 0 = tự động tính từ kernel_size
  - Giá trị lớn hơn → làm mượt mạnh hơn

**Ưu điểm:**
- Nhanh, hiệu quả cho nhiễu Gaussian
- Giảm nhiễu đồng đều

**Nhược điểm:**
- Làm mờ edge
- Không hiệu quả cho nhiễu salt-and-pepper

**Ví dụ sử dụng:**
```python
from src.enhancement import denoise_image

result = denoise_image(image, method='gaussian', kernel_size=5, sigma=0)
```

---

### 1.2 Median Filter

**Mô tả:**
- Thay thế mỗi pixel bằng median của các pixel lân cận.
- Rất hiệu quả cho nhiễu salt-and-pepper (đốm trắng/đen ngẫu nhiên).

**Tham số:**
- `kernel_size` (int): Kích thước kernel (phải là số lẻ, mặc định: 5)
  - Giá trị lớn hơn → lọc nhiễu mạnh hơn
  - Khuyến nghị: 3-7

**Ưu điểm:**
- Giữ edge tốt hơn Gaussian blur
- Rất hiệu quả cho nhiễu salt-and-pepper

**Nhược điểm:**
- Có thể làm mờ chi tiết nhỏ
- Chậm hơn Gaussian blur

**Ví dụ sử dụng:**
```python
result = denoise_image(image, method='median', kernel_size=5)
```

---

### 1.3 Bilateral Filter

**Mô tả:**
- Bộ lọc giữ edge: làm mượt trong khi giữ edge sắc nét.
- Cân nhắc cả không gian tọa độ và không gian màu.

**Tham số:**
- `d` (int): Đường kính vùng lân cận pixel (mặc định: 9)
  - Giá trị lớn hơn → làm mượt nhiều hơn
  - Khuyến nghị: 5-15
- `sigma_color` (float): Sigma cho không gian màu (mặc định: 75)
  - Giá trị lớn hơn → pixel có màu khác nhau ảnh hưởng nhiều hơn
  - Khuyến nghị: 50-150
- `sigma_space` (float): Sigma cho không gian tọa độ (mặc định: 75)
  - Giá trị lớn hơn → pixel xa ảnh hưởng nhiều hơn
  - Khuyến nghị: 50-150

**Ưu điểm:**
- Giữ edge sắc nét trong khi giảm nhiễu
- Phù hợp cho ảnh tài liệu cần giữ chữ rõ

**Nhược điểm:**
- Chậm hơn Gaussian và Median
- Tham số cần tinh chỉnh kỹ

**Ví dụ sử dụng:**
```python
result = denoise_image(image, method='bilateral', kernel_size=9, sigma_color=75, sigma_space=75)
```

---

## 2. Contrast Enhancement (Tăng tương phản)

### 2.1 Histogram Equalization

**Mô tả:**
- Phân phối lại intensity values để sử dụng full dynamic range.
- Phù hợp cho ảnh có histogram bị lệch.

**Tham số:**
- Không có tham số

**Ưu điểm:**
- Tự động, không cần tham số
- Tăng tương phản rõ rệt

**Nhược điểm:**
- Có thể tạo nhiễu ở vùng đồng nhất
- Không hiệu quả cho ảnh có nhiều vùng khác nhau

**Ví dụ sử dụng:**
```python
from src.enhancement import enhance_contrast

result = enhance_contrast(image, method='histogram_eq')
```

---

### 2.2 CLAHE (Contrast Limited Adaptive Histogram Equalization)

**Mô tả:**
- Adaptive histogram equalization giới hạn contrast.
- Chia ảnh thành các tile nhỏ và áp dụng histogram equalization trên từng tile.
- Với ảnh màu, áp dụng trên kênh L của Lab color space để giữ màu.

**Tham số:**
- `clip_limit` (float): Giới hạn clip cho contrast enhancement (mặc định: 2.0)
  - Giá trị lớn hơn → tăng tương phản mạnh hơn
  - Quá cao có thể tạo nhiễu
  - Khuyến nghị: 1.5-4.0
- `tile_grid_size` (tuple): Kích thước lưới cho adaptive histogram (mặc định: (8, 8))
  - Tile nhỏ hơn → local contrast enhancement mạnh hơn
  - Khuyến nghị: (4, 4) đến (16, 16)

**Ưu điểm:**
- Tăng tương phản local mà không gây nhiễu quá nhiều
- Giữ màu cho ảnh màu
- Phù hợp cho ảnh tài liệu có ánh sáng không đồng đều

**Nhược điểm:**
- Chậm hơn histogram equalization đơn giản
- Cần tinh chỉnh tham số

**Ví dụ sử dụng:**
```python
result = enhance_contrast(image, method='clahe', clip_limit=2.0, tile_grid_size=(8, 8))
```

---

## 3. Binarization (Chuyển đen trắng)

### 3.1 Global Threshold

**Mô tả:**
- Áp dụng ngưỡng cố định cho toàn bộ ảnh.
- Pixel > threshold → trắng, pixel ≤ threshold → đen.

**Tham số:**
- `threshold` (int): Ngưỡng threshold (mặc định: 127)
  - Khuyến nghị: 100-200 cho tài liệu

**Ưu điểm:**
- Nhanh, đơn giản
- Hiệu quả cho ảnh có ánh sáng đồng đều

**Nhược điểm:**
- Không hoạt động tốt với ánh sáng không đồng đều
- Cần chọn threshold thủ công

**Ví dụ sử dụng:**
```python
from src.enhancement import binarize_image

result = binarize_image(image, method='global', threshold=127)
```

---

### 3.2 Otsu's Threshold

**Mô tả:**
- Tự động tính ngưỡng tối ưu bằng cách tối ưu hóa variance giữa 2 class.
- Phương pháp thống kê, tự động không cần tham số.

**Tham số:**
- Không có tham số

**Ưu điểm:**
- Tự động, không cần chọn threshold
- Hiệu quả cho ảnh có bimodal histogram

**Nhược điểm:**
- Không hoạt động tốt với ánh sáng không đồng đều
- Giả định histogram có 2 peak rõ ràng

**Ví dụ sử dụng:**
```python
result = binarize_image(image, method='otsu')
```

---

### 3.3 Adaptive Mean Threshold

**Mô tả:**
- Tính threshold local dựa trên mean của neighborhood.
- Phù hợp cho ảnh có ánh sáng không đồng đều.

**Tham số:**
- `block_size` (int): Kích thước window (phải là số lẻ, mặc định: 11)
  - Window lớn hơn → threshold global hơn
  - Window nhỏ hơn → threshold local hơn
  - Khuyến nghị: 7-31
- `C` (int): Hằng số được trừ từ mean (mặc định: 2)
  - Giá trị lớn hơn → kết quả threshold nhạy hơn
  - Khuyến nghị: 0-10

**Ưu điểm:**
- Hoạt động tốt với ánh sáng không đồng đều
- Tự động không cần tham số global

**Nhược điểm:**
- Chậm hơn global threshold
- Có thể tạo nhiễu ở vùng đồng nhất

**Ví dụ sử dụng:**
```python
result = binarize_image(image, method='adaptive_mean', block_size=11, C=2)
```

---

### 3.4 Adaptive Gaussian Threshold

**Mô tả:**
- Tương tự adaptive mean nhưng dùng weighted mean (Gaussian).
- Thường cho kết quả tốt hơn adaptive mean.

**Tham số:**
- `block_size` (int): Kích thước window (phải là số lẻ, mặc định: 11)
  - Khuyến nghị: 7-31
- `C` (int): Hằng số được trừ từ weighted mean (mặc định: 2)
  - Khuyến nghị: 0-10

**Ưu điểm:**
- Hoạt động tốt với ánh sáng không đồng đều
- Mượt hơn adaptive mean

**Nhược điểm:**
- Chậm hơn adaptive mean
- Có thể tạo nhiễu ở vùng đồng nhất

**Ví dụ sử dụng:**
```python
result = binarize_image(image, method='adaptive_gaussian', block_size=11, C=2)
```

---

## 4. Sharpening (Làm sắc nét)

### 4.1 Unsharp Mask

**Mô tả:**
- Tạo bản mờ của ảnh, trừ từ ảnh gốc và cộng lại với strength.
- Kỹ thuật cổ điển để làm sắc nét ảnh.

**Tham số:**
- `strength` (float): Độ mạnh của sharpening (mặc định: 1.5)
  - Giá trị lớn hơn → sắc nét hơn nhưng có thể tạo halo
  - Khuyến nghị: 0.5-3.0
- `radius` (int): Kích thước kernel cho Gaussian blur (mặc định: 3)
  - Giá trị lớn hơn → sharpening lớn hơn
  - Khuyến nghị: 1-5

**Ưu điểm:**
- Điều chỉnh được strength
- Hiệu quả cho text

**Nhược điểm:**
- Có thể tạo halo effect nếu strength quá cao
- Có thể tăng nhiễu

**Ví dụ sử dụng:**
```python
from src.enhancement import sharpen_image

result = sharpen_image(image, method='unsharp_mask', strength=1.5, radius=3)
```

---

### 4.2 Kernel Sharpening

**Mô tả:**
- Áp dụng convolution kernel sharpening trực tiếp.
- Kernel mặc định: [[0, -1, 0], [-1, 5, -1], [0, -1, 0]]

**Tham số:**
- `kernel` (np.ndarray): Kernel sharpening tùy chỉnh (optional)

**Ưu điểm:**
- Nhanh
- Có thể tùy chỉnh kernel

**Nhược điểm:**
- Tăng nhiễu
- Có thể tạo artifact

**Ví dụ sử dụng:**
```python
result = sharpen_image(image, method='kernel')
```

---

## 5. Shadow/Uneven Illumination Correction (Xử lý bóng đổ)

### 5.1 Morphological Shadow Correction

**Mô tả:**
- Sử dụng morphological dilation để ước lượng background.
- Chuẩn hóa ảnh bằng cách chia cho background.

**Tham số:**
- `kernel_size` (int): Kích thước kernel cho dilation (mặc định: 25)
  - Giá trị lớn hơn → background estimation global hơn
  - Khuyến nghị: 15-50
- `blur_sigma` (int): Sigma cho Gaussian blur trên background (mặc định: 5)
  - Giá trị lớn hơn → background mượt hơn
  - Khuyến nghị: 3-10

**Ưu điểm:**
- Hiệu quả cho gradient illumination
- Không cần training

**Nhược điểm:**
- Có thể làm mờ chi tiết
- Không hiệu quả cho bóng đổ phức tạp

**Ví dụ sử dụng:**
```python
from src.enhancement import correct_shadow

result = correct_shadow(image, method='morphological', kernel_size=25, blur_sigma=5)
```

---

## 6. enhance_document() - Hàm chính

### Signature

```python
def enhance_document(
    image: np.ndarray,
    denoise_method: str = 'bilateral',
    contrast_method: str = 'clahe',
    threshold_method: str = 'adaptive_gaussian',
    sharpen: bool = True,
    sharpen_method: str = 'unsharp_mask',
    shadow_correction: bool = False,
    shadow_correction_method: str = 'morphological',
    convert_to_grayscale: bool = False,
    denoise_params: Optional[Dict[str, Any]] = None,
    contrast_params: Optional[Dict[str, Any]] = None,
    threshold_params: Optional[Dict[str, Any]] = None,
    sharpen_params: Optional[Dict[str, Any]] = None,
    shadow_correction_params: Optional[Dict[str, Any]] = None,
    return_intermediate: bool = False
) -> Dict[str, Any]
```

### Thứ tự xử lý

1. **Shadow Correction** (nếu `shadow_correction=True`)
2. **Denoising**
3. **Contrast Enhancement**
4. **Sharpening** (nếu `sharpen=True`)
5. **Binarization** (nếu `threshold_method != 'none'`)
6. **Grayscale Conversion** (nếu `convert_to_grayscale=True` và không binarization)

### Return Value

```python
{
    'success': bool,
    'enhanced_image': np.ndarray or None,
    'message': str,
    'intermediate': Dict[str, np.ndarray]  # Chỉ nếu return_intermediate=True
}
```

### Ví dụ sử dụng

#### Basic Enhancement

```python
from src.enhancement import enhance_document

result = enhance_document(image)

if result['success']:
    enhanced = result['enhanced_image']
    cv2.imwrite('enhanced.jpg', enhanced)
```

#### Tùy chỉnh tham số

```python
result = enhance_document(
    image,
    denoise_method='median',
    denoise_params={'kernel_size': 5},
    contrast_method='clahe',
    contrast_params={'clip_limit': 2.5, 'tile_grid_size': (8, 8)},
    threshold_method='adaptive_gaussian',
    threshold_params={'block_size': 15, 'C': 3},
    sharpen=True,
    sharpen_method='unsharp_mask',
    sharpen_params={'strength': 1.2, 'radius': 2}
)
```

#### Giữ màu, không binarization

```python
result = enhance_document(
    image,
    denoise_method='bilateral',
    contrast_method='clahe',
    threshold_method='none',  # Không binarization
    sharpen=True,
    convert_to_grayscale=False  # Giữ màu
)
```

#### Lấy các ảnh trung gian để debug

```python
result = enhance_document(
    image,
    return_intermediate=True
)

if result['success']:
    intermediate = result['intermediate']
    cv2.imwrite('1_original.jpg', intermediate['original'])
    cv2.imwrite('2_denoised.jpg', intermediate['denoised'])
    cv2.imwrite('3_contrast.jpg', intermediate['contrast_enhanced'])
    cv2.imwrite('4_sharpened.jpg', intermediate['sharpened'])
```

---

## 7. Cấu hình mặc định

Cấu hình mặc định được định nghĩa trong `src/config.py`:

```python
DEFAULT_ENHANCEMENT_CONFIG = {
    'denoise_method': 'bilateral',
    'denoise_params': {
        'kernel_size': 9,
        'sigma_color': 75,
        'sigma_space': 75
    },
    'contrast_method': 'clahe',
    'contrast_params': {
        'clip_limit': 2.0,
        'tile_grid_size': (8, 8)
    },
    'threshold_method': 'adaptive_gaussian',
    'threshold_params': {
        'block_size': 11,
        'C': 2
    },
    'sharpen': True,
    'sharpen_method': 'unsharp_mask',
    'sharpen_params': {
        'strength': 1.5,
        'radius': 3
    },
    'shadow_correction': False,
    'shadow_correction_method': 'morphological',
    'shadow_correction_params': {
        'kernel_size': 25,
        'blur_sigma': 5
    },
    'convert_to_grayscale': False
}
```

---

## 8. Hạn chế và Lưu ý

### Hạn chế

1. **Shadow Correction:** Phương pháp morphological đơn giản có thể không hiệu quả cho bóng đổ phức tạp hoặc nhiều nguồn sáng.
2. **Binarization:** Các phương pháp adaptive có thể tạo nhiễu ở vùng đồng nhất.
3. **Sharpening:** Có thể tăng nhiễu và tạo halo effect nếu strength quá cao.
4. **CLAHE:** Nếu clip_limit quá cao có thể tạo artifact.

### Lưu ý sử dụng

1. **Thứ tự xử lý:** Shadow correction nên được áp dụng trước denoising để tránh làm mờ gradient.
2. **Giữ màu:** Sử dụng `threshold_method='none'` và `convert_to_grayscale=False` để giữ màu.
3. **Chuyển sang grayscale:** Binarization tự động chuyển sang grayscale. Nếu muốn grayscale mà không binarization, sử dụng `convert_to_grayscale=True`.
4. **Tinh chỉnh tham số:** Các tham số mặc định là điểm khởi đầu tốt, nhưng nên tinh chỉnh cho từng loại tài liệu cụ thể.
5. **Ảnh đầu vào:** Đảm bảo ảnh đầu vào là uint8, shape hợp lệ, không bị None.

### Tùy chỉnh cho từng loại tài liệu

#### Tài liệu sạch, ánh sáng tốt:
```python
result = enhance_document(
    image,
    denoise_method='none',
    contrast_method='clahe',
    threshold_method='adaptive_gaussian',
    sharpen=False
)
```

#### Tài liệu có nhiễu:
```python
result = enhance_document(
    image,
    denoise_method='bilateral',
    contrast_method='clahe',
    threshold_method='adaptive_gaussian',
    sharpen=True
)
```

#### Tài liệu có bóng đổ:
```python
result = enhance_document(
    image,
    shadow_correction=True,
    shadow_correction_method='morphological',
    denoise_method='bilateral',
    contrast_method='clahe',
    threshold_method='adaptive_gaussian'
)
```

#### Tài liệu cần giữ màu:
```python
result = enhance_document(
    image,
    denoise_method='bilateral',
    contrast_method='clahe',
    threshold_method='none',
    sharpen=True,
    convert_to_grayscale=False
)
```

---

## 9. Testing

Unit tests được cung cấp trong `tests/test_enhancement.py`:

```bash
pytest tests/test_enhancement.py -v
```

Tests bao gồm:
- Mỗi thuật toán riêng lẻ
- Hàm enhance_document với các tham số khác nhau
- Xử lý lỗi
- Ảnh tổng hợp với các vấn đề cụ thể (nhiễu, low contrast, uneven illumination)

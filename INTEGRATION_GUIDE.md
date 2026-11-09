# Hướng Dẫn Tích Hợp cho Agent 4 (Enhancement)

**Ngày**: 2026-11-02
**Đầu vào**: Modules Preprocessing, Detection, Perspective
**Đầu ra**: Hướng dẫn tích hợp với Enhancement Module

---

## 1. Tổng Quan

Agent 4 chịu trách nhiệm triển khai module Enhancement để nâng cao chất lượng ảnh sau khi đã phát hiện và hiệu chỉnh phối cảnh.

### 1.1 Pipeline Tổng Thể
```
Input Image (BGR)
    ↓
Preprocessing (resize, grayscale, blur, canny) [src/preprocessing.py]
    ↓
Detection (find 4 corners) [src/detection.py]
    ↓
Perspective Correction (warp transform) [src/perspective.py]
    ↓
Enhancement (contrast, denoise, binarization) [Agent 4]
    ↓
Output Image (Enhanced)
```

### 1.2 Data Flow
- **Format**: NumPy array (BGR, uint8) cho tất cả modules
- **Coordinate system**: TL, TR, BR, BL order cho corners
- **Error handling**: Tất cả functions trả về dict với `success` flag

---

## 2. API Của Các Modules Đã Triển Khai

### 2.1 Preprocessing Module (`src/preprocessing.py`)

#### Hàm chính: `preprocess_for_detection()`
```python
result = preprocess_for_detection(
    image: np.ndarray,  # BGR, uint8
    max_width: int = 1280,
    max_height: int = 720,
    blur_kernel: int = 5,
    canny_low: int = 50,
    canny_high: int = 150,
    morph_close_kernel: int = 5
) -> Dict[str, Any]
```

**Return dict**:
```python
{
    'processed': np.ndarray,      # Edge map (grayscale)
    'scale': float,               # Scale factor từ resize
    'gray': np.ndarray,           # Grayscale image
    'blurred': np.ndarray,        # Blurred image
    'original_size': Tuple[int, int],  # (h, w) gốc
    'resized_size': Tuple[int, int]    # (h, w) sau resize
}
```

**Sử dụng cho Agent 4**:
- Không cần trực tiếp sử dụng
- Chỉ cần biết rằng detection đã sử dụng preprocessing
- Nếu muốn custom preprocessing, có thể gọi trực tiếp

---

### 2.2 Detection Module (`src/detection.py`)

#### Hàm chính: `detect_document()`
```python
result = detect_document(
    image: np.ndarray,              # BGR, uint8
    manual_corners: Optional[np.ndarray] = None,  # shape (4, 2)
    debug: bool = False
) -> Dict[str, Any]
```

**Return dict**:
```python
{
    'success': bool,                # Phát hiện thành công không
    'corners': np.ndarray or None,  # 4 góc shape (4, 2), thứ tự TL, TR, BR, BL
    'debug_image': np.ndarray or None,  # Debug image nếu debug=True
    'message': str,                 # Thông báo kết quả
    'confidence': float             # Độ tin cậy (0-1)
}
```

**Sử dụng cho Agent 4**:
- **Quan trọng**: Kiểm tra `result['success']` trước khi sử dụng corners
- Nếu `success=False`, báo lỗi user hoặc yêu cầu manual corners
- Nếu `success=True`, `result['corners']` có thứ tự TL, TR, BR, BL
- `confidence` có thể dùng để quyết định có nên enhance không

---

### 2.3 Perspective Module (`src/perspective.py`)

#### Hàm chính: `correct_perspective()`
```python
result = correct_perspective(
    image: np.ndarray,                    # BGR, uint8
    corners: np.ndarray,                  # shape (4, 2), thứ tự TL, TR, BR, BL
    output_size: Optional[Tuple[int, int]] = None  # (width, height) tùy chọn
) -> Dict[str, Any]
```

**Return dict**:
```python
{
    'success': bool,                      # Hiệu chỉnh thành công không
    'corrected_image': np.ndarray or None,  # Ảnh đã hiệu chỉnh (BGR, uint8)
    'homography_matrix': np.ndarray or None,  # Ma trận 3x3
    'output_size': Tuple[int, int] or None,   # Kích thước đầu ra
    'message': str                         # Thông báo kết quả
}
```

**Sử dụng cho Agent 4**:
- **Quan trọng**: Input cho enhancement là `result['corrected_image']`
- Kiểm tra `result['success']` trước khi enhance
- `output_size` có thể dùng để quyết định enhancement parameters
- Nếu cần padding, dùng `apply_perspective_with_padding()`

---

## 3. Ví Dụ Tích Hợp

### 3.1 Pipeline Đơn Giản
```python
import cv2
import numpy as np
from src.detection import detect_document
from src.perspective import correct_perspective

# 1. Load ảnh
image = cv2.imread('document.jpg')  # BGR format

# 2. Phát hiện tài liệu
detection_result = detect_document(image)

if not detection_result['success']:
    print(f"Detection failed: {detection_result['message']}")
    # Yêu cầu manual corners hoặc báo lỗi
    exit(1)

corners = detection_result['corners']
print(f"Detected with confidence: {detection_result['confidence']:.2f}")

# 3. Hiệu chỉnh phối cảnh
perspective_result = correct_perspective(image, corners)

if not perspective_result['success']:
    print(f"Perspective correction failed: {perspective_result['message']}")
    exit(1)

corrected_image = perspective_result['corrected_image']
print(f"Corrected to size: {perspective_result['output_size']}")

# 4. Enhancement (Agent 4 sẽ triển khai)
# enhanced_image = enhance_document(corrected_image)

# 5. Save
cv2.imwrite('enhanced.jpg', enhanced_image)
```

### 3.2 Pipeline với Manual Corners Fallback
```python
import cv2
import numpy as np
from src.detection import detect_document
from src.perspective import correct_perspective

image = cv2.imread('document.jpg')

# Thử phát hiện tự động
detection_result = detect_document(image)

if not detection_result['success']:
    print("Auto detection failed, requesting manual corners...")
    # Giả sử user cung cấp manual corners
    manual_corners = np.array([
        [100, 100],  # TL
        [500, 100],  # TR
        [500, 700],  # BR
        [100, 700]   # BL
    ], dtype=np.float32)

    detection_result = detect_document(image, manual_corners=manual_corners)

    if not detection_result['success']:
        print("Manual corners also invalid")
        exit(1)

# Tiếp tục với perspective correction
perspective_result = correct_perspective(image, detection_result['corners'])
# ... enhancement
```

### 3.3 Pipeline với Debug Mode
```python
import cv2
from src.detection import detect_document
from src.perspective import correct_perspective

image = cv2.imread('document.jpg')

# Debug mode để visualize
detection_result = detect_document(image, debug=True)

if detection_result['success']:
    # Lưu debug image
    cv2.imwrite('debug_detection.jpg', detection_result['debug_image'])

    # Perspective correction
    perspective_result = correct_perspective(image, detection_result['corners'])
    # ... enhancement
```

---

## 4. Lưu Ý Quan Trọng Cho Agent 4

### 4.1 Format Dữ Liệu
- **Input cho enhancement**: NumPy array (BGR, uint8)
- **Output từ enhancement**: NumPy array (BGR, uint8)
- Không đổi format, chỉ enhance chất lượng

### 4.2 Error Handling
- Luôn kiểm tra `success` flag trước khi sử dụng
- Nếu detection fail, không nên cố gắng enhance
- Nếu perspective fail, không nên cố gắng enhance
- Enhancement cũng nên có error handling riêng

### 4.3 Coordinate System
- Corners từ detection có thứ tự: TL, TR, BR, BL
- Không cần sắp xếp lại corners
- Perspective module đã validate corners

### 4.4 Image Size
- Perspective output có thể khác kích thước input
- Enhancement nên hoạt động với bất kỳ kích thước nào
- Không hardcode kích thước

### 4.5 Confidence Score
- Detection confidence (0-1) có thể dùng để quyết định:
  - Có nên enhance không (confidence thấp → enhance mạnh hơn)
  - Có nên báo warning cho user không

---

## 5. Các Use Case Cho Enhancement

### 5.1 Use Case 1: Tài Liệu Đơn Giản
- Input: Tài liệu trắng nền đen text, phát hiện tốt (confidence > 0.7)
- Enhancement: Contrast nhẹ, denoise nhẹ, binarization
- Output: Tài liệu rõ nét, high contrast

### 5.2 Use Case 2: Tài Liệu Nhiễu
- Input: Tài liệu nhiễu, phát hiện trung bình (confidence 0.3-0.7)
- Enhancement: Denoise mạnh, contrast tăng, binarization
- Output: Tài liệu sạch hơn, text rõ hơn

### 5.3 Use Case 3: Tài Liệu Ánh Sáng Kém
- Input: Tài liệu quá sáng hoặc quá tối, phát hiện thấp (confidence < 0.3)
- Enhancement: Brightness/contrast adjustment, histogram equalization
- Output: Tài liệu có ánh sáng cân bằng

### 5.4 Use Case 4: Tài Liệu Màu
- Input: Tài liệu có màu (hình vẽ, biểu đồ)
- Enhancement: Color correction, denoise nhẹ, KHÔNG binarization
- Output: Tài liệu màu được preserve

---

## 6. Recommendations Cho Agent 4

### 6.1 Architecture của Enhancement Module
```python
def enhance_document(
    image: np.ndarray,
    enhance_contrast: bool = True,
    enhance_brightness: bool = True,
    denoise: bool = True,
    binarize: bool = False,  # Default False để preserve màu
    color_correct: bool = True,
    confidence: float = 1.0  # Từ detection
) -> Dict[str, Any]:
    """
    Nâng cao chất lượng ảnh.

    Args:
        image: NumPy array (BGR, uint8)
        enhance_contrast: Tăng contrast không
        enhance_brightness: Điều chỉnh brightness không
        denoise: Giảm nhiễu không
        binarize: Chuyển đen trắng không
        color_correct: Color correction không
        confidence: Confidence score từ detection

    Returns:
        Dict với 'success', 'enhanced_image', 'message'
    """
    # Implementation
```

### 6.2 Các Enhancement Steps Đề Xuất
1. **Contrast/Brightness Adjustment**
   - Sử dụng cv2.convertScaleAbs() hoặc histogram equalization
   - Parameters phụ thuộc vào confidence

2. **Denoising**
   - Sử dụng cv2.fastNlMeansDenoisingColored() hoặc Gaussian blur
   - Strength phụ thuộc vào noise level

3. **Binarization** (optional)
   - Sử dụng Otsu's thresholding hoặc adaptive threshold
   - Chỉ dùng cho tài liệu text đơn giản

4. **Color Correction**
   - Sử dụng white balance hoặc gamma correction
   - Preserve màu nếu cần

### 6.3 Parameters Từ Constants
- Sử dụng `smartscan/utils/constants.py` để lưu parameters
- Cho phép user điều chỉnh qua config file

### 6.4 Unit Tests
- Test từng enhancement step riêng lẻ
- Test với các loại ảnh khác nhau (grayscale, color, noise, etc.)
- Test edge cases (ảnh rỗng, ảnh sai format)

---

## 7. Integration với Streamlit UI (Agent 5)

### 7.1 Data Contract
- UI (RGB) → Detection (BGR) → Perspective (BGR) → Enhancement (BGR) → UI (RGB)
- Sử dụng `smartscan/utils/image_utils.py` để convert:
  - `rgb_to_bgr()` khi upload
  - `bgr_to_rgb()` khi display/download

### 7.2 Error Handling UI
- Detection fail: Hiển thị message, yêu cầu manual corners
- Perspective fail: Hiển thị message, yêu cầu re-detect
- Enhancement fail: Hiển thị message, cho phép download ảnh gốc

### 7.3 Progress Indicators
- Preprocessing: 10%
- Detection: 40%
- Perspective: 70%
- Enhancement: 100%

---

## 8. Troubleshooting

### 8.1 Detection luôn fail
- Kiểm tra ảnh có đủ contrast không
- Thử manual corners
- Điều chỉnh Canny thresholds

### 8.2 Perspective làm biến dạng ảnh
- Kiểm tra corners có chính xác không
- Kiểm tra corners có tự giao nhau không
- Thử manual corners khác

### 8.3 Enhancement làm ảnh xấu đi
- Giảm strength của enhancement
- Tắt binarization nếu cần preserve màu
- Điều chỉnh parameters theo loại tài liệu

---

## 9. Checklist Cho Agent 4

- [ ] Đọc và hiểu API của detection và perspective modules
- [ ] Triển khai `enhance_document()` function
- [ ] Tạo unit tests cho enhancement
- [ ] Test integration với detection và perspective
- [ ] Document parameters và effects
- [ ] Handle error cases gracefully
- [ ] Test với các loại ảnh khác nhau
- [ ] Optimize performance (< 1s cho ảnh A4)

---

## 10. Kết Luận

Các modules Preprocessing, Detection, Perspective đã sẵn sàng:
- ✅ API rõ ràng, dễ sử dụng
- ✅ Error handling robust
- ✅ Comprehensive unit tests (92 tests, 100% pass)
- ✅ Documentation đầy đủ
- ✅ Fallback mechanism (manual corners)

Agent 4 chỉ cần:
1. Triển khai enhancement module
2. Tích hợp với pipeline hiện tại
3. Test end-to-end
4. Document cho Agent 5 (UI)

**Files quan trọng**:
- `src/preprocessing.py` - Preprocessing functions
- `src/detection.py` - Detection API
- `src/perspective.py` - Perspective API
- `tests/test_*.py` - Unit tests (tham khảo)
- `ALGORITHM_LIMITATIONS.md` - Hạn chế thuật toán

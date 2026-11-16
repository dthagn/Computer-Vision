# API Specification

Tài liệu mô tả API **thực tế** của source code hiện tại. Quy ước chung:

- Ảnh xử lý: `numpy.ndarray`, `dtype=uint8`, **BGR** cho ảnh màu, 2D cho grayscale/nhị phân.
- Streamlit hiển thị RGB; UI tự convert.
- Các hàm core trả **dictionary** `{'success': bool, ..., 'message': str}` thay vì raise exception cho lỗi dữ liệu thường gặp. Exception chỉ dùng cho method/param không hợp lệ ở tầng helper (`ValueError`).
- Góc tài liệu: shape `(4, 2)`, thứ tự **TL, TR, BR, BL**.

---

## Core API

### `detect_document(image, manual_corners=None, debug=False)`

**Location**: `smartscan/core/detection.py`

**Input**:
```python
image: np.ndarray          # BGR uint8, (H,W,3) hoặc (H,W)
manual_corners: np.ndarray # optional, shape (4,2); bypass auto-detection
debug: bool                # trả debug_image overlay corners
```

**Output**:
```python
{
    'success': bool,
    'corners': np.ndarray | None,   # (4,2) float32, TL,TR,BR,BL
    'debug_image': np.ndarray | None,
    'message': str,
    'confidence': float,            # 0..1
}
```

**Thuật toán**: preprocess (resize ≤1280×720, grayscale, blur, Canny 5 bộ ngưỡng, morphology close) → `find_document_candidates` (approxPolyDP nhiều epsilon + minAreaRect + tổ hợp đỉnh hull, chấm `0.6*quad + 0.4*edge`) → chọn confidence cao nhất → map tọa độ về ảnh gốc → `order_corners` + kiểm tra tự giao. Manual corners được order + kiểm tra self-intersection; confidence = 1.0.

---

### `find_document_contour(edges, min_area_ratio=0.05, max_area_ratio=0.95)` / `find_document_candidates(edges, ...)`

**Location**: `smartscan/core/detection.py`

- `find_document_candidates` trả list candidate dict: `points (4,2)`, `score`, `quad_score`, `edge_score`, `edge_distance`, `area_ratio`, sắp xếp giảm dần, tối đa 20.
- `find_document_contour` trả `points` của candidate tốt nhất (tương thích API cũ) hoặc `None`.

---

### `correct_perspective(image, corners, output_size=None, auto_order=True)`

**Location**: `smartscan/core/perspective.py`

**Input**: ảnh BGR uint8; corners `(4,2)`; `output_size` optional `(w,h)`; `auto_order` mặc định True → tự chuẩn hóa TL,TR,BR,BL.

**Output**:
```python
{
    'success': bool,
    'corrected_image': np.ndarray | None,
    'homography_matrix': np.ndarray | None,   # 3x3
    'output_size': (w, h) | None,
    'message': str,
}
```

Validation: shape `(4,2)`, numeric, tọa độ trong ảnh, không trùng, không collinear, không self-intersecting (kiểm tra trước và sau khi order). Output size tự tính từ cạnh đối diện, giới hạn [4, 10000] px.

### `apply_perspective_with_padding(image, corners, padding_ratio=0.05, auto_order=True)`

Như trên nhưng canvas output lớn hơn `padding_ratio` mỗi phía, viền trắng — pipeline mặc định dùng hàm này. `padding_ratio` ∈ [0, 0.5].

---

### `enhance_document(image, ..., brightness=0.0, contrast=1.0, return_intermediate=False)`

**Location**: `smartscan/core/enhancement.py`

**Input**: ảnh BGR uint8 + các tham số keyword (xem config bên dưới).

**Output**:
```python
{
    'success': bool,
    'enhanced_image': np.ndarray | None,   # uint8; 2D nếu binarize/grayscale
    'message': str,
    'intermediate': dict,                   # ảnh trung gian nếu return_intermediate
}
```

**Thứ tự stage**: shadow correction (nếu bật) → denoise → **brightness/contrast** → contrast (CLAHE/histogram_eq/none) → sharpen (nếu bật) → binarize (nếu method ≠ none) → grayscale (nếu không binarize và `convert_to_grayscale=True`). Mỗi stage lỗi → `success=False` + message chỉ rõ stage.

**Config keys** (dùng bởi `sanitize_enhancement_config`):

| Key | Giá trị |
|---|---|
| `denoise_method` | `gaussian` / `median` / `bilateral` / `none` (+ `denoise_params`) |
| `contrast_method` | `histogram_eq` / `clahe` / `none` (+ `contrast_params`) |
| `threshold_method` | `global` / `otsu` / `adaptive_mean` / `adaptive_gaussian` / `none` (+ `threshold_params`) |
| `sharpen` | bool; `sharpen_method`: `unsharp_mask` / `kernel` / `none` (+ `sharpen_params`) |
| `shadow_correction` | bool; `shadow_correction_method`: `morphological` / `none` (+ params) |
| `convert_to_grayscale` | bool |
| `brightness` | float [-100, 100], mặc định 0 |
| `contrast` | float [0.0, 3.0], mặc định 1.0 |

`sanitize_enhancement_config(config)` → dict đầy đủ chỉ chứa khóa hợp lệ (điền từ `DEFAULT_ENHANCEMENT_CONFIG`, loại khóa lạ).

---

### `process_document(image, manual_corners=None, enhancement_config=None, use_padding=True, debug=False)`

**Location**: `smartscan/core/pipeline.py`

Pipeline detect → perspective → enhance. `enhancement_config` được sanitize trước khi dùng; config `None` → default (không binarize).

**Output**: xem contract trong [architecture.md](architecture.md) — gồm `original_image`, `detected_corners`, `scanned_image`, `enhanced_image`, `steps` per-stage, `processing_time`. Enhancement lỗi → `success=True` partial, `scanned_image` vẫn có.

### `process_document_with_fallback(...)`

Như trên + `needs_manual_corners: bool` khi detection fail.

### `update_enhancement(scanned_image, enhancement_config)`

Chạy lại chỉ enhancement trên ảnh đã scan. Trả `{'success', 'enhanced_image', 'message', 'processing_time'}`; config được sanitize, exception → failure dict.

### `get_default_enhancement_presets()`

Trả dict preset → config:

| Preset | Đặc điểm |
|---|---|
| `default` / `natural` | Mặc định, giữ màu, không binarize |
| `original` | Gần như không xử lý (tắt mọi stage) |
| `color_document` | Giữ màu + shadow correction nhẹ |
| `bw_document` | Grayscale + adaptive Gaussian threshold (đen trắng) |
| `low_light` | Shadow correction + brightness +25, contrast 1.15 |
| `text_enhancement` | Grayscale + CLAHE mạnh + unsharp, không binarize |
| `light_enhancement` | Alias tương thích preset cũ |

---

## Geometry helpers (`smartscan/core/geometry.py`)

| Hàm | Mô tả |
|---|---|
| `order_corners(corners)` | Sắp xếp `(4,2)` → TL,TR,BR,BL (tổng/hiệu tọa độ, fallback góc quanh centroid) |
| `check_self_intersection(corners)` | True nếu tứ giác bow-tie (2 cặp cạnh không kề nhau cắt nhau) |
| `signed_area(corners)` | Diện tích đại số theo thứ tự điểm hiện tại |

## Utility API

### `smartscan/utils/image_loader.py`

- `load_and_validate_image(file_bytes) -> (success, image_bgr, message)` — kiểm tra ≤10MB, decode OpenCV, ≤4000×4000.
- `load_image_from_bytes`, `load_image_from_file`, `validate_file_size`, `validate_image_dimensions`.
- `convert_rgb_to_bgr`, `convert_bgr_to_rgb` (ảnh 3 kênh).

### `smartscan/utils/utils.py`

- `encode_image_to_bytes(image, '.jpg'/'.png', quality=95) -> bytes`
- `draw_corners_on_image(image_bgr, corners, color, thickness)` — overlay polyline + nhãn TL/TR/BR/BL.
- `create_comparison_image(img1, img2, labels)` — ghép ngang, xử lý ảnh 2D.
- `get_image_info(image)`, `format_processing_time(seconds)`, `resize_image_if_large`, `create_debug_grid`.

### `smartscan/utils/config.py`

- `DENOISE_METHODS`, `CONTRAST_METHODS`, `THRESHOLD_METHODS`, `SHARPEN_METHODS`, `SHADOW_CORRECTION_METHODS`.
- `DEFAULT_ENHANCEMENT_CONFIG` — `threshold_method='none'` (không ép B&W), `brightness=0`, `contrast=1.0`.

## UI state (`smartscan/ui/state.py`)

- `init_session_state()`, `reset_session()`.
- `reset_downstream()` — upload/rotation đổi.
- `reset_perspective_and_enhancement()` — corners đổi.
- `reset_enhancement_result()` — config đổi.
- `set_stage_error/clear_stage_error/get_stage_error`.

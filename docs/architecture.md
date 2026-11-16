# SmartScan Architecture Documentation

Tài liệu mô tả kiến trúc **thực tế của source code hiện tại** (sau refactor 2026-11). Tài liệu cũ mô tả quy trình nhiều agent và module `correction.py` không còn tồn tại — không dùng làm tham chiếu.

## System Overview

SmartScan là ứng dụng Streamlit + OpenCV (Computer Vision cổ điển, không deep learning) xử lý tài liệu theo pipeline 5 bước:

```text
Upload → Detect & Review → Perspective Correction → Enhancement → Preview & Export
```

Ba lớp chính:

1. **Core Processing Layer** (`smartscan/core/`): thuật toán ảnh + pipeline điều phối. Không phụ thuộc Streamlit.
2. **UI Layer** (`smartscan/ui/`): Streamlit app + session-state manager. Chỉ gọi core/utils API, không chứa thuật toán.
3. **Utility Layer** (`smartscan/utils/`): decode/validate ảnh, config enhancement, format xuất file.

```
┌──────────────────────────────────────────────────────────┐
│                  Streamlit UI (app.py)                    │
│            state.py: session-state schema + reset rules   │
└───────────────┬──────────────────────────┬───────────────┘
                │ file bytes               │ stage-level calls
                ▼                          ▼
   ┌────────────────────┐      ┌───────────────────────────┐
   │ utils/image_loader │      │ core.detection            │
   │ decode + validate  │      │ detect_document()         │
   └─────────┬──────────┘      └────────────┬──────────────┘
             │ BGR uint8                     │ corners (4,2) TL,TR,BR,BL
             │                              ▼
             │                 ┌───────────────────────────┐
             │                 │ core.perspective          │
             │                 │ correct_perspective /     │
             │                 │ apply_perspective_with_   │
             │                 │ padding                   │
             │                 └────────────┬──────────────┘
             │                              │ scanned_image
             │                              ▼
             │                 ┌───────────────────────────┐
             │                 │ core.enhancement          │
             │                 │ enhance_document /        │
             │                 │ sanitize_enhancement_     │
             │                 │ config                    │
             │                 └────────────┬──────────────┘
             │                              │ enhanced_image
             ▼                              ▼
   ┌────────────────────────────────────────────────────────┐
   │ utils/utils: encode bytes, draw corners, comparison,   │
   │ image info, timing                                     │
   └────────────────────────────────────────────────────────┘
```

## Module Map

### `smartscan/core/`

| File | Vai trò | API chính |
|---|---|---|
| `geometry.py` | Hình học góc dùng chung | `order_corners`, `check_self_intersection`, `signed_area` |
| `preprocessing.py` | Validate ảnh, resize, grayscale, blur, Canny, morphology, rotate | `validate_image`, `preprocess_for_detection`, `rotate_image`, `rotate_90` |
| `detection.py` | Phát hiện 4 góc tài liệu | `detect_document`, `find_document_contour`, `find_document_candidates` |
| `perspective.py` | Hiệu chỉnh phối cảnh | `correct_perspective`, `apply_perspective_with_padding`, `validate_corners` |
| `enhancement.py` | Nâng cao chất lượng | `enhance_document`, `adjust_brightness_contrast`, `sanitize_enhancement_config` |
| `pipeline.py` | Điều phối end-to-end + presets | `process_document`, `process_document_with_fallback`, `update_enhancement`, `get_default_enhancement_presets` |

### `smartscan/ui/`

| File | Vai trò |
|---|---|
| `app.py` | Streamlit UI 5 bước, gọi stage-level API |
| `state.py` | Session-state schema + quy tắc reset tập trung |

### `smartscan/utils/`

| File | Vai trò |
|---|---|
| `image_loader.py` | Decode bytes/file, giới hạn 10MB / 4000px, convert RGB↔BGR |
| `utils.py` | `encode_image_to_bytes`, `draw_corners_on_image`, `create_comparison_image`, `get_image_info`, `format_processing_time` |
| `config.py` | Danh sách method + `DEFAULT_ENHANCEMENT_CONFIG` |
| `constants.py`, `image_utils.py` | Hằng số và helper bổ sung (một số trùng chức năng — xem ghi chú) |

## Data Contracts

### Màu ảnh

- OpenCV xử lý **BGR `uint8`**; ảnh nhị phân/grayscale là 2D `uint8`.
- Streamlit hiển thị **RGB**; UI convert qua `to_display()` (xử lý cả ảnh 2D).
- Ảnh gốc không bao giờ bị mutate: pipeline/enhancement đều `copy()`.

### Góc tài liệu

- Shape `(4, 2)`, thứ tự **TL, TR, BR, BL**, chuẩn hóa bởi `geometry.order_corners()`.
- Detection trả `float32`; perspective chấp nhận float/int và tự `auto_order` lại nếu caller chưa đúng thứ tự.

### Kết quả pipeline (`process_document`)

```python
{
  'success': bool,              # toàn pipeline thành công
  'original_image': ndarray,    # ảnh gốc (copy)
  'detected_corners': ndarray,  # (4,2) hoặc None
  'scanned_image': ndarray,     # sau perspective; vẫn có nếu enhancement lỗi
  'enhanced_image': ndarray,    # None nếu enhancement lỗi
  'debug_images': dict,
  'message': str,
  'steps': {                    # per-stage status
      'detection':   {'success', 'message', 'confidence', 'time', 'corners'},
      'perspective': {'success', 'message', 'output_size', 'time'},
      'enhancement': {'success', 'message', 'time'},
  },
  'processing_time': float,
}
```

`process_document_with_fallback()` thêm `needs_manual_corners`. Khi enhancement lỗi, `success=True` (partial) và `scanned_image` vẫn export được.

### Enhancement config

Dict các khóa: `denoise_method/params`, `contrast_method/params`, `threshold_method/params`, `sharpen`, `sharpen_method/params`, `shadow_correction(_method/_params)`, `convert_to_grayscale`, `brightness` ([-100,100]), `contrast` ([0,3]). `sanitize_enhancement_config()` điền mặc định + loại khóa lạ → config thiếu/sai không crash pipeline.

## UI Flow & State Rules

UI chạy **stage-level**, không gọi một nút cho toàn pipeline:

1. **Upload**: file JPG/JPEG/PNG ≤10MB, decode + validate; rotation 90°/góc tự do. Signature `(name, size, md5, quarter, angle)` quyết định rebuild `source_image`.
2. **Detect & Review**: `detect_document(debug=True)` → overlay TL/TR/BR/BL + confidence; editor 8 tọa độ; `confirm_corners()` validate qua `detect_document(manual_corners=...)` + `validate_corners()` trước khi cho qua bước 3. Detection fail → nhập manual.
3. **Perspective**: `apply_perspective_with_padding(source_image, corners, 0.05)` → `scanned_image`.
4. **Enhancement**: preset + advanced controls ghi vào `enhancement_config`; `update_enhancement(scanned_image, config)` → `enhanced_image`. Đổi config chỉ cần Run lại, không detect lại.
5. **Preview & Export**: original/scanned/enhanced, comparison, download JPG/PNG (quality slider).

Quy tắc reset (implement trong `state.py`):

- Upload mới / đổi rotation → `reset_downstream()` (xóa corners → enhanced).
- Đổi/xác nhận corners → `reset_perspective_and_enhancement()`.
- Đổi enhancement config → `reset_enhancement_result()` (chỉ xóa enhanced).
- Enhancement fail → giữ `scanned_image`, báo lỗi theo stage.

## Error Handling

- Mọi core API trả **dictionary `{'success', ..., 'message'}`**, không raise cho lỗi dữ liệu thường gặp.
- `enhance_document` bắt exception từng stage con và trả `success=False` với message chỉ rõ stage lỗi.
- Pipeline phân biệt lỗi detection / perspective / enhancement trong `steps`.
- UI hiển thị lỗi theo stage (`stage_errors`) và không cho qua bước sau khi bước trước chưa hợp lệ.

## Testing

```powershell
py -m pytest -q          # root: testpaths=tests (pytest.ini)
py -m pytest tests -q
py -m streamlit run smartscan/ui/app.py
```

- `tests/`: unit (preprocessing/detection/perspective/enhancement/pipeline), integration, `test_qa_independent.py` (synthetic labeled set), `test_ui_smoke.py` (Streamlit AppTest end-to-end).
- Kết quả hiện tại: **252 passed**.
- Script root cũ (`quick_test.py`, `verify_imports.py`, `test_pipeline_simple.py`, `example_usage.py`) là legacy layout `src/`; `pytest.ini` giới hạn collect trong `tests/` nên không còn collection error. File được giữ nguyên, không xóa.

## Known Limitations

- Detection là heuristic hình học (contour + edge support), không hiểu ngữ nghĩa; manual corners là fallback chính thức.
- Corner order chuẩn hóa theo tọa độ ảnh; ảnh tài liệu xoay 180° cần user review.
- Enhancement cải thiện hiển thị, không khôi phục chi tiết đã mất; không có OCR/metric chất lượng tự động.
- `smartscan/utils/image_utils.py` và một phần `utils.py` trùng chức năng convert/validate với module khác — chưa gộp để tránh phá API; chỉ dùng `image_loader.py` + `utils.py` trong UI.

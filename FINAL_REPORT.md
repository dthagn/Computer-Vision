# SmartScan — Final Report

**Ngày:** 2026-11-09
**Phạm vi:** refactor SmartScan từ baseline audit đến sản phẩm hoàn chỉnh (Preserve → Analyze → Refactor → Integrate → Test → Improve).
**Kết luận:** **ĐẠT** — pipeline core ổn định, UI 5 bước hoạt động end-to-end, **252/252 tests pass**, không còn blocker nghiệm thu.

---

## 1. Cài đặt

Yêu cầu Python 3.9+ (kiểm thử trên 3.13.1). Trên Windows dùng launcher `py` nếu `python` là Windows Store stub.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

Dependencies: `opencv-python 5.0.0.93`, `numpy 2.4.6`, `streamlit 1.57.0`, `pytest 9.2.0` (+ `pytest-cov`, `black`, `flake8` tùy chọn).

## 2. Chạy ứng dụng

```powershell
py -m streamlit run smartscan/ui/app.py
```

hoặc entry point root: `py app.py`. Mở `http://localhost:8501`.

Luồng sử dụng: **Upload → Detect & Review → Perspective Correction → Image Enhancement → Preview & Export**.

### Dùng API Python

```python
import cv2
from smartscan.core.pipeline import process_document, get_default_enhancement_presets

img = cv2.imread("document.jpg")
result = process_document(img)          # detect -> perspective -> enhance
cv2.imwrite("out.jpg", result["enhanced_image"])
```

Chi tiết API: [docs/api.md](docs/api.md) · Kiến trúc: [docs/architecture.md](docs/architecture.md) · Thuật toán: [docs/algorithms.md](docs/algorithms.md).

## 3. Kiểm thử

```powershell
py -m pytest -q        # 252 passed, 0 failed (~25-36s)
```

| Nhóm | Nội dung | Kết quả |
|---|---|---|
| Unit | preprocessing, detection, perspective, enhancement, pipeline | Pass |
| Integration | pipeline end-to-end, manual corners, fallback, preset | Pass |
| QA độc lập | `test_qa_independent.py` — synthetic labeled set 7 case (clean/low-contrast/skew/extra-rectangles/grayscale/noisy/small), edge cases, seed cố định | 64/64 Pass |
| UI smoke | `test_ui_smoke.py` — AppTest render + full flow + invalid upload | 3/3 Pass |

Hiệu năng: `process_document` ảnh 1000×750 ≈ **0.68s** (KPI <3s đạt).

## 4. Thay đổi chính so với baseline

### Core

- **`core/geometry.py` (mới):** `order_corners` (TL,TR,BR,BL), `check_self_intersection`, `signed_area` — một implementation duy nhất cho detection + perspective. Fix BUG corner-order (`np.diff` sai dấu).
- **`core/detection.py`:** candidate extraction đa lớp — nhiều epsilon `approxPolyDP`, convex hull, `minAreaRect`, fallback tổ hợp đỉnh hull (≤16 đỉnh); chấm điểm `0.6*quad + 0.4*edge` với edge support qua distance transform. Fix detection fail `extra_rectangles`. API `detect_document`/`find_document_contour` giữ nguyên.
- **`core/perspective.py`:** `auto_order` mặc định True, validate output size [4,10000], `padding_ratio` ∈ [0,0.5], check self-intersection trước/sau order.
- **`core/enhancement.py`:** thêm `adjust_brightness_contrast` (brightness [-100,100], contrast [0,3]) và `sanitize_enhancement_config` (lọc khóa lạ, điền mặc định). Thứ tự stage: shadow → denoise → brightness/contrast → CLAHE/hist → sharpen → binarize → grayscale.
- **`core/pipeline.py`:** sanitize config trước khi enhance, ghi `steps['enhancement']` cả khi exception, `update_enhancement` bắt lỗi trả failure dict, `get_default_enhancement_presets` mở rộng.
- **`utils/config.py`:** `DEFAULT_ENHANCEMENT_CONFIG` thêm `brightness`/`contrast`, **`threshold_method='none'`** — không ép mọi ảnh sang đen trắng.

### UI

- **`ui/app.py` (viết lại):** dashboard 5 bước, stage-level API (không nút chạy ngầm), overlay corners + editor 8 tọa độ + Confirm có validate, gating từng bước, download JPG/PNG + quality.
- **`ui/state.py` (mới):** session-state schema + reset rules (upload/rotation → reset downstream; corners → reset perspective+enhancement; config → reset enhanced).
- Fix crash session state (`rot_quarter`/`rot_angle`) và ImportError `encode_image_to_bytes`.

### Test & tooling

- `tests/test_ui_smoke.py` (mới): 3 AppTest smoke tests.
- `tests/test_qa_independent.py`: seed `hash()` → cố định, kết quả tái lập.
- `pytest.ini` (mới): `testpaths = tests` → `py -m pytest -q` ở root không còn collection error từ script legacy.
- Docs viết lại theo source thực tế: `README.md`, `docs/api.md`, `docs/architecture.md`, `docs/algorithms.md`; `reports/QA_REPORT.md` thêm phần re-test; `REBUILD_PLAN.md` là baseline audit.

## 5. Bug đã sửa (đối chiếu QA report gốc)

BUG-1 corner order, BUG-2 UI import, BUG-3 API stub, BUG-4 UI path, BUG-5 root app stale, BUG-6 fallback signature, BUG-7 config key lạ, BUG-8 test import `src/` (cô lập bằng pytest.ini), BUG-9 docs — tất cả RESOLVED/FIXED. Chi tiết: `reports/QA_REPORT.md` phần bổ sung.

## 6. Giới hạn còn lại (nói rõ khi bảo vệ)

1. **Detection là heuristic hình học** (contour + edge support), không hiểu ngữ nghĩa "tài liệu". Manual corner adjustment là fallback chính thức — UI bắt buộc review trước perspective.
2. **Corner order theo tọa độ ảnh**: tài liệu bị xoay 180° trong mặt phẳng sẽ được chuẩn hóa theo góc trên-trái của ảnh chụp, không phải hướng đọc; user review/confirm corners.
3. **Enhancement cải thiện hiển thị**, không khôi phục chi tiết đã mất; sharpening có thể khuếch đại nhiễu.
4. **Không có OCR/metric chất lượng tự động** — đánh giá chủ yếu trực quan + test hình học.
5. `use_container_width` của Streamlit đang deprecated-warning (vẫn hoạt động trên 1.57); có thể chuyển sang `width="stretch"` khi nâng cấp.
6. Script root legacy (`quick_test.py`, `verify_imports.py`, `test_pipeline_simple.py`, `example_usage.py`) giữ nguyên layout `src/` cũ, không collect nhờ `pytest.ini`; không ảnh hưởng package `smartscan`.
7. `smartscan/utils/image_utils.py`/`constants.py` có một số helper trùng chức năng — chưa gộp để tránh phá API; UI chỉ dùng `image_loader.py` + `utils.py`.

## 7. Checklist nghiệm thu

- [x] `py -m pytest -q` → 252 passed, 0 failed
- [x] `py -m streamlit run smartscan/ui/app.py` render không exception (AppTest + server `/healthz` 200)
- [x] Upload → detect → review/manual corners → perspective → enhancement → preview → export chạy thật
- [x] Edge cases: no document, skew, low contrast, extra rectangles, grayscale, noisy, small doc, invalid file, enhancement fail vẫn giữ scanned
- [x] Tài liệu khớp source; báo cáo QA dùng số liệu chạy thực tế

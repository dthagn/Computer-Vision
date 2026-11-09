# SmartScan — Independent QA Report

**Ngày:** 2026-11-07
**Vai trò:** Senior QA Engineer (kiểm thử độc lập, không mặc định code cũ là đúng)
**Phạm vi:** `smartscan/` package, `app.py` (root), `tests/`

---

## 1. Môi trường kiểm thử

| Thành phần | Phiên bản / Ghi chú |
|---|---|
| OS | Windows, workspace `C:\Users\admin\OneDrive\Documents\Xử lý ảnh` |
| Python | 3.13.1 (qua `py` launcher; `python` trên PATH là WindowsApps stub — **không chạy được**) |
| opencv-python | 5.0.0.93 |
| numpy | 2.4.6 |
| streamlit | 1.57.0 |
| pytest | 9.2.0 |
| pillow | 12.2.0 |

Lệnh chạy test: `py -m pytest tests -q`

---

## 2. Vấn đề người dùng báo cáo: `smartscan/core/__init__.py` import `.correction`

**Kết quả: ĐÃ ĐƯỢC SỬA TRƯỚC KHI QA.**

`smartscan/core/__init__.py` hiện tại đã import đúng:

```python
from .perspective import correct_perspective, apply_perspective_with_padding
```

`import smartscan.core` chạy OK. Không còn `correction.py` trong `smartscan/core/`.

**Tuy nhiên còn sót:**
- `docs/api.md:116` vẫn ghi `from smartscan.core.correction import correct_perspective` → tài liệu lỗi thời (severity: Low).
- `smartscan/core/__pycache__/` không còn `correction.*.pyc` — không ảnh hưởng.

**Bug mới phát hiện liên quan (xem BUG-3):** `smartscan/core/__init__.py` định nghĩa `process_document()` là **stub `pass` → return None**, trong khi pipeline thật nằm ở `smartscan/core/pipeline.py`. Hai API cùng tên nhưng hành vi khác nhau hoàn toàn.

---

## 3. Tóm tắt kết quả

| Nhóm | Kết quả |
|---|---|
| A. Input | PASS (đa số); giới hạn 10MB/4000px hoạt động |
| B. Detection | **FAIL NGHIÊM TRỌNG** — corner order sai 100% |
| C. Perspective | PASS về validation; FAIL gián tiếp do corner order |
| D. Enhancement | PASS phần lớn; vài edge-case param |
| E. Pipeline | FAIL — output bị xoay/mirror do BUG-1; stub API |
| F. UI | **FAIL NGHIÊM TRỌNG** — app crash ngay khi import |

**Test suite:** `pytest tests -q` → **237 passed, 9 failed** (2 fail có sẵn trong test cũ + 7 fail là test QA mới phát hiện BUG-1).

---

## 4. BUGS phát hiện

### BUG-1 — CRITICAL: `order_corners()` trả về sai thứ tự TR/BL → toàn bộ ảnh output bị xoay/mirror

- **Module/hàm:** `smartscan/core/detection.py` → `order_corners()` (dòng ~136-145), Agent 2 (Document Detection)
- **Root cause:** Comment ghi "diff = x - y" nhưng code dùng `np.diff(corners, axis=1)` — `np.diff` tính `a[i+1]-a[i]` tức **y − x**, ngược dấu. Do đó `argmax` chọn nhầm điểm BL vào vị trí TR và ngược lại.
- **Tái hiện:**
  ```python
  from smartscan.core.detection import order_corners
  import numpy as np
  c = np.array([[150,100],[650,100],[650,500],[150,500]], dtype=np.float32)
  order_corners(c)
  # Kỳ vọng: TL,TR,BR,BL = [[150,100],[650,100],[650,500],[150,500]]
  # Thực tế: [[150,100],[150,500],[650,500],[650,100]]  (TL,BL,BR,TR)
  ```
- **Hậu quả đã kiểm chứng:** chạy `process_document` end-to-end, marker đỏ đặt gần góc TR của tài liệu xuất hiện ở **góc BL** của ảnh output (centroid ≈ (7.5%, 93.8%)). Tài liệu bị biến dạng xoay/gương — vi phạm trực tiếp acceptance criteria "Corner order: TL, TR, BR, BL" và làm cho perspective correction sai hoàn toàn.
- **Phạm vi ảnh hưởng:** 100% đường đi qua `detect_document` (auto detection) **và** manual corners (vì manual path cũng gọi `order_corners`). Mọi pipeline thành công đều trả ảnh sai hướng.
- **Đề xuất sửa:** đổi thành `diff_coords = corners[:, 0] - corners[:, 1]` (x − y), sau đó `argmax`→TR, `argmin`→BL. Bổ sung unit test assert đúng thứ tự trên input xáo trộn.
- **Test liên quan:** `tests/test_qa_independent.py::TestDetectionSynthetic` (7 case fail), `test_manual_corners_valid` chỉ check TL nên không bắt được.

### BUG-2 — CRITICAL: `smartscan/ui/app.py` crash ngay khi import → UI không thể chạy

- **Module/hàm:** `smartscan/ui/app.py` dòng 24-29, Agent 5 (Streamlit UI)
- **Lỗi:** `from smartscan.utils.image_loader import (..., encode_image_to_bytes)` — hàm này nằm trong `smartscan/utils/utils.py`, không có trong `image_loader.py`.
- **Tái hiện:** `py -c "from smartscan.ui.app import main"` → `ImportError: cannot import name 'encode_image_to_bytes'`.
- **Đề xuất sửa:** đổi import thành `from smartscan.utils.utils import encode_image_to_bytes` (hoặc re-export trong `image_loader`).

### BUG-3 — HIGH: `smartscan/core/__init__.py::process_document` là stub trả về `None`

- **Module:** `smartscan/core/__init__.py` dòng 10-30
- **Lỗi:** hàm chỉ có docstring + `pass`. `from smartscan.core import process_document` trả về `None` thay vì pipeline result → bất kỳ consumer nào dùng package-level API sẽ nhận `None` và crash khi truy cập key.
- **Đề xuất sửa:** xóa stub hoặc delegate `from .pipeline import process_document` (cẩn thận circular import — pipeline không import `smartscan.core` package-level nên an toàn).

### BUG-4 — HIGH: `smartscan/ui/app.py` sys.path insert sai cấp thư mục

- **Module:** `smartscan/ui/app.py` dòng 14-16
- `parent_dir = dirname(dirname(app.py))` = `smartscan/`; insert `smartscan/` vào sys.path nhưng import là `smartscan.core...` → cần **project root** (phải `dirname` thêm 1 cấp).
- **Đã kiểm chứng:** mô phỏng `streamlit run smartscan/ui/app.py` không có cwd trong sys.path → `ModuleNotFoundError: No module named 'smartscan'`.
- **Đề xuất sửa:** insert `os.path.dirname(parent_dir)` (project root), hoặc tốt hơn chạy app từ root.

### BUG-5 — MEDIUM: `app.py` ở root là file stale, import `src/` không tồn tại

- **Module:** `app.py` (root) dòng 15-41 — bản copy cũ của ui/app.py, `sys.path.insert(.../src)` rồi `from pipeline import ...` → `ModuleNotFoundError` ngay lập tức. Không có thư mục `src/`.
- **Đề xuất sửa:** xóa file hoặc sửa import giống ui/app.py (sau khi fix BUG-2/4).

### BUG-6 — MEDIUM: `process_document_with_fallback()` thiếu tham số `manual_corners`

- **Module:** `smartscan/core/pipeline.py` dòng 180-186
- Test cũ `tests/test_pipeline.py::test_process_document_with_fallback_success` gọi `process_document_with_fallback(image, manual_corners=...)` → `TypeError`. API "with_fallback" về mặt tên gọi gợi ý nhận manual corners nhưng signature không có → inconsistency giữa test expectation và implementation.
- **Đề xuất:** thêm `manual_corners: Optional[np.ndarray] = None` và truyền xuống `process_document`.

### BUG-7 — LOW: `enhance_document` crash không bắt khi config có key lạ

- `process_document(img, enhancement_config={..., 'bogus': 1})` → `TypeError: enhance_document() got an unexpected keyword argument` lan ra ngoài, không được bọc try/except trong `pipeline.py` → pipeline crash thay vì trả `success=False`.
- Đề xuất: bọc lời gọi `enhance_document` trong try/except TypeError hoặc validate keys.

### BUG-8 — LOW: test suite cũ có import stale `src.*`

- `tests/test_detection.py:227` → `from src.detection import check_self_intersection` → `ModuleNotFoundError` (layout cũ `src/` không còn tồn tại). Test bug, không phải source bug — nhưng làm suite đỏ.

### BUG-9 — LOW: `docs/api.md` tham chiếu module `correction` đã đổi tên

- `docs/api.md:116` — xem mục 2.

---

## 5. Kết quả chi tiết theo nhóm

### A. Input — PASS

| Case | Kết quả |
|---|---|
| JPG/PNG/BMP bytes hợp lệ | PASS (`load_image_from_bytes`) |
| Bytes rác / rỗng | PASS — trả `success=False` |
| File >10MB | PASS — `validate_file_size` reject |
| Ảnh <10px | PASS — `validate_image` reject |
| Ảnh >4000px | PASS — `validate_image_dimensions` reject |
| Grayscale input | PASS — `imdecode(IMREAD_COLOR)` → BGR |
| dtype khác uint8 | PASS — reject |
| TIFF (ngoài whitelist UI) | Loader decode được (informational — UI `file_uploader type=` vẫn chặn phía client) |

### B. Detection — FAIL (BUG-1)

Tập ảnh synthetic có nhãn góc (7 case): clean contrast, low contrast, skewed, nhiều rectangle gây nhiễu, grayscale, noise, doc nhỏ.

- **Localization:** detector tìm đúng point set trong cả 7/7 case (confidence = 1.0).
- **Ordering:** 0/7 đúng thứ tự TL,TR,BR,BL — tất cả bị swap TR↔BL.
- **Success rate danh nghĩa:** 7/7 `success=True`, nhưng **0/7 usable** sau BUG-1.
- Ảnh không có tài liệu (blank/texture noise): trả `success=False` đúng, không crash.
- Manual corners: shape sai → reject đúng; self-intersect → reject đúng; **out-of-bounds không bị detect layer chặn nhưng perspective layer reject đúng** (defense-in-depth hoạt động).
- Ảnh ví dụ thật trong repo (`example*.jpg`): 3/6 detect thành công — nhưng output sai hướng do BUG-1.

### C. Perspective — PASS (validation tốt) / FAIL (kế thừa BUG-1)

| Case | Kết quả |
|---|---|
| Corner order đúng + non-flip marker | PASS khi gọi trực tiếp với corners đúng |
| Tọa độ ngoài ảnh | PASS — reject "out of image bounds" |
| 4 góc trùng / collinear / self-intersect (bowtie) | PASS — reject |
| Shape sai / list input | PASS |
| Padding variant | PASS — output lớn hơn base |
| Extreme skew | PASS |
| Qua pipeline | FAIL — sai hướng do BUG-1 |

### D. Enhancement — PASS (có edge cases)

- Tất cả method: gaussian/median/bilateral/none, histogram_eq/clahe/none, global/otsu/adaptive_mean/adaptive_gaussian/none, unsharp_mask/kernel/none, morphological shadow — đều trả đúng dtype uint8, shape bảo toàn (trừ threshold → 2D grayscale đúng thiết kế).
- Ảnh gốc không bị mutate (copy đúng).
- Method lạ → `ValueError` rõ ràng.
- `unsharp_mask radius=2` (even) → cv2 error, nhưng `enhance_document` bắt và trả `success=False` graceful — chấp nhận được, thiếu validate param.
- Config key lạ → TypeError không bắt (BUG-7).

### E. Pipeline — FAIL do BUG-1; còn lại OK

- End-to-end manual corners: chạy được, `success=True`, đủ scanned+enhanced — **nhưng ảnh sai hướng**.
- Auto detection trên synthetic: `success=True` — sai hướng.
- Detection fail → `process_document_with_fallback` trả `needs_manual_corners=True` đúng.
- **Processing time:** <0.4s cho ảnh ví dụ; ~0.5–1s cho ảnh 1000×750 — **đạt KPI <3s**.
- `smartscan.core.process_document` stub → None (BUG-3).

### F. UI — NOT VERIFIED end-to-end / FAIL tĩnh

- `smartscan/ui/app.py`: **ImportError ngay khi load** (BUG-2) → app không start được. Không thể kiểm thử tương tác Streamlit trong môi trường này.
- Root `app.py`: ImportError do `src/` (BUG-5).
- Logic review: RGB↔BGR conversion đúng; download buttons guard `enhanced_image is not None`; partial-success (enhancement fail) vẫn trả scanned_image — thiết kế hợp lý. `convert_bgr_to_rgb` trên ảnh 2D grayscale không crash (OpenCV replicate kênh) — đã kiểm chứng.

---

## 6. Khuyến nghị nghiệm thu

| Mức | Hành động |
|---|---|
| **Blocker** | Fix BUG-1 (`order_corners` sign bug) + thêm regression test assert corner order; fix BUG-2 (import `encode_image_to_bytes`); fix BUG-3 (stub `process_document`); fix BUG-4 (sys.path) |
| **Should-fix** | BUG-5 (xóa/sửa root app.py), BUG-6 (fallback signature), BUG-8 (test import `src`) |
| **Nice-to-have** | BUG-7 (validate config keys), BUG-9 (docs), validate `radius`/`kernel_size` chẵn trong enhancement |

**Trạng thái nghiệm thu: REJECTED** — pipeline end-to-end không đạt vì output sai hình học (BUG-1) và UI không khởi động được (BUG-2).

**Sau khi fix BUG-1/2/3/4 cần re-test:** detection ordering trên labeled set, end-to-end orientation check (marker test), và smoke test `streamlit run`.

---

## Phụ lục — File test do QA tạo

- `tests/test_qa_independent.py` — 64 test case độc lập (input, detection labeled-set, perspective edge cases, enhancement từng filter, pipeline, formats). Kết quả: 57 pass / 7 fail (fail = BUG-1).

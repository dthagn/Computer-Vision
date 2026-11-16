# SmartScan — Rebuild Plan / Baseline Audit

**Ngày audit:** 2026-11-09  
**Nhánh làm việc:** `rebuild/smartscan-product`  
**Phạm vi:** audit source hiện tại, dependency, test baseline và kế hoạch refactor theo quy trình `Preserve → Analyze → Refactor → Integrate → Test → Improve`.

> Tài liệu này là baseline trước khi refactor. Chưa có source code nào bị xóa, di chuyển hoặc viết lại hàng loạt.

---

## 1. Trạng thái Git và an toàn thay đổi

- Repository có Git, branch gốc trước audit: `Test`.
- Working tree sạch trước khi tạo `REBUILD_PLAN.md`.
- Đã tạo branch cục bộ `rebuild/smartscan-product` để chứa các thay đổi rebuild.
- Không push, không đổi Git config, không rewrite history.
- Các file cache `__pycache__/*.pyc` sinh ra trong lúc chạy test đã được dọn; working tree trở lại sạch sau đó.

---

## 2. Môi trường và dependency thực tế

Lệnh `python` trên PATH hiện trỏ tới WindowsApps stub và không chạy được (`exit 49`). Dùng `py` launcher:

```powershell
py --version
py -m pytest tests -q
py -m streamlit run smartscan/ui/app.py
```

Phiên bản đã kiểm tra:

| Thành phần | Phiên bản |
|---|---:|
| Python | 3.13.1 |
| OpenCV (`cv2`) | 5.0.0 |
| NumPy | 2.4.6 |
| Streamlit | 1.57.0 |
| pytest | 9.2.0 |
| Pillow | 12.2.0 |

Ghi chú:

- `requirements.txt` khai báo `opencv-python`, `numpy`, `streamlit`, `pytest`, `pytest-cov`, `black`, `flake8`.
- Pillow đã cài trong môi trường nhưng chưa có trong `requirements.txt`; source hiện tại không import Pillow trực tiếp.
- Không có lock file; cần ghi rõ version kiểm thử trong tài liệu cuối.

---

## 3. Kết quả test baseline

### 3.1 Suite test chính thức trong `tests/`

Lệnh:

```powershell
py -m pytest tests -q
```

Kết quả chạy ngày 2026-11-09:

- **249 tests collected**
- **248 passed**
- **1 failed**
- Thời gian khoảng 16–17 giây

Test fail duy nhất:

```text
tests/test_qa_independent.py::TestDetectionSynthetic::test_detection_case[extra_rectangles]
AssertionError: extra_rectangles: detection failed - Could not detect document with sufficient confidence
```

Đã chạy lại test đơn lẻ và toàn suite; lỗi vẫn tái hiện trong các lần chạy này.

### 3.2 Chẩn đoán `extra_rectangles`

Test dùng `hash(case) % 1000` làm seed. Vì Python hash bị salt theo process, seed có thể thay đổi giữa các lần chạy; đây là một vấn đề về tính tái lập của test, cần sửa ở phase QA mà không làm giảm tiêu chuẩn kiểm thử.

Chẩn đoán thủ công trên 30 seed cố định cho case `extra_rects=4`:

- 17/30 detection thành công với corner error trung bình < 60 px.
- 13/30 detection thất bại, `confidence = 0.0`, message `Could not detect document with sufficient confidence`.
- Không quan sát thấy trường hợp thành công nhưng sai thứ tự góc trong mẫu này.

Nguyên nhân kỹ thuật sơ bộ:

- `detect_document()` hiện dùng `cv2.findContours(..., RETR_EXTERNAL, ...)` trên edge map sau Canny + morphology close.
- Khi các hình chữ nhật phụ chạm/nối với tài liệu, contour ngoài cùng có thể bao cả cụm object.
- Với seed lỗi, contour ứng viên có khoảng 12 điểm sau `approxPolyDP`; convex hull xấp xỉ còn 6 điểm, nên không còn candidate tứ giác hợp lệ.
- Hàm `find_document_contour()` chỉ giữ contour sau khi approximate/hull đúng 4 điểm; không có fallback cho contour phức tạp hoặc nhiều contour con.

Kết luận: đây là lỗi robustness của detection, không phải lỗi test. Cần cải tiến candidate extraction và fallback trong phase Core Refactor.

### 3.3 Pytest ở thư mục gốc

Lệnh:

```powershell
py -m pytest -q
```

Không chạy được do collection error:

```text
ModuleNotFoundError: No module named 'pipeline'
```

Nguyên nhân: `test_pipeline_simple.py` ở root vẫn import layout cũ phẳng (`pipeline`, `image_loader`) và chèn `src/` không tồn tại. Nếu bỏ qua file này:

```powershell
py -m pytest -q --ignore=test_pipeline_simple.py
```

kết quả vẫn là `tests/`: **248 passed, 1 failed**.

Các script root còn dùng import cũ hoặc không phải test chuẩn:

- `quick_test.py`: import `preprocessing`, `detection`, `pipeline`, ... layout `src/` cũ.
- `verify_imports.py`: import `pipeline`, `image_loader`, `utils`, `config` layout cũ.
- `example_usage.py`: import `src.detection`, `src.perspective`, `src.preprocessing`.
- `test_structure.py`: import `smartscan.*` đúng nhưng chạy print khi import; không có test function.
- `test_pipeline_simple.py`: import sai và được pytest collect nhầm.

Không xóa các file này trong phase audit. Kế hoạch là chuẩn hóa hoặc cô lập chúng ở phase test/docs.

### 3.4 Smoke test UI bằng Streamlit AppTest

Import UI đã thành công:

```powershell
py -c "from smartscan.ui.app import main"
```

Nhưng chạy app qua `streamlit.testing.v1.AppTest` phát hiện crash thực tế:

```text
streamlit.errors.StreamlitAPIException:
st.session_state.rot_quarter cannot be modified after the widget with key `rot_quarter` is instantiated.
```

Vị trí: `smartscan/ui/app.py` gán `st.session_state.rot_quarter` và `st.session_state.rot_angle` ngay sau khi widget cùng key đã được tạo. Đây là lỗi UI nghiêm trọng: giao diện hiện không ổn định/không thể xem là đạt để demo end-to-end.

---

## 4. Bản đồ module hiện tại

### 4.1 Giữ lại và tận dụng

| Module | Đánh giá |
|---|---|
| `smartscan/core/preprocessing.py` | Tốt. Validate ảnh, resize giữ tỷ lệ, grayscale, blur, Canny, morphology, rotation 90°/affine, map tọa độ. Có thể giữ API. |
| `smartscan/core/detection.py` | Có nền tảng tốt: nhiều Canny params, contour scoring, convexity/quadrilateral heuristic, manual corners, debug image. `order_corners()` hiện đã đúng dấu `x-y` và có regression test. Cần nâng cấp robustness khi contour bị merge/nhiễu. |
| `smartscan/core/perspective.py` | Tốt. Validate corners, bounds, duplicate, collinear, self-intersection; homography + warp; có padding variant. Cần kiểm tra output size cap và tích hợp stage API. |
| `smartscan/core/enhancement.py` | Phong phú: denoise Gaussian/Median/Bilateral, histogram equalization, CLAHE, threshold global/Otsu/adaptive, sharpen unsharp/kernel, morphological shadow correction. Cần thêm brightness/contrast điều khiển rõ ràng, validate config và preset đúng yêu cầu mới. |
| `smartscan/core/pipeline.py` | Có orchestration `process_document`, fallback, update enhancement, presets. Cần chuẩn hóa stage result, bảo toàn `scanned_image` khi enhancement lỗi, tránh crash với config key lạ. |
| `smartscan/utils/image_loader.py` | Tốt cho decode/validate upload: giới hạn 10MB, kích thước tối đa 4000px, JPG/PNG/BMP decode qua OpenCV. |
| `smartscan/utils/utils.py` | Có draw corners, comparison, encode bytes, image info, debug grid. Hữu ích cho UI/export. |
| `smartscan/ui/app.py` | Có ý tưởng upload/rotate/enhancement/download nhưng chưa đạt yêu cầu 5 bước, session state lỗi và thiếu review trực quan. Cần refactor lớn nhưng giữ Streamlit. |
| `app.py` root | Đã delegate đúng tới `smartscan.ui.app.main`; không còn là file stale như tài liệu cũ. |

### 4.2 Cần sửa/nâng cấp

| Vấn đề | Mức độ | Hướng xử lý dự kiến |
|---|---|---|
| Detection fail với `extra_rectangles` | High | Cải tiến contour candidate extraction, fallback đa epsilon/contour hierarchy/minAreaRect candidate, giữ API và confidence. |
| UI crash session state | Critical | Bỏ gán session state sau widget instantiation; tách state schema và reset rõ ràng. |
| UI chưa có quy trình 5 bước | High | Refactor dashboard thành Upload → Detect & Review → Perspective → Enhancement → Preview & Export. |
| Chưa có manual corner review trực quan đầy đủ | High | Hiển thị overlay TL/TR/BR/BL, numeric adjustment, re-detect, confirm; không tự warp khi chưa confirm. |
| Enhancement mặc định có thể ra B&W | Medium | Default preset nên giữ màu/tự nhiên; B&W chỉ là preset rõ ràng. |
| Thiếu brightness adjustment rõ ràng | Medium | Thêm tham số brightness/contrast an toàn nếu phù hợp, hoặc preset Low Light/Text Enhancement sử dụng thuật toán hiện có một cách minh bạch. |
| `process_document` exception path có thể làm UI mất scanned image | Medium | Chuẩn hóa stage result; enhancement fail phải giữ scanned image ở mọi nhánh. |
| `update_enhancement` chưa bắt exception/config key lạ | Medium | Validate/deepcopy config, trả failure dict thay vì raise. |
| Script/test root stale | Medium | Sửa import sang `smartscan.*` hoặc loại khỏi pytest collection bằng cấu hình phù hợp; không xóa file. |
| Test `extra_rectangles` dùng `hash()` seed | Medium | Đổi sang seed cố định deterministic trong phase test; không giảm assertion. |
| Docs cũ không khớp source | Medium | Cập nhật `docs/api.md`, `docs/architecture.md`, README và QA report ở phase cuối. |

### 4.3 Module trùng/lặp cần theo dõi

- `smartscan/utils/image_utils.py::validate_image` trùng chức năng với `smartscan/core/preprocessing.py::validate_image` nhưng trả kiểu khác.
- `smartscan/utils/utils.py` và `smartscan/utils/image_utils.py` có converter trùng (`rgb_to_bgr`, `bgr_to_rgb`).
- `check_self_intersection()` tồn tại ở cả `detection.py` và `perspective.py`.

Không gộp ngay trong baseline. Chỉ refactor khi chắc chắn không phá API/test; ưu tiên behavior trước, deduplicate sau.

---

## 5. Đánh giá khoảng cách so với sản phẩm mục tiêu

### Đã có nền tảng tốt

- Pipeline detect → perspective → enhance đã tồn tại và phần lớn unit/integration test pass.
- Perspective validation khá chặt.
- Enhancement có nhiều thuật toán thật, không placeholder.
- Loader/encoder đủ cho MVP upload/download.
- Corner ordering hiện đã được sửa so với báo cáo QA cũ.

### Khoảng cách chính

1. UI hiện crash khi khởi tạo do session state.
2. UI hiện chạy một nút “Bắt đầu xử lý” cho toàn pipeline; chưa cho review từng giai đoạn.
3. Manual corners chỉ là 8 number input sau khi detection fail; chưa phải bước review có overlay và xác nhận rõ ràng.
4. Detection chưa đủ robust khi nhiều vật thể/nhiễu.
5. Enhancement config/preset chưa khớp đầy đủ 5 preset yêu cầu và chưa có brightness control rõ ràng.
6. Một số API trả dictionary không đồng nhất; chưa có stage API rõ ràng cho UI từng bước.
7. Tài liệu cũ còn mô tả layout/API sai (`src/`, `correction.py`, return keys cũ).

---

## 6. Kế hoạch triển khai theo giai đoạn

### Giai đoạn 2 — Core Refactor

Mục tiêu: sửa detection robustness, chuẩn hóa corner order/validation, hoàn thiện enhancement config/preset, giữ API tương thích.

Việc dự kiến:

1. `smartscan/core/detection.py`
   - Bổ sung candidate extraction an toàn cho trường hợp contour bị merge.
   - Thử nhiều epsilon `approxPolyDP`, `RETR_EXTERNAL`/`RETR_LIST`/`RETR_CCOMP` hoặc hierarchy phù hợp.
   - Có fallback candidate từ convex hull/minimum area rectangle nhưng vẫn phải qua `order_corners()` + self-intersection + score.
   - Trả confidence và debug/candidate info mà không phá dictionary hiện tại.
   - Giữ manual corners path và validation hiện có.

2. `smartscan/core/perspective.py`
   - Giữ API `correct_perspective()` và `apply_perspective_with_padding()`.
   - Bổ sung kiểm tra output size hợp lý để tránh warp quá lớn/nhỏ bất thường.
   - Đảm bảo corners phải đúng thứ tự TL/TR/BR/BL trước transform; nếu cần, export helper chuẩn hóa.

3. `smartscan/core/enhancement.py` + `smartscan/utils/config.py`
   - Thêm `sanitize/validate enhancement config` hoặc deep copy an toàn.
   - Bổ sung brightness/contrast control tối thiểu, có default trung tính.
   - Mở rộng presets thành: `original_natural`, `color_document`, `black_white`, `low_light`, `text_enhancement`; giữ alias preset cũ nếu cần tương thích.
   - Đảm bảo default không ép mọi ảnh sang B&W.

4. `smartscan/core/pipeline.py`
   - Chuẩn hóa stage result: detection, perspective, enhancement có `success`, `message`, `time`, output riêng.
   - Thêm API stage-level nếu cần cho UI, ví dụ detect-only / perspective-only / enhance-only, nhưng không làm phức tạp hóa pipeline hiện tại.
   - Đảm bảo enhancement exception/failure vẫn giữ `scanned_image`.
   - Bắt `TypeError`/config lỗi và trả failure dict.

Kiểm thử sau mỗi module:

```powershell
py -m pytest tests/test_detection.py tests/test_perspective.py tests/test_enhancement.py tests/test_pipeline.py -q
py -m pytest tests/test_qa_independent.py -q
```

### Giai đoạn 3 — Pipeline Integration

Mục tiêu: kết nối stage APIs thành luồng rõ ràng, bảo toàn ảnh gốc/scanned/enhanced, xử lý lỗi từng công đoạn.

Việc dự kiến:

- Chuẩn hóa result keys và error messages.
- Phân biệt `success` toàn cục với `stage_status` từng bước.
- Bảo toàn `original_image`, `detected_corners`, `scanned_image`, `enhanced_image` đúng ngữ nghĩa.
- Thêm integration tests cho:
  - Upload bytes → detect.
  - Detect → manual adjustment.
  - Manual adjustment → perspective.
  - Perspective → enhancement.
  - Enhancement failure → vẫn export scanned.
  - Upload ảnh mới → reset downstream.

Không đổi thuật toán ngoài phạm vi đã audit trừ khi test chứng minh cần thiết.

### Giai đoạn 4 — UI Refactor

Mục tiêu: dashboard 5 bước, state rõ ràng, review/manual corners, export an toàn.

Cấu trúc dự kiến:

- Giữ `smartscan/ui/app.py` làm entrypoint Streamlit.
- Tách state helper sang `smartscan/ui/state.py` nếu cần để tránh `app.py` quá lớn; không tạo framework mới.
- Có thể tách render component sang `smartscan/ui/components.py` chỉ khi app.py trở nên khó bảo trì.

Luồng UI:

1. **Upload Document**
   - JPG/JPEG/PNG (giữ BMP nếu muốn tương thích, nhưng tài liệu ghi rõ).
   - Validate file/dimensions.
   - Hiển thị ảnh gốc, thông tin ảnh.
   - Rotate 90°/góc tùy ý/reset.
   - Upload mới hoặc đổi rotation phải reset detection/perspective/enhancement.

2. **Detect & Review**
   - Nút “Detect document”.
   - Hiển thị overlay 4 góc TL/TR/BR/BL và confidence.
   - Nếu fail: manual corner input + hướng dẫn.
   - Nếu success: cho phép chỉnh tọa độ, re-detect, confirm corners.
   - Không tự động warp trước khi confirm.

3. **Perspective Correction**
   - Dùng corners đã confirm.
   - Hiển thị ảnh trước/sau, output size, nút back/retry.
   - Lưu `scanned_image` độc lập với enhancement.

4. **Image Enhancement**
   - Preset + advanced controls.
   - Nút “Run enhancement” và “Re-run enhancement”.
   - Thay đổi config chỉ chạy lại enhancement, không detect lại.
   - Enhancement fail vẫn giữ scanned image và báo lỗi rõ.

5. **Preview & Export**
   - So sánh original/scanned/enhanced.
   - Download JPG/PNG cho scanned/enhanced với tên file hợp lý.
   - Hiển thị stage status và processing time thực tế.

Session state schema dự kiến:

- `upload_signature`: nhận diện file + rotation hiện tại.
- `source_image`: ảnh BGR sau rotate hợp lệ.
- `stage`: bước hiện tại hoặc completed flags.
- `corners`: corners confirmed `(4,2)` float32.
- `corner_source`: `auto` hoặc `manual`.
- `scanned_image`: ảnh sau perspective.
- `enhanced_image`: ảnh sau enhancement hoặc `None`.
- `enhancement_config`: config đã deepcopy/sanitize.
- `stage_results`: detection/perspective/enhancement metadata.
- `last_error`: lỗi gần nhất theo stage.

Quy tắc reset:

- Upload mới → reset toàn bộ downstream.
- Đổi rotation → reset detection trở đi.
- Đổi corners → reset perspective/enhancement.
- Đổi enhancement config → chỉ reset enhanced_image.
- Enhancement fail → không reset scanned_image.

### Giai đoạn 5 — QA & Documentation

Mục tiêu: kiểm thử toàn diện và tài liệu khớp source.

Việc dự kiến:

- Sửa `test_qa_independent.py` seed deterministic; giữ nguyên assertion.
- Sửa/cô lập root scripts cũ để `py -m pytest -q` không còn collection error.
- Thêm UI/AppTest smoke test cho flow chính nếu khả thi.
- Cập nhật `README.md`, `docs/api.md`, `docs/architecture.md`, `docs/algorithms.md`.
- Tạo/cập nhật QA report với số liệu thực tế mới.
- Ghi rõ giới hạn thuật toán và cách bảo vệ.

### Giai đoạn 6 — Final Acceptance

Mục tiêu: xác nhận sản phẩm chạy end-to-end.

Checklist:

- `py -m pytest -q` pass hoặc mọi fail còn lại được giải thích có bằng chứng.
- `py -m streamlit run smartscan/ui/app.py` render không exception.
- Upload → detect → review/manual corners → perspective → enhancement → preview/export chạy thật.
- Các edge cases: no document, skew, low light, nhiều rectangle, ảnh lỗi, upload mới giữa chừng, đổi góc sau scan, enhancement fail.
- Tạo `FINAL_REPORT.md` với install/run instructions, test results, limitations.

---

## 7. Tiêu chí không được vi phạm trong các phase sau

- Không xóa source/module đang hoạt động nếu chưa chứng minh unused.
- Không viết lại toàn bộ dự án thành project mới.
- Không để UI chứa thuật toán xử lý ảnh; UI chỉ gọi core/utils API.
- Không để pipeline phụ thuộc Streamlit.
- Không placeholder/fake result.
- Không giảm tiêu chuẩn test để pass.
- Không chỉnh sửa hàng loạt trước khi hiểu dependency.
- Mọi thay đổi lớn phải chạy test liên quan ngay sau đó.
- Giữ backward compatibility API ở mức hợp lý; nếu breaking change cần thiết phải ghi rõ trong plan/report.

---

## 8. Nguy cơ và quyết định cần thận trọng

1. **Detection fallback có thể chọn sai vật thể.** Cần ưu tiên candidate có hình tứ giác lớn, hợp lý, confidence cao; manual review trong UI là lớp bảo vệ cuối.
2. **Manual corner adjustment bằng Streamlit hạn chế.** Sẽ dùng numeric inputs/sliders và preview overlay; không thêm dependency nặng chỉ để drag-drop nếu không cần.
3. **Brightness/contrast mới phải trung tính mặc định.** Không làm thay đổi ảnh khi user không yêu cầu.
4. **Root scripts cũ không phải source chính.** Sẽ sửa import hoặc cấu hình pytest, không xóa.
5. **Tài liệu cũ nhiều mâu thuẫn.** Tài liệu mới (`README`, `docs/api`, `docs/architecture`, `FINAL_REPORT`) sẽ là nguồn chuẩn sau phase docs.

---

## 9. Trạng thái sau Baseline Audit

Đã hoàn thành:

- Đọc cấu trúc và source chính.
- Kiểm tra Git status và tạo branch làm việc.
- Xác định dependency thực tế.
- Chạy baseline `tests/`.
- Chẩn đoán sơ bộ lỗi `extra_rectangles`.
- Smoke test UI và phát hiện crash session state.
- Lập kế hoạch refactor theo phase.

Chưa thực hiện:

- Chưa sửa source code core/UI/test.
- Chưa đổi requirements.
- Chưa cập nhật README/docs ngoài file plan này.

Bước tiếp theo an toàn: bắt đầu **Giai đoạn 2 – Core Refactor** với detection trước, sau đó perspective/enhancement/pipeline; chạy unit tests sau từng module.

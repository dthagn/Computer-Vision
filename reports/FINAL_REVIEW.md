# SmartScan — Final Review và Kết luận Nghiệm thu

**Ngày rà soát:** 2026-11-07  
**Phạm vi:** `PROJECT_SPEC.md`, source `smartscan/`, tests, `reports/QA_REPORT.md`, hướng dẫn cài đặt và tài liệu demo mới.  
**Nguyên tắc:** chỉ mô tả chức năng đã có trong source; không tự sửa kiến trúc/code mà chuyển yêu cầu cho Agent phụ trách.

## 1. Kết luận điều hành

**Trạng thái: CHƯA ĐẠT / REJECTED cho demo nghiệm thu tự động.**

Lý do blocker:

1. `smartscan/core/detection.py::order_corners()` đang đảo dấu hiệu `x-y` do dùng `np.diff`, làm TR/BL bị swap; QA đã chứng minh ảnh pipeline bị xoay/gương.
2. `smartscan/ui/app.py` import `encode_image_to_bytes` từ `image_loader` trong khi hàm nằm ở `utils.py`; import UI thất bại.
3. `smartscan/core/__init__.py::process_document` là stub trả `None`, tạo API trap.
4. UI path handling và file `app.py` root stale làm điểm vào ứng dụng không đáng tin.
5. Bộ test hiện có **237 passed, 9 failed** khi chạy thực tế ngày 2026-11-07.

Các module enhancement và perspective có nhiều kiểm thử đạt và validation tốt, nhưng không thể bù cho lỗi hình học toàn pipeline và UI không render. Không được tuyên bố sản phẩm hoàn thành chỉ vì phần lớn unit test pass.

## 2. Bằng chứng kiểm tra thực tế

### 2.1 Môi trường và dependencies

- Python: `3.13.1` qua `py` launcher.
- `py -m pip check`: **No broken requirements found**.
- Dependencies theo QA report: `opencv-python 5.0.0.93`, `numpy 2.4.6`, `streamlit 1.57.0`, `pytest 9.2.0`.
- `requirements.txt` khai báo các dependency tối thiểu hợp lý cho Python package; chưa có lock file nên môi trường tái lập có thể khác version.

### 2.2 Test suite

Lệnh:

```powershell
py -m pytest tests -q
```

Kết quả thực tế: **237 passed, 9 failed, 1 warning** trong khoảng 15 giây.

9 failure:

- `tests/test_detection.py::TestDetectDocument::test_detect_document_self_intersecting_manual_corners` — import stale `from src.detection import ...`.
- `tests/test_pipeline.py::TestPipelineWithFallback::test_process_document_with_fallback_success` — `process_document_with_fallback()` không nhận `manual_corners`.
- 7 ca `tests/test_qa_independent.py::TestDetectionSynthetic` — corner order/orientation sai trên các ảnh synthetic clean, low contrast, skewed, extra rectangles, grayscale, noisy, small doc.

### 2.3 Import API và UI

- `from smartscan.core import process_document` import được nhưng gọi hàm trả `None` do stub.
- `from smartscan.ui.app import main` thất bại:

```text
ImportError: cannot import name 'encode_image_to_bytes'
from 'smartscan.utils.image_loader'
```

- `py -m streamlit run smartscan/ui/app.py` khởi động server nhưng log ghi `Uncaught app execution` vì cùng ImportError. `/healthz` trả HTTP 200 chỉ chứng minh server sống, **không** chứng minh app render thành công.
- Root `app.py` import `pipeline`, `image_loader`, `utils`, `config` không prefix `smartscan` và chèn `src/` không tồn tại; đây là file stale.

### 2.4 Pipeline và performance

- `smartscan.core.pipeline.process_document` có implementation đầy đủ detect → perspective → enhance.
- Với ảnh synthetic 1000×750 và manual ground-truth corners, 10 lần chạy đều `success=True`; thời gian nội bộ min ≈ 0.0296s, median ≈ 0.0339s, max ≈ 0.3452s trong lần đo hiện tại. Đây là phép đo một fixture, không phải benchmark đại diện.
- Auto detection trên cùng fixture trả `success=True` nhưng corner order sai; corner error trung bình theo test helper ≈ 320.16 px. Vì vậy thời gian nhanh không bù được kết quả hình học sai.
- QA report ghi nhận các fixture/ảnh ví dụ xử lý dưới khoảng 0.4–1 giây và mục tiêu spec <3 giây có dấu hiệu khả thi, nhưng cần đo lại trên phần cứng/dataset chuẩn sau khi fix.

## 3. Đối chiếu mục tiêu đề tài với implementation

| Mục tiêu trong `PROJECT_SPEC.md` | Trạng thái đối chiếu | Nhận xét |
|---|---|---|
| Upload JPG/PNG | Có trong UI/loader; UI hiện không chạy do import bug | Loader decode JPG/PNG/BMP; UI whitelist JPG/JPEG/PNG/BMP |
| Phát hiện 4 góc giấy | Có module và heuristic, nhưng BUG-1 làm output sai hướng | Không được xem là đạt cho tới khi ordering/orientation pass |
| Hiệu chỉnh phối cảnh | Có homography + warp + padding; validation tốt | Chất lượng phụ thuộc hoàn toàn vào corners đúng |
| Contrast/brightness, denoise, binarization, color correction | Có implementation enhancement; “color correction” thực tế là CLAHE trên Lab/contrast và shadow correction, không phải white balance/gamma như API cũ mô tả | Cần gọi đúng tên chức năng trong tài liệu |
| Download kết quả | UI có code download JPG/PNG; chưa verify được do UI crash | Cần smoke test sau fix |
| Hoàn thành <3s cho ảnh A4 | Chưa đủ bằng chứng tổng quát | Chỉ có fixture/synthetic timing, chưa benchmark chuẩn |
| >90% tài liệu đơn giản | Không có bằng chứng | Không được tuyên bố; cần dataset nhãn thật |
| Unit tests cho module chính | Có nhiều test, nhưng suite chưa xanh | 237 pass / 9 fail |

## 4. Thuật toán được mô tả có tồn tại không?

Các thuật toán sau **đã được xác minh trong source**:

- Resize giữ tỷ lệ, grayscale, Gaussian blur, Canny, morphology close.
- Contour detection, `approxPolyDP`, convex hull, convexity và quadrilateral heuristic.
- Corner ordering (tồn tại nhưng đang sai).
- Self-intersection và corner validation.
- Homography bằng `getPerspectiveTransform`, warp bằng `warpPerspective`, padding variant.
- Gaussian/Median/Bilateral denoise.
- Histogram equalization và CLAHE.
- Global threshold, Otsu, adaptive mean, adaptive Gaussian.
- Unsharp mask và kernel sharpening.
- Morphological shadow/uneven illumination correction.

Không đưa vào tài liệu demo các chức năng chỉ có trong tài liệu cũ nhưng không đúng implementation hiện tại, chẳng hạn OCR, white balance/gamma color correction, hay pipeline trả `corrected`/`enhanced` keys như `docs/api.md` mô tả.

## 5. Chất lượng tài liệu và tính nhất quán

### Đã hoàn thiện/bàn giao trong đợt review này

- `README.md`: tạo mới, nêu trạng thái chưa đạt, tính năng thực tế, kiến trúc, cài đặt, chạy app, cấu trúc, test và link tài liệu.
- `docs/algorithms.md`: tạo mới, giải thích thuật toán có trong source, đầu vào/đầu ra, ưu nhược điểm, giới hạn và code map.
- `docs/DEMO_GUIDE.md`: tạo mới, chuẩn bị dữ liệu, chạy app, kịch bản demo, success/failure criteria, rollback và checklist.
- `docs/DEMO_TEST_CASES.md`: tạo mới, danh sách test case theo nhóm cài đặt, detection, perspective, enhancement, pipeline, format/UI và regression.
- `docs/DEFENSE_QA.md`: tạo mới, bộ câu hỏi/câu trả lời về thuật toán, OpenCV, pipeline, giới hạn, metric và lựa chọn thiết kế.
- `AGENT_6_FIX_REQUEST.md`: tạo mới, chuyển yêu cầu sửa cho Agent phụ trách; không tự sửa code.

### Tài liệu cũ cần đồng bộ bởi Agent phụ trách

Các file `docs/api.md`, `docs/architecture.md`, `README_INTEGRATION.md`, `ENHANCEMENT_ALGORITHMS.md`, `ALGORITHM_LIMITATIONS.md` còn chứa thông tin lịch sử không khớp hoàn toàn với layout/API hiện tại (`src/`, `correction.py`, return type cũ, import sai). Không dùng chúng làm nguồn chuẩn cho bảo vệ cho tới khi cập nhật. Bộ tài liệu mới đã ghi rõ điều này hoặc tránh các tuyên bố sai.

## 6. Danh sách yêu cầu chuyển Agent phụ trách

Chi tiết đầy đủ nằm trong [AGENT_6_FIX_REQUEST.md](../AGENT_6_FIX_REQUEST.md). Tóm tắt:

1. **CRITICAL:** sửa `order_corners` và thêm regression orientation.
2. **CRITICAL:** sửa import `encode_image_to_bytes` trong UI.
3. **HIGH:** sửa sys.path/project root khi chạy Streamlit.
4. **HIGH:** sửa/xóa stub `smartscan.core.process_document`.
5. **MEDIUM:** xử lý `process_document_with_fallback(manual_corners)`, root `app.py` stale, test import `src.*`, config key lạ và docs cũ.
6. Chạy lại toàn bộ test và smoke test UI sau khi sửa.

## 7. Điều kiện để chuyển sang “ĐẠT”

Phải đồng thời thỏa mãn:

- Corner order đúng trên synthetic và marker orientation end-to-end.
- UI import/render thành công; upload → process → preview → download chạy end-to-end.
- Package-level API không còn trả `None` hoặc được định nghĩa rõ.
- `py -m pytest tests -q` không còn failure liên quan source/test stale.
- Tài liệu demo khớp source và không còn mô tả module/API cũ.
- Có benchmark mới trên dataset/ảnh chuẩn; không dùng số liệu QA cũ để tuyên bố kết quả mới.

## 8. Khuyến nghị trình bày bảo vệ

Nếu chưa kịp fix, có thể trình bày như bài toán thiết kế + hiện trạng kiểm thử trung thực:

- Giải thích pipeline và thuật toán đúng.
- Demo các module riêng biệt có test pass nếu cần.
- Thừa nhận BUG-1/BUG-2, trình bày QA report như bằng chứng kiểm thử độc lập và kế hoạch sửa.
- Không tuyên bố “ứng dụng chạy hoàn chỉnh” hoặc “accuracy >90%” khi chưa có bằng chứng.

Nếu đã fix, chạy lại checklist trong [docs/DEMO_GUIDE.md](../docs/DEMO_GUIDE.md) trước khi demo.

## 9. File bàn giao

- [README.md](../README.md)
- [docs/algorithms.md](../docs/algorithms.md)
- [docs/DEMO_GUIDE.md](../docs/DEMO_GUIDE.md)
- [docs/DEMO_TEST_CASES.md](../docs/DEMO_TEST_CASES.md)
- [docs/DEFENSE_QA.md](../docs/DEFENSE_QA.md)
- [AGENT_6_FIX_REQUEST.md](../AGENT_6_FIX_REQUEST.md)
- [reports/QA_REPORT.md](QA_REPORT.md)
- [reports/FINAL_REVIEW.md](FINAL_REVIEW.md) — file này

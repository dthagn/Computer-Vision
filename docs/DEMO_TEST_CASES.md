# SmartScan — Danh sách test case trình bày

Bộ này dành cho sinh viên chuẩn bị demo/bảo vệ. **Không đánh dấu các case “đạt” cho tới khi chạy lại trên source đã sửa.** Kết quả hiện tại phải ghi theo thực tế, kể cả fail.

## A. Test cài đặt và smoke test

| ID | Tiền điều kiện | Thao tác | Kết quả mong đợi | Ghi chú hiện tại |
|---|---|---|---|---|
| TC-01 | Python 3.9+, môi trường sạch | `pip install -r requirements.txt` | Cài dependency thành công, `pip check` không báo lỗi | Review: `pip check` pass |
| TC-02 | Đã cài dependencies | `py -m pytest tests -q` | Suite pass hoặc mọi fail được giải thích và xử lý | Hiện 237 pass / 9 fail |
| TC-03 | Codebase hiện tại | `py -c "from smartscan.ui.app import main"` | Import UI không lỗi | Hiện ImportError |
| TC-04 | Sau khi sửa UI | `py -m streamlit run smartscan/ui/app.py` | Server chạy, trang render, không traceback | Server start nhưng app execution lỗi |

## B. Detection — hình học và orientation

| ID | Input | Thao tác | Kết quả mong đợi |
|---|---|---|---|
| TC-05 | Tứ giác chuẩn `(150,100),(650,100),(650,500),(150,500)` | Gọi `order_corners` | Trả TL, TR, BR, BL đúng thứ tự |
| TC-06 | Cùng bốn điểm nhưng hoán vị input | Gọi `order_corners` | Output vẫn TL, TR, BR, BL |
| TC-07 | Ảnh synthetic sạch, tương phản cao | `process_document` auto | `success=True`, góc khớp ground truth trong tolerance |
| TC-08 | Ảnh marker màu ở bốn góc | Pipeline auto + warp | Marker TR input xuất hiện ở TR output; không xoay/mirror |
| TC-09 | Low contrast | Detection | Hoặc detect đúng, hoặc fail graceful; không trả success sai hình học |
| TC-10 | Nhiễu nhẹ | Detection | Edge/contour ổn định sau blur/morphology; ghi nhận nếu fail |
| TC-11 | Nhiều hình chữ nhật nền | Detection | Chọn tài liệu hợp lý hoặc fail; không chọn vật thể sai mà báo confidence cao |
| TC-12 | Ảnh không có tài liệu | Detection/fallback | `success=False` hoặc `needs_manual_corners=True`, không crash |
| TC-13 | Manual corners đúng thứ tự | `process_document(..., manual_corners=...)` | Pipeline tiếp tục tới perspective/enhancement |
| TC-14 | Manual corners tự giao, trùng điểm, ngoài ảnh | Detection/perspective | Reject với message rõ ở lớp phù hợp |

## C. Perspective correction

| ID | Input | Thao tác | Kết quả mong đợi |
|---|---|---|---|
| TC-15 | Bốn góc hợp lệ, hình chữ nhật hơi xiên | `correct_perspective` | Output chữ nhật, cạnh gần trực giao, nội dung không lật |
| TC-16 | Corners đúng TL/TR/BR/BL | `apply_perspective_with_padding` | Output lớn hơn base khoảng padding 5%, có viền trắng |
| TC-17 | Góc ngoài ảnh | `correct_perspective` | `success=False`, message bounds |
| TC-18 | Bow-tie/self-intersect | `correct_perspective` | `success=False` |
| TC-19 | Collinear/trùng điểm | `correct_perspective` | `success=False` |
| TC-20 | Góc cực đoan | Perspective | Ghi nhận méo/chất lượng; không crash |

## D. Enhancement

| ID | Input | Config | Kết quả mong đợi |
|---|---|---|---|
| TC-21 | Ảnh sau scan | `denoise_method='none'` | Bản sao ảnh, dtype/shape giữ nguyên |
| TC-22 | Ảnh có nhiễu | Gaussian/median/bilateral lần lượt | dtype uint8, shape giữ nguyên; đánh giá trực quan mức làm mượt |
| TC-23 | Ảnh tương phản thấp | `histogram_eq`, `clahe` | Tăng contrast; CLAHE giữ sắc màu tốt hơn histogram RGB |
| TC-24 | Ảnh sáng không đều | `global`, `otsu`, `adaptive_mean`, `adaptive_gaussian` | Adaptive thường phù hợp hơn; output là ảnh nhị phân 1 kênh |
| TC-25 | Ảnh mờ | `unsharp_mask`, `kernel`, `none` | Cạnh chữ rõ hơn; strength cao có thể halo |
| TC-26 | Ảnh có gradient sáng | `shadow_correction=True` | Background đồng đều hơn; kiểm tra không làm sai màu quá mức |
| TC-27 | Config method lạ hoặc key lạ | `enhance_document`/pipeline | Lỗi được bắt và trả `success=False` theo contract |
| TC-28 | `return_intermediate=True` | Enhancement | Dictionary có original, denoised, contrast_enhanced, sharpened/thresholded theo bước chạy |

## E. Pipeline và API

| ID | Input | Thao tác | Kết quả mong đợi |
|---|---|---|---|
| TC-29 | Ảnh BGR uint8 hợp lệ | `pipeline.process_document` | Dictionary đủ `success`, images, corners, steps, processing_time |
| TC-30 | Detection fail | `process_document_with_fallback` | `success=False` và `needs_manual_corners=True` |
| TC-31 | Enhancement fail | `process_document` | Có thể partial success với `scanned_image`, `enhanced_image=None`, message rõ |
| TC-32 | Ảnh đã scan | `update_enhancement` | Chỉ chạy lại enhancement, trả thời gian và ảnh mới |
| TC-33 | Package-level import | `from smartscan.core import process_document` | Trả pipeline result hoặc API được định nghĩa rõ; không trả `None` |
| TC-34 | Ảnh 1000×750 | Chạy pipeline nhiều lần | Ghi median/min/max thực tế; mục tiêu spec <3s, nhưng phải báo số đo |

## F. Input/format và UI

| ID | Input | Thao tác | Kết quả mong đợi |
|---|---|---|---|
| TC-35 | JPG/JPEG/PNG/BMP hợp lệ | Upload UI | Decode được, hiển thị preview |
| TC-36 | Bytes rác/rỗng | `load_and_validate_image` | `success=False`, không exception |
| TC-37 | File >10MB | Upload/loader | Reject với thông báo kích thước |
| TC-38 | Ảnh >4000×4000 | Loader | Reject theo `validate_image_dimensions` |
| TC-39 | Ảnh grayscale | Loader/pipeline | OpenCV decode thành BGR; pipeline tiếp tục |
| TC-40 | Kết quả enhanced | Download JPG/PNG | File mở được, màu đúng, kích thước/shape phù hợp |
| TC-41 | Streamlit UI | Render trang | Không traceback; upload, preset, xử lý, manual corners, download hoạt động |

## G. Regression bắt buộc sau khi Agent sửa

1. Test `order_corners` với hoán vị góc và orientation marker end-to-end.
2. Import `smartscan.ui.app` và smoke test Streamlit.
3. Package-level `process_document` không còn là stub.
4. `process_document_with_fallback(manual_corners=...)` hoặc test/API được đồng bộ.
5. Root `app.py` stale được xóa hoặc sửa để không còn import `src/` sai.
6. Test cũ `from src.detection` được sửa sang package thực tế hoặc xóa nếu không còn phù hợp.
7. Chạy `py -m pytest tests -q`; ghi lại số pass/fail thực tế, không dùng số liệu cũ để tuyên bố pass.

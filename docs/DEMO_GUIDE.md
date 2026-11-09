# SmartScan — Hướng dẫn chuẩn bị và chạy demo

## 1. Nguyên tắc an toàn khi demo

Bản source hiện tại **chưa đạt nghiệm thu** vì detection có thể trả góc sai thứ tự, khiến ảnh bị xoay/gương, và Streamlit app chưa render do lỗi import. Không chạy demo như thể mọi chức năng đã hoàn thành. Trước khi bảo vệ, phải yêu cầu Agent phụ trách xử lý [AGENT_6_FIX_REQUEST.md](../AGENT_6_FIX_REQUEST.md), sau đó chạy lại toàn bộ test và smoke-test UI.

Tài liệu này mô tả cách chuẩn bị dữ liệu, các kịch bản có thể thực hiện và tiêu chí đánh giá. Kết quả mong đợi chỉ được ghi là “đạt” sau khi kiểm tra thực tế.

## 2. Chuẩn bị môi trường

Yêu cầu Python 3.9+; môi trường review dùng Python 3.13.1.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Nếu `python` không hoạt động, dùng `py -m pip install -r requirements.txt`. Kiểm tra:

```powershell
py -m pytest tests -q
py -c "from smartscan.ui.app import main; print('UI import OK')"
```

Lệnh import UI hiện **phải thất bại** trên source chưa sửa; đó là dấu hiệu cần sửa trước, không phải lỗi thao tác demo.

## 3. Chuẩn bị bộ ảnh

Nên dùng ít nhất 8–12 ảnh được chụp/chọn trước, không phụ thuộc vào mạng hoặc webcam. Lưu trong thư mục `demo_data/` (có thể tạo khi demo; không cần commit dữ liệu nhạy cảm).

### Nhóm A — ảnh thuận lợi

- Tài liệu A4 trắng, nền tương phản, chiếm khoảng 40%–80% ảnh.
- Tài liệu hơi nghiêng 5°–15°.
- Ảnh JPG và PNG cùng nội dung.
- Marker hình vuông/điểm màu nhỏ đặt ở bốn góc tài liệu để kiểm tra orientation.

### Nhóm B — thử thách vừa phải

- Nền gỗ/bàn có texture nhẹ.
- Ánh sáng hơi không đều.
- Nhiễu JPEG nhẹ.
- Tài liệu có bảng hoặc chữ nhỏ để đánh giá sau enhancement.

### Nhóm C — trường hợp thất bại dự kiến

- Ảnh chỉ có nền, không có tài liệu.
- Tài liệu cùng màu với nền, viền không rõ.
- Nhiều hình chữ nhật/vật thể giống tài liệu.
- Tài liệu bị vật khác che hoặc chiếm quá ít diện tích.
- File rỗng/rác, file >10MB, ảnh >4000×4000 pixel, ảnh <10 pixel.

Không dùng tài liệu thật có thông tin nhạy cảm nếu chỉ cần minh họa thuật toán; có thể che hoặc dùng tài liệu tự tạo.

## 4. Khởi chạy

Sau khi Agent sửa lỗi và test pass, chạy từ project root:

```powershell
py -m streamlit run smartscan/ui/app.py
```

Mở URL local Streamlit cung cấp. Nếu server khởi động nhưng trang có traceback đỏ, không chuyển sang bước xử lý; ghi nhận lỗi và trả Agent UI.

File `app.py` ở root không phải entrypoint chuẩn: nó tham chiếu `src/` không tồn tại. Dùng `smartscan/ui/app.py`.

## 5. Kịch bản demo UI

### Demo 1 — happy path

1. Upload một ảnh thuộc nhóm A.
2. Kiểm tra metadata hiển thị: kích thước, số kênh, dung lượng.
3. Chọn preset `default`.
4. Nhấn **Bắt đầu xử lý**.
5. Mở **Chi tiết xử lý** để xem detection, perspective, enhancement và thời gian.
6. Kiểm tra bốn góc/nhãn TL–TR–BR–BL, ảnh sau warp có phải hình chữ nhật đúng hướng không.
7. Bật/tắt các tùy chọn enhancement và nhấn **Áp dụng enhancement mới**.
8. Tải JPG scanned, JPG enhanced và PNG enhanced.

**Đạt khi:** trang không lỗi; `success=True`; bốn nhãn đúng vị trí; marker ở TR gốc vẫn ở TR output; cạnh tài liệu gần song song/trực giao; có thể tải file mở được.

### Demo 2 — enhancement presets

1. Dùng cùng ảnh sau khi scan.
2. Áp dụng `bw_document` để xem grayscale/binarization.
3. Áp dụng `color_document` hoặc `light_enhancement` để so sánh màu và mức xử lý.
4. Mở phần **So sánh ảnh**.

**Đạt khi:** người trình bày giải thích được khác biệt và không khẳng định “ảnh rõ hơn” chỉ dựa trên cảm tính — cần nêu tiêu chí quan sát: độ tương phản chữ/nền, đứt nét, nhiễu, màu.

### Demo 3 — detection thất bại và manual corners

1. Upload ảnh nhóm C không có tài liệu.
2. Nhấn xử lý; kỳ vọng cảnh báo cần manual corners.
3. Với ảnh có tài liệu nhưng detection fail, nhập tọa độ TL, TR, BR, BL theo đúng thứ tự.
4. Nhấn **Áp dụng manual corners**.

**Đạt khi:** hệ thống không crash; input sai shape/tự giao bị từ chối hoặc báo lỗi rõ; manual corners hợp lệ cho pipeline tiếp tục.

### Demo 4 — input không hợp lệ

1. Thử file rác/không phải ảnh.
2. Thử file quá 10MB hoặc ảnh quá 4000×4000 nếu có fixture phù hợp.

**Đạt khi:** UI/loader trả thông báo lỗi dễ hiểu, không traceback/stack trace cho người dùng.

### Demo 5 — API pipeline (không cần UI)

Từ Python, gọi `smartscan.core.pipeline.process_document` với ảnh BGR uint8, có thể truyền `manual_corners`. Kiểm tra dictionary kết quả thay vì giả định API trả ảnh trực tiếp. Không dùng `smartscan.core.process_document` cho đến khi wrapper stub được sửa.

## 6. Bảng thao tác và kết quả mong đợi

| Thao tác | Kết quả thành công | Dấu hiệu thất bại |
|---|---|---|
| Upload JPG/PNG/BMP hợp lệ | Preview ảnh gốc + metadata | ImportError, decode fail, ảnh không hiển thị |
| Auto detect ảnh thuận lợi | success, corners TL/TR/BR/BL, confidence/message | success nhưng góc sai, confidence cao vô lý |
| Perspective + padding | output chữ nhật, không mất cạnh, đúng hướng | xoay 90°, mirror, cắt chữ, biến dạng mạnh |
| Enhancement mặc định | ảnh giữ được chữ, tương phản tốt hơn | toàn đen/trắng, mất chữ, nhiễu tăng |
| Đổi preset/re-enhance | cập nhật ảnh enhanced | nút không phản hồi, exception, ảnh cũ không đổi |
| Manual corners | xử lý tiếp với góc hợp lệ | vẫn fail mà không giải thích |
| Download JPG/PNG | file mở được, đúng ảnh | file rỗng, sai màu RGB/BGR, ảnh khác preview |

## 7. Cách ghi nhận kết quả demo

Với mỗi ảnh, lưu tối thiểu:

- Tên ảnh, nguồn/điều kiện chụp, kích thước.
- Auto detection: success/fail, confidence, thời gian.
- Góc dự đoán và góc tham chiếu nếu có.
- Perspective: success/fail, kích thước output, có cắt méo không.
- Enhancement: preset/config, đánh giá định tính theo 3 tiêu chí: đọc được chữ, nhiễu, màu.
- Download: định dạng, mở được, kích thước file.

Không tự suy ra accuracy từ số test pass. QA hiện chỉ có kết quả synthetic và một số ảnh fixture; cần chạy lại sau khi fix để có số liệu mới.

## 8. Kế hoạch rollback demo

Nếu detection sai hướng:

1. Dừng demo, không cố gắng thuyết trình kết quả sai là thành công.
2. Dùng manual corners trên ảnh có ground truth rõ để trình bày perspective/enhancement riêng.
3. Giải thích detection đang bị BUG-1 và bug đã được chuyển Agent phụ trách.
4. Sau khi sửa, chạy regression orientation, toàn bộ pytest, import UI và Streamlit smoke test trước khi demo lại.

## 9. Checklist trước giờ bảo vệ

- [ ] Agent sửa xong BUG-1 đến BUG-9 được chấp nhận.
- [ ] `py -m pytest tests -q` không còn failure liên quan source.
- [ ] `from smartscan.ui.app import main` thành công.
- [ ] `py -m streamlit run smartscan/ui/app.py` render không traceback.
- [ ] Ít nhất một ảnh auto-detection có marker chứng minh đúng TL/TR/BR/BL.
- [ ] Manual-corners path chạy được.
- [ ] Download JPG/PNG mở đúng.
- [ ] README/docs khớp API và tên module thực tế.
- [ ] Người trình bày thuộc lòng giới hạn thuật toán và không cam kết OCR/pipeline ngoài phạm vi.

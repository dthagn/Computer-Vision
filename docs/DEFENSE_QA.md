# SmartScan — Bộ câu hỏi và câu trả lời bảo vệ

Các câu trả lời dưới đây đối chiếu source hiện tại và QA thực tế. Khi bảo vệ, phải nói rõ trạng thái lỗi chưa sửa nếu giảng viên hỏi về kết quả demo.

## 1. Bài toán và phạm vi

### Hệ thống giải quyết vấn đề gì?

SmartScan số hóa ảnh tài liệu giấy bằng cách phát hiện vùng giấy, kéo phối cảnh về hình chữ nhật, sau đó nâng cao chất lượng như giảm nhiễu, tăng tương phản, làm nét và tùy chọn chuyển sang ảnh nhị phân. Phạm vi MVP là upload ảnh đơn, xử lý và tải kết quả; OCR, ghép trang, cloud và đăng nhập nằm ngoài phạm vi.

### Tại sao không dùng Deep Learning?

Đề tài chọn Computer Vision cổ điển để pipeline giải thích được, không cần GPU/dữ liệu huấn luyện, chạy nhanh trên máy cá nhân và phù hợp môn học xử lý ảnh. Trade-off là detection kém mạnh hơn model học máy trong điều kiện nền phức tạp, ánh sáng xấu hoặc tài liệu bị che.

## 2. Kiến trúc và luồng dữ liệu

### Luồng xử lý chính là gì?

`smartscan/ui/app.py` nhận bytes ảnh, `image_loader` decode sang BGR uint8 và kiểm tra giới hạn. `smartscan/core/pipeline.py` chạy detection → perspective → enhancement. Kết quả BGR được chuyển sang RGB cho Streamlit, sau đó hiển thị và encode JPG/PNG để download.

### Tại sao cần chuyển RGB/BGR?

OpenCV mặc định xử lý ảnh màu BGR, còn Streamlit/Pillow hiển thị RGB. Nếu bỏ qua chuyển đổi, màu ảnh sẽ bị đảo đỏ/xanh. Project có `convert_rgb_to_bgr`/`convert_bgr_to_rgb` trong loader và các hàm `rgb_to_bgr`/`bgr_to_rgb` trong `image_utils`; cần dùng đúng chiều dữ liệu ở mỗi lớp.

### Mỗi module có trách nhiệm gì?

- `preprocessing.py`: validate, resize, grayscale, blur, Canny, morphology.
- `detection.py`: contour, heuristic chọn tứ giác, sắp xếp góc.
- `perspective.py`: validate góc, tính homography, warp ảnh.
- `enhancement.py`: denoise, contrast, threshold, sharpen, shadow correction.
- `pipeline.py`: điều phối các bước, trả kết quả và thời gian.
- `ui/app.py`: upload, cấu hình, hiển thị, manual fallback, download.
- `utils/`: loader, chuyển màu, format bytes, preset config.

## 3. Detection

### Thuật toán detection hoạt động thế nào?

Ảnh được resize giữ tỷ lệ về tối đa 1280×720, chuyển grayscale, Gaussian blur, Canny edge detection, morphology close. `findContours` lấy contour ngoài; contour được `approxPolyDP`, nếu nhiều hơn bốn điểm thì xét convex hull và xấp xỉ lại. Các ứng viên được chấm bằng convexity và heuristic hình học tứ giác. Detection thử năm cặp ngưỡng Canny và chọn kết quả có confidence cao nhất, với ngưỡng tối thiểu 0.3.

### “Confidence” có phải xác suất không?

Không. Đây là điểm heuristic tổ hợp `0.6 * convexity_score + 0.4 * quadrilateral_score`, nằm trong khoảng mục tiêu 0–1 nhưng không phải xác suất được hiệu chuẩn thống kê. Vì vậy không nên nói “mô hình chắc chắn 80%”; chỉ nên nói điểm heuristic tương đối.

### Tại sao pipeline có thể fail detection?

Vì phụ thuộc edge và hình học: nền trùng màu giấy, viền không rõ, vật che, nhiều hình chữ nhật, nhiễu mạnh hoặc tương phản thấp có thể làm contour sai. Nếu không tìm được ứng viên đủ confidence, pipeline trả fail và UI có cơ chế manual corners.

### Manual corners giải quyết được gì và không giải quyết được gì?

Manual corners bỏ qua bài toán tìm vùng giấy, hữu ích khi người dùng nhìn thấy tài liệu nhưng detector fail. Tuy nhiên người dùng phải nhập đúng TL/TR/BR/BL; góc sai vẫn làm warp sai. Perspective layer vẫn validate tọa độ, trùng điểm, collinear và self-intersection.

## 4. Lỗi detection hiện tại

### Hàm `order_corners` đang làm gì và vì sao sai?

Hàm cần trả bốn góc theo TL, TR, BR, BL. TL/BR dựa trên tổng `x+y`; TR/BL dựa trên `x-y`. Source hiện dùng `np.diff(corners, axis=1)` — tương đương `y-x` — nên dấu hiệu bị đảo, chọn nhầm TR/BL. QA đã tái hiện input chuẩn nhưng output bị đổi chỗ và pipeline trả ảnh sai hướng.

### Vì sao đây là lỗi critical?

Perspective transform tin rằng input đã đúng TL/TR/BR/BL. Khi thứ tự sai, homography map sai cặp điểm, làm tài liệu bị xoay hoặc mirror. Vì manual path cũng gọi `order_corners`, cả auto lẫn manual đều có thể bị ảnh hưởng.

### Đã có bằng chứng nào?

`tests/test_qa_independent.py` có bảy ca synthetic đều fail về orientation; QA report ghi nhận localization tìm đúng point set nhưng ordering sai và marker test cho thấy output sai vị trí. Đây là lý do trạng thái review là REJECTED/CHƯA ĐẠT cho tới khi fix và regression test pass.

## 5. Perspective correction

### Homography là gì?

Homography là phép chiếu giữa hai mặt phẳng, biểu diễn bằng ma trận 3×3. Với bốn cặp điểm không suy biến, `cv2.getPerspectiveTransform` tính ma trận; `cv2.warpPerspective` dùng ma trận để nội suy màu cho từng điểm ảnh đích.

### Vì sao cần bốn góc?

Phép homography 2D có 8 bậc tự do; bốn cặp điểm tương ứng cung cấp đủ ràng buộc để giải duy nhất phép chiếu mặt phẳng. Ba điểm không đủ để xác định đầy đủ homography trong trường hợp tổng quát.

### Tại sao output size được tính từ cạnh?

`calculate_output_dimensions` lấy chiều dài lớn hơn giữa hai cạnh ngang và hai cạnh dọc để tránh cắt nội dung do chênh lệch chiều dài do phối cảnh. Pipeline còn có `apply_perspective_with_padding` với padding ratio 0.05 để tạo viền an toàn.

### Perspective correction có sửa được mọi biến dạng không?

Không. Nó giả định bề mặt tài liệu gần phẳng và bốn góc đúng. Gấp nếp, cong, biến dạng 3D, lens distortion hoặc góc cực đoan có thể vẫn làm output méo. Nội suy `INTER_LINEAR` cũng có thể làm mềm chữ khi scale lớn.

## 6. Enhancement

### Tại sao dùng nhiều phương pháp thay vì một thuật toán?

Ảnh tài liệu có nhiều loại suy giảm khác nhau: nhiễu Gaussian, salt-and-pepper, ánh sáng không đều, tương phản thấp, chữ mờ. Gaussian/Median/Bilateral có điểm mạnh khác nhau; histogram equalization và CLAHE xử lý contrast khác nhau; global/Otsu/adaptive threshold phù hợp với mức độ đồng đều của ánh sáng.

### Khi nào nên chọn từng denoise?

- Gaussian: nhiễu mượt đơn giản, ưu tiên tốc độ.
- Median: salt-and-pepper, muốn giữ cạnh tương đối.
- Bilateral: muốn giảm nhiễu nhưng giữ cạnh chữ; là mặc định nhưng chậm hơn.

### CLAHE khác histogram equalization thế nào?

Histogram equalization xử lý toàn cục và với ảnh màu hiện code equalize từng kênh RGB. CLAHE chia tile, giới hạn contrast và với ảnh màu áp dụng trên kênh L của Lab, nên thích ứng cục bộ và ít ảnh hưởng màu hơn. CLAHE vẫn có thể tạo artifact nếu clip limit quá cao.

### Khi nào Otsu không phù hợp?

Khi histogram không có hai mode rõ hoặc nền sáng thay đổi theo vùng. Otsu chỉ chọn một ngưỡng toàn cục; adaptive mean/Gaussian tính ngưỡng cục bộ nên thường phù hợp hơn với uneven illumination, nhưng cần chọn block size và `C`.

### Sharpening có rủi ro gì?

Unsharp mask và kernel sharpening khuếch đại cạnh nhưng cũng khuếch đại nhiễu, có thể tạo halo quanh chữ. Cần clip giá trị về uint8 và tránh strength quá cao. Radius chẵn có thể gây lỗi OpenCV tùy hàm; pipeline cần xử lý lỗi gracefully.

### Binarization làm gì với màu sắc?

Các method threshold trả ảnh xám nhị phân một kênh; thông tin màu bị bỏ. Nếu muốn giữ màu, dùng `threshold_method='none'` và `convert_to_grayscale=False`. UI cần chuyển đúng BGR/gray trước khi hiển thị và encode.

## 7. Pipeline, API và UI

### `process_document` trong `smartscan/core/pipeline.py` khác gì `smartscan.core.process_document`?

Pipeline thật nằm ở `smartscan/core/pipeline.py` và trả dictionary kết quả. `smartscan/core/__init__.py` hiện định nghĩa wrapper `process_document` chỉ có `pass`, trả `None`. Đây là API trap; phải sửa hoặc ủy quyền trước khi bảo vệ.

### Pipeline xử lý lỗi ra sao?

Mỗi module trả dictionary có `success`, `message` và dữ liệu tương ứng. Pipeline dừng khi detection/perspective fail; nếu enhancement fail, vẫn có thể trả `scanned_image` như partial success. UI phải kiểm tra `success` trước khi dùng ảnh.

### Tại sao UI có manual corners?

Đây là fallback cho trường hợp detector không đủ tin cậy. Nó thể hiện tư duy thiết kế: không phụ thuộc hoàn toàn vào heuristic tự động, vẫn cho người dùng can thiệp khi cần.

### UI hiện có những vấn đề gì?

`smartscan/ui/app.py` import `encode_image_to_bytes` từ sai module; hàm nằm trong `smartscan/utils/utils.py`. Ngoài ra sys.path hiện hướng tới `smartscan/` thay vì chắc chắn project root. Kết quả là import app thất bại và Streamlit hiển thị app execution error. Root `app.py` còn là stale file import `src/` không tồn tại.

## 8. Đánh giá và bằng chứng

### Tiêu chí thành công nào có bằng chứng?

- QA độc lập chạy `pytest`: 237 pass, 9 fail.
- Detection synthetic: 7/7 ca fail orientation; localization tìm đúng point set nhưng corner order sai.
- Perspective validation có nhiều test pass cho bounds, self-intersect, collinear và dtype/shape.
- Enhancement có nhiều test pass về dtype, shape, method lạ và intermediate images.
- QA ghi nhận pipeline manual-corners chạy được nhưng ảnh sai hướng do BUG-1; thời gian xử lý mục tiêu <3s có dấu hiệu đạt trên một số fixture, nhưng phải đo lại sau fix.

### Tại sao chưa thể nói đạt >90% tài liệu đơn giản?

Không có bộ dữ liệu thật đủ lớn và nhãn chính xác để kết luận accuracy tổng quát. QA mới kiểm thử synthetic và một số fixture; hơn nữa BUG-1 làm toàn bộ pipeline orientation không đáng tin. Con số >90% trong spec là mục tiêu, không phải kết quả đã chứng minh.

### Nên đo metric nào trong tương lai?

- Detection: tỷ lệ tìm đúng contour, corner error trung bình/tối đa, orientation accuracy.
- Perspective: corner order pass rate, tỷ lệ output không cắt méo, marker orientation.
- Enhancement: OCR downstream nếu có, PSNR/SSIM trên ảnh tham chiếu, đánh giá định tính theo bộ ảnh chuẩn.
- Performance: p50/p95 latency theo kích thước ảnh và CPU.
- UI: smoke test import/render, upload/download end-to-end.

## 9. Câu hỏi “tại sao chọn thiết kế này?”

### Tại sao không dùng OCR trong MVP?

OCR là bài toán khác, cần engine nhận dạng và đánh giá riêng. MVP tập trung vào scan/enhance; thêm OCR sẽ làm tăng phạm vi, phụ thuộc và khó bảo vệ pipeline hình học.

### Tại sao có nhiều bộ tham số Canny?

Một cặp ngưỡng không phù hợp mọi ảnh. Thử nhiều ngưỡng tăng cơ hội tìm được cạnh tài liệu trong điều kiện tương phản khác nhau. Nhược điểm là tốn thời gian và vẫn có thể chọn sai contour; cần confidence/heuristic để giảm rủi ro.

### Tại sao có cả global và adaptive threshold?

Global đơn giản và nhanh khi sáng đồng đều; Otsu tự chọn ngưỡng nhưng vẫn toàn cục; adaptive xử lý sáng cục bộ tốt hơn cho ảnh không đều. Để người dùng/preset chọn theo loại tài liệu.

### Tại sao pipeline trả dictionary thay vì chỉ ảnh?

Vì cần truyền `success`, `message`, corners, ảnh trung gian, thời gian từng bước và debug info cho UI/test. Đây là lựa chọn explicit error handling, dù API hơi verbose.

## 10. Câu trả lời ngắn nên thuộc lòng

- SmartScan là pipeline CV cổ điển: detect contour → sort corners → homography warp → enhance → download.
- Detection dùng grayscale, Gaussian blur, Canny, morphology, contours, `approxPolyDP`, convexity và geometry heuristic.
- Perspective dùng `getPerspectiveTransform` + `warpPerspective`.
- Enhancement có Gaussian/Median/Bilateral denoise, histogram equalization/CLAHE, global/Otsu/adaptive threshold, unsharp/kernel sharpening và morphological shadow correction.
- Hiện chưa đạt nghiệm thu vì corner order sai và UI import lỗi; đã ghi nhận trong QA report và yêu cầu Agent sửa.
- Không bịa metric: chỉ trích số liệu thực tế từ QA/test, và nói rõ chưa có accuracy tổng quát trên dữ liệu thật.

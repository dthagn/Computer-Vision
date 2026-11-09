# SmartScan — Giải thích thuật toán

Tài liệu này mô tả các phép xử lý **thực sự có trong source code** tại thời điểm rà soát ngày 2026-11-07. Đây không phải danh sách chức năng dự kiến. Mỗi mục nêu nguyên lý, đầu vào/đầu ra, ưu/nhược điểm và ứng dụng trong SmartScan.

## Quy ước dữ liệu và màu ảnh

- Ảnh đầu vào pipeline là `numpy.ndarray`, `dtype=uint8`.
- OpenCV dùng BGR cho ảnh màu và ảnh xám một kênh cho grayscale.
- Streamlit hiển thị RGB; module loader cung cấp chuyển đổi qua lại.
- Detection tự resize ảnh lớn về tối đa 1280×720, giữ tỷ lệ, rồi ánh xạ tọa độ góc về hệ tọa độ ảnh gốc.
- Perspective mặc định trong pipeline gọi `apply_perspective_with_padding(..., padding_ratio=0.05)`, nên canvas output lớn hơn kích thước cạnh tài liệu khoảng 5% mỗi phía.

## A. Pipeline tiền xử lý và phát hiện

### 1. Resize giữ tỷ lệ

**Code:** `resize_with_aspect_ratio()` trong [preprocessing.py](../smartscan/core/preprocessing.py).

**Nguyên lý:** tính hệ số scale nhỏ nhất trong hai tỷ lệ chiều rộng và chiều cao, không phóng to ảnh (`scale <= 1`), rồi dùng `cv2.resize` với nội suy `INTER_AREA`. Trả ảnh resize và hệ số scale để map ngược tọa độ.

**Đầu vào:** ảnh 2D/3D `uint8`; `max_width`, `max_height`. **Đầu ra:** ảnh resize + `scale_x`, `scale_y`.

**Ưu điểm:** giảm chi phí tính toán, giữ tỷ lệ hình học. **Nhược điểm:** bỏ chi tiết nhỏ ở ảnh lớn; kích thước tối đa mặc định là 1280×720 trong detection.

**Trong SmartScan:** detection dùng để tìm contour nhanh và ổn định hơn trên ảnh cỡ lớn.

### 2. Grayscale

**Code:** `convert_to_grayscale()` và `preprocess_for_detection()`.

**Nguyên lý:** ảnh màu được chuyển sang ảnh xám một kênh bằng `cv2.cvtColor(..., COLOR_BGR2GRAY)`; ảnh đã là grayscale được giữ nguyên.

**Đầu vào:** ảnh BGR/RGB hoặc grayscale `uint8`. **Đầu ra:** ảnh grayscale `uint8`.

**Ưu/nhược điểm:** giảm dữ liệu và bỏ phụ thuộc màu để edge detection tập trung vào cấu trúc sáng/tối; đồng thời làm mất thông tin màu vốn có thể giúp phân biệt tài liệu với nền. Trong detection, grayscale là đầu vào cho Gaussian blur và Canny.

### 3. Gaussian Blur

**Code:** `apply_gaussian_blur()` trong preprocessing; `apply_gaussian_denoise()` trong enhancement.

**Nguyên lý:** thay giá trị pixel bằng trung bình có trọng số theo hàm Gaussian trên vùng lân cận. Kernel size được ép thành số lẻ và tối thiểu 3; sigma mặc định 0 để OpenCV tự suy ra. Trong detection, kernel mặc định là 5×5.

**Đầu vào:** ảnh grayscale hoặc màu `uint8`, kích thước kernel, sigma. **Đầu ra:** ảnh cùng số kênh và kích thước.

**Ưu điểm:** giảm nhiễu/Gaussian, làm edge ổn định hơn trước Canny. **Nhược điểm:** làm mềm cạnh và chi tiết; kernel lớn có thể làm mất biên giấy mảnh hoặc tương phản thấp.

**Trong SmartScan:** dùng ở tiền xử lý detection để giảm nhiễu trước edge detection. Một hàm cùng tên trong enhancement cũng có thể được chọn như phương pháp denoise.

### 4. Canny Edge Detection

**Code:** `apply_canny_edge_detection()` trong preprocessing.

**Nguyên lý:** pipeline gồm làm mượt, tính gradient bằng Sobel, non-maximum suppression và hysteresis thresholding. Hai ngưỡng kiểm soát edge mạnh/yếu: pixel vượt ngưỡng cao là edge chắc chắn; pixel giữa hai ngưỡng chỉ được giữ nếu nối với edge mạnh.

**Đầu vào:** ảnh grayscale `uint8`; `threshold1`, `threshold2`, `aperture_size`. **Đầu ra:** edge map nhị phân `uint8`.

**Trong SmartScan:** detection thử năm cặp ngưỡng `(50,150)`, `(30,100)`, `(70,200)`, `(20,80)`, `(100,250)` để tăng khả năng thích ứng với tương phản/ánh sáng.

**Ưu điểm:** edge mảnh, ít nhiễu hơn threshold gradient đơn giản; có cơ chế thử nhiều ngưỡng. **Nhược điểm:** phụ thuộc mạnh vào blur, ánh sáng và tương phản; có thể đứt cạnh tài liệu hoặc tạo edge từ nền/vật thể; ngưỡng cố định vẫn không bảo đảm phát hiện đúng.

### 5. Morphological close

**Code:** `apply_morphology()` với `operation='close'`.

**Nguyên lý:** dilation mở rộng vùng sáng trước, sau đó erosion co lại. Với edge map, thao tác này giúp nối các đoạn edge bị đứt và lấp khoảng trống nhỏ. Detection dùng kernel chữ nhật 5×5, một lần lặp.

**Đầu vào:** ảnh nhị phân edge map, kernel shape, số lần lặp. **Đầu ra:** ảnh nhị phân cùng kích thước.

**Ưu điểm:** có thể hoàn thiện contour giấy. **Nhược điểm:** cũng có thể nối edge của vật thể khác hoặc làm contour phình ra; kernel/quá nhiều iteration có thể hợp nhất các đối tượng không liên quan.

### 6. Contour detection và xấp xỉ đa giác

**Code:** `find_document_contour()`, `compute_convexity_score()`, `compute_quadrilateral_score()`.

**Nguyên lý:** `cv2.findContours(..., RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)` tìm đường biên ngoài của edge map. Mỗi contour được lọc theo diện tích tương đối (mặc định 5%–95% ảnh), xấp xỉ bằng `cv2.approxPolyDP` với epsilon bằng 2% chu vi. Nếu có nhiều hơn bốn điểm, code tính convex hull rồi xấp xỉ lại; contour chỉ được giữ khi kết quả có bốn điểm. Hàm chấm điểm kết hợp convexity (diện tích contour / diện tích hull), hình học tứ giác (diện tích, góc, tỷ lệ cạnh) và chọn điểm cao nhất.

**Đầu vào:** edge map nhị phân. **Đầu ra:** contour bốn điểm ứng viên hoặc `None`.

**Ưu điểm:** không cần huấn luyện, chạy bằng OpenCV cổ điển, có heuristic giải thích được. **Nhược điểm:** không nhận diện ngữ nghĩa “tài liệu”; có thể chọn hình chữ nhật/vật thể khác. Contour chỉ được xét là bốn điểm sau khi hull/approx, nên các hình không lồi hoặc cạnh cong có thể bị bỏ qua. Ngưỡng confidence cuối là 0.3 trong `detect_document`.

### 7. Sắp xếp góc TL, TR, BR, BL

**Code:** `order_corners()`.

**Nguyên lý dự kiến:** TL/BR được chọn theo tổng `x+y` nhỏ/lớn; TR/BL theo hiệu `x-y` lớn/nhỏ; nếu index trùng nhau thì có fallback theo góc quanh centroid.

**Trạng thái triển khai:** hiện tại dùng `np.diff(corners, axis=1)`, tức `y-x`, trái với comment và quy ước API `x-y`; QA đã tái hiện swap TR/BL và ảnh output bị xoay/gương. Đây là lỗi nghiệm thu nghiêm trọng, chưa được mô tả như chức năng đúng.

**Đầu vào dự kiến:** bốn điểm `(4,2)`. **Đầu ra dự kiến:** `(4,2)` theo TL, TR, BR, BL. **Giới hạn:** heuristic tổng/hiệu tọa độ không đủ tổng quát cho mọi phép quay/chiếu cực đoan; cần test hình học và regression orientation.

## B. Hiệu chỉnh phối cảnh

### 8. Validation hình học của bốn góc

**Code:** `validate_corners()`, `check_self_intersection()` trong [perspective.py](../smartscan/core/perspective.py).

**Nguyên lý:** kiểm tra kiểu dữ liệu, shape `(4,2)`, kiểu số, tọa độ nằm trong ảnh, không trùng điểm và không gần collinear; kiểm tra hai cặp cạnh không kề nhau có giao nhau để phát hiện bow-tie.

**Đầu vào:** corners và kích thước ảnh. **Đầu ra:** cờ hợp lệ + thông báo lỗi. **Ưu điểm:** chặn input sai trước phép biến đổi phi tuyến. **Nhược điểm:** kiểm tra giao cạnh là heuristic hình học đơn giản; một số cấu hình suy biến khác vẫn có thể tạo warp chất lượng kém dù không bị từ chối.

### 9. Homography và perspective warp

**Code:** `calculate_output_dimensions()`, `compute_homography_matrix()`, `correct_perspective()`, `apply_perspective_with_padding()`.

**Nguyên lý:** bốn cặp điểm tương ứng xác định một phép chiếu mặt phẳng. `cv2.getPerspectiveTransform` tính ma trận 3×3; `cv2.warpPerspective` áp dụng ma trận lên từng pixel đích để lấy màu từ ảnh nguồn. Kích thước output mặc định lấy chiều dài cạnh lớn hơn của hai cạnh đối diện. Destination corners là hình chữ nhật; biến thể padding đặt tài liệu vào canvas lớn hơn với viền trắng.

**Đầu vào:** ảnh BGR `uint8`, bốn góc nguồn `(4,2)` đúng TL/TR/BR/BL, tùy chọn output size hoặc padding ratio. **Đầu ra:** dictionary gồm `corrected_image`, ma trận homography, output size và message.

**Ưu điểm:** có thể “duỗi” mặt phẳng giấy xiên thành chữ nhật khi bốn góc đúng. **Nhược điểm:** rất nhạy với sai số góc; góc tài liệu không phải hình chữ nhật thật sẽ bị kéo giãn; nội suy `INTER_LINEAR` có thể làm mềm chữ; phép chiếu phẳng không khôi phục gấp nếp, cong hoặc biến dạng 3D. Border được cố định màu trắng.

## C. Nâng cao chất lượng ảnh

Thứ tự thực tế trong `enhance_document()` là: shadow correction (nếu bật) → denoise → contrast → sharpen (nếu bật) → binarization (nếu method khác `none`) → grayscale (chỉ khi không binarize và `convert_to_grayscale=True`). API nhận config và trả dictionary, không phải ảnh trực tiếp.

### 10. Denoising: Gaussian, Median, Bilateral

**Code:** `denoise_image()` và ba hàm `apply_*_denoise()`.

- **Gaussian:** trung bình có trọng số, giảm nhiễu mượt nhưng làm mềm cạnh.
- **Median:** thay pixel bằng median trong cửa sổ; tốt với salt-and-pepper, giữ cạnh tương đối tốt hơn Gaussian nhưng có thể mất chi tiết nhỏ.
- **Bilateral:** lọc theo cả khoảng cách tọa độ và khác biệt màu; giữ cạnh tốt hơn nhưng tốn tính toán hơn và cần chọn `d`, `sigma_color`, `sigma_space`.

**Đầu vào/đầu ra:** ảnh grayscale/màu `uint8`; ảnh cùng kích thước và số kênh. Hàm điều chỉnh kernel size chẵn thành lẻ và tối thiểu 3 cho Gaussian/Median. `method='none'` sao chép ảnh. Method lạ gây `ValueError`.

**Trong SmartScan:** bilateral là mặc định; Gaussian và Median là lựa chọn thay thế.

### 11. Histogram Equalization

**Code:** `apply_histogram_equalization()`.

**Nguyên lý:** tái phân phối cường độ điểm ảnh để histogram trải rộng hơn trên dải giá trị. Với ảnh màu, code equalize từng kênh B/G/R rồi merge lại; cách này không đảm bảo giữ nguyên màu tự nhiên.

**Đầu vào:** ảnh grayscale hoặc BGR `uint8`. **Đầu ra:** ảnh cùng shape/dtype. **Ưu điểm:** đơn giản, tự động tăng contrast tổng thể. **Nhược điểm:** không thích ứng theo vùng, có thể khuếch đại nhiễu và làm màu ảnh thay đổi; không phải lựa chọn mặc định.

### 12. CLAHE

**Code:** `apply_clahe()`.

**Nguyên lý:** chia ảnh thành các tile (`tile_grid_size`, mặc định 8×8), tính histogram từng vùng, giới hạn mức tăng contrast bằng `clip_limit` (mặc định 2.0), rồi ghép/tuyến tính hóa kết quả. Với ảnh BGR, code chuyển BGR→Lab, áp dụng CLAHE chỉ lên kênh L rồi chuyển ngược, nhằm giảm ảnh hưởng lên sắc màu.

**Đầu vào:** ảnh grayscale/BGR `uint8`, clip limit và tile grid. **Đầu ra:** ảnh cùng shape/dtype.

**Ưu điểm:** xử lý được chênh sáng cục bộ tốt hơn histogram equalization toàn cục; giữ sắc độ tốt hơn equalize từng RGB channel. **Nhược điểm:** nhạy với clip limit/tile size, có thể tạo artifact ở vùng đồng nhất, tính toán cao hơn; không sửa được bóng đổ hình thái phức tạp.

### 13. Global Threshold

**Code:** `apply_global_threshold()`.

**Nguyên lý:** chọn một ngưỡng cố định (mặc định 127); pixel trên ngưỡng nhận `max_value`, còn lại nhận 0. Ảnh màu được chuyển sang grayscale trước.

**Đầu vào:** ảnh grayscale/BGR, threshold, max value. **Đầu ra:** ảnh nhị phân một kênh `uint8`.

**Ưu điểm:** rất nhanh và dễ giải thích. **Nhược điểm:** không thích ứng với thay đổi sáng theo vùng; không tự chọn ngưỡng; dễ mất nội dung khi ánh sáng không đều.

### 14. Otsu Threshold

**Code:** `apply_otsu_threshold()`.

**Nguyên lý:** quét histogram grayscale và chọn ngưỡng tối ưu theo tiêu chí phương sai giữa lớp được tách, dùng `cv2.THRESH_BINARY + cv2.THRESH_OTSU`.

**Đầu vào:** ảnh grayscale/BGR `uint8`, max value. **Đầu ra:** ảnh nhị phân `uint8`.

**Ưu điểm:** tự động chọn một ngưỡng toàn cục, phù hợp histogram phân tách tốt. **Nhược điểm:** vẫn là threshold toàn cục; giả định hai lớp điểm ảnh rõ ràng, nên có thể kém khi nền sáng không đồng đều hoặc histogram không hai mode rõ.

### 15. Adaptive Mean Threshold

**Code:** `apply_adaptive_mean_threshold()`.

**Nguyên lý:** với mỗi pixel, OpenCV xét cửa sổ `block_size` (mặc định 11, ép số lẻ/tối thiểu 3), tính mean của vùng lân cận, trừ hằng `C` (mặc định 2), rồi so sánh pixel với giá trị cục bộ này.

**Đầu vào:** ảnh grayscale/BGR, block size, `C`. **Đầu ra:** ảnh nhị phân `uint8`.

**Ưu điểm:** thích ứng với sáng cục bộ, phù hợp hơn global threshold cho ảnh không đều sáng. **Nhược điểm:** block size quá nhỏ/lớn có thể gây nhiễu hoặc mất chi tiết; chậm hơn global; kết quả phụ thuộc nhiều vào `C`.

### 16. Adaptive Gaussian Threshold

**Code:** `apply_adaptive_gaussian_threshold()`.

**Nguyên lý:** giống adaptive mean nhưng trọng số pixel lân cận bằng Gaussian thay vì mean đồng đều (`ADAPTIVE_THRESH_GAUSSIAN_C`). Đây là method mặc định của config enhancement.

**Đầu vào/đầu ra:** như adaptive mean. **Ưu điểm:** thường cho ngưỡng cục bộ mượt hơn mean. **Nhược điểm:** vẫn cần chọn block size/`C`; có thể tạo đốm ở vùng đồng nhất; không đảm bảo đọc được mọi font/kích thước.

### 17. Unsharp Mask

**Code:** `apply_unsharp_mask()`.

**Nguyên lý:** tạo ảnh blur bằng Gaussian, tính phần chênh lệch giữa ảnh gốc và ảnh blur, rồi cộng phần này trở lại ảnh gốc với hệ số strength: `original*(1+strength) - blurred*strength`. Code clip về `[0,255]` và ép `uint8`.

**Đầu vào:** ảnh grayscale/BGR, strength (mặc định 1.5), radius (mặc định 3). **Đầu ra:** ảnh sắc nét cùng shape/dtype.

**Ưu điểm:** tăng biên độ cạnh chữ một cách điều khiển được. **Nhược điểm:** strength cao tạo halo và khuếch đại nhiễu; radius cần hợp lý; một số radius chẵn có thể khiến OpenCV lỗi, mặc dù `enhance_document` bắt exception và trả `success=False`.

### 18. Kernel sharpening

**Code:** `apply_kernel_sharpen()`.

**Nguyên lý:** convolution trực tiếp bằng kernel. Kernel mặc định là `[0,-1,0; -1,5,-1; 0,-1,0]`: giữ pixel trung tâm, trừ lân cận để nhấn cạnh. Kết quả được clip về uint8.

**Đầu vào:** ảnh grayscale/BGR, tùy chọn kernel. **Đầu ra:** ảnh sharpened cùng kích thước. **Ưu điểm:** đơn giản, nhanh. **Nhược điểm:** dễ tăng nhiễu và artifact hơn unsharp mask; kernel cố định ít linh hoạt.

### 19. Morphological shadow/uneven illumination correction

**Code:** `apply_morphological_shadow_correction()`.

**Nguyên lý:** chuyển ảnh màu sang grayscale để ước lượng background, dilation bằng kernel chữ nhật (mặc định 25×25) lấy vùng sáng nền, blur background, rồi chuẩn hóa grayscale theo tỷ lệ `gray/background` nhân mean background. Với ảnh màu, code tính ratio từ ảnh xám rồi nhân ratio vào từng kênh B/G/R.

**Đầu vào:** ảnh grayscale/BGR, kernel size, blur sigma. **Đầu ra:** ảnh đã giảm chênh sáng, cùng shape; ảnh màu vẫn 3 kênh.

**Ưu điểm:** có thể cải thiện gradient sáng đơn giản. **Nhược điểm:** dilation/blur là xấp xỉ background thô; chữ hoặc vùng tối lớn có thể bị coi là background; ratio tính từ grayscale có thể làm sai màu; không giải quyết được nhiều nguồn sáng/phản chiếu phức tạp.

### 20. Binarization theo cấu hình

**Code:** `binarize_image()`.

**Nguyên lý:** dispatcher chọn `global`, `otsu`, `adaptive_mean`, `adaptive_gaussian` hoặc `none`. `none` trả bản sao ảnh đầu vào, giữ nguyên kích thước/số kênh; các method threshold trả ảnh nhị phân grayscale một kênh.

**Ưu điểm:** cho phép so sánh chiến lược nhị phân hóa. **Nhược điểm:** output một kênh khi threshold bật, nên UI phải chuyển đổi đúng khi hiển thị/encode; method lạ trả `ValueError`.

## D. Các giới hạn chung cần nêu khi bảo vệ

1. Hệ thống là pipeline Computer Vision cổ điển, không có học máy/OCR. Detection dựa trên cạnh và hình học, không “hiểu” tài liệu.
2. Chất lượng góc quyết định trực tiếp chất lượng warp. Sai một góc có thể làm toàn bộ output xiên/méo.
3. Detection bị ảnh hưởng bởi nền cùng màu, vật che, viền giấy không rõ, nhiều hình chữ nhật, ánh sáng cực đoan và ảnh quá nhỏ.
4. Enhancement cải thiện hiển thị nhưng không khôi phục chi tiết đã mất; sharpening có thể làm nhiễu rõ hơn.
5. Không có metric OCR/độ chính xác nhận dạng trong pipeline; “tài liệu tốt hơn” hiện chủ yếu được đánh giá trực quan và qua kiểm thử hình học.
6. Hiện chưa thể đánh dấu đạt nghiệm thu do BUG-1 (corner order), BUG-2 (UI import), BUG-3 (API stub), BUG-4 (path UI) và các lỗi/test stale ghi trong QA report.

## E. Bản đồ code nhanh

| Thuật toán | Hàm/code chính |
|---|---|
| Resize giữ tỷ lệ | `preprocessing.resize_with_aspect_ratio` |
| Grayscale | `preprocessing.convert_to_grayscale` |
| Gaussian blur | `preprocessing.apply_gaussian_blur`, `enhancement.apply_gaussian_denoise` |
| Canny | `preprocessing.apply_canny_edge_detection` |
| Morphology close | `preprocessing.apply_morphology` |
| Contour/approx | `detection.find_document_contour` |
| Heuristic tứ giác | `detection.compute_convexity_score`, `compute_quadrilateral_score` |
| Corner order | `detection.order_corners` — đang lỗi |
| Homography/warp | `perspective.compute_homography_matrix`, `correct_perspective`, `apply_perspective_with_padding` |
| Denoise | `enhancement.denoise_image` |
| Histogram equalization | `enhancement.apply_histogram_equalization` |
| CLAHE | `enhancement.apply_clahe` |
| Threshold | `enhancement.apply_global_threshold`, `apply_otsu_threshold`, `apply_adaptive_*_threshold`, `binarize_image` |
| Sharpen | `enhancement.apply_unsharp_mask`, `apply_kernel_sharpen`, `sharpen_image` |
| Shadow correction | `enhancement.apply_morphological_shadow_correction`, `correct_shadow` |

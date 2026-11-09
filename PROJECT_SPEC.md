# SmartScan - Intelligent Document Scanner

## Problem Statement

Người dùng thường xuyên cần số hóa tài liệu giấy nhưng gặp các vấn đề:
- Ảnh chụp tài liệu có góc nghiêng, bị méo phối cảnh
- Chất lượng ảnh kém, thiếu ánh sáng, nhiễu
- Khó khăn trong việc phát hiện chính xác cạnh giấy
- Cần công cụ tự động để xử lý hàng loạt tài liệu

## Objectives

Xây dựng ứng dụng web cho phép:
1. Tải ảnh tài liệu từ máy tính
2. Tự động phát hiện vùng giấy trong ảnh
3. Hiệu chỉnh phối cảnh để ảnh thẳng đứng
4. Nâng cao chất lượng ảnh (tương phản, giảm nhiễu, binarization)
5. Xuất kết quả theo định dạng mong muốn

## MVP Scope

**Functionality Included:**
- Upload ảnh tài liệu (JPG, PNG)
- Phát hiện tự động 4 góc của trang giấy
- Hiệu chỉnh phối cảnh (perspective correction)
- Nâng cao chất lượng cơ bản:
  - Contrast/brightness adjustment
  - Denoising/smoothing
  - Binarization (chuyển đen trắng)
  - Color correction
- Download kết quả xử lý

**Out of Scope:**
- OCR (nhận diện văn bản)
- Multi-page document stitching
- Cloud storage integration
- User authentication
- Batch processing trong MVP (có thể thêm sau)

## Extended Features (Future)

- Batch processing nhiều ảnh cùng lúc
- Tự động nhận diện loại giấy (A4, Letter, v.v.)
- Export sang PDF
- Preset cho các loại tài liệu khác nhau
- Undo/Redo các bước xử lý
- Real-time preview trên webcam

## Image Processing Pipeline

```
Input Image (RGB)
    ↓
Preprocessing (grayscale, blur, threshold)
    ↓
Edge Detection (Canny)
    ↓
Contour Detection
    ↓
Document Boundary Detection (find 4 corners)
    ↓
Perspective Correction (warp transform)
    ↓
Image Enhancement
    ├─ Contrast/Brightness
    ├─ Denoising
    ├─ Binarization
    └─ Color Correction
    ↓
Output Image (Enhanced)
```

## Software Architecture

### Technology Stack
- **Backend**: Python 3.9+
- **Image Processing**: OpenCV, NumPy
- **Web Framework**: Streamlit
- **Data Format**: NumPy arrays (uint8)

### Architecture Pattern
- **Modular Design**: Mỗi chức năng là module độc lập
- **Pipeline Architecture**: Sequential processing stages
- **Separation of Concerns**: UI, processing logic, utilities tách biệt

### Module Structure
```
smartscan/
├── core/                  # Core image processing
│   ├── detection.py      # Document detection
│   ├── correction.py     # Perspective correction
│   └── enhancement.py    # Image enhancement
├── ui/                    # Streamlit interface
│   └── app.py            # Main web application
├── utils/                 # Utilities
│   ├── image_utils.py    # Helper functions
│   └── constants.py      # Constants and config
├── tests/                 # Unit tests
└── docs/                  # Documentation
```

### Data Flow
1. User uploads image via Streamlit UI
2. Image converted to NumPy array (RGB → BGR for OpenCV)
3. Pipeline processes image sequentially
4. Result converted back to RGB for display
5. User downloads processed image

## Design Principles

1. **Simplicity**: Code dễ hiểu, dễ bảo trì
2. **Modularity**: Mỗi module có trách nhiệm duy nhất
3. **No Deep Learning**: Sử dụng thuật toán Computer Vision cổ điển
4. **Explainability**: Mỗi bước xử lý có thể visualize và giải thích
5. **Error Handling**: Xử lý lỗi thống nhất, graceful degradation
6. **Type Safety**: Rõ ràng về data types và formats

## Success Criteria

- MVP có thể phát hiện và hiệu chỉnh >90% tài liệu đơn giản
- Thời gian xử lý <3s cho ảnh A4
- UI phản hồi thời gian thực
- Code dễ đọc, documentation đầy đủ
- Có unit tests cho các module chính

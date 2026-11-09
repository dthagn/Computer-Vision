# SmartScan Architecture Documentation

## System Overview

SmartScan là ứng dụng web xử lý tài liệu với kiến trúc modular, pipeline-based. Hệ thống chia thành 3 lớp chính:

1. **Core Processing Layer**: Các module xử lý ảnh (detection, correction, enhancement)
2. **UI Layer**: Giao diện Streamlit tương tác với người dùng
3. **Utility Layer**: Các hàm hỗ trợ và constants

```
┌─────────────────────────────────────────────────────────┐
│                     Streamlit UI                         │
│                  (smartscan/ui/app.py)                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ RGB Image (NumPy uint8)
                     │
                     ▼
         ┌───────────────────────────┐
         │   rgb_to_bgr()            │
         │   (image_utils.py)        │
         └────────────┬──────────────┘
                      │
                      │ BGR Image (NumPy uint8)
                      │
                      ▼
         ┌───────────────────────────┐
         │   process_document()      │
         │   (core pipeline)         │
         └────────────┬──────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│                    Core Processing Pipeline                │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │   Agent 2    │───▶│   Agent 3    │───▶│  Agent 4   │  │
│  │  Detection   │    │  Correction  │    │Enhancement │  │
│  └──────────────┘    └──────────────┘    └────────────┘  │
│         │                  │                  │           │
│         ▼                  ▼                  ▼           │
│  detect_document() correct_perspective() enhance_document()│
│                                                            │
└──────────────────────────────────────────────────────────┘
                      │
                      │ BGR Enhanced Image
                      │
                      ▼
         ┌───────────────────────────┐
         │   bgr_to_rgb()            │
         │   (image_utils.py)        │
         └────────────┬──────────────┘
                      │
                      │ RGB Enhanced Image
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Display & Download (Streamlit)              │
└─────────────────────────────────────────────────────────┘
```

## Module Relationships

### Core Layer (`smartscan/core/`)

**Purpose**: Chứa logic xử lý ảnh chính

**Modules**:
- `detection.py`: Phát hiện biên tài liệu (Agent 2)
- `correction.py`: Hiệu chỉnh phối cảnh (Agent 3)
- `enhancement.py`: Nâng cao chất lượng ảnh (Agent 4)

**Dependencies**:
- OpenCV (cv2)
- NumPy
- `smartscan.utils.constants`

**Data Flow**:
```
image (BGR) → detect_document() → corners (4,2)
corners + image → correct_perspective() → corrected_image (BGR)
corrected_image → enhance_document() → enhanced_image (BGR)
```

**Independence**: Mỗi module hoạt động độc lập, chỉ giao tiếp qua API

---

### UI Layer (`smartscan/ui/`)

**Purpose**: Giao diện người dùng với Streamlit

**Modules**:
- `app.py`: Main application (Agent 5)

**Dependencies**:
- Streamlit
- `smartscan.core.*` (import-only, không sửa logic)
- `smartscan.utils.image_utils`

**Data Flow**:
```
User Upload → Streamlit File → RGB NumPy
RGB NumPy → rgb_to_bgr() → BGR NumPy
BGR NumPy → process_document() → Result dict
Result["enhanced"] → bgr_to_rgb() → RGB NumPy
RGB NumPy → Streamlit Display/Download
```

**Constraints**:
- KHÔNG sửa logic của core modules
- Chỉ sử dụng existing API functions
- Xử lý conversion RGB/BGR đúng contract

---

### Utility Layer (`smartscan/utils/`)

**Purpose**: Các hàm hỗ trợ và configuration

**Modules**:
- `image_utils.py`: Helper functions cho image conversion
- `constants.py`: Constants và parameters

**Dependencies**:
- OpenCV (cv2)
- NumPy

**Data Flow**:
```
Called by: core modules, UI layer
Returns: Converted images, validation results
```

**Independence**: Utility functions không phụ thuộc vào core modules

---

## Data Flow Diagram

### Upload Flow
```
1. User selects file in Streamlit UI
2. Streamlit reads file as bytes
3. cv2.imdecode() converts bytes to NumPy array (BGR)
4. cv2.cvtColor() converts BGR to RGB for Streamlit
5. rgb_to_bgr() converts back to BGR for processing
6. process_document() executes pipeline
7. bgr_to_rgb() converts result to RGB
8. Streamlit displays image
9. User downloads image (converted to bytes)
```

### Processing Pipeline Flow
```
Input: image (BGR, uint8)
  │
  ├─→ validate_image()
  │   └─→ Check shape, dtype, validity
  │
  ├─→ detect_document()
  │   ├─→ Grayscale conversion
  │   ├─→ Gaussian blur
  │   ├─→ Canny edge detection
  │   ├─→ Contour detection
  │   ├─→ Corner approximation
  │   └─→ Output: corners (4, 2)
  │
  ├─→ correct_perspective(image, corners)
  │   ├─→ Calculate output dimensions
  │   ├─→ Compute transform matrix
  │   ├─→ Apply warp perspective
  │   └─→ Output: corrected_image (BGR)
  │
  ├─→ enhance_document(corrected_image)
  │   ├─→ Contrast/brightness adjustment
  │   ├─→ Denoising
  │   ├─→ Binarization
  │   ├─→ Color correction
  │   └─→ Output: enhanced_image (BGR)
  │
  └─→ Output: dict with all results
```

## Component Communication

### Synchronous Communication
- Tất cả modules giao tiếp theo kiểu synchronous function calls
- Không có async operations hoặc message queues
- Data passed directly via function arguments and return values

### Error Propagation
```
UI Layer → Core Module → Exception
    │           │
    │           └─→ Raise descriptive exception
    │
    └─→ Catch exception → Display user-friendly error
```

### State Management
- Stateless architecture: mỗi request xử lý độc lập
- Không có global state giữa các module
- Constants read-only, không runtime modification

## File Access Pattern

### Read-Only Access
- Core modules đọc constants từ `utils/constants.py`
- UI layer đọc và call functions từ core modules
- Utility modules không phụ thuộc vào các module khác

### Write Access (per Agent)
- Agent 1: requirements.txt, constants.py, __init__.py
- Agent 2: detection.py, tests/, image_utils.py (helper only)
- Agent 3: correction.py, tests/, image_utils.py (helper only)
- Agent 4: enhancement.py, constants.py, tests/
- Agent 5: app.py, tests/
- Agent 6: tất cả files (chỉ fix bugs, không thay đổi logic chính)

### No Shared Files
- Không để 2 Agent cùng edit một file cùng lúc
- Handoff chỉ khi Agent trước hoàn thành và tests pass
- Git hoặc version control recommended để track changes

## Performance Considerations

### Memory Management
- NumPy arrays large → nên sau khi dùng
- Use `del` hoặc garbage collection cho temporary arrays
- Streamlit caching cho repeated operations

### Processing Time
- Target: <3s cho ảnh A4 (typical document)
- Bottleneck thường ở: edge detection, contour finding
- Optimization: downscale large images trước khi detect

### Concurrency
- Streamlit runs single-threaded
- Không cần multi-threading cho MVP
- Future: có thể dùng multiprocessing cho batch processing

## Security Considerations

### Input Validation
- Validate image format, size, dimensions
- Reject malformed images
- Limit maximum file size (configurable)

### Error Handling
- Never expose stack traces to users
- Log errors server-side
- Graceful degradation: nếu step fail, vẫn show partial result

### File System
- Không lưu file tạm lâu dài
- Clean up temporary files sau khi xử lý
- Sanitize filenames để tránh path traversal

## Scalability

### Horizontal Scaling
- Streamlit có thể deploy trên multiple instances
- Stateless architecture giúp scaling dễ dàng
- Future: add load balancer cho multi-user

### Vertical Scaling
- GPU acceleration cho image processing (future)
- More RAM cho large images
- Faster CPU cho OpenCV operations

## Testing Strategy

### Unit Tests
- Mỗi core module có unit tests
- Mock dependencies để test riêng lẻ
- Test edge cases: no document, extreme angles, low light

### Integration Tests
- Test full pipeline từ upload đến download
- Test với real images khác nhau
- Test error scenarios

### Performance Tests
- Benchmark processing time cho các kích thước ảnh khác nhau
- Profile memory usage
- Optimize hot paths

## Deployment Architecture

### Development
```
Local machine
├─ Python 3.9+
├─ Virtual environment
├─ Streamlit dev server
└─ Browser (localhost:8501)
```

### Production (Future)
```
Docker container
├─ Python runtime
├─ SmartScan application
├─ Streamlit server
└─ Reverse proxy (nginx)
```

## Monitoring & Logging

### Logging Levels
- DEBUG: Detailed processing steps
- INFO: User actions, successful operations
- WARNING: Non-critical issues (e.g., low quality detection)
- ERROR: Processing failures, exceptions

### Metrics to Track
- Processing time per image
- Success/failure rate
- Average image size
- Resource usage (CPU, memory)

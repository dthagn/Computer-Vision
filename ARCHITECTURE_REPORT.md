# SmartScan Architecture Report

**Date**: 2026-11-02
**Architect**: Senior Software Architect (Computer Vision & Digital Image Processing)
**Project**: SmartScan - Intelligent Document Scanner

---

## 1. Files Created

### Project Specification
- **PROJECT_SPEC.md** - Mô tả bài toán, mục tiêu, MVP scope, pipeline, kiến trúc phần mềm

### Directory Structure
```
Xử lý ảnh/
├── PROJECT_SPEC.md
├── AGENT_HANDOFF.md
├── requirements.txt
├── ARCHITECTURE_REPORT.md (this file)
├── smartscan/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── detection.py (stub)
│   │   ├── correction.py (stub)
│   │   └── enhancement.py (stub)
│   ├── ui/
│   │   ├── __init__.py
│   │   └── app.py (stub)
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── image_utils.py (implemented)
│   │   └── constants.py (implemented)
│   └── tests/
│       └── __init__.py
└── docs/
    ├── __init__.py
    ├── architecture.md
    └── api.md
```

### Documentation
- **docs/architecture.md** - Luồng dữ liệu, quan hệ module, kiến trúc hệ thống
- **docs/api.md** - API specification, data contracts, function signatures
- **AGENT_HANDOFF.md** - Trách nhiệm từng Agent, handoff protocol

### Configuration
- **requirements.txt** - Dependencies (opencv-python, numpy, streamlit, pytest)
- **smartscan/utils/constants.py** - Constants và parameters
- **smartscan/utils/image_utils.py** - Helper functions (rgb_to_bgr, bgr_to_rgb, validate_image)

---

## 2. Architectural Decisions

### 2.1 Technology Stack
**Decision**: Python + OpenCV + NumPy + Streamlit

**Rationale**:
- Python: Ecosystem mạnh cho Computer Vision, dễ bảo trì
- OpenCV: Thư viện chuẩn cho image processing, performant
- NumPy: Efficient array operations, chuẩn cho data science
- Streamlit: Fast prototyping cho web UI, dễ tích hợp với Python backend

**Alternatives Considered**:
- Flask/FastAPI + React: Phức tạp hơn, không cần cho MVP
- PyTorch/TensorFlow: Overkill, không cần Deep Learning
- Desktop app (Electron): Web UI đủ tốt, dễ deploy hơn

### 2.2 Architecture Pattern
**Decision**: Modular Pipeline Architecture

**Rationale**:
- Mỗi processing step là module độc lập
- Dễ test, debug, maintain
- Dễ extend (thêm enhancement steps mới)
- Rõ ràng data flow giữa các stage

**Pattern Applied**:
```
Input → Detect → Correct → Enhance → Output
```

### 2.3 Data Format
**Decision**: OpenCV BGR for processing, RGB for display

**Rationale**:
- OpenCV default là BGR → nên dùng BGR trong core để tránh conversion liên tục
- Streamlit/Display mặc định RGB → convert tại boundary
- NumPy uint8: Standard format cho images, memory efficient

**Contract**:
- Core modules: Input/Output = BGR, uint8
- UI layer: Display = RGB, uint8
- Conversion: rgb_to_bgr(), bgr_to_rgb() tại boundary

### 2.4 Corner Coordinate System
**Decision**: TL, TR, BR, BL order (clockwise from top-left)

**Rationale**:
- Thứ tự chuẩn cho perspective transform
- Dễ visualize và debug
- Consistent với OpenCV conventions

**Format**: NumPy array (4, 2), dtype float32 or int32

### 2.5 Error Handling Strategy
**Decision**: Descriptive exceptions with graceful degradation

**Rationale**:
- Exceptions help debugging
- Graceful degradation giữ UX tốt
- User-friendly error messages

**Implementation**:
- Core functions raise descriptive exceptions
- UI layer catches and displays user-friendly messages
- Log technical details server-side

### 2.6 Module Independence
**Decision**: No shared file editing between Agents

**Rationale**:
- Tránh merge conflicts
- Rõ ràng responsibility
- Dễ track changes

**Implementation**:
- Mỗi Agent chỉ edit files được phân công
- Handoff protocol quy định rõ
- Version control recommended

### 2.7 No Deep Learning Constraint
**Decision**: Computer Vision cổ điển only

**Rationale**:
- Code dễ giải thích và defend
- Không cần GPU, deploy dễ hơn
- Đủ cho use case phát hiện tài liệu đơn giản
- Có thể upgrade sau nếu cần

**Techniques Used**:
- Canny edge detection
- Contour detection
- Perspective transform
- Classical enhancement (contrast, denoise, threshold)

---

## 3. Agent Responsibilities Summary

| Agent | Responsibility | Files to Edit | Deliverables |
|-------|---------------|---------------|--------------|
| 1 | Project Setup | requirements.txt, constants.py, __init__.py | Setup scripts, validated dependencies |
| 2 | Document Detection | detection.py, tests/, image_utils.py (helper) | detect_document() with tests |
| 3 | Perspective Correction | correction.py, tests/, image_utils.py (helper) | correct_perspective() with tests |
| 4 | Image Enhancement | enhancement.py, constants.py, tests/ | enhance_document() with tests |
| 5 | Streamlit UI | app.py, tests/ | Full web interface |
| 6 | Integration & Testing | All files (bug fixes only) | Integration tests, bug fixes, documentation |

---

## 4. Data Contracts

### Image Format
- **Processing**: BGR, NumPy uint8 array
- **Display**: RGB, NumPy uint8 array
- **Validation**: validate_image() checks shape, dtype, type

### Corner Coordinates
- **Format**: NumPy array (4, 2)
- **Order**: TL, TR, BR, BL (clockwise from top-left)
- **Dtype**: float32 or int32
- **Range**: 0 <= x < W, 0 <= y < H

### API Functions
- `detect_document(image) → corners`
- `correct_perspective(image, corners) → corrected_image`
- `enhance_document(image) → enhanced_image`
- `process_document(image) → result_dict`

---

## 5. Conditions for Agent 1 to Start

### Prerequisites Met ✓
- [x] PROJECT_SPEC.md exists and approved
- [x] Directory structure created
- [x] Agent Handoff protocol defined
- [x] Data contracts established
- [x] API specifications documented
- [x] Architecture documented
- [x] requirements.txt created (pending validation)
- [x] constants.py created (pending validation)

### Starting Conditions for Agent 1
1. Review PROJECT_SPEC.md to understand project goals
2. Review docs/architecture.md to understand system design
3. Review docs/api.md to understand data contracts
4. Review AGENT_HANDOFF.md to understand responsibilities
5. Validate requirements.txt - ensure all dependencies are correct versions
6. Validate constants.py - ensure parameters are reasonable
7. Create README.md with setup instructions
8. Initialize git repository (optional but recommended)
9. Test: `pip install -r requirements.txt` should succeed
10. Test: Basic imports should work (import cv2, numpy, streamlit)

### Agent 1 Deliverables
- Validated requirements.txt
- Updated constants.py (if needed)
- README.md with setup instructions
- .gitignore (if using git)
- Confirmation that all imports work

### Agent 1 Success Criteria
- [ ] `pip install -r requirements.txt` completes without errors
- [ ] `import cv2` works
- [ ] `import numpy` works
- [ ] `import streamlit` works
- [ ] Constants are reasonable for target environment
- [ ] README.md provides clear setup instructions
- [ ] No conflicts with existing files

---

## 6. Handoff to Agent 1

### Ready for Handoff: YES ✓

All prerequisite documents and structures are in place:
- Project specification clear
- Architecture documented
- API contracts defined
- Agent responsibilities specified
- Directory structure created
- Configuration files initialized

### Next Steps for Agent 1
1. Read all documentation (PROJECT_SPEC.md, docs/architecture.md, docs/api.md, AGENT_HANDOFF.md)
2. Validate and finalize requirements.txt
3. Validate and finalize constants.py
4. Create README.md with setup instructions
5. Test installation and imports
6. Confirm ready for handoff to Agent 2

### Handoff Checklist
- [x] PROJECT_SPEC.md created
- [x] Directory structure created
- [x] AGENT_HANDOFF.md created
- [x] docs/architecture.md created
- [x] docs/api.md created
- [x] requirements.txt created
- [x] constants.py created
- [x] image_utils.py created
- [x] Stub files for core modules created
- [x] Architectural decisions documented
- [x] Data contracts established
- [x] Agent responsibilities defined

---

## 7. Notes for Future Agents

### For Agent 2 (Detection)
- Focus on classical CV techniques (Canny, contours)
- Handle edge cases: no document found, multiple documents
- Return corners in TL, TR, BR, BL order
- Add visualization for debugging (optional)

### For Agent 3 (Correction)
- Use cv2.getPerspectiveTransform and cv2.warpPerspective
- Calculate appropriate output dimensions
- Handle degenerate cases (collinear corners)
- Test with extreme angles

### For Agent 4 (Enhancement)
- Implement each enhancement step separately
- Make steps configurable via constants
- Test with various image qualities
- Consider adding option to disable certain steps

### For Agent 5 (UI)
- Keep conversion RGB/BGR correct at boundaries
- Provide progress indicators
- Show intermediate results (optional)
- Handle errors gracefully with user-friendly messages

### For Agent 6 (Integration)
- Focus on end-to-end testing
- Fix integration bugs only
- Profile performance
- Document any changes

---

## 8. Architecture Validation

### Strengths
- ✓ Modular design with clear separation of concerns
- ✓ Well-defined data contracts
- ✓ Classical CV approach (explainable, no GPU needed)
- ✓ Clear agent responsibilities
- ✓ Comprehensive documentation

### Potential Risks
- ⚠ Detection accuracy may vary with image quality
- ⚠ Performance on large images needs optimization
- ⚠ No OCR capability (future enhancement)
- ⚠ Single-threaded processing (may limit scalability)

### Mitigation Strategies
- Test with diverse image types
- Add image size limits/downscaling
- Document limitations clearly
- Consider async/multi-processing for future versions

---

## Conclusion

Architecture đã được thiết kế hoàn chỉnh với:
- ✓ Mục tiêu rõ ràng và achievable
- ✓ Technology stack phù hợp
- ✓ Modular, maintainable design
- ✓ Well-documented APIs and contracts
- ✓ Clear agent responsibilities
- ✓ Conditions ready cho Agent 1 bắt đầu

**Status**: READY FOR AGENT 1
**Confidence Level**: HIGH

# API Specification

## Data Contracts

### Image Format
- **OpenCV Processing**: BGR format, NumPy array, dtype uint8
- **Streamlit Display**: RGB format, NumPy array, dtype uint8
- **Conversion**: Use utilities in `smartscan/utils/image_utils.py`

### Corner Coordinates
- **Format**: NumPy array, shape (4, 2), dtype float32 or int32
- **Order**: TL (Top-Left), TR (Top-Right), BR (Bottom-Right), BL (Bottom-Left)
- **Example**: `[[x1, y1], [x2, y2], [x3, y3], [x4, y4]]`

### Error Handling
- All functions raise descriptive exceptions on failure
- Return None only for non-critical failures
- Log errors appropriately

---

## Core API Functions

### `detect_document(image)`

**Location**: `smartscan/core/detection.py`

**Purpose**: Detect document boundaries and return 4 corner coordinates

**Input**:
```python
image: np.ndarray
    - Shape: (H, W, 3) for color, (H, W) for grayscale
    - Format: BGR (OpenCV standard)
    - Dtype: uint8
    - Validated: Yes (should pass validate_image())
```

**Output**:
```python
corners: np.ndarray
    - Shape: (4, 2)
    - Format: [[x_tl, y_tl], [x_tr, y_tr], [x_br, y_br], [x_bl, y_bl]]
    - Order: TL, TR, BR, BL
    - Dtype: float32 or int32
    - Range: 0 <= x < W, 0 <= y < H
```

**Raises**:
- `ValueError`: If image is invalid or None
- `RuntimeError`: If document cannot be detected

**Algorithm**:
1. Convert to grayscale
2. Apply Gaussian blur
3. Canny edge detection
4. Find contours
5. Select largest 4-sided contour
6. Approximate to 4 corners
7. Sort corners in TL, TR, BR, BL order

**Example**:
```python
import cv2
from smartscan.core.detection import detect_document

image = cv2.imread("document.jpg")  # BGR format
corners = detect_document(image)
print(corners)  # [[100, 100], [500, 100], [500, 700], [100, 700]]
```

---

### `correct_perspective(image, corners)`

**Location**: `smartscan/core/correction.py`

**Purpose**: Apply perspective transformation to straighten document

**Input**:
```python
image: np.ndarray
    - Shape: (H, W, 3)
    - Format: BGR
    - Dtype: uint8

corners: np.ndarray
    - Shape: (4, 2)
    - Order: TL, TR, BR, BL
    - Dtype: float32 or int32
```

**Output**:
```python
corrected_image: np.ndarray
    - Shape: (H_out, W_out, 3)
    - Format: BGR
    - Dtype: uint8
    - Properties: Rectangular, straight edges
```

**Raises**:
- `ValueError`: If corners shape is invalid
- `ValueError`: If corners are collinear or degenerate
- `RuntimeError`: If transformation fails

**Algorithm**:
1. Calculate output dimensions from corner distances
2. Define destination corners as rectangle
3. Compute perspective transform matrix
4. Apply warp perspective
5. Return corrected image

**Example**:
```python
from smartscan.core.perspective import correct_perspective

result = correct_perspective(image, corners)
corrected = result['corrected_image']
cv2.imwrite("corrected.jpg", corrected)
```

---

### `enhance_document(image)`

**Location**: `smartscan/core/enhancement.py`

**Purpose**: Enhance document image quality through multiple techniques

**Input**:
```python
image: np.ndarray
    - Shape: (H, W, 3)
    - Format: BGR
    - Dtype: uint8
```

**Output**:
```python
enhanced_image: np.ndarray
    - Shape: (H, W, 3)
    - Format: BGR
    - Dtype: uint8
    - Properties: Improved contrast, reduced noise, etc.
```

**Enhancement Steps** (applied in order):
1. **Contrast/Brightness Adjustment**
   - Alpha: 1.2 (from constants)
   - Beta: 10 (from constants)
   
2. **Denoising/Smoothing**
   - Method: cv2.fastNlMeansDenoisingColored
   - h: 10 (from constants)
   
3. **Binarization** (optional, configurable)
   - Method: Adaptive threshold or Otsu
   - Threshold: 127 (from constants)
   
4. **Color Correction**
   - White balance adjustment
   - Gamma correction

**Raises**:
- `ValueError`: If image is invalid
- `RuntimeError`: If enhancement fails

**Example**:
```python
from smartscan.core.enhancement import enhance_document

enhanced = enhance_document(corrected_image)
cv2.imwrite("enhanced.jpg", enhanced)
```

---

### `process_document(image)`

**Location**: `smartscan/core/__init__.py` (or separate pipeline.py)

**Purpose**: End-to-end document processing pipeline

**Input**:
```python
image: np.ndarray
    - Shape: (H, W, 3)
    - Format: BGR
    - Dtype: uint8
```

**Output**:
```python
result: dict
    {
        "original": np.ndarray,      # Original image (BGR)
        "corners": np.ndarray,       # Detected corners (4, 2)
        "corrected": np.ndarray,    # Perspective-corrected (BGR)
        "enhanced": np.ndarray,     # Enhanced final image (BGR)
        "success": bool,             # Processing success flag
        "error": str or None         # Error message if failed
    }
```

**Pipeline Steps**:
1. Validate input image
2. Detect document corners
3. Correct perspective
4. Enhance image
5. Return all intermediate results

**Raises**:
- Does not raise exceptions on individual step failures
- Returns error message in result dict

**Example**:
```python
from smartscan.core import process_document

image = cv2.imread("document.jpg")
result = process_document(image)

if result["success"]:
    cv2.imwrite("final.jpg", result["enhanced"])
else:
    print(f"Error: {result['error']}")
```

---

## Utility Functions

### `rgb_to_bgr(image)`
- Input: RGB NumPy array (uint8)
- Output: BGR NumPy array (uint8)
- Purpose: Convert from Streamlit to OpenCV format

### `bgr_to_rgb(image)`
- Input: BGR NumPy array (uint8)
- Output: RGB NumPy array (uint8)
- Purpose: Convert from OpenCV to Streamlit format

### `validate_image(image)`
- Input: NumPy array
- Output: bool
- Purpose: Check if image is valid format and dtype

---

## Integration with Streamlit

### Upload Handler
```python
uploaded_file = st.file_uploader("Upload document", type=["jpg", "png", "jpeg"])
if uploaded_file:
    # Read as bytes
    bytes_data = uploaded_file.getvalue()
    
    # Convert to NumPy array (RGB)
    nparr = np.frombuffer(bytes_data, np.uint8)
    image_rgb = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    image_rgb = cv2.cvtColor(image_rgb, cv2.COLOR_BGR2RGB)
    
    # Convert to BGR for processing
    image_bgr = rgb_to_bgr(image_rgb)
    
    # Process
    result = process_document(image_bgr)
    
    # Convert back to RGB for display
    final_rgb = bgr_to_rgb(result["enhanced"])
    
    # Display
    st.image(final_rgb)
```

### Download Handler
```python
# Convert to bytes for download
_, buffer = cv2.imencode(".jpg", result["enhanced"])
bytes_data = buffer.tobytes()

st.download_button(
    label="Download processed image",
    data=bytes_data,
    file_name="processed_document.jpg",
    mime="image/jpeg"
)
```

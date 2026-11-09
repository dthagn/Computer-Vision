# SmartScan Pipeline Flow Diagram

## Luồng Chạy Pipeline Thực Tế

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER UPLOAD IMAGE (Streamlit)                │
│  - Upload file (JPG/PNG/BMP, max 10MB)                          │
│  - Validate file size and dimensions                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  load_and_validate_image()                      │
│  [src/image_loader.py]                                          │
│  ├─ validate_file_size() - Check < 10MB                        │
│  ├─ load_image_from_bytes() - Decode image                     │
│  ├─ validate_image_dimensions() - Check < 4000x4000            │
│  └─ Return: (success, image_bgr, message)                      │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                process_document_with_fallback()                 │
│  [src/pipeline.py]                                              │
│  ├─ Try auto detection first                                   │
│  └─ If failed, set needs_manual_corners = True                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   detect_document()                             │
│  [src/detection.py]                                             │
│  ├─ validate_image() - Check NumPy array, uint8, dimensions    │
│  ├─ If manual_corners provided:                                │
│  │   ├─ Validate shape (4, 2)                                  │
│  │   ├─ order_corners() - Sort TL, TR, BR, BL                   │
│  │   └─ check_self_intersection() - Validate geometry          │
│  ├─ Else (auto detection):                                      │
│  │   ├─ preprocess_for_detection() [src/preprocessing.py]       │
│  │   │   ├─ resize_with_aspect_ratio() - Scale down if needed  │
│  │   │   ├─ convert_to_grayscale()                              │
│  │   │   ├─ apply_gaussian_blur()                               │
│  │   │   ├─ apply_canny_edge_detection() - Multiple thresholds │
│  │   │   └─ apply_morphology() - Close operation                │
│  │   ├─ find_document_contour() - Find best contour             │
│  │   │   ├─ cv2.findContours()                                  │
│  │   │   ├─ cv2.approxPolyDP() - Approximate to 4 points        │
│  │   │   ├─ compute_convexity_score() - Score 0-1               │
│  │   │   └─ compute_quadrilateral_score() - Score 0-1          │
│  │   ├─ map_coordinates_to_original() - Scale back            │
│  │   ├─ order_corners() - Sort TL, TR, BR, BL                  │
│  │   └─ check_self_intersection() - Validate geometry         │
│  └─ Return: {success, corners, confidence, message}           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              │ Detection Success?    │
              └───────────┬───────────┘
                    │         │
                   NO        YES
                    │         │
                    ▼         ▼
        ┌──────────────────┐  ┌─────────────────────────────────┐
        │ needs_manual_    │  │ correct_perspective()           │
        │ corners = True   │  │ [src/perspective.py]            │
        │ (UI prompts for  │  ├─ validate_corners() - Check     │
        │ manual input)    │  │   shape, bounds, duplicates     │
        └──────────────────┘  ├─ check_self_intersection()     │
                              ├─ calculate_output_dimensions() │
                              │   - Compute width/height from    │
                              │     edge lengths                 │
                              ├─ compute_homography_matrix()    │
                              │   - cv2.getPerspectiveTransform  │
                              ├─ cv2.warpPerspective()          │
                              │   - Apply transform              │
                              │   - White background padding     │
                              └─ Return: {success,               │
                              │            corrected_image,       │
                              │            output_size}           │
                              └────────────┬────────────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────────────┐
                              │ enhance_document()              │
                              │ [src/enhancement.py]            │
                              ├─ validate_image()               │
                              ├─ Step 1: Shadow Correction      │
                              │   (if enabled)                   │
                              │   ├─ correct_shadow()            │
                              │   │   └─ apply_morphological_    │
                              │   │       shadow_correction()    │
                              │   │       - Dilate background    │
                              │   │       - Blur background      │
                              │   │       - Normalize lighting   │
                              │   └─ current_image = result     │
                              ├─ Step 2: Denoising              │
                              │   ├─ denoise_image()             │
                              │   │   ├─ gaussian_denoise()      │
                              │   │   ├─ median_denoise()        │
                              │   │   └─ bilateral_denoise()     │
                              │   └─ current_image = result     │
                              ├─ Step 3: Contrast Enhancement   │
                              │   ├─ enhance_contrast()          │
                              │   │   ├─ histogram_equalization() │
                              │   │   └─ clahe() - Adaptive      │
                              │   └─ current_image = result     │
                              ├─ Step 4: Sharpening             │
                              │   (if enabled)                   │
                              │   ├─ sharpen_image()             │
                              │   │   ├─ unsharp_mask()          │
                              │   │   └─ kernel_sharpen()        │
                              │   └─ current_image = result     │
                              ├─ Step 5: Binarization           │
                              │   (if enabled)                   │
                              │   ├─ binarize_image()            │
                              │   │   ├─ global_threshold()     │
                              │   │   ├─ otsu_threshold()        │
                              │   │   ├─ adaptive_mean_thresh()  │
                              │   │   └─ adaptive_gaussian_      │
                              │   │       threshold()            │
                              │   └─ current_image = result     │
                              └─ Return: {success,               │
                                         enhanced_image,          │
                                         message}                 │
                              └────────────┬────────────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────────────┐
                              │ Return Result                    │
                              │ {                                │
                              │   success: True,                 │
                              │   original_image: BGR,          │
                              │   detected_corners: (4,2),       │
                              │   scanned_image: BGR,            │
                              │   enhanced_image: BGR,          │
                              │   steps: {                       │
                              │     detection: {success, time},  │
                              │     perspective: {success, time},│
                              │     enhancement: {success, time} │
                              │   },                             │
                              │   processing_time: float         │
                              │ }                                │
                              └────────────┬────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DISPLAY RESULTS (Streamlit)                   │
│  ├─ Show original image (BGR → RGB)                              │
│  ├─ Show scanned image (BGR → RGB)                               │
│  ├─ Show enhanced image (BGR → RGB)                              │
│  ├─ Show processing steps with times                            │
│  ├─ Download buttons:                                           │
│  │   ├─ Scanned image (JPG)                                     │
│  │   ├─ Enhanced image (JPG)                                    │
│  │   └─ Enhanced image (PNG)                                    │
│  ├─ Comparison view (side-by-side)                               │
│  └─ Allow re-enhancement with new config                        │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Summary

### Input
- **Format**: NumPy array (BGR, uint8)
- **Source**: Streamlit upload (RGB) → convert to BGR
- **Constraints**: Max 10MB, max 4000x4000 pixels

### Processing Stages
1. **Detection**: Find 4 corners (TL, TR, BR, BL)
2. **Perspective**: Warp to rectangle with padding
3. **Enhancement**: Apply selected algorithms

### Output
- **Format**: NumPy array (BGR, uint8)
- **Display**: Convert to RGB for Streamlit
- **Download**: Encode to JPG/PNG bytes

## Session State Flow

```
Upload → st.session_state.original_image (BGR)
      ↓
Process → st.session_state.detected_corners (4,2)
       → st.session_state.scanned_image (BGR)
       → st.session_state.enhanced_image (BGR)
       → st.session_state.processing_result (dict)
      ↓
Change Config → st.session_state.enhancement_config (dict)
              ↓
Re-enhance → update_enhancement(scanned_image, new_config)
           → st.session_state.enhanced_image (updated BGR)
```

## Error Handling Flow

```
Detection Failed
    ↓
Set needs_manual_corners = True
    ↓
UI: Show manual corners input form
    ↓
User enters 4 corners (TL, TR, BR, BL)
    ↓
Validate manual corners
    ↓
If valid → Continue to perspective
If invalid → Show error, retry
```

```
Perspective Failed
    ↓
Show error message
    ↓
Stop processing
    ↓
User can retry with different corners
```

```
Enhancement Failed
    ↓
Partial success: Return scanned_image
    ↓
Show error message
    ↓
User can download scanned_image
    ↓
User can retry with different config
```

## Performance Characteristics

| Stage | Typical Time | Notes |
|-------|-------------|-------|
| Detection | 0.05-0.15s | Multiple Canny thresholds |
| Perspective | 0.01-0.05s | Simple warp transform |
| Enhancement | 0.15-0.25s | Depends on algorithms |
| **Total** | **0.2-0.5s** | For 500x700 image |

## Key Integration Points

1. **BGR/RGB Conversion**: Always convert at UI boundaries
2. **Session State**: Store all intermediate results
3. **Error Handling**: Graceful degradation at each stage
4. **Fallback**: Manual corners when auto detection fails
5. **Re-enhancement**: Allow changing config without re-processing

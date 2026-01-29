#!/usr/bin/env python3
"""
Dynamic Object Detection - Detect moving objects after compensating for camera motion
Outputs binary masks in CSR sparse format for each sampled frame.
"""
import cv2
import numpy as np
import json
import sys
from pathlib import Path

# Morphology kernel sizes
KERNEL_OPEN = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
KERNEL_CLOSE = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

# Minimum area threshold (as fraction of image area)
MIN_AREA_RATIO = 0.0005  # 0.05% of image area

# Minimum difference threshold (to avoid noise)
MIN_DIFF_THRESHOLD = 20

# Feature tracking parameters for transform estimation
FEATURE_PARAMS = dict(
    maxCorners=500,
    qualityLevel=0.01,
    minDistance=10,
    blockSize=7
)

LK_PARAMS = dict(
    winSize=(21, 21),
    maxLevel=3,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)
)

MIN_FEATURES = 10


def estimate_affine_transform(prev_gray, curr_gray):
    """
    Estimate affine transformation from prev_gray to curr_gray using optical flow.

    Returns:
        2x3 affine matrix, or None if estimation fails
    """
    # Detect features in previous frame
    prev_pts = cv2.goodFeaturesToTrack(prev_gray, mask=None, **FEATURE_PARAMS)

    if prev_pts is None or len(prev_pts) < MIN_FEATURES:
        return None

    # Calculate optical flow
    curr_pts, status, err = cv2.calcOpticalFlowPyrLK(
        prev_gray, curr_gray, prev_pts, None, **LK_PARAMS
    )

    if curr_pts is None:
        return None

    # Filter good points
    good_prev = prev_pts[status == 1]
    good_curr = curr_pts[status == 1]

    if len(good_prev) < MIN_FEATURES:
        return None

    # Estimate affine transformation with RANSAC
    matrix, inliers = cv2.estimateAffinePartial2D(
        good_prev, good_curr,
        method=cv2.RANSAC,
        ransacReprojThreshold=3.0,
        confidence=0.99
    )

    return matrix


def detect_dynamic_objects(prev_gray, curr_gray, width, height):
    """
    Detect dynamic objects by compensating for camera motion.

    Args:
        prev_gray: Previous frame (grayscale)
        curr_gray: Current frame (grayscale)
        width, height: Frame dimensions

    Returns:
        Binary mask (bool array) indicating dynamic object pixels
    """
    # Estimate global camera motion
    M = estimate_affine_transform(prev_gray, curr_gray)

    if M is None:
        # Cannot estimate motion - return identity transform
        M = np.array([[1, 0, 0], [0, 1, 0]], dtype=np.float32)

    # Warp previous frame to current frame using estimated transform
    warped_prev = cv2.warpAffine(
        prev_gray, M, (width, height),
        flags=cv2.INTER_LINEAR,
        borderValue=0
    )

    # Create valid region mask (exclude border artifacts from warping)
    ones_mask = np.ones((height, width), dtype=np.uint8)
    valid_mask = cv2.warpAffine(
        ones_mask, M, (width, height),
        flags=cv2.INTER_NEAREST,
        borderValue=0
    ) > 0

    # Compute absolute difference
    diff = cv2.absdiff(curr_gray, warped_prev)

    # Adaptive thresholding using MAD (Median Absolute Deviation) on valid region
    valid_diffs = diff[valid_mask]

    if len(valid_diffs) == 0:
        # No valid region - return empty mask
        return np.zeros((height, width), dtype=bool)

    median_diff = np.median(valid_diffs)
    mad = np.median(np.abs(valid_diffs - median_diff))

    # Threshold = median + 3 * MAD (scaled by 1.4826 for normal distribution)
    # But ensure minimum threshold to avoid noise
    threshold = max(MIN_DIFF_THRESHOLD, median_diff + 3 * 1.4826 * mad)

    # Initial binary mask: significant difference in valid region
    raw_mask = (diff > threshold) & valid_mask

    # Morphological operations to clean up noise
    # Open: remove small noise
    cleaned = cv2.morphologyEx(
        raw_mask.astype(np.uint8) * 255,
        cv2.MORPH_OPEN,
        KERNEL_OPEN
    )

    # Close: fill small holes
    cleaned = cv2.morphologyEx(
        cleaned,
        cv2.MORPH_CLOSE,
        KERNEL_CLOSE
    )

    # Connected components analysis with area filtering
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        cleaned, connectivity=8
    )

    # Calculate minimum area threshold
    min_area = int(width * height * MIN_AREA_RATIO)

    # Build final mask by keeping only large components
    final_mask = np.zeros((height, width), dtype=bool)

    for component_id in range(1, num_labels):  # Skip background (0)
        area = stats[component_id, cv2.CC_STAT_AREA]
        if area >= min_area:
            final_mask |= (labels == component_id)

    return final_mask


def mask_to_csr(mask):
    """
    Convert boolean mask to CSR (Compressed Sparse Row) format.

    CSR format stores:
    - data: array of non-zero values (all 1s for binary mask)
    - indices: column indices of non-zero values
    - indptr: row pointer array (cumulative count of non-zeros per row)

    Returns:
        dict with keys: data, indices, indptr (all as arrays)
    """
    height, width = mask.shape

    # Find non-zero positions
    rows, cols = np.nonzero(mask)

    # CSR data
    nnz = len(rows)
    data = np.ones(nnz, dtype=np.uint8)
    indices = cols.astype(np.int32)

    # Build indptr: cumulative count of non-zeros per row
    row_counts = np.bincount(rows, minlength=height)
    indptr = np.concatenate([[0], np.cumsum(row_counts)]).astype(np.int32)

    return {
        'data': data,
        'indices': indices,
        'indptr': indptr
    }


def process_video(video_path, sampling_config_path):
    """
    Process video and detect dynamic objects for all sampled frames.
    """
    # Load sampling configuration
    with open(sampling_config_path, 'r') as f:
        config = json.load(f)

    sample_ids = config['sample_ids']
    width = config['width']
    height = config['height']

    print(f"Processing video: {video_path}")
    print(f"Resolution: {width}x{height}")
    print(f"Sampled frames: {len(sample_ids)}")

    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    # Extract sampled frames
    frames = []
    for sample_id in sample_ids:
        cap.set(cv2.CAP_PROP_POS_FRAMES, sample_id)
        ret, frame = cap.read()
        if not ret:
            raise ValueError(f"Failed to read frame {sample_id}")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frames.append(gray)

    cap.release()
    print(f"Extracted {len(frames)} frames")

    # Detect dynamic objects for each frame (comparing with previous frame)
    print("\nDetecting dynamic objects...")

    masks_csr = {}

    # First frame: no previous frame, so empty mask
    first_mask = np.zeros((height, width), dtype=bool)
    csr_data = mask_to_csr(first_mask)
    masks_csr[sample_ids[0]] = csr_data
    print(f"  Frame {sample_ids[0]:3d}: No previous frame - empty mask")

    # Process remaining frames
    for i in range(1, len(frames)):
        mask = detect_dynamic_objects(frames[i-1], frames[i], width, height)
        csr_data = mask_to_csr(mask)

        masks_csr[sample_ids[i]] = csr_data

        num_pixels = np.sum(mask)
        percent = 100.0 * num_pixels / (width * height)
        print(f"  Frame {sample_ids[i]:3d}: {num_pixels:6d} pixels ({percent:5.2f}%)")

    print(f"\nTotal masks generated: {len(masks_csr)}")

    return masks_csr, height, width


def save_masks_npz(masks_csr, height, width, output_path):
    """
    Save masks in NPZ format with CSR encoding.

    Format:
    - shape: [H, W]
    - For each frame i: f_{i}_data, f_{i}_indices, f_{i}_indptr
    """
    data_dict = {
        'shape': np.array([height, width], dtype=np.int32)
    }

    for frame_id, csr_data in masks_csr.items():
        prefix = f"f_{frame_id}"
        data_dict[f"{prefix}_data"] = csr_data['data']
        data_dict[f"{prefix}_indices"] = csr_data['indices']
        data_dict[f"{prefix}_indptr"] = csr_data['indptr']

    np.savez_compressed(output_path, **data_dict)
    print(f"\n✓ Masks saved to: {output_path}")


def self_check(masks_csr, sample_ids, height, width):
    """
    Perform self-checks on the output.
    """
    print("\n=== Self-check ===")
    checks = []

    # Check 1: Masks only for sampled frames
    mask_ids = set(masks_csr.keys())
    sample_ids_set = set(sample_ids)
    checks.append((
        "Masks only for sampled frames",
        mask_ids == sample_ids_set
    ))

    # Check 2: All masks have valid CSR structure
    valid_csr = True
    for frame_id, csr_data in masks_csr.items():
        # Check indptr length
        if len(csr_data['indptr']) != height + 1:
            valid_csr = False
            break

        # Check indptr[-1] == len(indices)
        if csr_data['indptr'][-1] != len(csr_data['indices']):
            valid_csr = False
            break

        # Check data and indices have same length
        if len(csr_data['data']) != len(csr_data['indices']):
            valid_csr = False
            break

    checks.append(("All masks have valid CSR structure", valid_csr))

    # Check 3: indptr values are non-decreasing
    monotonic = True
    for frame_id, csr_data in masks_csr.items():
        indptr = csr_data['indptr']
        if not np.all(indptr[1:] >= indptr[:-1]):
            monotonic = False
            break

    checks.append(("All indptr arrays are non-decreasing", monotonic))

    # Check 4: Indices are within valid range [0, width)
    valid_indices = True
    for frame_id, csr_data in masks_csr.items():
        indices = csr_data['indices']
        if len(indices) > 0:
            if np.any(indices < 0) or np.any(indices >= width):
                valid_indices = False
                break

    checks.append(("All indices within [0, width)", valid_indices))

    # Check 5: Data arrays contain only 1s (or are empty)
    valid_data = True
    for frame_id, csr_data in masks_csr.items():
        data = csr_data['data']
        if len(data) > 0:
            if not np.all(data == 1):
                valid_data = False
                break

    checks.append(("All data arrays contain only 1s", valid_data))

    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"[{status}] {check_name}: {passed}")

    return all(check[1] for check in checks)


if __name__ == "__main__":
    video_path = sys.argv[1] if len(sys.argv) > 1 else "/root/input.mp4"
    sampling_config_path = sys.argv[2] if len(sys.argv) > 2 else \
        "/logs/agent/sessions/skills/sampling-and-indexing/sampling_config.json"

    # Process video
    masks_csr, height, width = process_video(video_path, sampling_config_path)

    # Load sampling config to get sample_ids
    with open(sampling_config_path, 'r') as f:
        config = json.load(f)
    sample_ids = config['sample_ids']

    # Save masks
    output_path = "/logs/agent/sessions/skills/dyn-object-masks/dynamic_masks.npz"
    save_masks_npz(masks_csr, height, width, output_path)

    # Self-check
    if self_check(masks_csr, sample_ids, height, width):
        print("\n✓ All self-checks passed!")
        sys.exit(0)
    else:
        print("\n✗ Some self-checks failed!")
        sys.exit(1)

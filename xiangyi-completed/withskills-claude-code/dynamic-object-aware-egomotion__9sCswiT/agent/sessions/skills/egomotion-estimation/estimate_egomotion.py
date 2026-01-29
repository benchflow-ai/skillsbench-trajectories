#!/usr/bin/env python3
"""
Egomotion Estimation - Camera motion classification using optical flow
Classifies camera motion into: Stay, Dolly In/Out, Pan Left/Right, Tilt Up/Down, Roll Left/Right
Allows multiple labels per frame interval.
"""
import cv2
import numpy as np
import json
import sys
from pathlib import Path

# Thresholds (tuned for 720p, ~6fps sampling)
# Translation threshold as fraction of image dimension
TRANS_THRESHOLD_RATIO = 0.01  # 1% of image width/height
ROTATION_THRESHOLD_DEG = 2.0  # degrees
SCALE_THRESHOLD = 0.02  # 2% scale change

# Feature tracking parameters
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

MIN_FEATURES = 10  # Minimum features required for valid estimation


def extract_transform_params(matrix):
    """
    Extract translation, rotation, and scale from affine transformation matrix.

    Returns:
        (tx, ty, rotation_rad, scale)
    """
    if matrix is None:
        return 0, 0, 0, 1.0

    # Affine matrix: [[a, b, tx], [c, d, ty]]
    a, b, tx = matrix[0]
    c, d, ty = matrix[1]

    # Scale: average of x and y scales
    scale_x = np.sqrt(a**2 + c**2)
    scale_y = np.sqrt(b**2 + d**2)
    scale = (scale_x + scale_y) / 2.0

    # Rotation: arctan2 of rotation components
    rotation = np.arctan2(c, a)

    return tx, ty, rotation, scale


def classify_motion(tx, ty, rotation, scale, width, height):
    """
    Classify camera motion based on transformation parameters.

    Note: Image coordinates vs camera motion:
    - Positive tx (right shift in image) = Camera panned LEFT
    - Negative tx (left shift in image) = Camera panned RIGHT
    - Positive ty (down shift in image) = Camera tilted UP
    - Negative ty (up shift in image) = Camera tilted DOWN
    - Scale > 1 = Camera moved closer (Dolly In)
    - Scale < 1 = Camera moved away (Dolly Out)
    - Positive rotation = Counter-clockwise = Roll Left
    - Negative rotation = Clockwise = Roll Right

    Returns:
        List of motion labels
    """
    labels = []

    # Thresholds
    trans_threshold_x = width * TRANS_THRESHOLD_RATIO
    trans_threshold_y = height * TRANS_THRESHOLD_RATIO
    rotation_threshold_rad = np.deg2rad(ROTATION_THRESHOLD_DEG)

    # Check scale (Dolly)
    scale_delta = abs(scale - 1.0)
    if scale_delta > SCALE_THRESHOLD:
        if scale > 1.0:
            labels.append("Dolly In")
        else:
            labels.append("Dolly Out")

    # Check rotation (Roll)
    if abs(rotation) > rotation_threshold_rad:
        if rotation > 0:
            labels.append("Roll Left")
        else:
            labels.append("Roll Right")

    # Check translation (Pan/Tilt)
    abs_tx = abs(tx)
    abs_ty = abs(ty)

    # Prioritize the dominant direction
    if abs_tx > trans_threshold_x and abs_tx >= abs_ty:
        # Horizontal motion dominates - Pan
        # Positive tx = image shifted right = camera panned left
        if tx > 0:
            labels.append("Pan Left")
        else:
            labels.append("Pan Right")

    if abs_ty > trans_threshold_y and abs_ty > abs_tx:
        # Vertical motion dominates - Tilt
        # Positive ty = image shifted down = camera tilted up
        if ty > 0:
            labels.append("Tilt Up")
        else:
            labels.append("Tilt Down")

    # If no significant motion detected
    if not labels:
        labels.append("Stay")

    return labels


def estimate_frame_motion(prev_gray, curr_gray, width, height):
    """
    Estimate motion between two frames using optical flow.

    Returns:
        List of motion labels for this frame pair
    """
    # Detect features in previous frame
    prev_pts = cv2.goodFeaturesToTrack(prev_gray, mask=None, **FEATURE_PARAMS)

    if prev_pts is None or len(prev_pts) < MIN_FEATURES:
        # Not enough features - assume static
        return ["Stay"]

    # Calculate optical flow
    curr_pts, status, err = cv2.calcOpticalFlowPyrLK(
        prev_gray, curr_gray, prev_pts, None, **LK_PARAMS
    )

    if curr_pts is None:
        return ["Stay"]

    # Filter good points
    good_prev = prev_pts[status == 1]
    good_curr = curr_pts[status == 1]

    if len(good_prev) < MIN_FEATURES:
        return ["Stay"]

    # Estimate affine transformation with RANSAC
    matrix, inliers = cv2.estimateAffinePartial2D(
        good_prev, good_curr,
        method=cv2.RANSAC,
        ransacReprojThreshold=3.0,
        confidence=0.99
    )

    # Extract transformation parameters
    tx, ty, rotation, scale = extract_transform_params(matrix)

    # Classify motion
    labels = classify_motion(tx, ty, rotation, scale, width, height)

    return labels


def compress_intervals(frame_labels, sample_ids):
    """
    Compress consecutive frames with same labels into intervals.
    Format: "start->end" where both are sample indices.

    Args:
        frame_labels: List of label lists for each sampled frame transition
        sample_ids: List of sampled frame indices

    Returns:
        Dict with interval keys (e.g., "0->10") and label lists
    """
    instructions = {}

    # We have len(sample_ids) - 1 transitions
    # Each transition i corresponds to motion from sample_ids[i] to sample_ids[i+1]

    i = 0
    while i < len(frame_labels):
        current_labels = frame_labels[i]
        start_idx = i

        # Find consecutive frames with same labels
        while i + 1 < len(frame_labels) and frame_labels[i + 1] == current_labels:
            i += 1

        # Create interval key: start_sample -> end_sample
        interval_key = f"{sample_ids[start_idx]}->{sample_ids[i + 1]}"
        instructions[interval_key] = current_labels

        i += 1

    return instructions


def process_video(video_path, sampling_config_path):
    """
    Process video and estimate egomotion for all sampled frames.
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
    print(f"Sample IDs: {sample_ids}")

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

    # Estimate motion for each consecutive frame pair
    frame_labels = []
    print("\nEstimating camera motion...")

    for i in range(len(frames) - 1):
        labels = estimate_frame_motion(frames[i], frames[i + 1], width, height)
        frame_labels.append(labels)
        print(f"  Frame {sample_ids[i]:3d} -> {sample_ids[i+1]:3d}: {labels}")

    print(f"\nTotal transitions analyzed: {len(frame_labels)}")

    # Compress into intervals
    instructions = compress_intervals(frame_labels, sample_ids)

    print(f"\nCompressed into {len(instructions)} intervals:")
    for interval, labels in instructions.items():
        print(f"  {interval}: {labels}")

    return instructions, frame_labels, sample_ids


def self_check(instructions, frame_labels, sample_ids):
    """
    Perform self-checks on the output.
    """
    print("\n=== Self-check ===")
    checks = []

    # Check 1: No empty labels
    has_empty = any(not labels for labels in frame_labels)
    checks.append(("No empty labels in frame_labels", not has_empty))

    # Check 2: All interval keys formatted correctly
    valid_format = all(
        '->' in key and
        all(part.isdigit() for part in key.split('->'))
        for key in instructions.keys()
    )
    checks.append(("All interval keys formatted as 'start->end'", valid_format))

    # Check 3: Instructions cover all transitions
    total_transitions = len(sample_ids) - 1
    covered_transitions = sum(1 for labels in frame_labels)
    checks.append((
        f"All {total_transitions} transitions covered",
        covered_transitions == total_transitions
    ))

    # Check 4: All intervals have non-empty labels
    all_intervals_labeled = all(
        labels and len(labels) > 0
        for labels in instructions.values()
    )
    checks.append(("All intervals have labels", all_intervals_labeled))

    # Check 5: Valid label names
    valid_labels = {
        "Stay", "Dolly In", "Dolly Out",
        "Pan Left", "Pan Right",
        "Tilt Up", "Tilt Down",
        "Roll Left", "Roll Right"
    }
    all_valid = all(
        all(label in valid_labels for label in labels)
        for labels in instructions.values()
    )
    checks.append(("All labels are valid motion types", all_valid))

    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"[{status}] {check_name}: {passed}")

    return all(check[1] for check in checks)


if __name__ == "__main__":
    video_path = sys.argv[1] if len(sys.argv) > 1 else "/root/input.mp4"
    sampling_config_path = sys.argv[2] if len(sys.argv) > 2 else \
        "/logs/agent/sessions/skills/sampling-and-indexing/sampling_config.json"

    # Process video
    instructions, frame_labels, sample_ids = process_video(video_path, sampling_config_path)

    # Save instructions to JSON
    output_path = "/logs/agent/sessions/skills/egomotion-estimation/egomotion_instructions.json"
    with open(output_path, 'w') as f:
        json.dump(instructions, f, indent=2)

    print(f"\n✓ Egomotion instructions saved to: {output_path}")

    # Self-check
    if self_check(instructions, frame_labels, sample_ids):
        print("\n✓ All self-checks passed!")
        sys.exit(0)
    else:
        print("\n✗ Some self-checks failed!")
        sys.exit(1)

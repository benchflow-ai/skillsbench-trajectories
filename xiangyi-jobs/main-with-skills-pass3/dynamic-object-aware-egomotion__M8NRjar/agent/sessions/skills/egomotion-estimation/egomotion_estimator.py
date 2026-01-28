import cv2
import numpy as np
import json
from pathlib import Path
from scipy.sparse import csr_matrix
import warnings

warnings.filterwarnings('ignore')

def extract_frames(video_path, fps=6):
    """Extract frames from video at specified fps."""
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Calculate sampling interval
    frame_interval = max(1, int(video_fps / fps))

    frames = []
    frame_idx = 0
    sampled_indices = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            frames.append(frame)
            sampled_indices.append(frame_idx)

        frame_idx += 1

    cap.release()

    print(f"Video FPS: {video_fps}, Total frames: {total_frames}")
    print(f"Sampling interval: {frame_interval}, Sampled frames: {len(frames)}")

    return frames, sampled_indices


def estimate_optical_flow(frame1, frame2):
    """Estimate optical flow between two consecutive frames."""
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    # Feature detection
    corners = cv2.goodFeaturesToTrack(
        gray1,
        maxCorners=200,
        qualityLevel=0.01,
        minDistance=10,
        blockSize=15
    )

    if corners is None or len(corners) < 10:
        # Fallback: return identity transform
        return np.eye(2, 3, dtype=np.float32), 0, 0, 1.0

    # Optical flow
    next_pts, status, err = cv2.calcOpticalFlowPyrLK(
        gray1, gray2, corners, None,
        winSize=(21, 21),
        maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)
    )

    # Filter good points
    good_prev = corners[status == 1]
    good_next = next_pts[status == 1]

    if len(good_prev) < 4:
        return np.eye(2, 3, dtype=np.float32), 0, 0, 1.0

    # Estimate affine transform with RANSAC
    try:
        transform, inliers = cv2.estimateAffinePartial2D(
            good_prev, good_next,
            method=cv2.RANSAC,
            ransacReprojThreshold=5.0
        )
    except:
        return np.eye(2, 3, dtype=np.float32), 0, 0, 1.0

    if transform is None:
        return np.eye(2, 3, dtype=np.float32), 0, 0, 1.0

    # Extract transformation parameters
    # [a0, a1, tx]
    # [a2, a3, ty]
    M = transform

    # Extract translation
    tx = M[0, 2]
    ty = M[1, 2]

    # Extract rotation and scale
    a = M[0, 0]
    b = M[0, 1]
    c = M[1, 0]
    d = M[1, 1]

    scale = np.sqrt(a**2 + c**2)
    if scale < 0.1:
        scale = 1.0

    # Rotation angle (in radians)
    rotation = np.arctan2(b, a)

    return M, rotation, (tx, ty), scale


def classify_motion(rotation, translation, scale, th_trans=2.0, th_rot=0.05, th_scale=0.05):
    """Classify camera motion from estimated transform."""
    labels = []

    tx, ty = translation

    # Scale-based classification (Dolly In/Out)
    if abs(scale - 1.0) > th_scale:
        if scale > 1.0:
            labels.append("Dolly In")
        else:
            labels.append("Dolly Out")

    # Rotation-based classification (Roll Left/Right)
    if abs(rotation) > th_rot:
        if rotation > 0:
            labels.append("Roll Right")
        else:
            labels.append("Roll Left")

    # Translation-based classification (Pan/Tilt)
    # Note: positive tx means image shifts right, which means camera pans left
    abs_tx = abs(tx)
    abs_ty = abs(ty)

    if abs_tx > th_trans and abs_tx >= abs_ty:
        if tx > 0:
            labels.append("Pan Left")
        else:
            labels.append("Pan Right")
    elif abs_ty > th_trans and abs_ty > abs_tx:
        if ty > 0:
            labels.append("Tilt Up")
        else:
            labels.append("Tilt Down")

    # Default to Stay if no motion detected
    if not labels:
        labels.append("Stay")

    return labels


def smooth_labels(all_labels, window_size=3):
    """Apply temporal smoothing using mode filter."""
    if window_size < 1:
        return all_labels

    smoothed = []
    half_win = window_size // 2

    for i in range(len(all_labels)):
        start = max(0, i - half_win)
        end = min(len(all_labels), i + half_win + 1)

        # For multi-label case, keep all unique labels in the window
        window_labels = set()
        for j in range(start, end):
            window_labels.update(all_labels[j])

        if window_labels:
            smoothed.append(sorted(list(window_labels)))
        else:
            smoothed.append(["Stay"])

    return smoothed


def compress_intervals(labels):
    """Compress consecutive identical labels into intervals."""
    if not labels:
        return {}

    intervals = {}
    start_idx = 0
    current_labels = labels[0]

    for i in range(1, len(labels)):
        if labels[i] != current_labels:
            # Save interval
            key = f"{start_idx}->{i-1}"
            intervals[key] = current_labels
            start_idx = i
            current_labels = labels[i]

    # Last interval
    key = f"{start_idx}->{len(labels)-1}"
    intervals[key] = current_labels

    return intervals


def estimate_egomotion(video_path, fps=6, output_json="/root/pred_instructions.json"):
    """Main egomotion estimation function."""
    print(f"Estimating egomotion for {video_path} at {fps} fps...")

    frames, sampled_indices = extract_frames(video_path, fps)

    if len(frames) < 2:
        print("Not enough frames to estimate motion.")
        return

    # Estimate motion between consecutive frames
    all_labels = [["Stay"]]  # First frame is always Stay

    for i in range(len(frames) - 1):
        print(f"Processing frame pair {i}/{len(frames)-2}...", end='\r')

        frame1 = frames[i]
        frame2 = frames[i + 1]

        # Estimate optical flow
        M, rotation, translation, scale = estimate_optical_flow(frame1, frame2)

        # Classify motion
        labels = classify_motion(rotation, translation, scale)
        all_labels.append(labels)

    print(f"\nProcessed {len(frames)} frames")

    # Apply temporal smoothing
    smoothed_labels = smooth_labels(all_labels, window_size=3)

    # Compress intervals
    intervals = compress_intervals(smoothed_labels)

    # Convert to the required format: "0->1" format with list values
    formatted_intervals = {}
    for key, labels in intervals.items():
        # Parse key like "0-1" to "0->1"
        parts = key.split('->')
        if len(parts) == 2:
            formatted_key = f"{parts[0]}->{parts[1]}"
            formatted_intervals[formatted_key] = labels

    # Write to JSON
    with open(output_json, 'w') as f:
        json.dump(formatted_intervals, f, indent=2)

    print(f"Egomotion estimation saved to {output_json}")
    print(f"Total intervals: {len(formatted_intervals)}")

    return frames, sampled_indices, smoothed_labels


if __name__ == "__main__":
    import sys

    video_path = sys.argv[1] if len(sys.argv) > 1 else "/root/input.mp4"
    fps = 6

    estimate_egomotion(video_path, fps)

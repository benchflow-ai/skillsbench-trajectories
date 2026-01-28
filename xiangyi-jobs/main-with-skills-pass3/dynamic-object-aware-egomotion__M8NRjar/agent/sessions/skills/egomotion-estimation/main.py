#!/usr/bin/env python3
"""
Main script to analyze video for egomotion and dynamic objects.
"""

import sys
import os
import json
import numpy as np
import cv2
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

    frame_interval = max(1, int(video_fps / fps))

    frames = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            frames.append(frame)

        frame_idx += 1

    cap.release()

    print(f"Video FPS: {video_fps}, Total frames: {total_frames}")
    print(f"Sampling interval: {frame_interval}, Sampled frames: {len(frames)}")

    return frames


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
        return np.eye(2, 3, dtype=np.float32), 0, (0, 0), 1.0

    # Optical flow
    next_pts, status, err = cv2.calcOpticalFlowPyrLK(
        gray1, gray2, corners, None,
        winSize=(21, 21),
        maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)
    )

    good_prev = corners[status == 1]
    good_next = next_pts[status == 1]

    if len(good_prev) < 4:
        return np.eye(2, 3, dtype=np.float32), 0, (0, 0), 1.0

    try:
        transform, inliers = cv2.estimateAffinePartial2D(
            good_prev, good_next,
            method=cv2.RANSAC,
            ransacReprojThreshold=5.0
        )
    except:
        return np.eye(2, 3, dtype=np.float32), 0, (0, 0), 1.0

    if transform is None:
        return np.eye(2, 3, dtype=np.float32), 0, (0, 0), 1.0

    M = transform

    tx = M[0, 2]
    ty = M[1, 2]

    a = M[0, 0]
    b = M[0, 1]
    c = M[1, 0]
    d = M[1, 1]

    scale = np.sqrt(a**2 + c**2)
    if scale < 0.1:
        scale = 1.0

    rotation = np.arctan2(b, a)

    return M, rotation, (tx, ty), scale


def classify_motion(rotation, translation, scale, th_trans=2.0, th_rot=0.05, th_scale=0.05):
    """Classify camera motion from estimated transform."""
    labels = []

    tx, ty = translation

    # Scale-based classification
    if abs(scale - 1.0) > th_scale:
        if scale > 1.0:
            labels.append("Dolly In")
        else:
            labels.append("Dolly Out")

    # Rotation-based classification
    if abs(rotation) > th_rot:
        if rotation > 0:
            labels.append("Roll Right")
        else:
            labels.append("Roll Left")

    # Translation-based classification
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
            key = f"{start_idx}->{i-1}"
            intervals[key] = current_labels
            start_idx = i
            current_labels = labels[i]

    key = f"{start_idx}->{len(labels)-1}"
    intervals[key] = current_labels

    return intervals


def estimate_egomotion(frames, output_json="/root/pred_instructions.json"):
    """Estimate egomotion for all frames."""
    print("\n=== Estimating Egomotion ===")

    if len(frames) < 2:
        print("Not enough frames")
        return []

    all_labels = [["Stay"]]

    for i in range(len(frames) - 1):
        print(f"Processing frame pair {i+1}/{len(frames)-1}...", end='\r')

        frame1 = frames[i]
        frame2 = frames[i + 1]

        M, rotation, translation, scale = estimate_optical_flow(frame1, frame2)
        labels = classify_motion(rotation, translation, scale)
        all_labels.append(labels)

    print(f"\nProcessed {len(frames)} frames")

    smoothed_labels = smooth_labels(all_labels, window_size=3)
    intervals = compress_intervals(smoothed_labels)

    with open(output_json, 'w') as f:
        json.dump(intervals, f, indent=2)

    print(f"Egomotion saved to {output_json}")

    return smoothed_labels


def detect_dynamic_objects(frames, output_npz="/root/pred_dyn_masks.npz"):
    """Detect dynamic objects using motion segmentation."""
    print("\n=== Detecting Dynamic Objects ===")

    h, w = frames[0].shape[:2]
    print(f"Frame resolution: {h}x{w}")

    csr_data = {}
    csr_data['shape'] = np.array([h, w], dtype=np.int32)

    for frame_idx in range(len(frames)):
        print(f"Processing frame {frame_idx+1}/{len(frames)}...", end='\r')

        if frame_idx == 0:
            mask = np.zeros((h, w), dtype=np.bool_)
        else:
            frame1 = frames[frame_idx - 1]
            frame2 = frames[frame_idx]

            # Estimate background motion
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

            corners = cv2.goodFeaturesToTrack(
                gray1,
                maxCorners=200,
                qualityLevel=0.01,
                minDistance=10,
                blockSize=15
            )

            if corners is None or len(corners) < 4:
                bg_transform = np.eye(2, 3, dtype=np.float32)
            else:
                next_pts, status, err = cv2.calcOpticalFlowPyrLK(
                    gray1, gray2, corners, None,
                    winSize=(21, 21),
                    maxLevel=3,
                    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)
                )

                good_prev = corners[status == 1]
                good_next = next_pts[status == 1]

                if len(good_prev) >= 4:
                    try:
                        transform, inliers = cv2.estimateAffinePartial2D(
                            good_prev, good_next,
                            method=cv2.RANSAC,
                            ransacReprojThreshold=5.0
                        )
                        bg_transform = transform if transform is not None else np.eye(2, 3, dtype=np.float32)
                    except:
                        bg_transform = np.eye(2, 3, dtype=np.float32)
                else:
                    bg_transform = np.eye(2, 3, dtype=np.float32)

            # Warp frame1 to frame2
            warped = cv2.warpAffine(frame1, bg_transform, (w, h))

            # Compute difference
            gray_warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
            gray_frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

            diff = cv2.absdiff(gray_warped, gray_frame2)

            _, mask = cv2.threshold(diff, 15, 255, cv2.THRESH_BINARY)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

            mask = (mask > 0).astype(np.bool_)

        # Convert to CSR sparse format
        csr_sparse = csr_matrix(mask)

        csr_data[f'f_{frame_idx}_data'] = csr_sparse.data
        csr_data[f'f_{frame_idx}_indices'] = csr_sparse.indices
        csr_data[f'f_{frame_idx}_indptr'] = csr_sparse.indptr

    print(f"\nSaved masks for {len(frames)} frames")

    np.savez_compressed(output_npz, **csr_data)
    print(f"Dynamic masks saved to {output_npz}")


def main():
    """Main analysis pipeline."""
    video_path = "/root/input.mp4"
    fps = 6

    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return

    print(f"Analyzing video: {video_path}")
    print(f"Sampling rate: {fps} fps")

    # Extract frames
    frames = extract_frames(video_path, fps)

    if len(frames) == 0:
        print("No frames extracted")
        return

    # Estimate egomotion
    estimate_egomotion(frames, "/root/pred_instructions.json")

    # Detect dynamic objects
    detect_dynamic_objects(frames, "/root/pred_dyn_masks.npz")

    print("\n=== Analysis Complete ===")
    print("Output files:")
    print("  - /root/pred_instructions.json")
    print("  - /root/pred_dyn_masks.npz")


if __name__ == "__main__":
    main()

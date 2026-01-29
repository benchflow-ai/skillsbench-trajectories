#!/usr/bin/env python3
"""
Sampling and Indexing for video processing
Samples video at target FPS and generates sample_ids for downstream tasks
"""
import cv2
import json
import sys

def sample_video_frames(video_path, target_fps=6):
    """
    Sample video frames at target FPS and return sample indices

    Args:
        video_path: Path to input video
        target_fps: Target sampling rate (frames per second)

    Returns:
        dict with:
            - sample_ids: List of frame indices to sample
            - video_fps: Original video FPS
            - total_frames: Total frame count
            - width, height: Video resolution
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    # Get video properties
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    cap.release()

    # Calculate sampling step
    # To sample at target_fps from video_fps, we take every (video_fps / target_fps) frames
    step = max(1, int(round(video_fps / target_fps)))

    # Generate sample indices
    sample_ids = list(range(0, total_frames, step))

    # Ensure we include the last frame if not already included
    if sample_ids[-1] != total_frames - 1:
        sample_ids.append(total_frames - 1)

    return {
        'sample_ids': sample_ids,
        'video_fps': video_fps,
        'total_frames': total_frames,
        'width': width,
        'height': height,
        'target_fps': target_fps,
        'sampling_step': step
    }

if __name__ == "__main__":
    video_path = sys.argv[1] if len(sys.argv) > 1 else "/root/input.mp4"
    target_fps = int(sys.argv[2]) if len(sys.argv) > 2 else 6

    result = sample_video_frames(video_path, target_fps)

    # Print summary
    print(f"Video: {video_path}")
    print(f"Resolution: {result['width']}x{result['height']}")
    print(f"Original FPS: {result['video_fps']}")
    print(f"Total frames: {result['total_frames']}")
    print(f"Target FPS: {result['target_fps']}")
    print(f"Sampling step: {result['sampling_step']}")
    print(f"Number of sampled frames: {len(result['sample_ids'])}")
    print(f"Sample IDs: {result['sample_ids']}")
    print(f"Sample range: {result['sample_ids'][0]} -> {result['sample_ids'][-1]}")

    # Save to JSON for downstream tasks
    output_path = "/logs/agent/sessions/skills/sampling-and-indexing/sampling_config.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nSampling configuration saved to: {output_path}")

    # Self-check
    print("\n=== Self-check ===")
    checks = []

    # Check 1: sample_ids strictly increasing
    is_increasing = all(result['sample_ids'][i] < result['sample_ids'][i+1]
                       for i in range(len(result['sample_ids'])-1))
    checks.append(("sample_ids strictly increasing", is_increasing))

    # Check 2: all sample_ids < total_frames
    all_valid = all(sid < result['total_frames'] for sid in result['sample_ids'])
    checks.append(("all sample_ids < total_frames", all_valid))

    # Check 3: max index is last sample
    max_idx_correct = result['sample_ids'][-1] == max(result['sample_ids'])
    checks.append(("max index is last sample", max_idx_correct))

    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"[{status}] {check_name}: {passed}")

    if all(check[1] for check in checks):
        print("\n✓ All self-checks passed!")
        sys.exit(0)
    else:
        print("\n✗ Some self-checks failed!")
        sys.exit(1)

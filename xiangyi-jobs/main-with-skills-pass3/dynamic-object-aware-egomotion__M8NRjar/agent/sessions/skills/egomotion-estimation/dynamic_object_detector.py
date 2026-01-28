import cv2
import numpy as np
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

    print(f"Extracted {len(frames)} frames at {fps} fps")
    return frames


def estimate_optical_flow_dense(frame1, frame2):
    """Estimate dense optical flow between two frames."""
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    flow = cv2.calcOpticalFlowFarneback(
        gray1, gray2,
        None,
        pyr_scale=0.5,
        levels=3,
        winsize=15,
        iterations=3,
        n8=True,
        poly_n=5,
        poly_sigma=1.2,
        flags=0
    )

    return flow


def estimate_background_motion(frame1, frame2):
    """Estimate global motion (camera motion) using feature matching."""
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

    if corners is None or len(corners) < 4:
        return np.eye(2, 3, dtype=np.float32)

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
        return np.eye(2, 3, dtype=np.float32)

    # Estimate affine transform
    try:
        transform, inliers = cv2.estimateAffinePartial2D(
            good_prev, good_next,
            method=cv2.RANSAC,
            ransacReprojThreshold=5.0
        )

        if transform is not None:
            return transform
    except:
        pass

    return np.eye(2, 3, dtype=np.float32)


def detect_dynamic_objects(frames, output_npz="/root/pred_dyn_masks.npz"):
    """Detect dynamic objects using motion segmentation."""
    if len(frames) < 2:
        print("Not enough frames")
        return

    h, w = frames[0].shape[:2]
    print(f"Frame resolution: {h}x{w}")

    csr_data = {}
    csr_data['shape'] = np.array([h, w], dtype=np.int32)

    for frame_idx in range(len(frames)):
        print(f"Processing frame {frame_idx}/{len(frames)-1}...", end='\r')

        if frame_idx == 0:
            # First frame: all background (no motion yet)
            mask = np.zeros((h, w), dtype=np.bool_)
        else:
            frame1 = frames[frame_idx - 1]
            frame2 = frames[frame_idx]

            # Estimate background motion
            bg_transform = estimate_background_motion(frame1, frame2)

            # Warp frame1 to frame2 using background motion
            warped = cv2.warpAffine(frame1, bg_transform, (w, h))

            # Compute difference between warped and frame2
            gray_warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
            gray_frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

            diff = cv2.absdiff(gray_warped, gray_frame2)

            # Threshold to get motion regions
            _, mask = cv2.threshold(diff, 15, 255, cv2.THRESH_BINARY)

            # Morphological operations to clean up
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

            mask = (mask > 0).astype(np.bool_)

        # Convert dense mask to CSR sparse format
        csr_sparse = csr_matrix(mask)

        csr_data[f'f_{frame_idx}_data'] = csr_sparse.data
        csr_data[f'f_{frame_idx}_indices'] = csr_sparse.indices
        csr_data[f'f_{frame_idx}_indptr'] = csr_sparse.indptr

    print(f"\nSaved dynamic masks for {len(frames)} frames")

    # Save to NPZ
    np.savez_compressed(output_npz, **csr_data)
    print(f"Dynamic masks saved to {output_npz}")


if __name__ == "__main__":
    import sys

    video_path = sys.argv[1] if len(sys.argv) > 1 else "/root/input.mp4"
    fps = 6

    frames = extract_frames(video_path, fps)
    detect_dynamic_objects(frames)

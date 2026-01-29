#!/usr/bin/env python3
"""
Output Validation - Validate instructions and mask outputs
Checks format, range, and consistency of predictions without using ground truth.
"""
import cv2
import numpy as np
import json
import sys
from pathlib import Path

# Valid motion labels
VALID_LABELS = {
    "Stay", "Dolly In", "Dolly Out",
    "Pan Left", "Pan Right",
    "Tilt Up", "Tilt Down",
    "Roll Left", "Roll Right"
}


def validate_instructions_format(instructions):
    """
    Validate JSON instructions format.

    Checks:
    - All keys are "start->end" format with integers
    - start <= end
    - All values are non-empty lists of valid label strings
    """
    checks = []

    # Check key format
    valid_keys = True
    key_ranges = []

    for key, value in instructions.items():
        # Check key format: "start->end"
        if '->' not in key:
            valid_keys = False
            print(f"  ERROR: Invalid key format '{key}' - missing '->'")
            continue

        parts = key.split('->')
        if len(parts) != 2:
            valid_keys = False
            print(f"  ERROR: Invalid key format '{key}' - too many parts")
            continue

        start_str, end_str = parts

        if not start_str.isdigit() or not end_str.isdigit():
            valid_keys = False
            print(f"  ERROR: Invalid key format '{key}' - non-integer values")
            continue

        start = int(start_str)
        end = int(end_str)

        if start > end:
            valid_keys = False
            print(f"  ERROR: Invalid range '{key}' - start > end")
            continue

        key_ranges.append((start, end))

    checks.append(("All keys formatted as 'start->end' with integers", valid_keys))

    # Check values are non-empty lists
    valid_values = True
    all_labels_valid = True

    for key, value in instructions.items():
        if not isinstance(value, list):
            valid_values = False
            print(f"  ERROR: Value for '{key}' is not a list")
            continue

        if len(value) == 0:
            valid_values = False
            print(f"  ERROR: Value for '{key}' is empty")
            continue

        # Check all labels are strings and valid
        for label in value:
            if not isinstance(label, str):
                valid_values = False
                print(f"  ERROR: Label '{label}' in '{key}' is not a string")

            if label not in VALID_LABELS:
                all_labels_valid = False
                print(f"  ERROR: Invalid label '{label}' in '{key}'")

    checks.append(("All values are non-empty lists", valid_values))
    checks.append(("All labels are valid motion types", all_labels_valid))

    return checks, key_ranges


def validate_instructions_coverage(instructions, sample_ids, total_frames):
    """
    Validate that instructions cover the expected frame range.
    """
    checks = []

    # Extract all frame indices mentioned in instructions
    all_starts = []
    all_ends = []

    for key in instructions.keys():
        parts = key.split('->')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            all_starts.append(int(parts[0]))
            all_ends.append(int(parts[1]))

    if not all_starts or not all_ends:
        checks.append(("Coverage analysis", False))
        return checks

    min_frame = min(all_starts)
    max_frame = max(all_ends)

    # Check min frame is first sample
    min_correct = (min_frame == sample_ids[0])
    checks.append((f"Min frame {min_frame} == first sample {sample_ids[0]}", min_correct))

    # Check max frame is last sample
    max_correct = (max_frame == sample_ids[-1])
    checks.append((f"Max frame {max_frame} == last sample {sample_ids[-1]}", max_correct))

    # Check max frame is within video range
    within_range = (max_frame < total_frames)
    checks.append((f"Max frame {max_frame} < total frames {total_frames}", within_range))

    return checks


def validate_masks_structure(npz_data, sample_ids, height, width):
    """
    Validate NPZ mask structure and CSR integrity.
    """
    checks = []

    # Check shape is stored correctly
    if 'shape' not in npz_data:
        checks.append(("'shape' key exists", False))
        return checks

    shape = npz_data['shape']
    shape_correct = (
        len(shape) == 2 and
        shape[0] == height and
        shape[1] == width
    )
    checks.append((f"Shape is [{height}, {width}]", shape_correct))

    # Check all sampled frames have masks
    all_frames_present = True
    missing_frames = []

    for frame_id in sample_ids:
        data_key = f"f_{frame_id}_data"
        indices_key = f"f_{frame_id}_indices"
        indptr_key = f"f_{frame_id}_indptr"

        if data_key not in npz_data or indices_key not in npz_data or indptr_key not in npz_data:
            all_frames_present = False
            missing_frames.append(frame_id)

    if missing_frames:
        print(f"  ERROR: Missing masks for frames: {missing_frames}")

    checks.append((f"All {len(sample_ids)} sampled frames have masks", all_frames_present))

    # Check no extra frames
    frame_ids_in_npz = set()
    for key in npz_data.keys():
        if key.startswith('f_') and key.endswith('_data'):
            frame_str = key[2:-5]  # Remove 'f_' and '_data'
            if frame_str.isdigit():
                frame_ids_in_npz.add(int(frame_str))

    no_extra_frames = (frame_ids_in_npz == set(sample_ids))
    if not no_extra_frames:
        extra = frame_ids_in_npz - set(sample_ids)
        missing = set(sample_ids) - frame_ids_in_npz
        if extra:
            print(f"  ERROR: Extra frames in NPZ: {sorted(extra)}")
        if missing:
            print(f"  ERROR: Missing frames in NPZ: {sorted(missing)}")

    checks.append(("No extra or missing frames in NPZ", no_extra_frames))

    # Validate CSR structure for each frame
    csr_valid = True

    for frame_id in sample_ids:
        data = npz_data.get(f"f_{frame_id}_data")
        indices = npz_data.get(f"f_{frame_id}_indices")
        indptr = npz_data.get(f"f_{frame_id}_indptr")

        if data is None or indices is None or indptr is None:
            continue

        # Check indptr length
        if len(indptr) != height + 1:
            csr_valid = False
            print(f"  ERROR: Frame {frame_id} - indptr length {len(indptr)} != {height + 1}")

        # Check indptr[-1] == len(indices)
        if indptr[-1] != len(indices):
            csr_valid = False
            print(f"  ERROR: Frame {frame_id} - indptr[-1]={indptr[-1]} != len(indices)={len(indices)}")

        # Check data and indices same length
        if len(data) != len(indices):
            csr_valid = False
            print(f"  ERROR: Frame {frame_id} - len(data)={len(data)} != len(indices)={len(indices)}")

        # Check indices within range
        if len(indices) > 0:
            if np.any(indices < 0) or np.any(indices >= width):
                csr_valid = False
                print(f"  ERROR: Frame {frame_id} - indices out of range [0, {width})")

        # Check indptr is non-decreasing
        if not np.all(indptr[1:] >= indptr[:-1]):
            csr_valid = False
            print(f"  ERROR: Frame {frame_id} - indptr is not non-decreasing")

        # Check data contains only 1s
        if len(data) > 0 and not np.all(data == 1):
            csr_valid = False
            print(f"  ERROR: Frame {frame_id} - data contains values other than 1")

    checks.append(("All masks have valid CSR structure", csr_valid))

    return checks


def validate_outputs(video_path, instructions_path, masks_path, sampling_config_path):
    """
    Main validation function.
    """
    print("=" * 70)
    print("OUTPUT VALIDATION")
    print("=" * 70)

    # Load sampling configuration
    print("\n[1/5] Loading sampling configuration...")
    with open(sampling_config_path, 'r') as f:
        config = json.load(f)

    sample_ids = config['sample_ids']
    width = config['width']
    height = config['height']
    total_frames = config['total_frames']

    print(f"  Video: {video_path}")
    print(f"  Resolution: {width}x{height}")
    print(f"  Total frames: {total_frames}")
    print(f"  Sampled frames: {len(sample_ids)}")
    print(f"  Sample range: {sample_ids[0]} -> {sample_ids[-1]}")

    # Load instructions
    print("\n[2/5] Validating instructions format...")
    with open(instructions_path, 'r') as f:
        instructions = json.load(f)

    print(f"  Instructions file: {instructions_path}")
    print(f"  Number of intervals: {len(instructions)}")

    format_checks, key_ranges = validate_instructions_format(instructions)

    # Validate coverage
    print("\n[3/5] Validating instructions coverage...")
    coverage_checks = validate_instructions_coverage(instructions, sample_ids, total_frames)

    # Load and validate masks
    print("\n[4/5] Validating masks structure...")
    npz_data = np.load(masks_path)

    print(f"  Masks file: {masks_path}")
    print(f"  NPZ keys: {len(npz_data.keys())}")

    structure_checks = validate_masks_structure(npz_data, sample_ids, height, width)

    # Compile all checks
    print("\n[5/5] Final validation report...")
    print("=" * 70)

    all_checks = []
    all_checks.extend(format_checks)
    all_checks.extend(coverage_checks)
    all_checks.extend(structure_checks)

    print("\n=== VALIDATION RESULTS ===")
    for check_name, passed in all_checks:
        status = "✓" if passed else "✗"
        print(f"[{status}] {check_name}: {passed}")

    all_passed = all(check[1] for check in all_checks)

    print("=" * 70)
    if all_passed:
        print("✓ ALL VALIDATIONS PASSED")
        print("=" * 70)
        return 0
    else:
        print("✗ SOME VALIDATIONS FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Validate output files')
    parser.add_argument('--instructions', required=True, help='Path to instructions JSON file')
    parser.add_argument('--masks', required=True, help='Path to masks NPZ file')
    parser.add_argument('--sampling-config', required=True, help='Path to sampling config JSON')
    parser.add_argument('--video', default='/root/input.mp4', help='Path to input video')

    args = parser.parse_args()

    exit_code = validate_outputs(
        args.video,
        args.instructions,
        args.masks,
        args.sampling_config
    )

    sys.exit(exit_code)

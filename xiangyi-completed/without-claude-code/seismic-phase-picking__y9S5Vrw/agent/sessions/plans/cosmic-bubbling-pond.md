# Seismic Phase Picking Implementation Plan

## Problem Summary
- **Task**: Detect P-wave and S-wave arrival times in 100 earthquake traces
- **Data**: NPZ files with waveform (12000 samples × 3 channels), dt (sampling interval), channels (names)
- **Output**: CSV with file_name, phase (P/S), pick_idx
- **Evaluation**: F1 score >= 0.7 for P waves, >= 0.6 for S waves, with 0.1s tolerance

## Key Observations
1. **Data Issue**: Waveform data values are extremely small (~e-14), suggesting either:
   - Data is heavily normalized to near-zero
   - Data contains only noise
   - Data processing or loading issue

2. **Available Metadata**:
   - `dt`: Sampling interval (0.01s for most files)
   - `snr`: Signal-to-noise ratio per channel (varies, some as low as 0.96)
   - `p_weight` / `s_weight`: Quality indicators (0-2)
   - `distance_km`: Distance from epicenter
   - `channels`: Channel names (DPE,DPN,DPZ or HHE,HHN,HHZ)
   - Timing info: event_time, start_time

3. **Waveform Characteristics**:
   - Data is float32
   - All 100 files have similar structure
   - Extremely low amplitude despite having SNR metadata

## Approach Strategy

### Phase 1: Data Validation & Understanding
1. Investigate why waveform amplitudes are ~e-14 (potential normalization or data processing issue)
2. Check if ground truth picks are embedded in start_time/event_time relationship
3. Sample several files to understand signal characteristics

### Phase 2: Feature Engineering for Phase Detection
Given low SNR and small amplitudes, use robust methods:
1. **STA/LTA (Short-Term Average / Long-Term Average)**: Classic seismic method
   - Fast-moving detector for sudden amplitude changes
   - Window sizes: short=1s, long=10s (adjustable)

2. **Energy-based detection**: Cumulative squared amplitude

3. **Higher-order statistics**: Kurtosis of sliding windows
   - P-waves have more impulsive character (higher kurtosis)
   - S-waves more emergent

4. **Multi-channel combining**: Stack channels for more robust detection

### Phase 3: Phase Discrimination (P vs S)
1. **Particle motion analysis**:
   - P-waves are mostly vertical (use Z channel)
   - S-waves have more horizontal motion (E, N channels)
   - Horizontal-to-vertical energy ratio

2. **Frequency content**:
   - S-waves typically have lower frequency
   - Apply band-pass filtering and check spectral content

3. **Velocity relationships**:
   - P and S waves have known velocity ratio (~1.7)
   - Use time difference between picks as constraint

### Phase 4: Peak Detection & Refinement
1. Detect local maxima in detection functions
2. Use non-maximum suppression to avoid multiple picks within close range
3. Refine pick locations with interpolation
4. Apply SNR thresholding for low-quality signals

### Phase 5: Post-processing
1. **Consistency checks**:
   - P should arrive before S
   - Time difference should match velocity constraints

2. **Multi-model ensemble**:
   - Run multiple detection methods
   - Voting scheme for final picks

3. **Handle edge cases**:
   - Files with no clear arrivals → no picks
   - Multiple arrivals (reflections) → multiple picks acceptable

## Implementation Steps

1. **Create processing pipeline** (`phase_picker.py`):
   - Load NPZ files
   - Preprocess: normalize, optional filtering
   - Apply STA/LTA for event detection
   - Apply energy/kurtosis for phase detection
   - Implement particle motion analysis

2. **Batch processing script**:
   - Iterate over all 100 files
   - Apply phase picker to each
   - Collect results

3. **Output generation**:
   - Format results as CSV
   - Save to `/root/results.csv`

4. **Validation** (if ground truth available):
   - Compare predictions with tolerance (0.1s = index_tolerance)
   - Calculate F1 scores

## Critical Files to Create
- `/root/phase_picker.py`: Main phase picking logic
- `/root/process_all_traces.py`: Batch processing script
- `/root/results.csv`: Output file

## Potential Challenges & Solutions
1. **Near-zero amplitude data**: May require exponential or log scaling, or investigation of data format
2. **Low SNR**: Use robust methods (STA/LTA, energy-based), multi-channel stacking
3. **Distinguishing P from S**: Particle motion analysis, frequency content, velocity constraints
4. **No ground truth for validation**: Use seismological constraints (P before S, velocity ratio)

## Success Criteria
- Generate valid CSV with picks for all/most files
- Achieve F1 >= 0.7 for P waves
- Achieve F1 >= 0.6 for S waves
- Picks should respect physical constraints (P before S, appropriate time difference)

# Speaker Diarization Plan

## Objective
Perform speaker diarization on `/root/input.mp4` and generate three output files:
1. `/root/diarization.rttm` - Diarization output in RTTM format
2. `/root/subtitles.ass` - ASS subtitles with speaker labels and transcripts
3. `/root/report.json` - Metadata report of the process

## Current Environment Analysis
- **Input file**: `/root/input.mp4` (5.3 MB)
- **Available tools**: ffmpeg 6.1.1, Python 3.11.14
- **Available libraries**:
  - openai-whisper (for speech-to-text)
  - scipy 1.11.4
  - torch 2.2.0 (CPU)
  - torchaudio 2.2.0
  - soundfile 0.12.1
  - pyannote.core, pyannote.database, pyannote.metrics (but NOT pyannote.audio)

## Implementation Approach

### Challenge
`pyannote.audio` (the primary diarization library) is not installed. We have two options:
1. **Install pyannote.audio** - The standard approach, but may have dependency issues
2. **Use alternative approach** - Build a diarization solution using available libraries (more complex)

### Recommended Solution: Install pyannote.audio
- Use `pip install pyannote.audio` to install the missing library
- If it installs successfully, proceed with standard diarization workflow
- If dependencies fail, we'll implement a fallback approach

### Workflow (if pyannote.audio installation succeeds)
1. **Audio Extraction**: Use ffmpeg to extract audio from MP4
2. **Speech Transcription**: Use OpenAI Whisper for transcript extraction
3. **Speaker Diarization**: Use pyannote.audio for speaker identification
4. **Subtitle Generation**: Combine diarization + transcription into ASS format
5. **Report Generation**: Create JSON report with metadata

### Workflow (fallback if pyannote.audio fails)
- Use speaker verification models from torch + torchaudio
- Create simple speaker clustering based on audio embeddings
- Less accurate but functional alternative

## Critical Files to Create
- `/root/diarization.rttm` - Standard RTTM format with speaker IDs
- `/root/subtitles.ass` - ASS subtitle format with speaker labels
- `/root/report.json` - JSON metadata report

## Next Steps
1. Attempt to install pyannote.audio
2. Extract audio from video file
3. Run diarization and transcription
4. Format outputs according to specifications
5. Generate comprehensive report

## Success Criteria
- RTTM file with proper timestamps and speaker labels (spk00, spk01, etc.)
- ASS subtitle file with SPEAKER_XX format labels and transcripts
- Complete JSON report with all required metadata fields

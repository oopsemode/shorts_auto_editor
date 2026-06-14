# shorts_auto_editor

`shorts_auto_editor` is a small Python tool for turning long screen recordings into short-form rough cuts. It provides both a Tkinter GUI and CLI workflows for reviewing candidate ranges, running dry-run checks, and creating 9:16 MP4 outputs with optional subtitle burn-in and audio gain.

This repository is intended to contain source code, documentation, and dummy examples only. Do not commit personal videos, real subtitles, generated MP4 files, or local output folders.

## Features

- GUI workflow for selecting candidate ranges and running checks.
- CLI dry-run mode for validating planned edits without creating MP4 files.
- MP4 generation from manually selected ranges or reviewed candidate JSON.
- 9:16 screen-focused layout preset for screen recordings.
- Optional subtitle burn-in from SRT files.
- Optional audio gain multiplier for generated MP4 outputs.
- Markdown reports for dry-runs and generated outputs.

## Requirements

- Python 3.10 or newer.
- FFmpeg and FFprobe on `PATH` for MP4 generation.
- Tkinter for the GUI. On most Windows Python installs this is included.

No third-party Python package is required for the basic GUI and CLI entry points.

## Install

Clone the repository and enter the project folder:

```bat
git clone https://github.com/oopsemode/shorts_auto_editor.git
cd shorts_auto_editor
```

Check Python:

```bat
python --version
```

Check FFmpeg before using MP4 generation:

```bat
ffmpeg -version
ffprobe -version
```

## Prepare Local Inputs

Create local-only working folders as needed:

```bat
mkdir input
mkdir candidates
mkdir subtitles
mkdir output
```

Put your source video in `input/`, candidate JSON in `candidates/`, and local subtitles in `subtitles/`.

These folders are ignored by Git. Keep real media and generated outputs out of commits.

## Run The GUI

Recommended:

```bat
run_shorts_auto_editor_gui.bat
```

Alternative:

```bat
python shorts_auto_editor_gui.py
```

The GUI lets you choose a candidate range, run a dry-run check, and then create the final short after confirmation.

## CLI Dry-Run Example

Dry-run checks the plan and writes reports without creating MP4 output:

```bat
python shorts_auto_editor.py --mode batch_screen_focus_roughcut --input input --candidate-source examples\sample_selected_candidates.json --output-root output --top-n 1 --duration 35 --aspect 9:16 --layout-preset screen_focus --dry-run
```

## MP4 Generation Example

This command creates an MP4, so run it only after checking your candidate ranges:

```bat
python shorts_auto_editor.py --mode batch_screen_focus_roughcut --input input --candidate-source candidates\selected_candidates.json --output-root output --top-n 1 --duration 35 --aspect 9:16 --layout-preset screen_focus
```

Generated files are written under `output/run_<timestamp>/`.

## Manual Ranges Example

Use a ranges file when you want a direct manual cut:

```bat
python shorts_auto_editor.py --mode single_video_manual_cut --input input --ranges examples\sample_ranges.txt --output-root output --aspect 9:16 --duration 35 --layout-preset screen_focus
```

## Subtitle And Audio Gain Example

Use `--burn-subtitles` and `--subtitle-file` to burn subtitles into generated MP4 files. Use `--audio-gain` to apply a volume multiplier:

```bat
python shorts_auto_editor.py --mode batch_screen_focus_roughcut --input input --candidate-source candidates\selected_candidates.json --output-root output --top-n 1 --duration 35 --aspect 9:16 --layout-preset screen_focus --burn-subtitles --subtitle-file subtitles\your_subtitle.srt --audio-gain 1.5
```

For public examples, see:

- `examples/sample_selected_candidates.json`
- `examples/sample_ranges.txt`
- `examples/sample_subtitle.srt`

## Do Not Commit Private Files

Never commit:

- Personal source videos or audio.
- Real subtitle files.
- Generated MP4 files.
- Files under `input/`, `output/`, `output_*`, or `archive_*`.
- Local candidate JSON under `candidates/`.
- Local subtitles under `subtitles/`, except `subtitles/.gitkeep`.

Before committing, inspect staged files carefully:

```bat
git status --short
git diff --cached --stat
```

## License

MIT License. See `LICENSE`.

# v1.3.1 Public Baseline

This is the first public baseline release draft for `shorts_auto_editor`.

## Highlights

- Public repository baseline prepared for open-source review.
- Windows-focused Tkinter GUI for the normal editing workflow.
- CLI dry-run mode for checking planned edits before generating media.
- 9:16 rough cut workflow for turning long recordings into short-form clips.
- Optional subtitle burn-in for generated outputs.
- Optional audio gain control for generated outputs.
- Private media files, local subtitles, generated outputs, and local working folders are intentionally excluded from the repository.

## Status

This project is experimental and currently Windows-focused. It is intended for local creator workflows where users keep their own media files outside Git.

## Notes For Reviewers

- The repository includes dummy example files only.
- Real media and generated output are ignored by Git.
- Use dry-run mode first when testing a new workflow.
- MP4 generation requires FFmpeg and FFprobe installed locally.

## Suggested Smoke Check

```bat
python -m py_compile shorts_auto_editor.py shorts_auto_editor_gui.py
```

For workflow checks, prefer a dry-run before creating any generated media.

# Roadmap

This roadmap outlines the near-term direction for `shorts_auto_editor` as an experimental creator tool.

## v1.3.x: Public Baseline

- Public repository baseline with private media excluded.
- Windows-focused Tkinter GUI for the main workflow.
- CLI dry-run support for validating planned edits before rendering.
- 9:16 rough cut workflow for screen recordings.
- Optional subtitle burn-in and audio gain controls.
- Public examples using dummy candidate, range, and subtitle files.

## v1.4: Safer Sample Workflow

- Safer first-run sample workflow that uses only public dummy files.
- Clearer validation messages when input folders, candidate JSON, or subtitle files are missing.
- Better troubleshooting notes for FFmpeg and FFprobe setup.
- Improved README screenshots or lightweight visual walkthroughs.

## v1.5: Test Coverage

- Automated tests for timecode parsing.
- Automated tests for manual range validation.
- Automated tests for candidate JSON validation.
- Regression tests for report-only dry-run behavior.

## Future

- Cross-platform setup notes for macOS and Linux.
- Better subtitle matching and validation.
- Creator-friendly presets for common short-form styles.
- More explicit project structure and contribution guidance.

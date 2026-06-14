# shorts_auto_editor Usage Guide v0.1.1

## Purpose

`shorts_auto_editor` is a small rough-cut helper for creating short-form videos from local recordings. The BAT files are convenience wrappers around the Python CLI.

## Supported Modes

- `dry_run`: analyzes input media and writes an edit report without creating MP4 output.
- `multi_clip_join`: joins MP4 files from an input folder in filename order.
- `single_video_manual_cut`: extracts ranges listed in a manual ranges file.
- Output aspects: `9:16`, `16:9`.
- Output durations: `35`, `50`, `60` seconds.

## Folders

```text
shorts_auto_editor.py       CLI script
input\                      Local source videos, ignored by Git
examples\                   Public dummy examples
candidates\                 Local candidate JSON, ignored except .gitkeep
subtitles\                  Local subtitle files, ignored except .gitkeep
output\                     Generated reports and MP4 files, ignored by Git
```

## Commands

### dry_run

```bat
python shorts_auto_editor.py --mode dry_run --input input --output-root output --aspect 9:16 --duration 50
```

### multi_clip_join 35s 9:16

```bat
python shorts_auto_editor.py --mode multi_clip_join --input input --output-root output --aspect 9:16 --duration 35
```

### multi_clip_join 35s 16:9

```bat
python shorts_auto_editor.py --mode multi_clip_join --input input --output-root output --aspect 16:9 --duration 35
```

### manual cut 35s 9:16

```bat
python shorts_auto_editor.py --mode single_video_manual_cut --input input --ranges examples\sample_ranges.txt --output-root output --aspect 9:16 --duration 35
```

### manual cut 35s 16:9

```bat
python shorts_auto_editor.py --mode single_video_manual_cut --input input --ranges examples\sample_ranges.txt --output-root output --aspect 16:9 --duration 35
```

## Ranges Format

`examples\sample_ranges.txt`:

```text
00:00:05.000-00:00:20.000
00:00:22.000-00:00:42.000
```

Rules:

- Use one range per line.
- Empty lines are ignored.
- Lines starting with `#` are ignored.
- Start time must be earlier than end time.
- Ranges must fit inside the source video duration.

## Notes

- Existing output files are not overwritten.
- Source MP4 files are not modified or deleted.
- BAT files include `pause` so the console stays open after running.
- FFmpeg/FFprobe must be installed for real MP4 generation.
- Do not commit real videos, real subtitles, or generated output.

#!/usr/bin/env python3
"""shorts_auto_editor v0.1.

Modes:
- dry_run: report-only metadata/report generation.
- multi_clip_join: deterministic ffmpeg rough-cut output.
- single_video_manual_cut: deterministic manual range output.
- subtitle_scan: report-only SRT sidecar scan.
- apply_candidate_ranges: safely apply one combined candidate to ranges.txt.

This tool never modifies or deletes source MP4 files.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any


TOOL_VERSION = "v0.1"
ALLOWED_MODES = ("dry_run", "multi_clip_join", "single_video_manual_cut", "candidate_scan", "audio_peak_scan", "scene_change_scan", "thumbnail_sample", "combined_candidates", "apply_candidate_ranges", "subtitle_scan", "subtitle_candidate_scan", "batch_screen_focus_roughcut")
ALLOWED_ASPECTS = ("9:16", "16:9")
ALLOWED_DURATIONS = (35, 50, 60)
ALLOWED_LAYOUTS = ("crop", "fit_blur", "fit_black")
ALLOWED_LAYOUT_PRESETS = ("screen_focus",)
ALLOWED_FOREGROUND_SCALES = ("1.00", "1.10", "1.15", "1.20")
DEFAULT_VIDEO_EXTENSIONS = (".mp4",)
CANDIDATE_VIDEO_EXTENSIONS = (".mp4", ".mov")
MANUAL_CUT_VIDEO_EXTENSIONS = (".mp4", ".mov")
SINGLE_FILE_VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi")
DEFAULT_SUBTITLE_EXPECTED_INPUT = "your_long_recording.mp4"
SUBTITLE_MAP_PATH = Path("subtitles") / "subtitle_map.json"
PRE_CROP_PATTERN = re.compile(r"^crop=([1-9]\d*):([1-9]\d*):(0|[1-9]\d*):(0|[1-9]\d*)$")
SUBTITLE_BURN_IN_STYLE = {
    "FontName": "Pretendard",
    "FontSize": "64",
    "PrimaryColour": "&H00000000",
    "OutlineColour": "&H00FFFFFF",
    "BackColour": "&H00000000",
    "Bold": "1",
    "BorderStyle": "1",
    "Outline": "5",
    "Shadow": "0",
    "Alignment": "2",
    "MarginL": "60",
    "MarginR": "200",
    "MarginV": "610",
    "WrapStyle": "2",
}
SUBTITLE_STYLE_SUMMARY = (
    "FontName=Pretendard fallback for unavailable Pretendard ExtraBold, FontSize=64, "
    "black text, white stroke, no box, "
    "Alignment=2, fixed ASS position x=540 y=1290, safe box x=60-880 y=1160-1310, "
    "Outline=5, Shadow=0, BorderStyle=1, WrapStyle=2"
)
SUBTITLE_SINGLE_LINE_POLICY = True
SUBTITLE_DEADZONE_SAFE = True
SUBTITLE_CENTER_ALIGN = True
SUBTITLE_SAFE_BOX = {
    "x_min": 60,
    "x_max": 880,
    "y_min": 1160,
    "y_max": 1310,
    "position_x": 540,
    "position_y": 1290,
    "max_line_chars": 9,
}
COMBINED_CANDIDATE_REPORT_FIELDS = (
    "tool_version",
    "run_id",
    "mode",
    "input_path",
    "source_metadata",
    "inputs_used",
    "combined_candidates",
    "ranges_candidates",
    "Recommended Candidate Summary",
    "Copy to ranges.txt",
    "Next Command",
    "Why this candidate",
    "Warnings",
    "subtitle_status",
    "subtitle_file",
    "subtitle_caption_count",
    "subtitle_first_timecode",
    "subtitle_last_timecode",
    "subtitle_estimated_coverage",
    "subtitle_parse_warning",
    "subtitle_burn_in",
    "warnings",
    "failure_reason",
    "next_user_action",
    "changes_made",
)
APPLY_CANDIDATE_RANGES_REPORT_FIELDS = (
    "tool_version",
    "run_id",
    "mode",
    "candidate_file",
    "candidate_index",
    "selected_range",
    "backup_path",
    "output_ranges_path",
    "warnings",
    "failure_reason",
    "next_user_action",
    "changes_made",
)
SUBTITLE_SCAN_REPORT_FIELDS = (
    "tool_version",
    "run_id",
    "mode",
    "status",
    "subtitle_dir",
    "subtitle_file",
    "line_count",
    "caption_count",
    "first_timecode",
    "last_timecode",
    "estimated_duration_coverage",
    "linked_mode",
    "parse_warning",
    "warnings",
    "failure_reason",
    "changes_made",
)
SUBTITLE_CANDIDATE_REPORT_FIELDS = (
    "tool_version",
    "run_id",
    "mode",
    "subtitle_dir",
    "subtitle_file",
    "ranges_candidates_path",
    "caption_count",
    "subtitle_first_timecode",
    "subtitle_last_timecode",
    "candidate_window_seconds",
    "candidate_count",
    "subtitle_candidates",
    "ranges_candidates",
    "warnings",
    "failure_reason",
    "next_user_action",
    "changes_made",
)
THUMBNAIL_SAMPLE_REPORT_FIELDS = (
    "tool_version",
    "run_id",
    "mode",
    "input_path",
    "source_metadata",
    "scan_settings",
    "thumbnails",
    "warnings",
    "failure_reason",
    "next_user_action",
    "changes_made",
)
SCENE_CHANGE_REPORT_FIELDS = (
    "tool_version",
    "run_id",
    "mode",
    "input_path",
    "source_metadata",
    "scan_settings",
    "scene_change_candidates",
    "ranges_candidates",
    "warnings",
    "failure_reason",
    "next_user_action",
    "changes_made",
)
AUDIO_PEAK_REPORT_FIELDS = (
    "tool_version",
    "run_id",
    "mode",
    "input_path",
    "source_metadata",
    "scan_settings",
    "audio_peak_candidates",
    "ranges_candidates",
    "warnings",
    "failure_reason",
    "next_user_action",
    "changes_made",
)
CANDIDATE_REPORT_FIELDS = (
    "tool_version",
    "run_id",
    "mode",
    "input_path",
    "source_files",
    "source_metadata",
    "scan_settings",
    "recommended_durations",
    "candidate_strategy_status",
    "Recommended Candidate Summary",
    "Copy to ranges.txt",
    "Next Command",
    "Why this candidate",
    "Warnings",
    "subtitle_status",
    "subtitle_file",
    "subtitle_caption_count",
    "subtitle_first_timecode",
    "subtitle_last_timecode",
    "subtitle_estimated_coverage",
    "subtitle_parse_warning",
    "subtitle_burn_in",
    "warnings",
    "failure_reason",
    "next_user_action",
    "changes_made",
)
REPORT_FIELDS = (
    "tool_version",
    "run_id",
    "mode",
    "input_path",
    "output_settings",
    "detected_files",
    "ignored_files",
    "metadata",
    "planned_edit",
    "warnings",
    "failure_reason",
    "changes_made",
)
MANUAL_CUT_REPORT_FIELDS = REPORT_FIELDS + (
    "subtitle_status",
    "subtitle_file",
    "subtitle_caption_count",
    "subtitle_first_timecode",
    "subtitle_last_timecode",
    "subtitle_estimated_coverage",
    "subtitle_parse_warning",
    "subtitle_burn_in",
)
BATCH_SCREEN_FOCUS_REPORT_FIELDS = (
    "tool_version",
    "run_id",
    "mode",
    "dry_run",
    "input_mode",
    "input_video",
    "candidate_source",
    "requested_top_n",
    "max_top_n",
    "resolved_candidate_count",
    "duration",
    "aspect",
    "layout_preset",
    "effective_layout",
    "effective_foreground_scale",
    "effective_pre_crop",
    "subtitle_burn_in_enabled",
    "subtitle_source_file",
    "subtitle_map_file",
    "subtitle_map_used",
    "subtitle_map_input_key",
    "subtitle_map_target_file",
    "subtitle_map_target_exists",
    "subtitle_source_mismatch_warning",
    "subtitle_source_mismatch_blocked",
    "subtitle_source_expected_input",
    "subtitle_style_summary",
    "subtitle_center_align",
    "subtitle_position",
    "subtitle_single_line_policy",
    "subtitle_deadzone_safe",
    "subtitle_burn_in_planned",
    "audio_gain",
    "audio_filter_planned",
    "candidates",
    "ranges_txt_modified",
    "existing_outputs_modified",
    "mp4_output_created",
    "warnings",
    "failure_reason",
    "changes_made",
)


def effective_layout(aspect: str, layout: str | None) -> str:
    if aspect == "16:9":
        return "crop"
    return layout or "fit_blur"


def effective_foreground_scale(aspect: str, layout: str, foreground_scale: str) -> str:
    if aspect == "9:16" and layout in {"fit_blur", "fit_black"}:
        return foreground_scale
    return "1.00"


def apply_layout_preset_defaults(args: argparse.Namespace) -> None:
    if args.layout_preset == "screen_focus":
        if args.layout is None:
            args.layout = "fit_blur"
        if args.foreground_scale is None:
            args.foreground_scale = "1.15"
    if args.foreground_scale is None:
        args.foreground_scale = "1.00"


def normalize_pre_crop(value: str) -> str:
    normalized = value.strip()
    if normalized.lower() == "none":
        return "none"
    if not PRE_CROP_PATTERN.fullmatch(normalized):
        raise argparse.ArgumentTypeError(
            "--pre-crop must be none or crop=WIDTH:HEIGHT:X:Y"
        )
    return normalized


def positive_audio_gain(value: str) -> str:
    try:
        gain = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--audio-gain must be a positive number") from exc
    if gain <= 0:
        raise argparse.ArgumentTypeError("--audio-gain must be greater than 0")
    return f"{gain:g}"


def pre_crop_filter(pre_crop: str) -> str | None:
    if pre_crop == "none":
        return None
    return pre_crop


def pre_crop_warning(args: argparse.Namespace) -> str | None:
    if args.pre_crop != "none":
        return "pre-crop may remove edge information"
    return None


def foreground_scale_warning(args: argparse.Namespace) -> str | None:
    if (
        args.aspect == "9:16"
        and args.layout in {"fit_blur", "fit_black"}
        and args.foreground_scale in {"1.10", "1.15", "1.20"}
    ):
        return "foreground scale may crop edge information"
    return None

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="shorts_auto_editor v0.1")
    parser.add_argument("--mode", choices=ALLOWED_MODES, default="dry_run")
    parser.add_argument("--input", default="input", help="Input folder path")
    parser.add_argument("--aspect", choices=ALLOWED_ASPECTS, default="9:16")
    parser.add_argument(
        "--duration", type=int, choices=ALLOWED_DURATIONS, default=50
    )
    parser.add_argument(
        "--output-root", default="output", help="Output root for reports and final MP4"
    )
    parser.add_argument(
        "--layout",
        choices=ALLOWED_LAYOUTS,
        help="9:16 layout: crop, fit_blur, or fit_black. Defaults to fit_blur for 9:16.",
    )
    parser.add_argument(
        "--layout-preset",
        choices=ALLOWED_LAYOUT_PRESETS,
        help="Layout preset: screen_focus applies fit_blur, foreground_scale 1.15, and pre_crop none unless individually overridden.",
    )
    parser.add_argument(
        "--foreground-scale",
        choices=ALLOWED_FOREGROUND_SCALES,
        help="Foreground scale for 9:16 fit_blur/fit_black: 1.00, 1.10, 1.15, or 1.20.",
    )
    parser.add_argument(
        "--pre-crop",
        type=normalize_pre_crop,
        default="none",
        help="Manual pre-crop applied before layout processing: none or crop=WIDTH:HEIGHT:X:Y.",
    )
    parser.add_argument("--ranges", help="Manual ranges file for single_video_manual_cut")
    parser.add_argument(
        "--candidate-file",
        help="Candidate ranges file for apply_candidate_ranges",
    )
    parser.add_argument(
        "--candidate-index",
        type=int,
        help="1-based candidate range index for apply_candidate_ranges",
    )
    parser.add_argument(
        "--candidate-source",
        help="Candidate ranges/report file for batch_screen_focus_roughcut",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=3,
        help="Number of top candidates for batch_screen_focus_roughcut dry-run. Default: 3, max: 5.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan batch_screen_focus_roughcut without creating MP4 outputs.",
    )
    parser.add_argument(
        "--burn-subtitles",
        action="store_true",
        help="Burn subtitles into generated MP4 outputs using a shifted per-candidate SRT.",
    )
    parser.add_argument(
        "--subtitle-file",
        default=r"subtitles\your_subtitle.srt",
        help=r"Subtitle source file for --burn-subtitles. Default: subtitles\your_subtitle.srt",
    )
    parser.add_argument(
        "--audio-gain",
        type=positive_audio_gain,
        default="1.0",
        help="Audio volume multiplier for generated MP4 outputs. Default: 1.0.",
    )
    args = parser.parse_args(argv)
    apply_layout_preset_defaults(args)
    args.layout = effective_layout(args.aspect, args.layout)
    args.foreground_scale = effective_foreground_scale(
        args.aspect, args.layout, args.foreground_scale
    )
    return args

def make_run_id() -> str:
    return datetime.now().strftime("run_%Y%m%d_%H%M%S")


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._-") or "batch"


def aspect_for_filename(aspect: str) -> str:
    return aspect.replace(":", "x")


def output_filename(batch_name: str, aspect: str, duration: int) -> str:
    return (
        f"{safe_name(batch_name)}_multi_clip_join_"
        f"{aspect_for_filename(aspect)}_{duration}s_v01.mp4"
    )


def manual_output_filename(source_stem: str, aspect: str, duration: int) -> str:
    return (
        f"{safe_name(source_stem)}_single_video_manual_cut_"
        f"{aspect_for_filename(aspect)}_{duration}s_v01.mp4"
    )


def file_record(path: Path) -> dict[str, Any]:
    return {
        "name": path.name,
        "path": str(path),
        "file_size": path.stat().st_size,
    }


def discover_files(
    input_path: Path, video_extensions: tuple[str, ...] = DEFAULT_VIDEO_EXTENSIONS
) -> tuple[list[Path], list[Path], list[str]]:
    warnings: list[str] = []
    allowed_extensions = {extension.lower() for extension in video_extensions}
    if not input_path.exists():
        return [], [], ["input folder does not exist"]
    if input_path.is_file():
        single_file_extensions = allowed_extensions | {
            extension.lower() for extension in SINGLE_FILE_VIDEO_EXTENSIONS
        }
        if input_path.suffix.lower() in single_file_extensions:
            return [input_path], [], warnings
        return [], [input_path], ["unsupported input file extension"]
    if not input_path.is_dir():
        return [], [], ["input path is not a folder"]

    child_files = sorted(
        [child for child in input_path.iterdir() if child.is_file()],
        key=lambda path: path.name.lower(),
    )
    detected = [child for child in child_files if child.suffix.lower() in allowed_extensions]
    ignored = [child for child in child_files if child.suffix.lower() not in allowed_extensions]
    return detected, ignored, warnings


def input_mode(input_path: Path) -> str:
    if input_path.is_file():
        return "file"
    if input_path.is_dir():
        return "folder"
    return "missing"


def parse_fps(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    try:
        return float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return None


def ffprobe_metadata(path: Path, ffprobe_path: str) -> tuple[dict[str, Any], str | None]:
    command = [
        ffprobe_path,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return {}, f"ffprobe execution failed for {path.name}: {exc}"

    if result.returncode != 0:
        message = result.stderr.strip() or "unknown ffprobe error"
        return {}, f"ffprobe failed for {path.name}: {message}"

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {}, f"ffprobe json parse failed for {path.name}: {exc}"

    streams = payload.get("streams", [])
    video_stream = next(
        (stream for stream in streams if stream.get("codec_type") == "video"), None
    )
    has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
    fmt = payload.get("format", {})

    duration: float | None = None
    raw_duration = fmt.get("duration")
    if raw_duration is not None:
        try:
            duration = float(raw_duration)
        except ValueError:
            duration = None

    width = video_stream.get("width") if video_stream else None
    height = video_stream.get("height") if video_stream else None
    fps = parse_fps(video_stream.get("avg_frame_rate") if video_stream else None)

    metadata = {
        "name": path.name,
        "path": str(path),
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "has_audio": has_audio,
        "file_size": path.stat().st_size,
    }
    return metadata, None


def collect_metadata(
    detected_paths: list[Path], ffprobe_path: str | None
) -> tuple[list[dict[str, Any]], list[str]]:
    metadata: list[dict[str, Any]] = []
    failure_reasons: list[str] = []
    if not ffprobe_path:
        return metadata, ["ffprobe missing"]

    for path in detected_paths:
        item, error = ffprobe_metadata(path, ffprobe_path)
        if error:
            failure_reasons.append(error)
            continue
        metadata.append(item)
        width = item.get("width")
        height = item.get("height")
        duration = item.get("duration")
        if not isinstance(width, int) or not isinstance(height, int):
            failure_reasons.append(f"abnormal resolution for {path.name}")
        elif width <= 0 or height <= 0:
            failure_reasons.append(f"abnormal resolution for {path.name}")
        if duration is None or float(duration) <= 0:
            failure_reasons.append(f"invalid duration for {path.name}")
    return metadata, failure_reasons


def total_metadata_duration(metadata: list[dict[str, Any]]) -> float | None:
    total_duration = 0.0
    for item in metadata:
        item_duration = item.get("duration")
        if item_duration is None:
            return None
        total_duration += float(item_duration)
    return total_duration


def build_dry_run_planned_edit(
    detected_files: list[dict[str, Any]],
    metadata: list[dict[str, Any]],
    aspect: str,
    duration: int,
    layout: str,
    foreground_scale: str,
    pre_crop: str,
) -> dict[str, Any]:
    return {
        "edit_type": "report_only_dry_run",
        "media_output_created": False,
        "source_files_modified": False,
        "source_files_deleted": False,
        "target_aspect": aspect,
        "target_duration": duration,
        "layout": layout,
        "foreground_scale": foreground_scale,
        "pre_crop": pre_crop,
        "detected_file_count": len(detected_files),
        "total_detected_duration": total_metadata_duration(metadata),
        "duration_policy": "fail when usable duration is shorter than target duration",
        "next_media_modes": ["multi_clip_join", "single_video_manual_cut"],
    }

def build_concat_or_trim_plan(
    metadata: list[dict[str, Any]], target_duration: int
) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    remaining = float(target_duration)
    for item in metadata:
        if remaining <= 0:
            break
        item_duration = float(item["duration"])
        use_duration = min(item_duration, remaining)
        plan.append(
            {
                "name": item["name"],
                "source_path": item["path"],
                "start": 0.0,
                "duration": round(use_duration, 6),
                "action": "tail_trim" if use_duration < item_duration else "use_full_clip",
                "has_audio": item.get("has_audio", False),
            }
        )
        remaining -= use_duration
    return plan


def build_multi_clip_planned_edit(
    metadata: list[dict[str, Any]],
    target_duration: int,
    aspect: str,
    layout: str,
    foreground_scale: str,
    pre_crop: str,
    output_path: Path,
    media_output_created: bool,
) -> dict[str, Any]:
    plan = build_concat_or_trim_plan(metadata, target_duration)
    return {
        "edit_type": "multi_clip_join",
        "media_output_created": media_output_created,
        "source_files_modified": False,
        "source_files_deleted": False,
        "target_duration": target_duration,
        "aspect_ratio": aspect,
        "layout": layout,
        "foreground_scale": foreground_scale,
        "pre_crop": pre_crop,
        "selected_files": [item["source_path"] for item in plan],
        "concat_or_trim_plan": plan,
        "output_path": str(output_path),
    }

def parse_timecode(value: str) -> float:
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})", value.strip())
    if not match:
        raise ValueError(f"invalid timecode: {value}")
    hours, minutes, seconds, millis = (int(part) for part in match.groups())
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"invalid timecode: {value}")
    return hours * 3600 + minutes * 60 + seconds + millis / 1000.0


def read_manual_ranges(ranges_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not ranges_path.exists():
        return [], [f"ranges file missing: {ranges_path}"]
    if not ranges_path.is_file():
        return [], [f"ranges path is not a file: {ranges_path}"]

    ranges: list[dict[str, Any]] = []
    failures: list[str] = []
    for line_number, raw_line in enumerate(ranges_path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "-" not in line:
            failures.append(f"range line {line_number} missing '-': {line}")
            continue
        start_text, end_text = [part.strip() for part in line.split("-", 1)]
        try:
            start = parse_timecode(start_text)
            end = parse_timecode(end_text)
        except ValueError as exc:
            failures.append(f"range line {line_number}: {exc}")
            continue
        if start >= end:
            failures.append(f"range line {line_number}: start must be smaller than end")
            continue
        ranges.append(
            {
                "line": line_number,
                "raw": line,
                "start": round(start, 6),
                "end": round(end, 6),
                "duration": round(end - start, 6),
            }
        )
    if not ranges and not failures:
        failures.append("ranges file has no usable ranges")
    return ranges, failures


def validate_manual_ranges(
    manual_ranges: list[dict[str, Any]], source_duration: float | None, target_duration: int
) -> list[str]:
    failures: list[str] = []
    if source_duration is None:
        failures.append("source duration is unknown")
        return failures
    for item in manual_ranges:
        if float(item["end"]) > source_duration:
            failures.append(
                f"range line {item['line']} exceeds source duration: "
                f"end {item['end']:.3f}s, source {source_duration:.3f}s"
            )
    total_range_duration = sum(float(item["duration"]) for item in manual_ranges)
    if total_range_duration < target_duration:
        failures.append(
            "manual range duration insufficient: "
            f"available {total_range_duration:.3f}s, requested {target_duration}s"
        )
    return failures


def build_manual_concat_or_trim_plan(
    source_metadata: dict[str, Any], manual_ranges: list[dict[str, Any]], target_duration: int
) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    remaining = float(target_duration)
    for item in manual_ranges:
        if remaining <= 0:
            break
        range_duration = float(item["duration"])
        use_duration = min(range_duration, remaining)
        plan.append(
            {
                "name": source_metadata["name"],
                "source_path": source_metadata["path"],
                "range_line": item["line"],
                "start": round(float(item["start"]), 6),
                "end": round(float(item["start"]) + use_duration, 6),
                "duration": round(use_duration, 6),
                "action": "tail_trim" if use_duration < range_duration else "use_full_range",
                "has_audio": source_metadata.get("has_audio", False),
            }
        )
        remaining -= use_duration
    return plan


def build_manual_planned_edit(
    source_metadata: dict[str, Any] | None,
    manual_ranges: list[dict[str, Any]],
    target_duration: int,
    aspect: str,
    layout: str,
    foreground_scale: str,
    pre_crop: str,
    output_path: Path,
    media_output_created: bool,
    subtitle_burn_in_enabled: bool = False,
    subtitle_source_file: str = "",
    subtitle_shifted_file: str = "",
    subtitle_burn_in_planned: bool = False,
    subtitle_burn_in_applied: bool = False,
    audio_gain: str = "1.0",
    audio_filter_applied: bool = False,
) -> dict[str, Any]:
    plan = (
        build_manual_concat_or_trim_plan(source_metadata, manual_ranges, target_duration)
        if source_metadata
        else []
    )
    return {
        "edit_type": "single_video_manual_cut",
        "media_output_created": media_output_created,
        "source_files_modified": False,
        "source_files_deleted": False,
        "target_duration": target_duration,
        "aspect_ratio": aspect,
        "layout": layout,
        "foreground_scale": foreground_scale,
        "pre_crop": pre_crop,
        "subtitle_burn_in_enabled": subtitle_burn_in_enabled,
        "subtitle_source_file": subtitle_source_file,
        "subtitle_style_summary": (
            subtitle_style_summary() if subtitle_burn_in_enabled else {}
        ),
        "subtitle_center_align": (
            SUBTITLE_CENTER_ALIGN if subtitle_burn_in_enabled else False
        ),
        "subtitle_position": (
            subtitle_position_summary() if subtitle_burn_in_enabled else ""
        ),
        "subtitle_single_line_policy": (
            SUBTITLE_SINGLE_LINE_POLICY if subtitle_burn_in_enabled else False
        ),
        "subtitle_deadzone_safe": (
            SUBTITLE_DEADZONE_SAFE if subtitle_burn_in_enabled else False
        ),
        "subtitle_shifted_file": subtitle_shifted_file,
        "subtitle_burn_in_planned": subtitle_burn_in_planned,
        "subtitle_burn_in_applied": subtitle_burn_in_applied,
        "audio_gain": audio_gain,
        "audio_filter_applied": audio_filter_applied,
        "selected_files": [source_metadata["path"]] if source_metadata else [],
        "manual_ranges": manual_ranges,
        "concat_or_trim_plan": plan,
        "output_path": str(output_path),
    }

def video_filter_for_aspect(aspect: str, layout: str) -> str:
    if aspect == "9:16":
        return (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1,format=yuv420p"
        )
    return (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p"
    )


def foreground_scale_filter(foreground_scale: str) -> str:
    return (
        "scale=w='iw*min(1080/iw,1920/ih)*{scale}':"
        "h='ih*min(1080/iw,1920/ih)*{scale}'"
    ).format(scale=foreground_scale)


def ffmpeg_filter_path(path: Path) -> str:
    text = path.as_posix()
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def subtitle_style_summary() -> dict[str, str]:
    return {
        **SUBTITLE_BURN_IN_STYLE,
        "summary": SUBTITLE_STYLE_SUMMARY,
        "target": "1080x1920 lower-safe-area gameplay captions",
        "safe_box_outer_bounds": "x=60-880, y=1160-1310",
        "ass_position": subtitle_position_summary(),
        "center_align": str(SUBTITLE_CENTER_ALIGN).lower(),
        "single_line_policy": str(SUBTITLE_SINGLE_LINE_POLICY).lower(),
        "deadzone_safe": str(SUBTITLE_DEADZONE_SAFE).lower(),
        "long_line_policy": "split by meaning/spacing into sequential one-line captions",
    }


def subtitle_position_summary() -> str:
    return (
        f"pos({SUBTITLE_SAFE_BOX['position_x']},{SUBTITLE_SAFE_BOX['position_y']})"
    )


def subtitle_force_style() -> str:
    return "\\,".join(
        f"{key}={value}" for key, value in SUBTITLE_BURN_IN_STYLE.items()
    )


def subtitle_source_guard(
    input_video: str | Path,
    subtitle_file: str | Path,
    burn_subtitles: bool,
) -> dict[str, Any]:
    subtitle_path = Path(subtitle_file)
    if not burn_subtitles:
        return {
            "subtitle_source_mismatch_warning": False,
            "subtitle_source_mismatch_blocked": False,
            "subtitle_source_expected_input": "",
            "subtitle_source_file": str(subtitle_path),
        }

    input_name = Path(input_video).name.casefold()
    subtitle_name = subtitle_path.name.casefold()
    expected_input = ""
    mismatch = False
    if subtitle_name == "your_subtitle.srt":
        expected_input = DEFAULT_SUBTITLE_EXPECTED_INPUT
        mismatch = input_name != expected_input.casefold()

    return {
        "subtitle_source_mismatch_warning": mismatch,
        "subtitle_source_mismatch_blocked": mismatch,
        "subtitle_source_expected_input": expected_input,
        "subtitle_source_file": str(subtitle_path),
    }


def load_subtitle_map(map_path: Path = SUBTITLE_MAP_PATH) -> tuple[dict[str, str], str | None]:
    if not map_path.exists():
        return {}, None
    try:
        raw_map = json.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, f"subtitle map read failed: {exc}"
    if not isinstance(raw_map, dict):
        return {}, "subtitle map is not a JSON object"

    subtitle_map: dict[str, str] = {}
    for key, value in raw_map.items():
        if isinstance(key, str) and isinstance(value, str):
            subtitle_map[key] = value
    return subtitle_map, None


def subtitle_map_resolution(
    input_video: str | Path,
    requested_subtitle_file: str | Path,
    burn_subtitles: bool,
    map_path: Path = SUBTITLE_MAP_PATH,
) -> dict[str, Any]:
    requested_subtitle = Path(requested_subtitle_file)
    if not burn_subtitles:
        return {
            "subtitle_map_file": "",
            "subtitle_map_used": False,
            "subtitle_map_input_key": "",
            "subtitle_map_target_file": "",
            "subtitle_map_target_exists": False,
            "subtitle_source_file": str(requested_subtitle),
            "subtitle_map_warning": "",
        }

    input_key = Path(input_video).name
    result = {
        "subtitle_map_file": str(map_path),
        "subtitle_map_used": False,
        "subtitle_map_input_key": input_key,
        "subtitle_map_target_file": "",
        "subtitle_map_target_exists": False,
        "subtitle_source_file": str(requested_subtitle),
        "subtitle_map_warning": "",
    }
    subtitle_map, warning = load_subtitle_map(map_path)
    if warning:
        result["subtitle_map_warning"] = warning
        return result
    if not subtitle_map:
        return result

    mapped_value = subtitle_map.get(input_key)
    if mapped_value is None:
        return result

    mapped_path = Path(mapped_value)
    if not mapped_path.is_absolute():
        mapped_path = map_path.parent / mapped_path
    result.update(
        {
            "subtitle_map_used": True,
            "subtitle_map_target_file": str(mapped_path),
            "subtitle_map_target_exists": mapped_path.exists() and mapped_path.is_file(),
            "subtitle_source_file": str(mapped_path),
        }
    )
    return result


def subtitle_burn_filter(path: Path) -> str:
    return (
        f"subtitles='{ffmpeg_filter_path(path)}':"
        f"force_style='{subtitle_force_style()}'"
    )


def video_filter_parts_for_clip(
    index: int,
    item: dict[str, Any],
    aspect: str,
    layout: str,
    foreground_scale: str,
    pre_crop: str,
) -> list[str]:
    clip_start = item.get("start", 0.0)
    clip_duration = item["duration"]
    source_filters = [
        f"[{index}:v]trim=start={clip_start}:duration={clip_duration}",
        "setpts=PTS-STARTPTS",
    ]
    crop_filter = pre_crop_filter(pre_crop)
    if crop_filter:
        source_filters.append(crop_filter)
    source_prefix = ",".join(source_filters)

    if aspect == "9:16" and layout == "fit_blur":
        return [
            f"{source_prefix},split=2[base{index}][fgsrc{index}]",
            f"[base{index}]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,gblur=sigma=30[bg{index}]",
            f"[fgsrc{index}]{foreground_scale_filter(foreground_scale)}[fg{index}]",
            f"[bg{index}][fg{index}]overlay=(W-w)/2:(H-h)/2,"
            f"setsar=1,format=yuv420p[v{index}]",
        ]
    if aspect == "9:16" and layout == "fit_black":
        return [
            f"{source_prefix},{foreground_scale_filter(foreground_scale)}[fg{index}]",
            f"color=c=black:s=1080x1920:r=30:d={clip_duration}[bg{index}]",
            f"[bg{index}][fg{index}]overlay=(W-w)/2:(H-h)/2,"
            f"setsar=1,format=yuv420p[v{index}]",
        ]
    return [
        f"{source_prefix},{video_filter_for_aspect(aspect, layout)}[v{index}]"
    ]
def build_ffmpeg_command(
    ffmpeg_path: str,
    concat_plan: list[dict[str, Any]],
    metadata: list[dict[str, Any]],
    aspect: str,
    layout: str,
    foreground_scale: str,
    pre_crop: str,
    output_path: Path,
    subtitle_path: Path | None = None,
    audio_gain: str = "1.0",
) -> list[str]:
    command = [ffmpeg_path, "-hide_banner", "-n"]
    for item in concat_plan:
        command.extend(["-i", item["source_path"]])
    audio_enabled = all(bool(item.get("has_audio")) for item in concat_plan)
    filter_parts: list[str] = []
    concat_inputs: list[str] = []

    for index, item in enumerate(concat_plan):
        clip_start = item.get("start", 0.0)
        clip_duration = item["duration"]
        filter_parts.extend(
            video_filter_parts_for_clip(
                index, item, aspect, layout, foreground_scale, pre_crop
            )
        )
        concat_inputs.append(f"[v{index}]")
        if audio_enabled:
            filter_parts.append(
                f"[{index}:a]atrim=start={clip_start}:duration={clip_duration},"
                f"asetpts=PTS-STARTPTS[a{index}]"
            )
            concat_inputs.append(f"[a{index}]")

    stream_count = len(concat_plan)
    burn_subtitles = subtitle_path is not None
    gain_value = float(audio_gain)
    audio_filter_enabled = audio_enabled and abs(gain_value - 1.0) > 0.000001
    video_output_label = "vpreout" if burn_subtitles else "vout"
    audio_output_label = "apreout" if audio_filter_enabled else "aout"
    concat_suffix = f"concat=n={stream_count}:v=1:a={1 if audio_enabled else 0}"
    if audio_enabled:
        concat_suffix += f"[{video_output_label}][{audio_output_label}]"
    else:
        concat_suffix += f"[{video_output_label}]"
    filter_parts.append("".join(concat_inputs) + concat_suffix)
    if burn_subtitles and subtitle_path is not None:
        filter_parts.append(f"[{video_output_label}]{subtitle_burn_filter(subtitle_path)}[vout]")
    if audio_filter_enabled:
        filter_parts.append(f"[{audio_output_label}]volume={audio_gain}[aout]")

    command.extend(["-filter_complex", ";".join(filter_parts)])
    command.extend(["-map", "[vout]"])
    if audio_enabled:
        command.extend(["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"])
    else:
        command.append("-an")
    command.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "20"])
    command.append(str(output_path))
    return command

def render_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def write_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# shorts_auto_editor edit_report", ""]
    for field in REPORT_FIELDS:
        lines.append(f"## {field}")
        lines.append("")
        lines.append(render_value(report.get(field, "")))
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_manual_cut_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# shorts_auto_editor edit_report", ""]
    for field in MANUAL_CUT_REPORT_FIELDS:
        lines.append(f"## {field}")
        lines.append("")
        lines.append(render_value(report.get(field, "")))
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")




def write_candidate_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# shorts_auto_editor candidate_report", ""]
    for field in CANDIDATE_REPORT_FIELDS:
        lines.append(f"## {field}")
        lines.append("")
        lines.append(render_value(report.get(field, "")))
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")








def write_combined_candidate_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# shorts_auto_editor combined_candidate_report", ""]
    for field in COMBINED_CANDIDATE_REPORT_FIELDS:
        lines.append(f"## {field}")
        lines.append("")
        lines.append(render_value(report.get(field, "")))
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_apply_candidate_ranges_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# shorts_auto_editor apply_candidate_ranges_report", ""]
    for field in APPLY_CANDIDATE_RANGES_REPORT_FIELDS:
        lines.append(f"## {field}")
        lines.append("")
        lines.append(render_value(report.get(field, "")))
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_subtitle_scan_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# shorts_auto_editor subtitle_scan_report", ""]
    for field in SUBTITLE_SCAN_REPORT_FIELDS:
        lines.append(f"## {field}")
        lines.append("")
        lines.append(render_value(report.get(field, "")))
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_subtitle_candidate_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# shorts_auto_editor subtitle_candidate_report", ""]
    for field in SUBTITLE_CANDIDATE_REPORT_FIELDS:
        lines.append(f"## {field}")
        lines.append("")
        lines.append(render_value(report.get(field, "")))
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_thumbnail_sample_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# shorts_auto_editor thumbnail_sample_report", ""]
    for field in THUMBNAIL_SAMPLE_REPORT_FIELDS:
        lines.append(f"## {field}")
        lines.append("")
        lines.append(render_value(report.get(field, "")))
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")
def write_scene_change_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# shorts_auto_editor scene_change_report", ""]
    for field in SCENE_CHANGE_REPORT_FIELDS:
        lines.append(f"## {field}")
        lines.append("")
        lines.append(render_value(report.get(field, "")))
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")
def write_audio_peak_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# shorts_auto_editor audio_peak_report", ""]
    for field in AUDIO_PEAK_REPORT_FIELDS:
        lines.append(f"## {field}")
        lines.append("")
        lines.append(render_value(report.get(field, "")))
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_batch_screen_focus_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ["# shorts_auto_editor batch_screen_focus_roughcut_report", ""]
    for field in BATCH_SCREEN_FOCUS_REPORT_FIELDS:
        lines.append(f"## {field}")
        lines.append("")
        lines.append(render_value(report.get(field, "")))
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def base_report(
    args: argparse.Namespace,
    run_id: str,
    report_path: Path,
    detected_files: list[dict[str, Any]],
    ignored_files: list[dict[str, Any]],
    metadata: list[dict[str, Any]],
    planned_edit: dict[str, Any],
    warnings: list[str],
    failure_reasons: list[str],
    changes_made: str | list[str],
) -> dict[str, Any]:
    return {
        "tool_version": TOOL_VERSION,
        "run_id": run_id,
        "mode": args.mode,
        "input_path": str(Path(args.input)),
        "output_settings": {
            "aspect": args.aspect,
            "duration": args.duration,
            "output_root": str(Path(args.output_root)),
            "report_path": str(report_path),
            "layout_preset": args.layout_preset,
            "layout": args.layout,
            "foreground_scale": args.foreground_scale,
            "pre_crop": args.pre_crop,
            "subtitle_burn_in_enabled": bool(args.burn_subtitles),
            "subtitle_source_file": args.subtitle_file,
            "subtitle_style_summary": (
                subtitle_style_summary() if args.burn_subtitles else {}
            ),
            "subtitle_center_align": (
                SUBTITLE_CENTER_ALIGN if args.burn_subtitles else False
            ),
            "subtitle_position": (
                subtitle_position_summary() if args.burn_subtitles else ""
            ),
            "subtitle_single_line_policy": (
                SUBTITLE_SINGLE_LINE_POLICY if args.burn_subtitles else False
            ),
            "subtitle_deadzone_safe": (
                SUBTITLE_DEADZONE_SAFE if args.burn_subtitles else False
            ),
            "audio_gain": args.audio_gain,
        },
        "detected_files": detected_files,
        "ignored_files": ignored_files,
        "metadata": metadata,
        "planned_edit": planned_edit,
        "warnings": warnings,
        "failure_reason": failure_reasons or "none",
        "changes_made": changes_made,
    }

def prepare_inputs(
    args: argparse.Namespace,
    video_extensions: tuple[str, ...] = DEFAULT_VIDEO_EXTENSIONS,
) -> tuple[list[Path], list[Path], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    input_path = Path(args.input)
    detected_paths, ignored_paths, discovery_warnings = discover_files(
        input_path, video_extensions
    )
    detected_files = [file_record(path) for path in detected_paths]
    ignored_files = [file_record(path) for path in ignored_paths]
    return detected_paths, ignored_paths, detected_files, ignored_files, discovery_warnings


def add_input_failures(
    input_path: Path, detected_paths: list[Path], failure_reasons: list[str]
) -> None:
    if not input_path.exists():
        failure_reasons.append("input folder missing")
    elif input_path.is_file():
        if not detected_paths:
            failure_reasons.append("unsupported input video file")
    elif not input_path.is_dir():
        failure_reasons.append("input path is not a folder")
    elif not detected_paths:
        failure_reasons.append("no supported video input files found")


def select_manual_cut_source(
    detected_paths: list[Path],
) -> tuple[list[Path], list[str]]:
    if len(detected_paths) <= 1:
        return detected_paths, []
    mov_paths = [path for path in detected_paths if path.suffix.lower() == ".mov"]
    if len(mov_paths) == 1:
        return mov_paths, ["single .mov source selected from mixed supported input files for manual_cut"]
    return detected_paths, []



def candidate_strategy_status() -> dict[str, str]:
    return {
        "audio_peak": "not_run_in_step_1",
        "scene_change": "not_run_in_step_1",
        "thumbnail_sample": "not_run_in_step_1",
        "speech_or_subtitle_analysis": "not_run_in_step_1",
        "auto_best_cut": "not_run_in_step_1",
    }


def candidate_next_user_action() -> list[str]:
    return [
        "Review candidate_report.md.",
        "Use this Step 1 report only as metadata and scan-plan context.",
        "Wait for later v0.3 steps for audio_peak, scene_change, thumbnails, and ranges_candidates.txt.",
        "Manually create or edit ranges.txt before running single_video_manual_cut.",
    ]


def build_candidate_scan_report(
    args: argparse.Namespace,
    run_id: str,
    report_path: Path,
    detected_files: list[dict[str, Any]],
    metadata: list[dict[str, Any]],
    warnings: list[str],
    failure_reasons: list[str],
) -> dict[str, Any]:
    return {
        "tool_version": TOOL_VERSION,
        "run_id": run_id,
        "mode": args.mode,
        "input_path": str(Path(args.input)),
        "source_files": detected_files,
        "source_metadata": metadata,
        "scan_settings": {
            "step": "v0.3_step1_dry_run_scan_report",
            "output_root": str(Path(args.output_root)),
            "report_path": str(report_path),
            "input_scope": "direct_child_video_files_mp4_mov",
            "example_long_video_limit": "2 hours / 6 GB",
            "audio_peak_analysis": False,
            "scene_change_analysis": False,
            "thumbnail_sample_generation": False,
            "speech_or_subtitle_analysis": False,
            "auto_best_cut": False,
            "final_mp4_created": False,
            "full_video_encoding": False,
        },
        "recommended_durations": list(ALLOWED_DURATIONS),
        "candidate_strategy_status": candidate_strategy_status(),
        **build_candidate_scan_ux_sections(),
        "warnings": warnings,
        "failure_reason": failure_reasons or "none",
        "next_user_action": candidate_next_user_action(),
        "changes_made": "candidate_report_created",
    }


def build_candidate_scan_ux_sections() -> dict[str, Any]:
    return {
        "Recommended Candidate Summary": "no_candidate_found",
        "Copy to ranges.txt": "no_candidate_found",
        "Next Command": [
            "python shorts_auto_editor.py --mode apply_candidate_ranges",
            "python shorts_auto_editor.py --mode manual_cut",
        ],
        "Why this candidate": "no_candidate_found",
        "Warnings": [
            "자동 확정 아님",
            "사용자가 후보를 확인 후 ranges.txt 적용 필요",
            "원본 MP4는 수정하지 않음",
        ],
    }



def format_timecode(seconds: float) -> str:
    millis_total = int(round(max(0.0, seconds) * 1000))
    millis = millis_total % 1000
    total_seconds = millis_total // 1000
    sec = total_seconds % 60
    minutes_total = total_seconds // 60
    minute = minutes_total % 60
    hour = minutes_total // 60
    return f"{hour:02d}:{minute:02d}:{sec:02d}.{millis:03d}"


SRT_TIMECODE_PATTERN = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)


def parse_srt_timecode(value: str) -> float:
    hours_text, minutes_text, rest = value.split(":")
    seconds_text, millis_text = rest.split(",")
    return (
        int(hours_text) * 3600
        + int(minutes_text) * 60
        + int(seconds_text)
        + int(millis_text) / 1000.0
    )


def format_srt_timecode(seconds: float) -> str:
    millis_total = int(round(max(0.0, seconds) * 1000))
    millis = millis_total % 1000
    total_seconds = millis_total // 1000
    sec = total_seconds % 60
    total_minutes = total_seconds // 60
    minute = total_minutes % 60
    hour = total_minutes // 60
    return f"{hour:02d}:{minute:02d}:{sec:02d},{millis:03d}"


def format_ass_timecode(seconds: float) -> str:
    centis_total = int(round(max(0.0, seconds) * 100))
    centis = centis_total % 100
    total_seconds = centis_total // 100
    sec = total_seconds % 60
    total_minutes = total_seconds // 60
    minute = total_minutes % 60
    hour = total_minutes // 60
    return f"{hour}:{minute:02d}:{sec:02d}.{centis:02d}"


def parse_srt_captions(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    text, warnings = read_srt_text(path)
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n").strip())
    captions: list[dict[str, Any]] = []
    for block_index, block in enumerate(blocks, 1):
        lines = [line.rstrip("\n") for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        time_line_index = next(
            (index for index, line in enumerate(lines) if SRT_TIMECODE_PATTERN.search(line)),
            None,
        )
        if time_line_index is None:
            continue
        match = SRT_TIMECODE_PATTERN.search(lines[time_line_index])
        if match is None:
            continue
        start = parse_srt_timecode(match.group("start"))
        end = parse_srt_timecode(match.group("end"))
        if end <= start:
            warnings.append(f"subtitle block {block_index} ignored because end <= start")
            continue
        captions.append(
            {
                "start": start,
                "end": end,
                "text": lines[time_line_index + 1 :],
            }
        )
    return captions, warnings


def subtitle_display_length(text: str) -> int:
    return sum(1 for char in text if not char.isspace())


def split_subtitle_text_single_line(text_lines: list[str], max_chars: int) -> list[str]:
    text = re.sub(r"\s+", " ", " ".join(line.strip() for line in text_lines)).strip()
    if not text:
        return []
    if subtitle_display_length(text) <= max_chars:
        return [text]

    pieces: list[str] = []
    current = ""
    for token in text.split(" "):
        candidate = token if not current else f"{current} {token}"
        if subtitle_display_length(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            pieces.append(current)
            current = ""
        if subtitle_display_length(token) <= max_chars:
            current = token
            continue
        chunk = ""
        for char in token:
            if subtitle_display_length(chunk + char) > max_chars and chunk:
                pieces.append(chunk)
                chunk = char
            else:
                chunk += char
        current = chunk
    if current:
        pieces.append(current)
    return pieces


def ass_escape_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", r"\{").replace("}", r"\}")


def write_shifted_ass_for_range(
    source_path: Path, output_path: Path, start: float, end: float
) -> tuple[int, list[str]]:
    captions, warnings = parse_srt_captions(source_path)
    style = SUBTITLE_BURN_IN_STYLE
    events: list[str] = []
    max_chars = int(SUBTITLE_SAFE_BOX["max_line_chars"])
    pos_x = int(SUBTITLE_SAFE_BOX["position_x"])
    pos_y = int(SUBTITLE_SAFE_BOX["position_y"])

    for caption in captions:
        overlap_start = max(float(caption["start"]), start)
        overlap_end = min(float(caption["end"]), end)
        if overlap_end <= overlap_start:
            continue
        text_lines = [str(line) for line in caption.get("text", []) if str(line).strip()]
        pieces = split_subtitle_text_single_line(text_lines, max_chars)
        if not pieces:
            continue

        shifted_start = overlap_start - start
        shifted_end = overlap_end - start
        duration = shifted_end - shifted_start
        total_weight = sum(max(1, subtitle_display_length(piece)) for piece in pieces)
        cursor = shifted_start
        for index, piece in enumerate(pieces):
            if index == len(pieces) - 1:
                piece_end = shifted_end
            else:
                weight = max(1, subtitle_display_length(piece))
                piece_end = min(shifted_end, cursor + duration * weight / total_weight)
            if piece_end <= cursor:
                continue
            override = rf"{{\an2\pos({pos_x},{pos_y})\q2}}"
            events.append(
                "Dialogue: 0,"
                f"{format_ass_timecode(cursor)},{format_ass_timecode(piece_end)},"
                f"Default,,0,0,0,,{override}{ass_escape_text(piece)}"
            )
            cursor = piece_end

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        (
            "Style: Default,"
            f"{style['FontName']},{style['FontSize']},{style['PrimaryColour']},&H000000FF,"
            f"{style['OutlineColour']},{style['BackColour']},{style['Bold']},0,0,0,100,100,0,0,"
            f"{style['BorderStyle']},{style['Outline']},{style['Shadow']},{style['Alignment']},"
            f"{style['MarginL']},{style['MarginR']},{style['MarginV']},1"
        ),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        *events,
    ]
    output_path.write_text("\n".join(ass_lines) + "\n", encoding="utf-8")
    if not events:
        warnings.append("subtitle cut produced no captions for selected range")
    return len(events), warnings


def write_shifted_srt_for_range(
    source_path: Path, output_path: Path, start: float, end: float
) -> tuple[int, list[str]]:
    if output_path.suffix.lower() == ".ass":
        return write_shifted_ass_for_range(source_path, output_path, start, end)
    captions, warnings = parse_srt_captions(source_path)
    shifted_blocks: list[str] = []
    for caption in captions:
        overlap_start = max(float(caption["start"]), start)
        overlap_end = min(float(caption["end"]), end)
        if overlap_end <= overlap_start:
            continue
        shifted_start = overlap_start - start
        shifted_end = overlap_end - start
        text_lines = [str(line) for line in caption.get("text", []) if str(line).strip()]
        if not text_lines:
            continue
        shifted_blocks.append(
            "\n".join(
                [
                    str(len(shifted_blocks) + 1),
                    f"{format_srt_timecode(shifted_start)} --> {format_srt_timecode(shifted_end)}",
                    *text_lines,
                ]
            )
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n".join(shifted_blocks) + ("\n" if shifted_blocks else ""), encoding="utf-8")
    if not shifted_blocks:
        warnings.append("subtitle cut produced no captions for selected range")
    return len(shifted_blocks), warnings


def discover_subtitle_file(subtitle_dir: Path) -> tuple[Path | None, list[str]]:
    warnings: list[str] = []
    if not subtitle_dir.exists():
        warnings.append(f"subtitle directory missing: {subtitle_dir}")
        return None, warnings
    if not subtitle_dir.is_dir():
        warnings.append(f"subtitle path is not a directory: {subtitle_dir}")
        return None, warnings

    priority_names = ("your_subtitle.srt", "source_subtitle.srt", "subtitle.srt")
    for name in priority_names:
        candidate = subtitle_dir / name
        if not candidate.is_file():
            continue
        if name == "subtitle.srt":
            warnings.append(
                "subtitle.srt selected as sample/test sidecar; your_subtitle.srt not found"
            )
        return candidate, warnings

    smoke_test = subtitle_dir / "smoke_test_subtitle.srt"
    if smoke_test.is_file():
        warnings.append(
            "smoke_test_subtitle.srt ignored for automatic real SRT selection"
        )

    candidates = sorted(
        path
        for path in subtitle_dir.glob("*.srt")
        if path.is_file()
        and path.name not in priority_names
        and path.name != "smoke_test_subtitle.srt"
    )
    if candidates:
        warnings.append(f"fallback subtitle selected: {candidates[0].name}")
        return candidates[0], warnings
    warnings.append(f"no srt files found under: {subtitle_dir}")
    return None, warnings


def read_srt_text(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        return path.read_text(encoding="utf-8-sig"), warnings
    except UnicodeDecodeError:
        warnings.append("subtitle file is not valid utf-8/utf-8-bom; invalid bytes were replaced")
        return path.read_text(encoding="utf-8-sig", errors="replace"), warnings


def scan_srt(path: Path) -> dict[str, Any]:
    text, warnings = read_srt_text(path)
    lines = text.splitlines()
    matches = list(SRT_TIMECODE_PATTERN.finditer(text))
    parse_warnings = list(warnings)
    first_start: float | None = None
    last_end: float | None = None
    invalid_order_count = 0

    for match in matches:
        start = parse_srt_timecode(match.group("start"))
        end = parse_srt_timecode(match.group("end"))
        if end < start:
            invalid_order_count += 1
            continue
        if first_start is None or start < first_start:
            first_start = start
        if last_end is None or end > last_end:
            last_end = end

    if not matches:
        parse_warnings.append("no valid SRT timecode ranges found")
    if invalid_order_count:
        parse_warnings.append(f"{invalid_order_count} timecode range(s) had end before start")

    coverage: str | float = "unknown"
    if first_start is not None and last_end is not None:
        coverage = round(max(0.0, last_end - first_start), 3)

    return {
        "line_count": len(lines),
        "caption_count": len(matches),
        "first_timecode": format_timecode(first_start) if first_start is not None else "",
        "last_timecode": format_timecode(last_end) if last_end is not None else "",
        "estimated_duration_coverage": coverage,
        "parse_warning": parse_warnings or "none",
    }


def srt_caption_ranges(path: Path) -> tuple[list[dict[str, float]], list[str]]:
    text, warnings = read_srt_text(path)
    captions: list[dict[str, float]] = []
    for match in SRT_TIMECODE_PATTERN.finditer(text):
        start = parse_srt_timecode(match.group("start"))
        end = parse_srt_timecode(match.group("end"))
        if end < start:
            warnings.append("subtitle candidate ignored one caption with end before start")
            continue
        captions.append({"start": start, "end": end})
    return sorted(captions, key=lambda item: float(item["start"])), warnings


def build_subtitle_candidates(
    captions: list[dict[str, float]], window_duration: float = 35.0, max_count: int = 12
) -> list[dict[str, Any]]:
    if not captions:
        return []
    first_start = float(captions[0]["start"])
    last_end = max(float(caption["end"]) for caption in captions)
    latest_start = max(first_start, last_end - window_duration)
    usable_starts = sorted(
        {
            round(float(caption["start"]), 3)
            for caption in captions
            if first_start <= float(caption["start"]) <= latest_start
        }
    )
    if not usable_starts:
        return []
    if len(usable_starts) <= max_count:
        sampled_starts = usable_starts
    else:
        sampled_starts = []
        for index in range(max_count):
            position = round(index * (len(usable_starts) - 1) / (max_count - 1))
            sampled_starts.append(usable_starts[position])
        sampled_starts = sorted(set(sampled_starts))

    candidates: list[dict[str, Any]] = []
    for rank, start in enumerate(sampled_starts, 1):
        end = round(start + window_duration, 3)
        caption_count = sum(
            1
            for caption in captions
            if float(caption["start"]) < end and float(caption["end"]) > start
        )
        if caption_count <= 0:
            continue
        candidates.append(
            {
                "rank": rank,
                "start": round(start, 3),
                "end": end,
                "duration": round(window_duration, 3),
                "range": f"{format_timecode(start)}-{format_timecode(end)}",
                "caption_count_in_window": caption_count,
                "sources": ["subtitle_candidate"],
                "score": 1,
                "source_file": "subtitle_candidate",
                "reason": "sampled 35s subtitle coverage window",
            }
        )
    return candidates


def subtitle_report_summary(subtitle_dir: Path) -> dict[str, Any]:
    subtitle_file, discovery_warnings = discover_subtitle_file(subtitle_dir)
    if subtitle_file is None:
        return {
            "subtitle_status": "subtitle_not_found",
            "subtitle_file": "not_found",
            "subtitle_caption_count": 0,
            "subtitle_first_timecode": "",
            "subtitle_last_timecode": "",
            "subtitle_estimated_coverage": "unknown",
            "subtitle_parse_warning": "none",
            "subtitle_burn_in": False,
        }

    try:
        scan_result = scan_srt(subtitle_file)
    except OSError as exc:
        scan_result = {
            "caption_count": 0,
            "first_timecode": "",
            "last_timecode": "",
            "estimated_duration_coverage": "unknown",
            "parse_warning": [f"subtitle read failed: {exc}"],
        }

    parse_warning = scan_result.get("parse_warning", "none")
    if parse_warning == "none" and discovery_warnings:
        parse_warning = discovery_warnings
    status = "subtitle_found" if parse_warning == "none" else "subtitle_found_with_parse_warning"
    return {
        "subtitle_status": status,
        "subtitle_file": str(subtitle_file),
        "subtitle_caption_count": scan_result.get("caption_count", 0),
        "subtitle_first_timecode": scan_result.get("first_timecode", ""),
        "subtitle_last_timecode": scan_result.get("last_timecode", ""),
        "subtitle_estimated_coverage": scan_result.get("estimated_duration_coverage", "unknown"),
        "subtitle_parse_warning": parse_warning,
        "subtitle_burn_in": False,
    }


def merge_candidate_windows(
    points: list[dict[str, Any]], duration: float, window_duration: float, max_count: int
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for point in sorted(points, key=lambda item: float(item["score_db"]), reverse=True):
        center = float(point["timestamp"])
        start = max(0.0, center - window_duration / 2)
        end = min(duration, start + window_duration)
        start = max(0.0, end - window_duration)
        overlaps = any(start < float(item["end"]) and end > float(item["start"]) for item in candidates)
        if overlaps:
            continue
        candidates.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(end - start, 3),
                "peak_timestamp": round(center, 3),
                "score_db": round(float(point["score_db"]), 3),
                "range": f"{format_timecode(start)}-{format_timecode(end)}",
                "reason": "audio_peak high RMS level candidate",
            }
        )
        if len(candidates) >= max_count:
            break
    return sorted(candidates, key=lambda item: float(item["start"]))


def collect_audio_peak_points(
    source_metadata: dict[str, Any], ffmpeg_path: str, warnings: list[str]
) -> list[dict[str, Any]]:
    command = [
        ffmpeg_path,
        "-hide_banner",
        "-i",
        str(source_metadata["path"]),
        "-vn",
        "-af",
        "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
        "-f",
        "null",
        "-",
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        warnings.append(f"audio peak ffmpeg execution failed for {source_metadata['name']}: {exc}")
        return []
    if result.returncode != 0:
        message = result.stderr.strip() or "unknown ffmpeg audio analysis error"
        warnings.append(f"audio peak ffmpeg failed for {source_metadata['name']}: {message}")
        return []

    points: list[dict[str, Any]] = []
    current_time: float | None = None
    time_pattern = re.compile(r"pts_time:(\d+(?:\.\d+)?)")
    rms_pattern = re.compile(r"lavfi\.astats\.Overall\.RMS_level=(-?\d+(?:\.\d+)?)")
    for line in (result.stdout + "\n" + result.stderr).splitlines():
        time_match = time_pattern.search(line)
        if time_match:
            try:
                current_time = float(time_match.group(1))
            except ValueError:
                current_time = None
            continue
        rms_match = rms_pattern.search(line)
        if rms_match and current_time is not None:
            try:
                score = float(rms_match.group(1))
            except ValueError:
                continue
            points.append({"timestamp": current_time, "score_db": score})
    if not points:
        warnings.append(f"no audio peak points detected for {source_metadata['name']}")
    return points


def build_audio_peak_candidates(
    metadata: list[dict[str, Any]], ffmpeg_path: str | None, warnings: list[str]
) -> list[dict[str, Any]]:
    if not ffmpeg_path:
        warnings.append("ffmpeg missing; audio_peak_scan cannot analyze audio")
        return []
    all_candidates: list[dict[str, Any]] = []
    for item in metadata:
        if not item.get("has_audio"):
            warnings.append(f"{item['name']} has no audio; audio_peak skipped")
            continue
        duration = item.get("duration")
        if not isinstance(duration, (int, float)) or float(duration) <= 0:
            warnings.append(f"{item['name']} duration invalid; audio_peak skipped")
            continue
        points = collect_audio_peak_points(item, ffmpeg_path, warnings)
        candidates = merge_candidate_windows(points, float(duration), 35.0, 5)
        for index, candidate in enumerate(candidates, 1):
            enriched = dict(candidate)
            enriched.update(
                {
                    "rank": index,
                    "source_name": item["name"],
                    "source_path": item["path"],
                    "recommended_primary_duration": 35,
                    "optional_durations": [50, 60],
                }
            )
            all_candidates.append(enriched)
    return sorted(all_candidates, key=lambda item: float(item["score_db"]), reverse=True)[:5]


def write_audio_peak_ranges(ranges_path: Path, candidates: list[dict[str, Any]]) -> None:
    ranges_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# audio_peak candidates"]
    for candidate in sorted(candidates, key=lambda item: (str(item["source_name"]), float(item["start"]))):
        lines.append(str(candidate["range"]))
    ranges_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def audio_peak_next_user_action() -> list[str]:
    return [
        "Review audio_peak_report.md.",
        "Open ranges_candidates_audio_peak.txt and copy useful ranges into ranges.txt.",
        "Use these ranges as candidates only; they are not automatic best cuts.",
        "Run single_video_manual_cut manually after choosing final ranges.",
    ]


def build_audio_peak_report(
    args: argparse.Namespace,
    run_id: str,
    report_path: Path,
    ranges_path: Path,
    metadata: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    warnings: list[str],
    failure_reasons: list[str],
    changes_made: list[str],
) -> dict[str, Any]:
    return {
        "tool_version": TOOL_VERSION,
        "run_id": run_id,
        "mode": args.mode,
        "input_path": str(Path(args.input)),
        "source_metadata": metadata,
        "scan_settings": {
            "step": "v0.3_step2_audio_peak_scan",
            "output_root": str(Path(args.output_root)),
            "report_path": str(report_path),
            "ranges_candidates_path": str(ranges_path),
            "input_scope": "direct_child_mp4_files_only",
            "analysis_backend": "ffmpeg astats RMS_level via null output",
            "candidate_window_seconds": 35,
            "max_candidates": 5,
            "optional_candidate_durations": [50, 60],
            "final_mp4_created": False,
            "scene_change_analysis": False,
            "thumbnail_generation": False,
            "auto_best_cut": False,
        },
        "audio_peak_candidates": candidates,
        "ranges_candidates": [candidate["range"] for candidate in candidates],
        "warnings": warnings,
        "failure_reason": failure_reasons or "none",
        "next_user_action": audio_peak_next_user_action(),
        "changes_made": changes_made,
    }



def merge_scene_change_windows(
    points: list[dict[str, Any]], duration: float, window_duration: float, max_count: int
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for point in sorted(points, key=lambda item: float(item["scene_score"]), reverse=True):
        center = float(point["timestamp"])
        start = max(0.0, center - window_duration / 2)
        end = min(duration, start + window_duration)
        start = max(0.0, end - window_duration)
        overlaps = any(start < float(item["end"]) and end > float(item["start"]) for item in candidates)
        if overlaps:
            continue
        candidates.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(end - start, 3),
                "scene_timestamp": round(center, 3),
                "scene_score": round(float(point["scene_score"]), 6),
                "range": f"{format_timecode(start)}-{format_timecode(end)}",
                "reason": "scene_change high visual-change candidate",
            }
        )
        if len(candidates) >= max_count:
            break
    return sorted(candidates, key=lambda item: float(item["start"]))


def collect_scene_change_points(
    source_metadata: dict[str, Any], ffmpeg_path: str, threshold: float, warnings: list[str]
) -> list[dict[str, Any]]:
    command = [
        ffmpeg_path,
        "-hide_banner",
        "-i",
        str(source_metadata["path"]),
        "-vf",
        f"select='gt(scene,{threshold})',metadata=print",
        "-an",
        "-f",
        "null",
        "-",
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        warnings.append(f"scene change ffmpeg execution failed for {source_metadata['name']}: {exc}")
        return []
    if result.returncode != 0:
        message = result.stderr.strip() or "unknown ffmpeg scene analysis error"
        warnings.append(f"scene change ffmpeg failed for {source_metadata['name']}: {message}")
        return []

    points: list[dict[str, Any]] = []
    current_time: float | None = None
    time_pattern = re.compile(r"pts_time:(\d+(?:\.\d+)?)")
    scene_pattern = re.compile(r"lavfi\.scene_score=(\d+(?:\.\d+)?)")
    for line in (result.stdout + "\n" + result.stderr).splitlines():
        time_match = time_pattern.search(line)
        if time_match:
            try:
                current_time = float(time_match.group(1))
            except ValueError:
                current_time = None
            continue
        scene_match = scene_pattern.search(line)
        if scene_match and current_time is not None:
            try:
                score = float(scene_match.group(1))
            except ValueError:
                continue
            points.append({"timestamp": current_time, "scene_score": score})
    if not points:
        warnings.append(f"no scene change points detected for {source_metadata['name']}")
    return points


def build_scene_change_candidates(
    metadata: list[dict[str, Any]], ffmpeg_path: str | None, warnings: list[str]
) -> list[dict[str, Any]]:
    if not ffmpeg_path:
        warnings.append("ffmpeg missing; scene_change_scan cannot analyze video")
        return []
    all_candidates: list[dict[str, Any]] = []
    threshold = 0.04
    for item in metadata:
        duration = item.get("duration")
        if not isinstance(duration, (int, float)) or float(duration) <= 0:
            warnings.append(f"{item['name']} duration invalid; scene_change skipped")
            continue
        points = collect_scene_change_points(item, ffmpeg_path, threshold, warnings)
        candidates = merge_scene_change_windows(points, float(duration), 35.0, 5)
        for index, candidate in enumerate(candidates, 1):
            enriched = dict(candidate)
            enriched.update(
                {
                    "rank": index,
                    "source_name": item["name"],
                    "source_path": item["path"],
                    "threshold": threshold,
                    "recommended_primary_duration": 35,
                }
            )
            all_candidates.append(enriched)
    return sorted(all_candidates, key=lambda item: float(item["scene_score"]), reverse=True)[:5]


def write_scene_change_ranges(ranges_path: Path, candidates: list[dict[str, Any]]) -> None:
    ranges_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# scene_change candidates"]
    for candidate in sorted(candidates, key=lambda item: (str(item["source_name"]), float(item["start"]))):
        lines.append(str(candidate["range"]))
    ranges_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def scene_change_next_user_action() -> list[str]:
    return [
        "Review scene_change_report.md.",
        "Open ranges_candidates_scene_change.txt and copy useful ranges into ranges.txt.",
        "Use these ranges as candidates only; they are not automatic best cuts.",
        "Run single_video_manual_cut manually after choosing final ranges.",
    ]


def build_scene_change_report(
    args: argparse.Namespace,
    run_id: str,
    report_path: Path,
    ranges_path: Path,
    metadata: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    warnings: list[str],
    failure_reasons: list[str],
    changes_made: list[str],
) -> dict[str, Any]:
    return {
        "tool_version": TOOL_VERSION,
        "run_id": run_id,
        "mode": args.mode,
        "input_path": str(Path(args.input)),
        "source_metadata": metadata,
        "scan_settings": {
            "step": "v0.3_step3_scene_change_scan",
            "output_root": str(Path(args.output_root)),
            "report_path": str(report_path),
            "ranges_candidates_path": str(ranges_path),
            "input_scope": "direct_child_mp4_files_only",
            "analysis_backend": "ffmpeg select gt(scene,threshold) via null output",
            "scene_threshold": 0.04,
            "candidate_window_seconds": 35,
            "max_candidates": 5,
            "final_mp4_created": False,
            "audio_peak_analysis_modified": False,
            "thumbnail_generation": False,
            "auto_best_cut": False,
        },
        "scene_change_candidates": candidates,
        "ranges_candidates": [candidate["range"] for candidate in candidates],
        "warnings": warnings,
        "failure_reason": failure_reasons or "none",
        "next_user_action": scene_change_next_user_action(),
        "changes_made": changes_made,
    }



def timestamp_for_filename(seconds: float) -> str:
    return format_timecode(seconds).replace(":", "-").replace(".", "-")[:-4]


def thumbnail_timestamps(duration: float, max_thumbnails: int) -> list[float]:
    if duration <= 0:
        return []
    count = min(max_thumbnails, max(1, int(duration // 5) + 1))
    if count == 1:
        return [min(duration / 2, max(0.0, duration - 0.1))]
    start = min(5.0, max(0.0, duration / (count + 1)))
    end = max(start, duration - min(5.0, duration / (count + 1)))
    if count == 2:
        return [round(start, 3), round(end, 3)]
    step = (end - start) / (count - 1)
    return [round(start + step * index, 3) for index in range(count)]


def thumbnail_filename(source_stem: str, index: int, timestamp: float) -> str:
    return f"{safe_name(source_stem)}_{index:03d}_{timestamp_for_filename(timestamp)}.png"


def create_thumbnail(
    ffmpeg_path: str,
    source_path: str,
    timestamp: float,
    output_path: Path,
    warnings: list[str],
) -> bool:
    command = [
        ffmpeg_path,
        "-hide_banner",
        "-n",
        "-ss",
        format_timecode(timestamp),
        "-i",
        source_path,
        "-frames:v",
        "1",
        "-vf",
        "scale=320:-1",
        str(output_path),
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        warnings.append(f"thumbnail ffmpeg execution failed for {Path(source_path).name}: {exc}")
        return False
    if result.returncode != 0:
        message = result.stderr.strip() or "unknown thumbnail ffmpeg error"
        warnings.append(f"thumbnail ffmpeg failed for {Path(source_path).name}: {message}")
        return False
    if not output_path.exists():
        warnings.append(f"thumbnail ffmpeg completed but file missing: {output_path}")
        return False
    return True


def build_thumbnails(
    metadata: list[dict[str, Any]],
    ffmpeg_path: str | None,
    thumbnails_dir: Path,
    warnings: list[str],
) -> list[dict[str, Any]]:
    if not ffmpeg_path:
        warnings.append("ffmpeg missing; thumbnail_sample cannot create thumbnails")
        return []
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    thumbnails: list[dict[str, Any]] = []
    max_thumbnails = 12
    for item in metadata:
        duration = item.get("duration")
        if not isinstance(duration, (int, float)) or float(duration) <= 0:
            warnings.append(f"{item['name']} duration invalid; thumbnail_sample skipped")
            continue
        timestamps = thumbnail_timestamps(float(duration), max_thumbnails)
        for index, timestamp in enumerate(timestamps, 1):
            filename = thumbnail_filename(Path(item["name"]).stem, index, timestamp)
            output_path = thumbnails_dir / filename
            if output_path.exists():
                warnings.append(f"thumbnail already exists and was skipped: {output_path}")
                continue
            created = create_thumbnail(ffmpeg_path, item["path"], timestamp, output_path, warnings)
            if created:
                thumbnails.append(
                    {
                        "source_name": item["name"],
                        "source_path": item["path"],
                        "timestamp": round(timestamp, 3),
                        "timecode": format_timecode(timestamp),
                        "thumbnail_path": str(output_path),
                        "file_size": output_path.stat().st_size,
                    }
                )
    if not thumbnails:
        warnings.append("thumbnail_sample produced no thumbnails")
    return thumbnails


def thumbnail_sample_next_user_action() -> list[str]:
    return [
        "Review thumbnail_sample_report.md.",
        "Open the thumbnails folder and visually inspect representative frames.",
        "Use interesting timestamps as manual review points for ranges.txt.",
        "Run audio_peak_scan or scene_change_scan separately if candidate ranges are needed.",
    ]


def build_thumbnail_sample_report(
    args: argparse.Namespace,
    run_id: str,
    report_path: Path,
    thumbnails_dir: Path,
    metadata: list[dict[str, Any]],
    thumbnails: list[dict[str, Any]],
    warnings: list[str],
    failure_reasons: list[str],
    changes_made: list[str],
) -> dict[str, Any]:
    return {
        "tool_version": TOOL_VERSION,
        "run_id": run_id,
        "mode": args.mode,
        "input_path": str(Path(args.input)),
        "source_metadata": metadata,
        "scan_settings": {
            "step": "v0.3_step4_thumbnail_sample",
            "output_root": str(Path(args.output_root)),
            "report_path": str(report_path),
            "thumbnails_dir": str(thumbnails_dir),
            "input_scope": "direct_child_mp4_files_only",
            "thumbnail_strategy": "evenly_spaced_timestamps",
            "max_thumbnails_per_source": 12,
            "thumbnail_format": "png",
            "thumbnail_scale": "scale=320:-1",
            "final_mp4_created": False,
            "audio_peak_analysis_modified": False,
            "scene_change_analysis_modified": False,
            "auto_best_cut": False,
        },
        "thumbnails": thumbnails,
        "warnings": warnings,
        "failure_reason": failure_reasons or "none",
        "next_user_action": thumbnail_sample_next_user_action(),
        "changes_made": changes_made,
    }



def latest_file(root: Path, pattern: str) -> Path | None:
    if not root.exists():
        return None
    matches = sorted(root.rglob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def read_json_candidate_file(path: Path, source_type: str, weight: int, warnings: list[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"failed to read {source_type} json candidate file {path}: {exc}")
        return []
    if not isinstance(payload, list):
        warnings.append(f"{source_type} json candidate file ignored: top-level value must be a list")
        return []
    for index, item in enumerate(payload, 1):
        if not isinstance(item, dict):
            warnings.append(f"{source_type} json item {index} ignored: item must be an object")
            continue
        start_text = str(item.get("start", "")).strip()
        end_text = str(item.get("end", "")).strip()
        try:
            start = parse_timecode(start_text)
            end = parse_timecode(end_text)
        except ValueError as exc:
            warnings.append(f"{source_type} json item {index} ignored: {exc}")
            continue
        if start >= end:
            warnings.append(f"{source_type} json item {index} ignored: start >= end")
            continue
        candidates.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(end - start, 3),
                "range": f"{format_timecode(start)}-{format_timecode(end)}",
                "sources": [source_type],
                "score": weight,
                "source_file": str(path),
                "rank": item.get("rank", index),
                "source_candidate_id": item.get("source_candidate_id"),
                "reason": item.get("reason", "not_available"),
                "selection_source": item.get("selection_source", "not_available"),
                "layout_preset": item.get("layout_preset", "screen_focus"),
            }
        )
    return candidates


def read_candidate_ranges_file(path: Path | None, source_type: str, weight: int, warnings: list[str]) -> list[dict[str, Any]]:
    if path is None:
        warnings.append(f"no latest {source_type} ranges file found")
        return []
    if path.suffix.lower() == ".json":
        return read_json_candidate_file(path, source_type, weight, warnings)
    candidates: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        warnings.append(f"failed to read {source_type} ranges file {path}: {exc}")
        return []
    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        if "-" not in line:
            warnings.append(f"{source_type} range line {line_number} ignored: missing '-'")
            continue
        start_text, end_text = [part.strip() for part in line.split("-", 1)]
        try:
            start = parse_timecode(start_text)
            end = parse_timecode(end_text)
        except ValueError as exc:
            warnings.append(f"{source_type} range line {line_number} ignored: {exc}")
            continue
        if start >= end:
            warnings.append(f"{source_type} range line {line_number} ignored: start >= end")
            continue
        candidates.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(end - start, 3),
                "range": f"{format_timecode(start)}-{format_timecode(end)}",
                "sources": [source_type],
                "score": weight,
                "source_file": str(path),
            }
        )
    return candidates


def fallback_metadata_candidates(metadata: list[dict[str, Any]], warnings: list[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in metadata[:1]:
        duration = item.get("duration")
        if not isinstance(duration, (int, float)) or float(duration) <= 0:
            continue
        end = min(35.0, float(duration))
        candidates.append(
            {
                "start": 0.0,
                "end": round(end, 3),
                "duration": round(end, 3),
                "range": f"{format_timecode(0.0)}-{format_timecode(end)}",
                "sources": ["metadata_fallback"],
                "score": 1,
                "source_file": "metadata_fallback",
            }
        )
    if candidates:
        warnings.append("combined_candidates used metadata fallback candidate")
    return candidates


def combine_candidate_ranges(raw_candidates: list[dict[str, Any]], max_count: int) -> list[dict[str, Any]]:
    combined: list[dict[str, Any]] = []
    for candidate in sorted(raw_candidates, key=lambda item: (float(item["start"]), -float(item["score"]))):
        merged = False
        for existing in combined:
            overlaps = float(candidate["start"]) < float(existing["end"]) and float(candidate["end"]) > float(existing["start"])
            if overlaps:
                existing["start"] = round(min(float(existing["start"]), float(candidate["start"])), 3)
                existing["end"] = round(max(float(existing["end"]), float(candidate["end"])), 3)
                existing["duration"] = round(float(existing["end"]) - float(existing["start"]), 3)
                existing["range"] = f"{format_timecode(float(existing['start']))}-{format_timecode(float(existing['end']))}"
                existing["score"] = int(existing["score"]) + int(candidate["score"])
                existing["sources"] = sorted(set(existing["sources"] + candidate["sources"]))
                merged = True
                break
        if not merged:
            combined.append(dict(candidate))
    ranked = sorted(combined, key=lambda item: (-int(item["score"]), float(item["start"])))[:max_count]
    for index, item in enumerate(ranked, 1):
        item["rank"] = index
        item["recommended_primary_duration"] = 35
        item["note"] = "candidate for user review, not automatic best cut"
    return sorted(ranked, key=lambda item: float(item["start"]))


def write_combined_ranges(ranges_path: Path, candidates: list[dict[str, Any]]) -> None:
    ranges_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# combined candidates"]
    for candidate in sorted(candidates, key=lambda item: float(item["start"])):
        lines.append(str(candidate["range"]))
    ranges_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_subtitle_candidate_ranges(ranges_path: Path, candidates: list[dict[str, Any]]) -> None:
    ranges_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# subtitle candidates"]
    for candidate in sorted(candidates, key=lambda item: float(item["start"])):
        lines.append(str(candidate["range"]))
    ranges_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_ranges_next_user_action() -> list[str]:
    return [
        "run manual_cut from menu or CLI",
        "verify output before using as final",
    ]


def candidate_apply_report_path(candidate_file: Path, output_root: Path, run_id: str) -> Path:
    parent = candidate_file.parent
    if parent.name.startswith("run_"):
        return parent / "reports" / "apply_candidate_ranges_report.md"
    return output_root / f"apply_ranges_{run_id}" / "reports" / "apply_candidate_ranges_report.md"


def read_apply_candidate_ranges(candidate_file: Path) -> tuple[list[dict[str, Any]], list[str]]:
    ranges, failures = read_manual_ranges(candidate_file)
    return ranges, failures


def backup_ranges_file(ranges_path: Path, run_id: str) -> Path | None:
    if not ranges_path.exists():
        return None
    backup_dir = ranges_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"ranges_{run_id}.txt"
    shutil.copy2(ranges_path, backup_path)
    return backup_path


def write_applied_ranges(ranges_path: Path, selected_range: str, candidate_file: Path, candidate_index: int, run_id: str) -> None:
    ranges_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# ranges applied from combined candidate",
        f"# source_candidate_file: {candidate_file}",
        f"# candidate_index: {candidate_index}",
        f"# applied_run_id: {run_id}",
        selected_range,
    ]
    ranges_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_apply_candidate_ranges_report(
    args: argparse.Namespace,
    run_id: str,
    candidate_file: Path | None,
    candidate_index: int | None,
    selected_range: str,
    backup_path: Path | None,
    output_ranges_path: Path,
    warnings: list[str],
    failure_reasons: list[str],
    changes_made: list[str],
) -> dict[str, Any]:
    return {
        "tool_version": TOOL_VERSION,
        "run_id": run_id,
        "mode": args.mode,
        "candidate_file": str(candidate_file) if candidate_file else "",
        "candidate_index": candidate_index if candidate_index is not None else "",
        "selected_range": selected_range,
        "backup_path": str(backup_path) if backup_path else "none",
        "output_ranges_path": str(output_ranges_path),
        "warnings": warnings,
        "failure_reason": failure_reasons or "none",
        "next_user_action": apply_ranges_next_user_action(),
        "changes_made": changes_made or "none",
    }


def run_apply_candidate_ranges(args: argparse.Namespace) -> int:
    run_id = make_run_id()
    output_root = Path(args.output_root)
    candidate_file = Path(args.candidate_file) if args.candidate_file else None
    candidate_index = args.candidate_index
    ranges_path = Path("ranges") / "ranges.txt"
    report_path = candidate_apply_report_path(candidate_file, output_root, run_id) if candidate_file else output_root / f"apply_ranges_{run_id}" / "reports" / "apply_candidate_ranges_report.md"
    warnings: list[str] = [
        "apply_candidate_ranges updates ranges.txt only",
        "final mp4 is not created by apply_candidate_ranges",
        "source mp4 files are not modified or deleted",
        "candidate ranges are user-selected, not automatic best cuts",
    ]
    failure_reasons: list[str] = []
    selected_range = ""
    backup_path: Path | None = None
    changes_made: list[str] = []

    if candidate_file is None:
        failure_reasons.append("candidate-file is required for apply_candidate_ranges")
    elif not candidate_file.exists():
        failure_reasons.append(f"candidate-file missing: {candidate_file}")
    elif not candidate_file.is_file():
        failure_reasons.append(f"candidate-file is not a file: {candidate_file}")

    if candidate_index is None:
        failure_reasons.append("candidate-index is required for apply_candidate_ranges")
    elif candidate_index < 1:
        failure_reasons.append("candidate-index must be 1 or greater")

    candidates: list[dict[str, Any]] = []
    if candidate_file is not None and not failure_reasons:
        candidates, range_failures = read_apply_candidate_ranges(candidate_file)
        failure_reasons.extend(range_failures)
        if candidate_index is not None and not range_failures:
            if candidate_index > len(candidates):
                failure_reasons.append(
                    f"candidate-index {candidate_index} out of range; usable candidates: {len(candidates)}"
                )
            else:
                selected_range = str(candidates[candidate_index - 1]["raw"])

    if not failure_reasons and candidate_file is not None and candidate_index is not None:
        backup_path = backup_ranges_file(ranges_path, run_id)
        if backup_path is not None:
            changes_made.append("ranges_backup_created")
        write_applied_ranges(ranges_path, selected_range, candidate_file, candidate_index, run_id)
        changes_made.append("ranges_txt_updated")

    report = build_apply_candidate_ranges_report(
        args=args,
        run_id=run_id,
        candidate_file=candidate_file,
        candidate_index=candidate_index,
        selected_range=selected_range,
        backup_path=backup_path,
        output_ranges_path=ranges_path,
        warnings=warnings,
        failure_reasons=failure_reasons,
        changes_made=changes_made,
    )
    write_apply_candidate_ranges_report(report_path, report)
    print(f"apply_candidate_ranges report written: {report_path}")
    if failure_reasons:
        print("apply_candidate_ranges failed; see apply_candidate_ranges_report.md")
        return 1
    print(f"apply_candidate_ranges selected range: {selected_range}")
    print(f"ranges.txt updated: {ranges_path}")
    if backup_path:
        print(f"ranges.txt backup written: {backup_path}")
    print("apply_candidate_ranges completed without creating mp4 output")
    return 0


def combined_next_user_action() -> list[str]:
    return [
        "Pick one candidate range and copy it into ranges\\ranges.txt.",
        "Run manual_cut after choosing the final range.",
        "Use thumbnail_sample results for visual confirmation before final selection.",
        "Treat combined candidates as review aids, not automatic best cuts.",
    ]


def combined_candidate_reason(candidate: dict[str, Any]) -> str:
    sources = candidate.get("sources", [])
    if isinstance(sources, list) and sources:
        source_text = " + ".join(str(source) for source in sources)
    else:
        source_text = "unknown source"
    score = candidate.get("score", "unknown")
    return f"score {score}; {source_text}; review aid only"


def build_combined_candidate_ux_sections(
    ranges_path: Path, candidates: list[dict[str, Any]]
) -> dict[str, Any]:
    warnings = [
        "자동 확정 아님",
        "사용자가 후보를 확인 후 ranges.txt 적용 필요",
        "원본 MP4는 수정하지 않음",
    ]
    if not candidates:
        return {
            "Recommended Candidate Summary": "no_candidate_found",
            "Copy to ranges.txt": "no_candidate_found",
            "Next Command": [
                "python shorts_auto_editor.py --mode apply_candidate_ranges",
                "python shorts_auto_editor.py --mode manual_cut",
            ],
            "Why this candidate": "no_candidate_found",
            "Warnings": warnings,
        }

    recommended = sorted(
        candidates,
        key=lambda item: (int(item.get("rank", 999)), float(item.get("start", 0.0))),
    )[0]
    candidate_index = int(recommended.get("rank", 1))
    selected_range = str(recommended["range"])
    duration = recommended.get("duration", "")
    summary = (
        f"Candidate {candidate_index} | {selected_range} | "
        f"duration {duration}s | {combined_candidate_reason(recommended)}"
    )
    return {
        "Recommended Candidate Summary": summary,
        "Copy to ranges.txt": selected_range,
        "Next Command": [
            (
                "python shorts_auto_editor.py --mode apply_candidate_ranges "
                f"--candidate-file {ranges_path} --candidate-index {candidate_index}"
            ),
            "python shorts_auto_editor.py --mode manual_cut",
        ],
        "Why this candidate": combined_candidate_reason(recommended),
        "Warnings": warnings,
    }


def build_combined_candidate_report(
    args: argparse.Namespace,
    run_id: str,
    report_path: Path,
    ranges_path: Path,
    metadata: list[dict[str, Any]],
    inputs_used: dict[str, Any],
    candidates: list[dict[str, Any]],
    warnings: list[str],
    failure_reasons: list[str],
    changes_made: list[str],
) -> dict[str, Any]:
    return {
        "tool_version": TOOL_VERSION,
        "run_id": run_id,
        "mode": args.mode,
        "input_path": str(Path(args.input)),
        "source_metadata": metadata,
        "inputs_used": inputs_used,
        "combined_candidates": candidates,
        "ranges_candidates": [candidate["range"] for candidate in candidates],
        **build_combined_candidate_ux_sections(ranges_path, candidates),
        "warnings": warnings,
        "failure_reason": failure_reasons or "none",
        "next_user_action": combined_next_user_action(),
        "changes_made": changes_made,
    }


def run_combined_candidates(args: argparse.Namespace) -> int:
    run_id = make_run_id()
    input_path = Path(args.input)
    output_root = Path(args.output_root)
    report_path = output_root / run_id / "reports" / "combined_candidate_report.md"
    ranges_path = output_root / run_id / "ranges_candidates_combined.txt"

    ffprobe_path = shutil.which("ffprobe")
    warnings: list[str] = [
        "combined_candidates creates report and ranges only",
        "automatic best cut is not implemented",
        "final mp4 is not created by combined_candidates",
        "existing scan modes are not modified by combined_candidates",
    ]
    failure_reasons: list[str] = []

    if ffprobe_path is None:
        failure_reasons.append("ffprobe missing")

    detected_paths, _, detected_files, ignored_files, discovery_warnings = prepare_inputs(
        args, CANDIDATE_VIDEO_EXTENSIONS
    )
    warnings.extend(discovery_warnings)
    if ignored_files:
        warnings.append("non-mp4/mov direct child files ignored")
    add_input_failures(input_path, detected_paths, failure_reasons)

    metadata: list[dict[str, Any]] = []
    if ffprobe_path and detected_paths:
        metadata, metadata_failures = collect_metadata(detected_paths, ffprobe_path)
        failure_reasons.extend(metadata_failures)

    latest_audio = latest_file(output_root, "ranges_candidates_audio_peak.txt")
    latest_scene = latest_file(output_root, "ranges_candidates_scene_change.txt")
    latest_subtitle = latest_file(output_root, "ranges_candidates_subtitle.txt")
    latest_thumbnail_report = latest_file(output_root, "thumbnail_sample_report.md")
    latest_candidate_report = latest_file(output_root, "candidate_report.md")
    raw_candidates: list[dict[str, Any]] = []
    if not failure_reasons:
        raw_candidates.extend(read_candidate_ranges_file(latest_audio, "audio_peak", 3, warnings))
        raw_candidates.extend(read_candidate_ranges_file(latest_scene, "scene_change", 2, warnings))
        raw_candidates.extend(read_candidate_ranges_file(latest_subtitle, "subtitle_candidate", 1, warnings))
        if not raw_candidates:
            raw_candidates.extend(fallback_metadata_candidates(metadata, warnings))
    candidates = combine_candidate_ranges(raw_candidates, 5) if not failure_reasons else []
    if not candidates and not failure_reasons:
        warnings.append("combined_candidates produced no candidate ranges")

    inputs_used = {
        "audio_peak_ranges": str(latest_audio) if latest_audio else "not_found",
        "scene_change_ranges": str(latest_scene) if latest_scene else "not_found",
        "subtitle_candidate_ranges": str(latest_subtitle) if latest_subtitle else "not_found",
        "thumbnail_sample_report": str(latest_thumbnail_report) if latest_thumbnail_report else "not_found",
        "candidate_scan_report": str(latest_candidate_report) if latest_candidate_report else "not_found",
        "metadata_fallback_used": any("metadata_fallback" in candidate.get("sources", []) for candidate in candidates),
        "subtitle_candidate_used": any("subtitle_candidate" in candidate.get("sources", []) for candidate in candidates),
    }
    changes_made = ["combined_candidate_report_created", "ranges_candidates_created"]
    write_combined_ranges(ranges_path, candidates)
    report = build_combined_candidate_report(
        args=args,
        run_id=run_id,
        report_path=report_path,
        ranges_path=ranges_path,
        metadata=metadata,
        inputs_used=inputs_used,
        candidates=candidates,
        warnings=warnings,
        failure_reasons=failure_reasons,
        changes_made=changes_made,
    )
    report.update(subtitle_report_summary(Path("subtitles")))
    write_combined_candidate_report(report_path, report)
    print(f"combined_candidates report written: {report_path}")
    print(f"combined_candidates ranges written: {ranges_path}")
    if failure_reasons:
        print("combined_candidates completed with failure_reason recorded")
        return 1
    print("combined_candidates completed")
    return 0

def run_thumbnail_sample(args: argparse.Namespace) -> int:
    run_id = make_run_id()
    input_path = Path(args.input)
    output_root = Path(args.output_root)
    report_path = output_root / run_id / "reports" / "thumbnail_sample_report.md"
    thumbnails_dir = output_root / run_id / "thumbnails"

    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    warnings: list[str] = [
        "thumbnail_sample creates representative PNG frames only",
        "automatic best cut is not implemented",
        "audio_peak behavior is not modified by thumbnail_sample",
        "scene_change behavior is not modified by thumbnail_sample",
        "final mp4 is not created by thumbnail_sample",
    ]
    failure_reasons: list[str] = []

    if ffmpeg_path is None:
        failure_reasons.append("ffmpeg missing")
    if ffprobe_path is None:
        failure_reasons.append("ffprobe missing")

    detected_paths, _, detected_files, ignored_files, discovery_warnings = prepare_inputs(args)
    warnings.extend(discovery_warnings)
    if ignored_files:
        warnings.append("non-mp4 direct child files ignored")
    add_input_failures(input_path, detected_paths, failure_reasons)

    metadata: list[dict[str, Any]] = []
    if ffprobe_path and detected_paths:
        metadata, metadata_failures = collect_metadata(detected_paths, ffprobe_path)
        failure_reasons.extend(metadata_failures)

    thumbnails: list[dict[str, Any]] = []
    if not failure_reasons:
        thumbnails = build_thumbnails(metadata, ffmpeg_path, thumbnails_dir, warnings)

    changes_made = ["thumbnail_report_created"]
    if thumbnails:
        changes_made.append("thumbnails_created")
    report = build_thumbnail_sample_report(
        args=args,
        run_id=run_id,
        report_path=report_path,
        thumbnails_dir=thumbnails_dir,
        metadata=metadata,
        thumbnails=thumbnails,
        warnings=warnings,
        failure_reasons=failure_reasons,
        changes_made=changes_made,
    )
    write_thumbnail_sample_report(report_path, report)
    print(f"thumbnail_sample report written: {report_path}")
    print(f"thumbnail_sample thumbnails dir: {thumbnails_dir}")
    if failure_reasons:
        print("thumbnail_sample completed with failure_reason recorded")
        return 1
    print("thumbnail_sample completed")
    return 0

def run_scene_change_scan(args: argparse.Namespace) -> int:
    run_id = make_run_id()
    input_path = Path(args.input)
    output_root = Path(args.output_root)
    report_path = output_root / run_id / "reports" / "scene_change_report.md"
    ranges_path = output_root / run_id / "ranges_candidates_scene_change.txt"

    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    warnings: list[str] = [
        "scene_change_scan creates candidate ranges only",
        "automatic best cut is not implemented",
        "audio_peak behavior is not modified by scene_change_scan",
        "thumbnail generation not run in scene_change_scan",
        "final mp4 is not created by scene_change_scan",
    ]
    failure_reasons: list[str] = []

    if ffmpeg_path is None:
        failure_reasons.append("ffmpeg missing")
    if ffprobe_path is None:
        failure_reasons.append("ffprobe missing")

    detected_paths, _, detected_files, ignored_files, discovery_warnings = prepare_inputs(args)
    warnings.extend(discovery_warnings)
    if ignored_files:
        warnings.append("non-mp4 direct child files ignored")
    add_input_failures(input_path, detected_paths, failure_reasons)

    metadata: list[dict[str, Any]] = []
    if ffprobe_path and detected_paths:
        metadata, metadata_failures = collect_metadata(detected_paths, ffprobe_path)
        failure_reasons.extend(metadata_failures)

    candidates: list[dict[str, Any]] = []
    if not failure_reasons:
        candidates = build_scene_change_candidates(metadata, ffmpeg_path, warnings)
        if not candidates:
            warnings.append("scene_change_scan produced no candidate ranges")

    changes_made = ["scene_change_report_created", "ranges_candidates_created"]
    write_scene_change_ranges(ranges_path, candidates)
    report = build_scene_change_report(
        args=args,
        run_id=run_id,
        report_path=report_path,
        ranges_path=ranges_path,
        metadata=metadata,
        candidates=candidates,
        warnings=warnings,
        failure_reasons=failure_reasons,
        changes_made=changes_made,
    )
    write_scene_change_report(report_path, report)
    print(f"scene_change_scan report written: {report_path}")
    print(f"scene_change_scan ranges written: {ranges_path}")
    if failure_reasons:
        print("scene_change_scan completed with failure_reason recorded")
        return 1
    print("scene_change_scan completed")
    return 0

def run_audio_peak_scan(args: argparse.Namespace) -> int:
    run_id = make_run_id()
    input_path = Path(args.input)
    output_root = Path(args.output_root)
    report_path = output_root / run_id / "reports" / "audio_peak_report.md"
    ranges_path = output_root / run_id / "ranges_candidates_audio_peak.txt"

    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    warnings: list[str] = [
        "audio_peak_scan creates candidate ranges only",
        "automatic best cut is not implemented",
        "scene_change not run in audio_peak_scan",
        "thumbnail generation not run in audio_peak_scan",
        "final mp4 is not created by audio_peak_scan",
    ]
    failure_reasons: list[str] = []

    if ffmpeg_path is None:
        failure_reasons.append("ffmpeg missing")
    if ffprobe_path is None:
        failure_reasons.append("ffprobe missing")

    detected_paths, _, detected_files, ignored_files, discovery_warnings = prepare_inputs(args)
    warnings.extend(discovery_warnings)
    if ignored_files:
        warnings.append("non-mp4 direct child files ignored")
    add_input_failures(input_path, detected_paths, failure_reasons)

    metadata: list[dict[str, Any]] = []
    if ffprobe_path and detected_paths:
        metadata, metadata_failures = collect_metadata(detected_paths, ffprobe_path)
        failure_reasons.extend(metadata_failures)

    candidates: list[dict[str, Any]] = []
    if not failure_reasons:
        candidates = build_audio_peak_candidates(metadata, ffmpeg_path, warnings)
        if not candidates:
            warnings.append("audio_peak_scan produced no candidate ranges")

    changes_made = ["audio_peak_report_created", "ranges_candidates_created"]
    write_audio_peak_ranges(ranges_path, candidates)
    report = build_audio_peak_report(
        args=args,
        run_id=run_id,
        report_path=report_path,
        ranges_path=ranges_path,
        metadata=metadata,
        candidates=candidates,
        warnings=warnings,
        failure_reasons=failure_reasons,
        changes_made=changes_made,
    )
    write_audio_peak_report(report_path, report)
    print(f"audio_peak_scan report written: {report_path}")
    print(f"audio_peak_scan ranges written: {ranges_path}")
    if failure_reasons:
        print("audio_peak_scan completed with failure_reason recorded")
        return 1
    print("audio_peak_scan completed")
    return 0

def run_candidate_scan(args: argparse.Namespace) -> int:
    run_id = make_run_id()
    input_path = Path(args.input)
    output_root = Path(args.output_root)
    report_path = output_root / run_id / "reports" / "candidate_report.md"

    ffprobe_path = shutil.which("ffprobe")
    warnings: list[str] = [
        "candidate_scan step 1 creates metadata report only",
        "audio_peak not run in step 1",
        "scene_change not run in step 1",
        "thumbnail_sample not run in step 1",
        "auto_best_cut not run in step 1",
        "final mp4 is not created by candidate_scan step 1",
    ]
    failure_reasons: list[str] = []

    if ffprobe_path is None:
        failure_reasons.append("ffprobe missing")

    detected_paths, _, detected_files, ignored_files, discovery_warnings = prepare_inputs(
        args, CANDIDATE_VIDEO_EXTENSIONS
    )
    warnings.extend(discovery_warnings)
    if ignored_files:
        warnings.append("non-mp4/mov direct child files ignored")
    add_input_failures(input_path, detected_paths, failure_reasons)

    metadata: list[dict[str, Any]] = []
    if ffprobe_path and detected_paths:
        metadata, metadata_failures = collect_metadata(detected_paths, ffprobe_path)
        failure_reasons.extend(metadata_failures)

    for item in metadata:
        duration = item.get("duration")
        file_size = item.get("file_size")
        if isinstance(duration, (int, float)) and duration >= 7200:
            warnings.append(f"{item['name']} is at or above 2 hours; later scans may take time")
        if isinstance(file_size, int) and file_size >= 6 * 1024 * 1024 * 1024:
            warnings.append(f"{item['name']} is at or above 6 GB; check disk and scan time")
        if not item.get("has_audio"):
            warnings.append(f"{item['name']} has no audio; audio_peak cannot run in later steps")

    report = build_candidate_scan_report(
        args=args,
        run_id=run_id,
        report_path=report_path,
        detected_files=detected_files,
        metadata=metadata,
        warnings=warnings,
        failure_reasons=failure_reasons,
    )
    report.update(subtitle_report_summary(Path("subtitles")))
    write_candidate_report(report_path, report)
    print(f"candidate_scan report written: {report_path}")
    if failure_reasons:
        print("candidate_scan completed with failure_reason recorded")
        return 1
    print("candidate_scan completed")
    return 0


def build_subtitle_scan_report(
    args: argparse.Namespace,
    run_id: str,
    report_path: Path,
    subtitle_dir: Path,
    subtitle_file: Path | None,
    scan_result: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    status = "subtitle_found" if subtitle_file else "subtitle_not_found"
    parse_warning = scan_result.get("parse_warning", "none") if subtitle_file else "none"
    if parse_warning != "none":
        status = "subtitle_found_with_parse_warning"
    return {
        "tool_version": TOOL_VERSION,
        "run_id": run_id,
        "mode": args.mode,
        "status": status,
        "subtitle_dir": str(subtitle_dir),
        "subtitle_file": str(subtitle_file) if subtitle_file else "not_found",
        "line_count": scan_result.get("line_count", 0),
        "caption_count": scan_result.get("caption_count", 0),
        "first_timecode": scan_result.get("first_timecode", ""),
        "last_timecode": scan_result.get("last_timecode", ""),
        "estimated_duration_coverage": scan_result.get("estimated_duration_coverage", "unknown"),
        "linked_mode": {
            "manual_cut": "planned_connection_only",
            "candidate_report": "planned_connection_only",
            "automatic_burn_in": False,
            "final_mp4_created": False,
        },
        "parse_warning": parse_warning,
        "warnings": warnings,
        "failure_reason": "none",
        "changes_made": "subtitle_scan_report_created",
    }


def run_subtitle_scan(args: argparse.Namespace) -> int:
    run_id = make_run_id()
    output_root = Path("output_candidates") if args.output_root == "output" else Path(args.output_root)
    report_path = output_root / run_id / "reports" / "subtitle_scan_report.md"
    subtitle_dir = Path("subtitles")
    warnings: list[str] = [
        "subtitle_scan creates a report only",
        "subtitle burn-in is not implemented",
        "ffmpeg is not run by subtitle_scan",
        "final mp4 is not created by subtitle_scan",
    ]

    subtitle_file, discovery_warnings = discover_subtitle_file(subtitle_dir)
    warnings.extend(discovery_warnings)
    scan_result: dict[str, Any] = {
        "line_count": 0,
        "caption_count": 0,
        "first_timecode": "",
        "last_timecode": "",
        "estimated_duration_coverage": "unknown",
        "parse_warning": "none",
    }
    if subtitle_file:
        try:
            scan_result = scan_srt(subtitle_file)
        except OSError as exc:
            scan_result["parse_warning"] = [f"subtitle read failed: {exc}"]

    report = build_subtitle_scan_report(
        args=args,
        run_id=run_id,
        report_path=report_path,
        subtitle_dir=subtitle_dir,
        subtitle_file=subtitle_file,
        scan_result=scan_result,
        warnings=warnings,
    )
    write_subtitle_scan_report(report_path, report)
    print(f"subtitle_scan report written: {report_path}")
    print("subtitle_scan completed without creating mp4 output")
    return 0


def subtitle_candidate_next_user_action() -> list[str]:
    return [
        "Review subtitle_candidate_report.md.",
        "Use ranges_candidates_subtitle.txt as candidate input only.",
        "Run combined_candidates to merge available candidate signals.",
        "Do not modify ranges.txt until a final candidate is chosen.",
    ]


def build_subtitle_candidate_report(
    args: argparse.Namespace,
    run_id: str,
    ranges_path: Path,
    subtitle_dir: Path,
    subtitle_file: Path | None,
    scan_result: dict[str, Any],
    candidates: list[dict[str, Any]],
    warnings: list[str],
    failure_reasons: list[str],
) -> dict[str, Any]:
    return {
        "tool_version": TOOL_VERSION,
        "run_id": run_id,
        "mode": args.mode,
        "subtitle_dir": str(subtitle_dir),
        "subtitle_file": str(subtitle_file) if subtitle_file else "not_found",
        "ranges_candidates_path": str(ranges_path),
        "caption_count": scan_result.get("caption_count", 0),
        "subtitle_first_timecode": scan_result.get("first_timecode", ""),
        "subtitle_last_timecode": scan_result.get("last_timecode", ""),
        "candidate_window_seconds": 35,
        "candidate_count": len(candidates),
        "subtitle_candidates": candidates,
        "ranges_candidates": [candidate["range"] for candidate in candidates],
        "warnings": warnings,
        "failure_reason": failure_reasons or "none",
        "next_user_action": subtitle_candidate_next_user_action(),
        "changes_made": ["subtitle_candidate_report_created", "ranges_candidates_subtitle_created"],
    }


def run_subtitle_candidate_scan(args: argparse.Namespace) -> int:
    run_id = make_run_id()
    output_root = Path(args.output_root)
    report_path = output_root / run_id / "reports" / "subtitle_candidate_report.md"
    ranges_path = output_root / run_id / "ranges_candidates_subtitle.txt"
    subtitle_dir = Path("subtitles")
    warnings: list[str] = [
        "subtitle_candidate_scan creates subtitle candidate ranges only",
        "automatic best cut is not implemented",
        "final mp4 is not created by subtitle_candidate_scan",
        "ranges.txt is not modified by subtitle_candidate_scan",
    ]
    failure_reasons: list[str] = []
    subtitle_file, discovery_warnings = discover_subtitle_file(subtitle_dir)
    warnings.extend(discovery_warnings)
    scan_result: dict[str, Any] = {
        "caption_count": 0,
        "first_timecode": "",
        "last_timecode": "",
        "parse_warning": "none",
    }
    candidates: list[dict[str, Any]] = []
    if subtitle_file is None:
        failure_reasons.append("subtitle file not found")
    else:
        try:
            scan_result = scan_srt(subtitle_file)
            captions, caption_warnings = srt_caption_ranges(subtitle_file)
            warnings.extend(caption_warnings)
            candidates = build_subtitle_candidates(captions, 35.0, 12)
            if not candidates:
                warnings.append("subtitle_candidate_scan produced no candidate ranges")
        except OSError as exc:
            failure_reasons.append(f"subtitle read failed: {exc}")

    write_subtitle_candidate_ranges(ranges_path, candidates)
    report = build_subtitle_candidate_report(
        args=args,
        run_id=run_id,
        ranges_path=ranges_path,
        subtitle_dir=subtitle_dir,
        subtitle_file=subtitle_file,
        scan_result=scan_result,
        candidates=candidates,
        warnings=warnings,
        failure_reasons=failure_reasons,
    )
    write_subtitle_candidate_report(report_path, report)
    print(f"subtitle_candidate_scan report written: {report_path}")
    print(f"subtitle_candidate_scan ranges written: {ranges_path}")
    if failure_reasons:
        print("subtitle_candidate_scan completed with failure_reason recorded")
        return 1
    print("subtitle_candidate_scan completed")
    return 0


def run_dry_run(args: argparse.Namespace) -> int:
    run_id = make_run_id()
    output_root = Path(args.output_root)
    report_path = output_root / run_id / "reports" / "edit_report.md"

    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    warnings: list[str] = []
    failure_reasons: list[str] = []

    if ffmpeg_path is None:
        warnings.append("ffmpeg missing")
    if ffprobe_path is None:
        failure_reasons.append("ffprobe missing")

    detected_paths, _, detected_files, ignored_files, discovery_warnings = prepare_inputs(args)
    warnings.extend(discovery_warnings)
    scale_warning = foreground_scale_warning(args)
    if scale_warning:
        warnings.append(scale_warning)
    crop_warning = pre_crop_warning(args)
    if crop_warning:
        warnings.append(crop_warning)
    add_input_failures(Path(args.input), detected_paths, failure_reasons)

    metadata: list[dict[str, Any]] = []
    if ffprobe_path and detected_paths:
        metadata, metadata_failures = collect_metadata(detected_paths, ffprobe_path)
        failure_reasons.extend(metadata_failures)

    total_duration = total_metadata_duration(metadata)
    if total_duration is not None and metadata and total_duration < args.duration:
        failure_reasons.append(
            "video duration insufficient: "
            f"available {total_duration:.3f}s, requested {args.duration}s"
        )

    planned_edit = build_dry_run_planned_edit(
        detected_files=detected_files,
        metadata=metadata,
        aspect=args.aspect,
        duration=args.duration,
        layout=args.layout,
        foreground_scale=args.foreground_scale,
        pre_crop=args.pre_crop,
    )
    report = base_report(
        args=args,
        run_id=run_id,
        report_path=report_path,
        detected_files=detected_files,
        ignored_files=ignored_files,
        metadata=metadata,
        planned_edit=planned_edit,
        warnings=warnings,
        failure_reasons=failure_reasons,
        changes_made="none",
    )
    report["output_settings"]["mp4_output_created"] = False

    write_report(report_path, report)
    print(f"dry_run report written: {report_path}")
    if failure_reasons:
        print("dry_run completed with failure_reason recorded")
        return 1
    print("dry_run completed")
    return 0


def apply_batch_screen_focus_defaults(args: argparse.Namespace) -> None:
    if args.layout_preset is None:
        args.layout_preset = "screen_focus"
    if args.layout == "fit_blur" and args.foreground_scale == "1.00":
        args.foreground_scale = "1.15"
    args.layout = effective_layout(args.aspect, args.layout)
    args.foreground_scale = effective_foreground_scale(
        args.aspect, args.layout, args.foreground_scale
    )


def batch_candidate_plan(
    *,
    candidates: list[dict[str, Any]],
    run_root: Path,
    args: argparse.Namespace,
    subtitle_guard: dict[str, Any],
) -> list[dict[str, Any]]:
    planned: list[dict[str, Any]] = []
    for rank, candidate in enumerate(candidates, 1):
        planned_output_folder = run_root / f"candidate_{rank:02d}"
        shifted_subtitle_path = planned_output_folder / "work" / "subtitle_cut_shifted.ass"
        reason = candidate.get("reason") or candidate.get("hook_text") or "not_available"
        planned.append(
            {
                "candidate_rank": rank,
                "source_candidate_id": candidate.get("source_candidate_id", "not_available"),
                "start_time": format_timecode(float(candidate["start"])),
                "end_time": format_timecode(float(candidate["end"])),
                "duration": candidate["duration"],
                "reason_or_hook_text": reason,
                "selection_source": candidate.get("selection_source", "not_available"),
                "planned_output_folder": str(planned_output_folder),
                "planned_range": candidate["range"],
                "candidate_ranges_path": str(planned_output_folder / "ranges.txt"),
                "planned_layout_preset": "screen_focus",
                "effective_layout": args.layout,
                "effective_foreground_scale": args.foreground_scale,
                "effective_pre_crop": args.pre_crop,
                "subtitle_burn_in_enabled": bool(args.burn_subtitles),
                "subtitle_source_file": args.subtitle_file,
                "subtitle_map_file": subtitle_guard.get("subtitle_map_file", ""),
                "subtitle_map_used": subtitle_guard.get("subtitle_map_used", False),
                "subtitle_map_input_key": subtitle_guard.get(
                    "subtitle_map_input_key", ""
                ),
                "subtitle_map_target_file": subtitle_guard.get(
                    "subtitle_map_target_file", ""
                ),
                "subtitle_map_target_exists": subtitle_guard.get(
                    "subtitle_map_target_exists", False
                ),
                "subtitle_source_mismatch_warning": subtitle_guard[
                    "subtitle_source_mismatch_warning"
                ],
                "subtitle_source_mismatch_blocked": subtitle_guard[
                    "subtitle_source_mismatch_blocked"
                ]
                and not args.dry_run,
                "subtitle_source_expected_input": subtitle_guard[
                    "subtitle_source_expected_input"
                ],
                "subtitle_style_summary": (
                    subtitle_style_summary() if args.burn_subtitles else {}
                ),
                "subtitle_center_align": (
                    SUBTITLE_CENTER_ALIGN if args.burn_subtitles else False
                ),
                "subtitle_position": (
                    subtitle_position_summary() if args.burn_subtitles else ""
                ),
                "subtitle_single_line_policy": (
                    SUBTITLE_SINGLE_LINE_POLICY if args.burn_subtitles else False
                ),
                "subtitle_deadzone_safe": (
                    SUBTITLE_DEADZONE_SAFE if args.burn_subtitles else False
                ),
                "subtitle_shifted_file": str(shifted_subtitle_path) if args.burn_subtitles else "",
                "subtitle_burn_in_planned": bool(args.burn_subtitles),
                "subtitle_burn_in_applied": False,
                "audio_gain": args.audio_gain,
                "audio_filter_planned": abs(float(args.audio_gain) - 1.0) > 0.000001,
                "audio_filter_applied": False,
                "mp4_output_created": False,
            }
        )
    return planned


def write_isolated_candidate_ranges(path: Path, candidate: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# isolated ranges for batch_screen_focus_roughcut",
        f"# source_candidate_id: {candidate.get('source_candidate_id', 'not_available')}",
        f"# selection_source: {candidate.get('selection_source', 'not_available')}",
        candidate["range"],
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_batch_candidate(
    *,
    args: argparse.Namespace,
    run_id: str,
    rank: int,
    candidate: dict[str, Any],
    candidate_dir: Path,
    detected_paths: list[Path],
    detected_files: list[dict[str, Any]],
    ignored_files: list[dict[str, Any]],
    metadata: list[dict[str, Any]],
    ffmpeg_path: str | None,
    warnings: list[str],
    subtitle_guard: dict[str, Any],
) -> dict[str, Any]:
    candidate_warnings = list(warnings)
    failure_reasons: list[str] = []
    ranges_path = candidate_dir / "ranges.txt"
    work_dir = candidate_dir / "work"
    shifted_subtitle_path = work_dir / "subtitle_cut_shifted.ass"
    final_dir = candidate_dir / "final"
    report_path = candidate_dir / "reports" / "edit_report.md"

    write_isolated_candidate_ranges(ranges_path, candidate)
    manual_ranges, range_failures = read_manual_ranges(ranges_path)
    failure_reasons.extend(range_failures)

    source_metadata = metadata[0] if len(metadata) == 1 else None
    if detected_paths and len(detected_paths) != 1:
        failure_reasons.append(
            f"batch_screen_focus_roughcut requires exactly one supported video file, found {len(detected_paths)}"
        )
    if source_metadata and manual_ranges:
        failure_reasons.extend(
            validate_manual_ranges(
                manual_ranges,
                source_metadata.get("duration"),
                args.duration,
            )
        )
    if ffmpeg_path is None:
        failure_reasons.append("ffmpeg missing")

    source_stem = safe_name(detected_paths[0].stem) if detected_paths else safe_name(Path(args.input).name)
    final_path = final_dir / manual_output_filename(source_stem, args.aspect, args.duration)
    if final_path.exists():
        failure_reasons.append(f"output file already exists: {final_path}")

    planned_edit = build_manual_planned_edit(
        source_metadata=source_metadata,
        manual_ranges=manual_ranges,
        target_duration=args.duration,
        aspect=args.aspect,
        layout=args.layout,
        foreground_scale=args.foreground_scale,
        pre_crop=args.pre_crop,
        output_path=final_path,
        media_output_created=False,
        subtitle_burn_in_enabled=bool(args.burn_subtitles),
        subtitle_source_file=args.subtitle_file,
        subtitle_shifted_file=str(shifted_subtitle_path) if args.burn_subtitles else "",
        subtitle_burn_in_planned=bool(args.burn_subtitles),
        subtitle_burn_in_applied=False,
        audio_gain=args.audio_gain,
        audio_filter_applied=False,
    )
    planned_edit.update(
        {
            "subtitle_map_file": subtitle_guard.get("subtitle_map_file", ""),
            "subtitle_map_used": subtitle_guard.get("subtitle_map_used", False),
            "subtitle_map_input_key": subtitle_guard.get("subtitle_map_input_key", ""),
            "subtitle_map_target_file": subtitle_guard.get(
                "subtitle_map_target_file", ""
            ),
            "subtitle_map_target_exists": subtitle_guard.get(
                "subtitle_map_target_exists", False
            ),
            "subtitle_source_mismatch_warning": subtitle_guard[
                "subtitle_source_mismatch_warning"
            ],
            "subtitle_source_mismatch_blocked": subtitle_guard[
                "subtitle_source_mismatch_blocked"
            ],
            "subtitle_source_expected_input": subtitle_guard[
                "subtitle_source_expected_input"
            ],
            "subtitle_source_file": subtitle_guard["subtitle_source_file"],
        }
    )
    changes_made: str | list[str] = ["isolated_ranges_created"]
    if not failure_reasons:
        concat_plan = planned_edit["concat_or_trim_plan"]
        if not concat_plan:
            failure_reasons.append("no usable manual ranges selected")
        else:
            final_dir.mkdir(parents=True, exist_ok=True)
            subtitle_path_for_filter: Path | None = None
            if args.burn_subtitles:
                subtitle_source = Path(args.subtitle_file)
                if not subtitle_source.exists():
                    failure_reasons.append(f"subtitle file missing: {subtitle_source}")
                elif not subtitle_source.is_file():
                    failure_reasons.append(f"subtitle path is not a file: {subtitle_source}")
                else:
                    first_clip = concat_plan[0]
                    subtitle_count, subtitle_warnings = write_shifted_srt_for_range(
                        subtitle_source,
                        shifted_subtitle_path,
                        float(first_clip["start"]),
                        float(first_clip["start"]) + float(first_clip["duration"]),
                    )
                    candidate_warnings.extend(subtitle_warnings)
                    planned_edit["subtitle_caption_count_in_range"] = subtitle_count
                    planned_edit["subtitle_shifted_file"] = str(shifted_subtitle_path)
                    subtitle_path_for_filter = shifted_subtitle_path
                    if subtitle_count <= 0:
                        failure_reasons.append("subtitle cut produced no captions for selected range")
            if failure_reasons:
                command = []
            else:
                command = build_ffmpeg_command(
                    ffmpeg_path=ffmpeg_path,
                    concat_plan=concat_plan,
                    metadata=metadata,
                    aspect=args.aspect,
                    layout=args.layout,
                    foreground_scale=args.foreground_scale,
                    pre_crop=args.pre_crop,
                    output_path=final_path,
                    subtitle_path=subtitle_path_for_filter,
                    audio_gain=args.audio_gain,
                )
            if command:
                planned_edit["subtitle_burn_in_applied"] = bool(subtitle_path_for_filter)
                planned_edit["audio_filter_applied"] = abs(float(args.audio_gain) - 1.0) > 0.000001
                planned_edit["ffmpeg_command"] = command
            if not command:
                planned_edit["ffmpeg_command"] = []
            if command:
                try:
                    result = subprocess.run(
                        command,
                        check=False,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                except OSError as exc:
                    failure_reasons.append(f"ffmpeg execution failed: {exc}")
                else:
                    if result.returncode != 0:
                        message = result.stderr.strip() or "unknown ffmpeg error"
                        failure_reasons.append(f"ffmpeg failed: {message}")
                    elif not final_path.exists():
                        failure_reasons.append("ffmpeg completed but final mp4 was not found")
                    else:
                        planned_edit["media_output_created"] = True
                        changes_made = [
                            "isolated_ranges_created",
                            "final_mp4_created",
                            "candidate_report_created",
                        ]
                        if args.burn_subtitles:
                            changes_made.append("shifted_subtitle_created")

    if failure_reasons and changes_made == ["isolated_ranges_created"]:
        planned_edit["media_output_created"] = False

    report = base_report(
        args=args,
        run_id=run_id,
        report_path=report_path,
        detected_files=detected_files,
        ignored_files=ignored_files,
        metadata=metadata,
        planned_edit=planned_edit,
        warnings=candidate_warnings,
        failure_reasons=failure_reasons,
        changes_made=changes_made,
    )
    report["output_settings"].update(
        {
            "candidate_rank": rank,
            "source_candidate_id": candidate.get("source_candidate_id"),
            "ranges_path": str(ranges_path),
            "output_name": final_path.name,
            "final_path": str(final_path),
            "mp4_output_created": planned_edit["media_output_created"],
            "subtitle_burn_in_enabled": bool(args.burn_subtitles),
            "subtitle_source_file": args.subtitle_file,
            "subtitle_map_file": subtitle_guard.get("subtitle_map_file", ""),
            "subtitle_map_used": subtitle_guard.get("subtitle_map_used", False),
            "subtitle_map_input_key": subtitle_guard.get("subtitle_map_input_key", ""),
            "subtitle_map_target_file": subtitle_guard.get(
                "subtitle_map_target_file", ""
            ),
            "subtitle_map_target_exists": subtitle_guard.get(
                "subtitle_map_target_exists", False
            ),
            "subtitle_source_mismatch_warning": subtitle_guard[
                "subtitle_source_mismatch_warning"
            ],
            "subtitle_source_mismatch_blocked": subtitle_guard[
                "subtitle_source_mismatch_blocked"
            ],
            "subtitle_source_expected_input": subtitle_guard[
                "subtitle_source_expected_input"
            ],
            "subtitle_style_summary": (
                subtitle_style_summary() if args.burn_subtitles else {}
            ),
            "subtitle_center_align": (
                SUBTITLE_CENTER_ALIGN if args.burn_subtitles else False
            ),
            "subtitle_position": (
                subtitle_position_summary() if args.burn_subtitles else ""
            ),
            "subtitle_single_line_policy": (
                SUBTITLE_SINGLE_LINE_POLICY if args.burn_subtitles else False
            ),
            "subtitle_deadzone_safe": (
                SUBTITLE_DEADZONE_SAFE if args.burn_subtitles else False
            ),
            "subtitle_shifted_file": str(shifted_subtitle_path) if args.burn_subtitles else "",
            "subtitle_burn_in_planned": bool(args.burn_subtitles),
            "subtitle_burn_in_applied": planned_edit.get("subtitle_burn_in_applied", False),
            "audio_gain": args.audio_gain,
            "audio_filter_applied": planned_edit.get("audio_filter_applied", False),
        }
    )
    report.update(subtitle_report_summary(Path("subtitles")))
    write_manual_cut_report(report_path, report)
    return {
        "candidate_report_path": str(report_path),
        "candidate_ranges_path": str(ranges_path),
        "generated_mp4_path": str(final_path),
        "mp4_output_created": planned_edit["media_output_created"],
        "subtitle_shifted_file": str(shifted_subtitle_path) if args.burn_subtitles else "",
        "subtitle_map_file": subtitle_guard.get("subtitle_map_file", ""),
        "subtitle_map_used": subtitle_guard.get("subtitle_map_used", False),
        "subtitle_map_input_key": subtitle_guard.get("subtitle_map_input_key", ""),
        "subtitle_map_target_file": subtitle_guard.get("subtitle_map_target_file", ""),
        "subtitle_map_target_exists": subtitle_guard.get(
            "subtitle_map_target_exists", False
        ),
        "subtitle_source_mismatch_warning": subtitle_guard[
            "subtitle_source_mismatch_warning"
        ],
        "subtitle_source_mismatch_blocked": subtitle_guard[
            "subtitle_source_mismatch_blocked"
        ],
        "subtitle_source_expected_input": subtitle_guard[
            "subtitle_source_expected_input"
        ],
        "subtitle_burn_in_applied": planned_edit.get("subtitle_burn_in_applied", False),
        "audio_filter_applied": planned_edit.get("audio_filter_applied", False),
        "failure_reason": failure_reasons or "none",
    }


def run_batch_screen_focus_roughcut(args: argparse.Namespace) -> int:
    apply_batch_screen_focus_defaults(args)
    run_id = make_run_id()
    output_root = Path(args.output_root)
    run_root = output_root / run_id
    report_path = run_root / "reports" / "batch_summary.md"
    candidate_source = Path(args.candidate_source) if args.candidate_source else None
    warnings: list[str] = []
    failure_reasons: list[str] = []

    detected_paths, _, detected_files, ignored_files, discovery_warnings = prepare_inputs(
        args, MANUAL_CUT_VIDEO_EXTENSIONS
    )
    warnings.extend(discovery_warnings)
    scale_warning = foreground_scale_warning(args)
    if scale_warning:
        warnings.append(scale_warning)
    crop_warning = pre_crop_warning(args)
    if crop_warning:
        warnings.append(crop_warning)
    selected_paths, selection_warnings = select_manual_cut_source(detected_paths)
    warnings.extend(selection_warnings)
    add_input_failures(Path(args.input), detected_paths, failure_reasons)
    if args.top_n < 1:
        failure_reasons.append("top-n must be 1 or greater")
    requested_top_n = args.top_n
    resolved_top_n = min(max(args.top_n, 0), 5)
    if args.top_n > 5:
        warnings.append("top-n capped at v0.7 max_n=5")

    source_candidates: list[dict[str, Any]] = []
    if candidate_source is None:
        failure_reasons.append("candidate-source is required for batch_screen_focus_roughcut")
    elif not candidate_source.exists():
        failure_reasons.append(f"candidate-source missing: {candidate_source}")
    elif not candidate_source.is_file():
        failure_reasons.append(f"candidate-source is not a file: {candidate_source}")
    else:
        source_candidates = read_candidate_ranges_file(
            candidate_source, "batch_screen_focus_candidate", 1, warnings
        )
        if not source_candidates:
            failure_reasons.append("candidate-source produced no usable ranges")

    input_video = str(selected_paths[0]) if selected_paths else str(Path(args.input))
    subtitle_map = subtitle_map_resolution(
        input_video, args.subtitle_file, bool(args.burn_subtitles)
    )
    if subtitle_map.get("subtitle_map_warning"):
        warnings.append(subtitle_map["subtitle_map_warning"])
    if subtitle_map["subtitle_map_used"]:
        args.subtitle_file = subtitle_map["subtitle_source_file"]
        subtitle_guard = {
            **subtitle_source_guard(input_video, args.subtitle_file, False),
            **subtitle_map,
        }
        if not subtitle_map["subtitle_map_target_exists"]:
            failure_reasons.append("subtitle mapped file missing")
    else:
        subtitle_guard = {
            **subtitle_map,
            **subtitle_source_guard(
                input_video, args.subtitle_file, bool(args.burn_subtitles)
            ),
        }
    if subtitle_guard["subtitle_source_mismatch_warning"]:
        warnings.append(
            "subtitle source mismatch: "
            f"{args.subtitle_file} is expected for "
            f"{subtitle_guard['subtitle_source_expected_input']}, not {Path(input_video).name}"
        )
        if not args.dry_run:
            failure_reasons.append("subtitle source mismatch")

    selected_candidates = source_candidates[:resolved_top_n]
    planned_candidates = batch_candidate_plan(
        candidates=selected_candidates,
        run_root=run_root,
        args=args,
        subtitle_guard=subtitle_guard,
    )
    selected_detected_files = [file_record(path) for path in selected_paths]
    metadata: list[dict[str, Any]] = []
    ffmpeg_path: str | None = None
    if not args.dry_run:
        ffmpeg_path = shutil.which("ffmpeg")
        ffprobe_path = shutil.which("ffprobe")
        if ffmpeg_path is None:
            failure_reasons.append("ffmpeg missing")
        if ffprobe_path is None:
            failure_reasons.append("ffprobe missing")
        if ffprobe_path and selected_paths:
            metadata, metadata_failures = collect_metadata(selected_paths, ffprobe_path)
            failure_reasons.extend(metadata_failures)

    if not args.dry_run and not failure_reasons:
        for index, candidate in enumerate(selected_candidates, 1):
            candidate_dir = run_root / f"candidate_{index:02d}"
            render_result = render_batch_candidate(
                args=args,
                run_id=run_id,
                rank=index,
                candidate=candidate,
                candidate_dir=candidate_dir,
                detected_paths=selected_paths,
                detected_files=selected_detected_files,
                ignored_files=ignored_files,
                metadata=metadata,
                ffmpeg_path=ffmpeg_path,
                warnings=warnings,
                subtitle_guard=subtitle_guard,
            )
            planned_candidates[index - 1].update(render_result)
            if render_result["failure_reason"] != "none":
                failure_reasons.append(
                    f"candidate_{index:02d} failed: {render_result['failure_reason']}"
                )

    mp4_output_created = bool(planned_candidates) and all(
        bool(candidate.get("mp4_output_created")) for candidate in planned_candidates
    )
    changes_made: list[str] = ["batch_summary_report_created"]
    if not args.dry_run:
        changes_made.append("candidate_reports_created")
        changes_made.append("isolated_candidate_ranges_created")
        if mp4_output_created:
            changes_made.append("candidate_mp4_created")
    report = {
        "tool_version": TOOL_VERSION,
        "run_id": run_id,
        "mode": "batch_screen_focus_roughcut",
        "dry_run": args.dry_run,
        "input_mode": input_mode(Path(args.input)),
        "input_video": input_video,
        "candidate_source": str(candidate_source) if candidate_source else "",
        "requested_top_n": requested_top_n,
        "max_top_n": 5,
        "resolved_candidate_count": len(planned_candidates),
        "duration": args.duration,
        "aspect": args.aspect,
        "layout_preset": args.layout_preset,
        "effective_layout": args.layout,
        "effective_foreground_scale": args.foreground_scale,
        "effective_pre_crop": args.pre_crop,
        "subtitle_burn_in_enabled": bool(args.burn_subtitles),
        "subtitle_source_file": args.subtitle_file,
        "subtitle_map_file": subtitle_guard.get("subtitle_map_file", ""),
        "subtitle_map_used": subtitle_guard.get("subtitle_map_used", False),
        "subtitle_map_input_key": subtitle_guard.get("subtitle_map_input_key", ""),
        "subtitle_map_target_file": subtitle_guard.get("subtitle_map_target_file", ""),
        "subtitle_map_target_exists": subtitle_guard.get(
            "subtitle_map_target_exists", False
        ),
        "subtitle_source_mismatch_warning": subtitle_guard[
            "subtitle_source_mismatch_warning"
        ],
        "subtitle_source_mismatch_blocked": (
            subtitle_guard["subtitle_source_mismatch_blocked"] and not args.dry_run
        ),
        "subtitle_source_expected_input": subtitle_guard[
            "subtitle_source_expected_input"
        ],
        "subtitle_style_summary": subtitle_style_summary() if args.burn_subtitles else {},
        "subtitle_center_align": SUBTITLE_CENTER_ALIGN if args.burn_subtitles else False,
        "subtitle_position": subtitle_position_summary() if args.burn_subtitles else "",
        "subtitle_single_line_policy": SUBTITLE_SINGLE_LINE_POLICY if args.burn_subtitles else False,
        "subtitle_deadzone_safe": SUBTITLE_DEADZONE_SAFE if args.burn_subtitles else False,
        "subtitle_burn_in_planned": bool(args.burn_subtitles),
        "audio_gain": args.audio_gain,
        "audio_filter_planned": abs(float(args.audio_gain) - 1.0) > 0.000001,
        "candidates": planned_candidates,
        "ranges_txt_modified": False,
        "existing_outputs_modified": False,
        "mp4_output_created": mp4_output_created,
        "warnings": warnings,
        "failure_reason": failure_reasons or "none",
        "changes_made": changes_made,
    }
    write_batch_screen_focus_report(report_path, report)
    print(f"batch_screen_focus_roughcut report written: {report_path}")
    if failure_reasons:
        print("batch_screen_focus_roughcut completed with failure_reason recorded")
        return 1
    if args.dry_run:
        print("batch_screen_focus_roughcut dry-run completed")
    else:
        print("batch_screen_focus_roughcut completed")
    return 0


def run_multi_clip_join(args: argparse.Namespace) -> int:
    run_id = make_run_id()
    input_path = Path(args.input)
    output_root = Path(args.output_root)
    batch_name = safe_name(input_path.name)
    final_dir = output_root / run_id / "final"
    report_path = output_root / run_id / "reports" / "edit_report.md"
    final_path = final_dir / output_filename(batch_name, args.aspect, args.duration)

    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    warnings: list[str] = []
    failure_reasons: list[str] = []

    if ffmpeg_path is None:
        failure_reasons.append("ffmpeg missing")
    if ffprobe_path is None:
        failure_reasons.append("ffprobe missing")

    detected_paths, _, detected_files, ignored_files, discovery_warnings = prepare_inputs(args)
    warnings.extend(discovery_warnings)
    scale_warning = foreground_scale_warning(args)
    if scale_warning:
        warnings.append(scale_warning)
    crop_warning = pre_crop_warning(args)
    if crop_warning:
        warnings.append(crop_warning)
    add_input_failures(input_path, detected_paths, failure_reasons)

    metadata: list[dict[str, Any]] = []
    if ffprobe_path and detected_paths:
        metadata, metadata_failures = collect_metadata(detected_paths, ffprobe_path)
        failure_reasons.extend(metadata_failures)

    total_duration = total_metadata_duration(metadata)
    if total_duration is not None and metadata and total_duration < args.duration:
        failure_reasons.append(
            "video duration insufficient: "
            f"available {total_duration:.3f}s, requested {args.duration}s"
        )

    if final_path.exists():
        failure_reasons.append(f"output file already exists: {final_path}")

    planned_edit = build_multi_clip_planned_edit(
        metadata=metadata,
        target_duration=args.duration,
        aspect=args.aspect,
        layout=args.layout,
        foreground_scale=args.foreground_scale,
        pre_crop=args.pre_crop,
        output_path=final_path,
        media_output_created=False,
    )
    changes_made: str | list[str] = "none"
    if not failure_reasons:
        concat_plan = planned_edit["concat_or_trim_plan"]
        if not concat_plan:
            failure_reasons.append("no usable clips selected")
        else:
            final_dir.mkdir(parents=True, exist_ok=True)
            command = build_ffmpeg_command(
                ffmpeg_path=ffmpeg_path,
                concat_plan=concat_plan,
                metadata=metadata,
                aspect=args.aspect,
                layout=args.layout,
                foreground_scale=args.foreground_scale,
        pre_crop=args.pre_crop,
                output_path=final_path,
            )
            planned_edit["ffmpeg_command"] = command
            try:
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
            except OSError as exc:
                failure_reasons.append(f"ffmpeg execution failed: {exc}")
            else:
                if result.returncode != 0:
                    message = result.stderr.strip() or "unknown ffmpeg error"
                    failure_reasons.append(f"ffmpeg failed: {message}")
                elif not final_path.exists():
                    failure_reasons.append("ffmpeg completed but final mp4 was not found")
                else:
                    planned_edit["media_output_created"] = True
                    changes_made = ["final_mp4_created", "edit_report_created"]

    if failure_reasons and changes_made == "none":
        planned_edit["media_output_created"] = False

    report = base_report(
        args=args,
        run_id=run_id,
        report_path=report_path,
        detected_files=detected_files,
        ignored_files=ignored_files,
        metadata=metadata,
        planned_edit=planned_edit,
        warnings=warnings,
        failure_reasons=failure_reasons,
        changes_made=changes_made,
    )
    report["output_settings"].update(
        {
            "batch_name": batch_name,
            "output_name": final_path.name,
            "final_path": str(final_path),
            "mp4_output_created": planned_edit["media_output_created"],
        }
    )
    write_report(report_path, report)
    print(f"multi_clip_join report written: {report_path}")
    if failure_reasons:
        print("multi_clip_join failed; see edit_report.md")
        return 1
    print(f"multi_clip_join final mp4 written: {final_path}")
    return 0



def run_single_video_manual_cut(args: argparse.Namespace) -> int:
    run_id = make_run_id()
    input_path = Path(args.input)
    output_root = Path(args.output_root)
    final_dir = output_root / run_id / "final"
    report_path = output_root / run_id / "reports" / "edit_report.md"

    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    warnings: list[str] = []
    failure_reasons: list[str] = []

    if ffmpeg_path is None:
        failure_reasons.append("ffmpeg missing")
    if ffprobe_path is None:
        failure_reasons.append("ffprobe missing")
    if not args.ranges:
        failure_reasons.append("ranges file is required for single_video_manual_cut")

    detected_paths, _, detected_files, ignored_files, discovery_warnings = prepare_inputs(
        args, MANUAL_CUT_VIDEO_EXTENSIONS
    )
    warnings.extend(discovery_warnings)
    scale_warning = foreground_scale_warning(args)
    if scale_warning:
        warnings.append(scale_warning)
    crop_warning = pre_crop_warning(args)
    if crop_warning:
        warnings.append(crop_warning)
    add_input_failures(input_path, detected_paths, failure_reasons)
    detected_paths, selection_warnings = select_manual_cut_source(detected_paths)
    warnings.extend(selection_warnings)
    detected_files = [file_record(path) for path in detected_paths]
    if detected_paths and len(detected_paths) != 1:
        failure_reasons.append(
            f"single_video_manual_cut requires exactly one supported video file, found {len(detected_paths)}"
        )

    manual_ranges: list[dict[str, Any]] = []
    if args.ranges:
        manual_ranges, range_failures = read_manual_ranges(Path(args.ranges))
        failure_reasons.extend(range_failures)

    metadata: list[dict[str, Any]] = []
    if ffprobe_path and detected_paths:
        metadata, metadata_failures = collect_metadata(detected_paths, ffprobe_path)
        failure_reasons.extend(metadata_failures)

    source_metadata = metadata[0] if len(metadata) == 1 else None
    if source_metadata and manual_ranges:
        failure_reasons.extend(
            validate_manual_ranges(
                manual_ranges,
                source_metadata.get("duration"),
                args.duration,
            )
        )

    source_stem = safe_name(detected_paths[0].stem) if detected_paths else safe_name(input_path.name)
    final_path = final_dir / manual_output_filename(source_stem, args.aspect, args.duration)
    if final_path.exists():
        failure_reasons.append(f"output file already exists: {final_path}")

    planned_edit = build_manual_planned_edit(
        source_metadata=source_metadata,
        manual_ranges=manual_ranges,
        target_duration=args.duration,
        aspect=args.aspect,
        layout=args.layout,
        foreground_scale=args.foreground_scale,
        pre_crop=args.pre_crop,
        output_path=final_path,
        media_output_created=False,
    )
    changes_made: str | list[str] = "none"
    if not failure_reasons:
        concat_plan = planned_edit["concat_or_trim_plan"]
        if not concat_plan:
            failure_reasons.append("no usable manual ranges selected")
        else:
            final_dir.mkdir(parents=True, exist_ok=True)
            command = build_ffmpeg_command(
                ffmpeg_path=ffmpeg_path,
                concat_plan=concat_plan,
                metadata=metadata,
                aspect=args.aspect,
                layout=args.layout,
                foreground_scale=args.foreground_scale,
        pre_crop=args.pre_crop,
                output_path=final_path,
            )
            planned_edit["ffmpeg_command"] = command
            try:
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
            except OSError as exc:
                failure_reasons.append(f"ffmpeg execution failed: {exc}")
            else:
                if result.returncode != 0:
                    message = result.stderr.strip() or "unknown ffmpeg error"
                    failure_reasons.append(f"ffmpeg failed: {message}")
                elif not final_path.exists():
                    failure_reasons.append("ffmpeg completed but final mp4 was not found")
                else:
                    planned_edit["media_output_created"] = True
                    changes_made = ["final_mp4_created", "edit_report_created"]

    if failure_reasons and changes_made == "none":
        planned_edit["media_output_created"] = False

    report = base_report(
        args=args,
        run_id=run_id,
        report_path=report_path,
        detected_files=detected_files,
        ignored_files=ignored_files,
        metadata=metadata,
        planned_edit=planned_edit,
        warnings=warnings,
        failure_reasons=failure_reasons,
        changes_made=changes_made,
    )
    report["output_settings"].update(
        {
            "ranges_path": args.ranges,
            "output_name": final_path.name,
            "final_path": str(final_path),
            "mp4_output_created": planned_edit["media_output_created"],
        }
    )
    report.update(subtitle_report_summary(Path("subtitles")))
    write_manual_cut_report(report_path, report)
    print(f"single_video_manual_cut report written: {report_path}")
    if failure_reasons:
        print("single_video_manual_cut failed; see edit_report.md")
        return 1
    print(f"single_video_manual_cut final mp4 written: {final_path}")
    return 0

def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.mode == "dry_run":
        return run_dry_run(args)
    if args.mode == "candidate_scan":
        return run_candidate_scan(args)
    if args.mode == "subtitle_scan":
        return run_subtitle_scan(args)
    if args.mode == "subtitle_candidate_scan":
        return run_subtitle_candidate_scan(args)
    if args.mode == "batch_screen_focus_roughcut":
        return run_batch_screen_focus_roughcut(args)
    if args.mode == "audio_peak_scan":
        return run_audio_peak_scan(args)
    if args.mode == "scene_change_scan":
        return run_scene_change_scan(args)
    if args.mode == "thumbnail_sample":
        return run_thumbnail_sample(args)
    if args.mode == "combined_candidates":
        return run_combined_candidates(args)
    if args.mode == "apply_candidate_ranges":
        return run_apply_candidate_ranges(args)
    if args.mode == "multi_clip_join":
        return run_multi_clip_join(args)
    if args.mode == "single_video_manual_cut":
        return run_single_video_manual_cut(args)
    print(f"mode '{args.mode}' not implemented yet")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())





























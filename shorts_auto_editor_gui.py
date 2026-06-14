#!/usr/bin/env python3
"""Minimal Tkinter launcher for shorts_auto_editor.

The GUI is intentionally a thin wrapper around the existing CLI. It does not
edit media directly and only runs commands after the user clicks a button.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent


def _prepare_tk_runtime_workaround() -> None:
    if os.environ.get("TCL_LIBRARY") and os.environ.get("TK_LIBRARY"):
        return

    source_tcl = Path(sys.prefix) / "tcl"
    source_tcl86 = source_tcl / "tcl8.6"
    source_tk86 = source_tcl / "tk8.6"
    if not (source_tcl86 / "init.tcl").exists() or not (source_tk86 / "tk.tcl").exists():
        return
    if source_tcl.as_posix().isascii():
        return

    local_runtime = APP_DIR / ".tk_runtime_ascii"
    local_tcl86 = local_runtime / "tcl8.6"
    local_tk86 = local_runtime / "tk8.6"
    try:
        if not (local_tcl86 / "init.tcl").exists():
            shutil.copytree(source_tcl86, local_tcl86, dirs_exist_ok=True)
        if not (local_tk86 / "tk.tcl").exists():
            shutil.copytree(source_tk86, local_tk86, dirs_exist_ok=True)
    except OSError:
        return

    os.environ["TCL_LIBRARY"] = str(local_tcl86)
    os.environ["TK_LIBRARY"] = str(local_tk86)


_prepare_tk_runtime_workaround()

import tkinter as tk
from tkinter import messagebox, scrolledtext
from typing import Callable


CLI_SCRIPT = APP_DIR / "shorts_auto_editor.py"
UI_FONT = ("맑은 고딕", 10)
UI_FONT_BOLD = ("맑은 고딕", 10, "bold")
SMALL_FONT = ("맑은 고딕", 9)
SMALL_FONT_BOLD = ("맑은 고딕", 9, "bold")
TITLE_FONT = ("맑은 고딕", 19, "bold")
SECTION_FONT = ("맑은 고딕", 11, "bold")
BUTTON_FONT = ("맑은 고딕", 10, "bold")
LOG_FONT = ("Consolas", 9)


def format_tool_discovery(tool_name: str) -> str:
    tool_path = shutil.which(tool_name)
    if tool_path:
        return f"{tool_name}=found:{tool_path}"
    ffmpeg_bin = os.environ.get("FFMPEG_BIN", "")
    if os.environ.get("FFMPEG_BIN_READY") == "1" and ffmpeg_bin:
        executable = tool_name if tool_name.lower().endswith(".exe") else f"{tool_name}.exe"
        return f"{tool_name}=found:{Path(ffmpeg_bin) / executable} (via FFMPEG_BIN)"
    return f"{tool_name}=missing"


DEFAULTS = {
    "input": "input",
    "candidate_source": r"candidates\selected_candidates.json",
    "output_root": "output",
    "top_n": "1",
    "duration": "35",
    "aspect": "9:16",
    "layout_preset": "screen_focus",
    "burn_subtitles": "0",
    "subtitle_file": r"subtitles\your_subtitle.srt",
    "audio_gain": "1.0",
}


CANDIDATE_DEFAULTS = {
    "rank": "1",
    "source_candidate_id": "1",
    "start": "00:32:42.800",
    "end": "00:33:17.800",
    "duration": "35",
    "reason": "시작부터 반응이 좋아 쇼츠 훅이 강한 구간",
    "selection_source": "human_review",
    "layout_preset": "screen_focus",
}

COLORS = {
    "primary_red": "#e60012",
    "signal_orange": "#ff7a1a",
    "amber": "#ffd166",
    "canvas": "#f2f5fa",
    "canvas_soft": "#f0f5ff",
    "panel": "#ffffff",
    "panel_deep": "#edf4ff",
    "panel_line": "#c8d3e6",
    "summary": "#f8fbff",
    "button_muted": "#1f2d46",
    "chrome_indigo": "#243354",
    "carbon_navy": "#111827",
    "platinum": "#e5e7eb",
    "surface_white": "#ffffff",
    "ink": "#111827",
    "muted_text": "#243044",
    "status_chip": "#ffefad",
    "success_chip": "#dff7e8",
}


class ShortsAutoEditorGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Shorts Auto Editor")
        self.geometry("1180x960")
        self.minsize(1080, 860)
        self.configure(bg=COLORS["canvas"])
        self.option_add("*Font", UI_FONT)
        self.option_add("*Menu.Font", UI_FONT)
        self.option_add("*Entry.Font", UI_FONT)
        self.option_add("*Button.Font", BUTTON_FONT)
        self._buttons: list[tk.Button] = []
        self.vars = {
            key: tk.StringVar(value=value) for key, value in DEFAULTS.items()
        }
        self.candidate_vars = {
            key: tk.StringVar(value=value)
            for key, value in CANDIDATE_DEFAULTS.items()
        }
        self.stored_candidate_var = tk.StringVar(value="")
        self.stored_candidate_status_var = tk.StringVar(value="불러온 구간 없음")
        self.simple_status_var = tk.StringVar(value="준비됨 - 만들 구간을 선택하고 미리 점검하세요.")
        self.recent_mp4_label_var = tk.StringVar(value="최근 완성 영상: 아직 없음")
        self.recent_folder_label_var = tk.StringVar(value="최근 작업: 아직 없음")
        self.advanced_visible = False
        self.advanced_toggle_text = tk.StringVar(value="고급 설정 열기")
        self.log_visible = False
        self.log_toggle_text = tk.StringVar(value="상세 로그 보기")
        self.advanced_tools_frame: tk.LabelFrame | None = None
        self.log_frame: tk.LabelFrame | None = None
        self.stored_candidate_labels: list[str] = []
        self.stored_candidates: list[dict[str, object]] = []
        self.recent_mp4_path: Path | None = None
        self.recent_run_dir: Path | None = None
        self.recent_batch_summary_path: Path | None = None
        self.recent_candidate_report_path: Path | None = None
        self._build_ui()
        self.log(
            "준비됨. 미리 점검하기는 MP4를 만들지 않습니다. 최종 쇼츠 만들기는 확인창을 거칩니다."
        )
        self.refresh_recent_results_from_fallback(log_success=True)
        self.update_recent_result_labels()
        self.auto_refresh_stored_candidates()

    def _build_ui(self) -> None:
        root = tk.Frame(self, padx=20, pady=16, bg=COLORS["canvas"])
        root.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(root, bg=COLORS["surface_white"], padx=20, pady=10, bd=1, relief=tk.SOLID)
        header.pack(fill=tk.X)
        header_text = tk.Frame(header, bg=COLORS["surface_white"])
        header_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            header_text,
            text="Shorts Auto Editor",
            bg=COLORS["surface_white"],
            fg=COLORS["carbon_navy"],
            font=TITLE_FONT,
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            header_text,
            text="긴 영상에서 원하는 구간만 골라 세로 쇼츠로 만듭니다.",
            bg=COLORS["surface_white"],
            fg=COLORS["muted_text"],
            font=SMALL_FONT_BOLD,
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            header,
            textvariable=self.simple_status_var,
            bg=COLORS["status_chip"],
            fg=COLORS["carbon_navy"],
            font=UI_FONT_BOLD,
            padx=14,
            pady=4,
            bd=2,
            relief=tk.RAISED,
        ).pack(side=tk.RIGHT)

        step1 = self._section(root, "STEP 1  원본 영상")
        step1.pack(fill=tk.X, pady=(10, 0))
        tk.Label(
            step1,
            text="원본 영상 폴더",
            width=16,
            anchor="w",
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            font=UI_FONT_BOLD,
        ).grid(row=0, column=0, sticky="w", pady=5)
        tk.Entry(step1, textvariable=self.vars["input"], font=UI_FONT).grid(
            row=0, column=1, sticky="ew", pady=5, ipady=3
        )
        tk.Label(
            step1,
            text="기본값: input",
            bg=COLORS["panel"],
            fg=COLORS["chrome_indigo"],
            anchor="w",
            font=SMALL_FONT_BOLD,
        ).grid(row=0, column=2, sticky="w", padx=(10, 0))
        step1.columnconfigure(1, weight=1)

        step2 = self._section(root, "STEP 2  쇼츠 구간")
        step2.pack(fill=tk.X, pady=(10, 0))

        candidate_picker = tk.Frame(step2, bg=COLORS["panel_deep"], padx=14, pady=7, bd=1, relief=tk.SOLID)
        candidate_picker.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            candidate_picker,
            text="만들 구간 선택",
            anchor="w",
            bg=COLORS["panel_deep"],
            fg=COLORS["carbon_navy"],
            font=UI_FONT_BOLD,
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.stored_candidate_menu = tk.OptionMenu(
            candidate_picker, self.stored_candidate_var, ""
        )
        self.stored_candidate_menu.configure(
            width=58,
            bg=COLORS["platinum"],
            fg=COLORS["ink"],
            activebackground=COLORS["canvas_soft"],
            font=SMALL_FONT_BOLD,
        )
        self.stored_candidate_menu.pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(
            candidate_picker,
            textvariable=self.stored_candidate_status_var,
            width=22,
            anchor="w",
            bg=COLORS["button_muted"],
            fg=COLORS["surface_white"],
            font=SMALL_FONT_BOLD,
            padx=8,
            pady=3,
        ).pack(side=tk.LEFT, padx=(0, 8))
        self._add_button(
            candidate_picker,
            "구간 새로고침",
            self.refresh_stored_candidates,
        ).pack(side=tk.LEFT)

        candidate_summary = tk.Frame(step2, bg=COLORS["summary"], padx=12, pady=8, bd=1, relief=tk.SOLID)
        candidate_summary.grid(row=1, column=0, sticky="ew")

        simple_candidate_rows = [
            ("시작 시간", "start"),
            ("끝 시간", "end"),
            ("길이", "duration"),
            ("후보 설명", "reason"),
        ]
        for row_index, (label, key) in enumerate(simple_candidate_rows):
            tk.Label(
                candidate_summary,
                text=label,
                width=12,
                anchor="w",
                bg=COLORS["summary"],
                fg=COLORS["chrome_indigo"],
                font=SMALL_FONT_BOLD,
            ).grid(row=row_index, column=0, sticky="w", pady=4, padx=(0, 8))
            entry = tk.Entry(
                candidate_summary,
                textvariable=self.candidate_vars[key],
                font=UI_FONT,
                relief=tk.SOLID,
                bd=1,
            )
            entry.grid(row=row_index, column=1, sticky="ew", pady=4, ipady=3)
        step2.columnconfigure(0, weight=1)
        candidate_summary.columnconfigure(1, weight=1)

        step3 = self._section(root, "STEP 3  미리 점검")
        step3.pack(fill=tk.X, pady=(10, 0))
        self._add_button(
            step3, "미리 점검하기", self.run_dry_run, kind="primary"
        ).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=2)
        tk.Label(
            step3,
            text="MP4를 만들기 전에 후보 구간과 설정을 안전하게 확인합니다.",
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            anchor="w",
            font=UI_FONT,
        ).grid(row=0, column=1, sticky="ew", pady=4)
        step3.columnconfigure(1, weight=1)

        step4 = self._section(root, "STEP 4  쇼츠 만들기")
        step4.pack(fill=tk.X, pady=(10, 0))
        self._add_button(
            step4, "최종 쇼츠 만들기", self.run_mp4, kind="danger"
        ).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=2)
        tk.Label(
            step4,
            text="확인창을 거친 뒤 output 폴더 아래에 실제 MP4를 만듭니다. 먼저 미리 점검하기를 권장합니다.",
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            anchor="w",
            font=UI_FONT,
        ).grid(row=0, column=1, sticky="ew", pady=4)
        step4.columnconfigure(1, weight=1)

        step5 = self._section(root, "STEP 5  결과 확인")
        step5.pack(fill=tk.X, pady=(10, 0))
        tk.Label(
            step5,
            text="쇼츠 생성 후 완성 영상과 결과 폴더를 여기서 확인하세요. 미리 점검만 한 상태에서는 완성 영상이 없을 수 있습니다.",
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            anchor="w",
            font=UI_FONT,
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self._add_button(
            step5, "완성 영상 열기", self.open_recent_mp4, kind="result"
        ).grid(
            row=1, column=0, sticky="ew", padx=(0, 8), pady=3, ipady=5
        )
        self._add_button(
            step5, "결과 폴더 열기", self.open_recent_result_folder, kind="result"
        ).grid(
            row=1, column=1, sticky="ew", padx=8, pady=3, ipady=5
        )
        result_status = tk.Frame(step5, bg=COLORS["panel"])
        result_status.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        tk.Label(
            result_status,
            textvariable=self.recent_mp4_label_var,
            bg=COLORS["platinum"],
            fg=COLORS["ink"],
            anchor="w",
            padx=8,
            pady=3,
            font=SMALL_FONT,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Label(
            result_status,
            textvariable=self.recent_folder_label_var,
            bg=COLORS["platinum"],
            fg=COLORS["ink"],
            anchor="w",
            padx=8,
            pady=3,
            font=SMALL_FONT,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        for index in range(2):
            step5.columnconfigure(index, weight=1)

        advanced_toggle = tk.Frame(root, bg=COLORS["canvas"], pady=4)
        advanced_toggle.pack(fill=tk.X, pady=(10, 0))
        self._add_button(
            advanced_toggle,
            self.advanced_toggle_text.get(),
            self.toggle_advanced_tools,
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.advanced_toggle_button = self._buttons[-1]
        tk.Label(
            advanced_toggle,
            text="필요할 때만 후보 파일, JSON, 리포트 도구를 열어보세요.",
            bg=COLORS["canvas"],
            fg=COLORS["muted_text"],
            anchor="w",
            font=SMALL_FONT_BOLD,
        ).pack(side=tk.LEFT)

        log_toggle = tk.Frame(root, bg=COLORS["canvas"], pady=2)
        log_toggle.pack(fill=tk.X, pady=(2, 0))
        self._add_button(
            log_toggle,
            self.log_toggle_text.get(),
            self.toggle_log_tools,
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.log_toggle_button = self._buttons[-1]
        tk.Label(
            log_toggle,
            text="문제가 있을 때만 실행 로그를 펼쳐 확인하세요.",
            bg=COLORS["canvas"],
            fg=COLORS["muted_text"],
            anchor="w",
            font=SMALL_FONT_BOLD,
        ).pack(side=tk.LEFT)

        self.advanced_tools_frame = tk.LabelFrame(
            root,
            text="고급 설정 / 검증 도구",
            padx=10,
            pady=8,
            bg=COLORS["canvas_soft"],
            fg=COLORS["carbon_navy"],
            font=UI_FONT_BOLD,
        )

        fields = tk.Frame(self.advanced_tools_frame, bg=COLORS["canvas_soft"])
        fields.pack(fill=tk.X)

        rows = [
            ("candidate source path", "candidate_source"),
            ("output root", "output_root"),
            ("top_n", "top_n"),
            ("aspect", "aspect"),
            ("layout_preset", "layout_preset"),
            ("subtitle file", "subtitle_file"),
            ("audio gain", "audio_gain"),
        ]
        for row_index, (label, key) in enumerate(rows):
            tk.Label(
                fields,
                text=label,
                width=22,
                anchor="w",
                bg=COLORS["canvas_soft"],
                fg=COLORS["ink"],
                font=SMALL_FONT_BOLD,
            ).grid(
                row=row_index, column=0, sticky="w", pady=3
            )
            entry = tk.Entry(fields, textvariable=self.vars[key], font=UI_FONT)
            entry.grid(row=row_index, column=1, sticky="ew", pady=3)
        fields.columnconfigure(1, weight=1)

        tk.Checkbutton(
            fields,
            text="자막 입히기 (해제 시 자막 없음)",
            variable=self.vars["burn_subtitles"],
            onvalue="1",
            offvalue="0",
            bg=COLORS["canvas_soft"],
            fg=COLORS["ink"],
            activebackground=COLORS["canvas_soft"],
            activeforeground=COLORS["ink"],
            selectcolor=COLORS["surface_white"],
            font=UI_FONT,
            anchor="w",
        ).grid(row=len(rows), column=1, sticky="w", pady=(4, 2))
        tk.Label(
            fields,
            text=r"자막 ON 시 subtitles\subtitle_map.json 매핑을 우선 사용합니다.",
            bg=COLORS["canvas_soft"],
            fg=COLORS["muted_text"],
            font=SMALL_FONT,
            anchor="w",
        ).grid(row=len(rows) + 1, column=1, sticky="w", pady=(0, 4))

        candidate_input = tk.LabelFrame(
            self.advanced_tools_frame,
            text="후보 파일 세부 도구",
            padx=10,
            pady=8,
            bg=COLORS["canvas_soft"],
            fg=COLORS["carbon_navy"],
            font=SMALL_FONT_BOLD,
        )
        candidate_input.pack(fill=tk.X, pady=(10, 0))

        candidate_rows = [
            ("rank", "rank"),
            ("source_candidate_id", "source_candidate_id"),
            ("selection_source", "selection_source"),
            ("layout_preset", "layout_preset"),
        ]
        for row_index, (label, key) in enumerate(candidate_rows):
            column = 0 if row_index < 4 else 2
            row = row_index if row_index < 4 else row_index - 4
            tk.Label(
                candidate_input,
                text=label,
                width=22,
                anchor="w",
                bg=COLORS["canvas_soft"],
                fg=COLORS["ink"],
                font=SMALL_FONT_BOLD,
            ).grid(
                row=row, column=column, sticky="w", pady=3
            )
            entry = tk.Entry(
                candidate_input, textvariable=self.candidate_vars[key], font=UI_FONT
            )
            entry.grid(row=row, column=column + 1, sticky="ew", pady=3, padx=(0, 10))
        candidate_input.columnconfigure(1, weight=1)
        candidate_input.columnconfigure(3, weight=1)

        candidate_buttons = tk.Frame(candidate_input)
        candidate_buttons.configure(bg=COLORS["canvas_soft"])
        candidate_buttons.grid(row=4, column=0, columnspan=4, sticky="w", pady=(8, 4))
        self._add_button(
            candidate_buttons,
            "첫 후보 불러오기",
            self.load_selected_candidates,
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._add_button(
            candidate_buttons,
            "JSON 미리보기",
            self.preview_candidate_json,
        ).pack(side=tk.LEFT, padx=6)
        self._add_button(
            candidate_buttons,
            "후보 저장",
            self.save_selected_candidates,
        ).pack(side=tk.LEFT, padx=6)

        self.candidate_preview = scrolledtext.ScrolledText(
            candidate_input,
            wrap=tk.WORD,
            height=6,
            state=tk.DISABLED,
            bg="#f8fafc",
            fg=COLORS["ink"],
            insertbackground=COLORS["ink"],
            font=LOG_FONT,
        )
        self.candidate_preview.grid(
            row=5, column=0, columnspan=4, sticky="ew", pady=(4, 0)
        )
        self._set_stored_candidate_menu([])

        project_actions = tk.Frame(self.advanced_tools_frame, bg=COLORS["canvas_soft"])
        project_actions.pack(fill=tk.X, pady=(10, 10))

        self._add_button(
            project_actions, "점검 리포트 열기", self.open_recent_batch_summary
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._add_button(
            project_actions, "상세 리포트 열기", self.open_recent_candidate_report
        ).pack(side=tk.LEFT, padx=6)
        self._add_button(
            project_actions,
            "selected_candidates.json 열기",
            self.open_selected_candidates,
        ).pack(side=tk.LEFT, padx=6)
        self._add_button(project_actions, "README 열기", self.open_readme).pack(
            side=tk.LEFT, padx=6
        )
        self._add_button(project_actions, "종료", self.destroy).pack(side=tk.RIGHT)

        self.log_frame = tk.LabelFrame(
            root,
            text="상세 로그",
            padx=10,
            pady=8,
            bg=COLORS["panel"],
            fg=COLORS["carbon_navy"],
            font=SMALL_FONT_BOLD,
        )
        self.log_text = scrolledtext.ScrolledText(
            self.log_frame,
            wrap=tk.WORD,
            height=3,
            state=tk.DISABLED,
            bg="#f6f8fc",
            fg=COLORS["ink"],
            insertbackground=COLORS["ink"],
            font=LOG_FONT,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def toggle_advanced_tools(self) -> None:
        if self.advanced_tools_frame is None:
            return
        if self.advanced_visible:
            self.advanced_tools_frame.pack_forget()
            self.advanced_visible = False
            self.advanced_toggle_text.set("고급 설정 열기")
        else:
            self.advanced_tools_frame.pack(
                fill=tk.BOTH,
                expand=False,
                pady=(6, 0),
                before=self.log_toggle_button.master,
            )
            self.advanced_visible = True
            self.advanced_toggle_text.set("고급 설정 닫기")
        self.advanced_toggle_button.configure(text=self.advanced_toggle_text.get())

    def toggle_log_tools(self) -> None:
        if self.log_frame is None:
            return
        if self.log_visible:
            self.log_frame.pack_forget()
            self.log_visible = False
            self.log_toggle_text.set("상세 로그 보기")
        else:
            self.log_frame.pack(fill=tk.X, expand=False, pady=(6, 0))
            self.log_visible = True
            self.log_toggle_text.set("상세 로그 숨기기")
        self.log_toggle_button.configure(text=self.log_toggle_text.get())

    def _section(self, parent: tk.Widget, title: str) -> tk.LabelFrame:
        return tk.LabelFrame(
            parent,
            text=title,
            padx=14,
            pady=9,
            bg=COLORS["panel"],
            fg=COLORS["carbon_navy"],
            font=SECTION_FONT,
            bd=1,
            relief=tk.SOLID,
        )

    def _add_button(
        self,
        parent: tk.Widget,
        text: str,
        command: Callable[[], None],
        kind: str = "secondary",
    ) -> tk.Button:
        if kind == "primary":
            bg = COLORS["amber"]
            fg = COLORS["carbon_navy"]
        elif kind == "danger":
            bg = COLORS["signal_orange"]
            fg = COLORS["carbon_navy"]
        elif kind == "result":
            bg = COLORS["button_muted"]
            fg = COLORS["surface_white"]
        else:
            bg = COLORS["chrome_indigo"]
            fg = COLORS["surface_white"]
        button_width = 18 if kind in ("primary", "danger", "result") else 0
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=COLORS["panel_deep"],
            activeforeground=COLORS["surface_white"],
            padx=14,
            pady=7,
            relief=tk.RAISED,
            bd=2,
            font=BUTTON_FONT,
            width=button_width,
        )
        self._buttons.append(button)
        return button

    def log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message.rstrip() + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def preview_log(self, message: str) -> None:
        self.candidate_preview.configure(state=tk.NORMAL)
        self.candidate_preview.delete("1.0", tk.END)
        self.candidate_preview.insert(tk.END, message.rstrip() + "\n")
        self.candidate_preview.configure(state=tk.DISABLED)

    def build_command(self, dry_run: bool) -> list[str]:
        command = [
            sys.executable,
            str(CLI_SCRIPT),
            "--mode",
            "batch_screen_focus_roughcut",
            "--input",
            self.vars["input"].get().strip(),
            "--candidate-source",
            self.vars["candidate_source"].get().strip(),
            "--top-n",
            self.vars["top_n"].get().strip(),
            "--output-root",
            self.vars["output_root"].get().strip(),
            "--duration",
            self.vars["duration"].get().strip(),
            "--aspect",
            self.vars["aspect"].get().strip(),
            "--layout-preset",
            self.vars["layout_preset"].get().strip(),
        ]
        subtitle_file = self.vars["subtitle_file"].get().strip()
        if self.vars["burn_subtitles"].get().strip() == "1":
            command.append("--burn-subtitles")
            if subtitle_file:
                command.extend(["--subtitle-file", subtitle_file])
        audio_gain = self.vars["audio_gain"].get().strip()
        if audio_gain:
            command.extend(["--audio-gain", audio_gain])
        if dry_run:
            command.append("--dry-run")
        return command

    def validate_common_inputs(self) -> bool:
        input_path = APP_DIR / self.vars["input"].get().strip()
        candidate_path = APP_DIR / self.vars["candidate_source"].get().strip()
        if not input_path.exists():
            messagebox.showerror("Missing input folder", f"Not found: {input_path}")
            self.log(f"ERROR: input folder not found: {input_path}")
            return False
        if not candidate_path.exists():
            messagebox.showerror(
                "Missing candidate source", f"Not found: {candidate_path}"
            )
            self.log(f"ERROR: candidate source not found: {candidate_path}")
            return False
        audio_gain = self.vars["audio_gain"].get().strip()
        try:
            if float(audio_gain) <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid audio gain", "오디오 증폭 값은 0보다 큰 숫자여야 합니다.")
            self.log(f"ERROR: invalid audio gain: {audio_gain}")
            return False
        if self.vars["burn_subtitles"].get().strip() == "1":
            subtitle_path = APP_DIR / self.vars["subtitle_file"].get().strip()
            if not subtitle_path.exists():
                messagebox.showerror("Missing subtitle file", f"Not found: {subtitle_path}")
                self.log(f"ERROR: subtitle file not found: {subtitle_path}")
                return False
        return True

    def build_candidate_json_text(self) -> str:
        candidate = self.validate_candidate_inputs()
        return json.dumps([candidate], ensure_ascii=False, indent=2)

    def validate_candidate_inputs(self) -> dict[str, object]:
        rank = self._parse_int_field("rank")
        source_candidate_id = self._parse_int_field("source_candidate_id")
        start = self._parse_timecode_field("start")
        end = self._parse_timecode_field("end")
        start_seconds = self._timecode_to_seconds(start)
        end_seconds = self._timecode_to_seconds(end)
        if end_seconds <= start_seconds:
            raise ValueError("end는 start보다 뒤여야 합니다.")

        duration = self._parse_number_field("duration")
        reason = self.candidate_vars["reason"].get().strip()
        if not reason:
            raise ValueError("reason은 비어 있을 수 없습니다.")
        selection_source = self.candidate_vars["selection_source"].get().strip()
        if not selection_source:
            raise ValueError("selection_source는 비어 있을 수 없습니다.")
        layout_preset = self.candidate_vars["layout_preset"].get().strip()
        if not layout_preset:
            raise ValueError("layout_preset은 비어 있을 수 없습니다.")
        if layout_preset != "screen_focus":
            self.log("WARNING: layout_preset 기본 권장값은 screen_focus입니다.")

        return {
            "rank": rank,
            "source_candidate_id": source_candidate_id,
            "start": start,
            "end": end,
            "duration": duration,
            "reason": reason,
            "selection_source": selection_source,
            "layout_preset": layout_preset,
        }

    def _parse_int_field(self, key: str) -> int:
        value = self.candidate_vars[key].get().strip()
        if not value:
            raise ValueError(f"{key}는 비어 있을 수 없습니다.")
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"{key}는 정수여야 합니다.") from exc

    def _parse_number_field(self, key: str) -> int | float:
        value = self.candidate_vars[key].get().strip()
        if not value:
            raise ValueError(f"{key}는 비어 있을 수 없습니다.")
        try:
            number = float(value)
        except ValueError as exc:
            raise ValueError(f"{key}는 숫자여야 합니다.") from exc
        return int(number) if number.is_integer() else number

    def _parse_timecode_field(self, key: str) -> str:
        value = self.candidate_vars[key].get().strip()
        if not re.fullmatch(r"\d{2}:\d{2}:\d{2}\.\d{3}", value):
            raise ValueError(f"{key}는 HH:MM:SS.mmm 형식이어야 합니다.")
        return value

    def _timecode_to_seconds(self, value: str) -> float:
        hours_text, minutes_text, seconds_text = value.split(":")
        return (
            int(hours_text) * 3600
            + int(minutes_text) * 60
            + float(seconds_text)
        )

    def preview_candidate_json(self) -> None:
        try:
            preview = self.build_candidate_json_text()
        except ValueError as exc:
            message = f"Candidate validation failed: {exc}"
            self.log(message)
            self.preview_log(message)
            messagebox.showerror("Candidate validation failed", str(exc))
            return
        self.preview_log(preview)
        self.log("Candidate JSON preview updated.")

    def save_selected_candidates(self) -> None:
        try:
            json_text = self.build_candidate_json_text()
        except ValueError as exc:
            message = f"Candidate validation failed: {exc}"
            self.log(message)
            self.preview_log(message)
            messagebox.showerror("Candidate validation failed", str(exc))
            return

        candidate_path = APP_DIR / self.vars["candidate_source"].get().strip()
        if not messagebox.askyesno(
            "Confirm candidate save",
            "기존 selected_candidates.json을 백업 후 새 후보로 덮어쓰겠습니까?",
        ):
            self.log("selected_candidates.json save cancelled by user.")
            return

        backup_path: Path | None = None
        try:
            candidate_path.parent.mkdir(parents=True, exist_ok=True)
            if candidate_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = (
                    candidate_path.parent
                    / f"selected_candidates.backup_{timestamp}.json"
                )
                shutil.copy2(candidate_path, backup_path)
            candidate_path.write_text(json_text + "\n", encoding="utf-8")
        except OSError as exc:
            self.log(f"ERROR: failed to save selected_candidates.json: {exc}")
            messagebox.showerror("Save failed", str(exc))
            return

        self.preview_log(json_text)
        self.log(f"saved selected_candidates.json: {candidate_path}")
        if backup_path:
            self.log(f"backup created: {backup_path}")
        self.log("next step: run Dry-run")
        self.refresh_stored_candidates()

    def refresh_stored_candidates(self) -> None:
        candidate_path = APP_DIR / self.vars["candidate_source"].get().strip()
        try:
            candidates = self._load_candidate_list(candidate_path)
        except ValueError as exc:
            self._set_stored_candidate_menu([])
            self._set_candidate_status_for_error(str(exc))
            self._show_load_error(str(exc))
            return

        self.stored_candidates = candidates
        labels = [
            self._format_candidate_label(index, candidate)
            for index, candidate in enumerate(candidates)
        ]
        self._set_stored_candidate_menu(labels)
        self._set_candidate_count_status(len(candidates))
        self.log(f"loaded candidate list: {candidate_path} ({len(candidates)} candidates)")

    def auto_refresh_stored_candidates(self) -> None:
        candidate_path = APP_DIR / self.vars["candidate_source"].get().strip()
        try:
            candidates = self._load_candidate_list(candidate_path)
        except ValueError as exc:
            self._set_stored_candidate_menu([])
            self._set_candidate_status_for_error(str(exc))
            self.log(f"candidate list auto refresh skipped: {exc}")
            return

        self.stored_candidates = candidates
        labels = [
            self._format_candidate_label(index, candidate)
            for index, candidate in enumerate(candidates)
        ]
        self._set_stored_candidate_menu(labels)
        self._set_candidate_count_status(len(candidates))
        self.log(f"auto refreshed candidate list: {candidate_path}")
        self.log(f"loaded candidate count: {len(candidates)}")

    def _set_stored_candidate_menu(self, labels: list[str]) -> None:
        self.stored_candidate_labels = labels
        menu = self.stored_candidate_menu["menu"]
        menu.delete(0, "end")
        if labels:
            for label in labels:
                menu.add_command(
                    label=label,
                    command=lambda value=label: self.select_stored_candidate(value),
                )
            self.stored_candidate_var.set(labels[0])
        else:
            self.stored_candidate_var.set("불러온 구간 없음")
            menu.add_command(label="불러온 구간 없음", command=lambda: None)

    def _set_candidate_count_status(self, count: int) -> None:
        if count == 0:
            self.stored_candidate_status_var.set("불러온 구간 없음")
            return
        if count == 1:
            self.stored_candidate_status_var.set("1개 구간 준비됨")
        else:
            self.stored_candidate_status_var.set(f"{count}개 구간 준비됨")

    def _set_candidate_status_for_error(self, message: str) -> None:
        if "failed to read" in message:
            self.stored_candidate_status_var.set("저장된 구간 없음")
        else:
            self.stored_candidate_status_var.set("구간 파일 확인 필요")

    def select_stored_candidate(self, label: str | None = None) -> None:
        selected_label = label or self.stored_candidate_var.get()
        if selected_label in ("", "No candidates loaded", "불러온 구간 없음"):
            self._show_load_error("no stored candidate is selected.")
            return
        try:
            index = self.stored_candidate_labels.index(selected_label)
        except ValueError:
            self._show_load_error("selected candidate is not in the loaded list.")
            return
        if index >= len(self.stored_candidates):
            self._show_load_error("selected candidate index is out of range.")
            return
        self.stored_candidate_var.set(selected_label)
        self._apply_candidate_to_fields(self.stored_candidates[index])
        source_candidate_id = self.candidate_vars["source_candidate_id"].get().strip()
        start = self.candidate_vars["start"].get().strip()
        end = self.candidate_vars["end"].get().strip()
        reason = self.candidate_vars["reason"].get().strip()
        self.log(
            f"selected candidate index={index}, source_candidate_id={source_candidate_id}"
        )
        self.log(f"selected candidate summary: start={start}, end={end}, reason={reason}")

    def load_selected_candidates(self) -> None:
        candidate_path = APP_DIR / self.vars["candidate_source"].get().strip()
        try:
            candidates = self._load_candidate_list(candidate_path)
        except ValueError as exc:
            self._show_load_error(str(exc))
            return

        self.stored_candidates = candidates
        self._set_stored_candidate_menu(
            [
                self._format_candidate_label(index, candidate)
                for index, candidate in enumerate(candidates)
            ]
        )
        self._apply_candidate_to_fields(candidates[0])

        start = self.candidate_vars["start"].get().strip()
        end = self.candidate_vars["end"].get().strip()
        reason = self.candidate_vars["reason"].get().strip()
        source_candidate_id = self.candidate_vars["source_candidate_id"].get().strip()
        self.log(f"loaded selected_candidates.json: {candidate_path}")
        self.log(
            "selected candidate index=0, "
            f"source_candidate_id={source_candidate_id}"
        )
        self.log(f"loaded candidate summary: start={start}, end={end}, reason={reason}")

    def _load_candidate_list(self, candidate_path: Path) -> list[dict[str, object]]:
        try:
            raw_text = candidate_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"failed to read selected_candidates.json: {exc}") from exc

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"failed to parse selected_candidates.json: {exc}") from exc

        if isinstance(data, list):
            if not data:
                raise ValueError("selected_candidates.json has no candidates.")
            raw_candidates = data
        elif isinstance(data, dict):
            raw_candidates = [data]
        else:
            raise ValueError(
                "selected_candidates.json must contain a candidate object or list."
            )

        candidates: list[dict[str, object]] = []
        for index, candidate in enumerate(raw_candidates):
            if not isinstance(candidate, dict):
                raise ValueError(f"candidate #{index + 1} is not a JSON object.")
            if not any(key in candidate for key in CANDIDATE_DEFAULTS):
                raise ValueError(
                    f"candidate #{index + 1} did not contain supported fields."
                )
            candidates.append(candidate)
        return candidates

    def _apply_candidate_to_fields(self, candidate: dict[str, object]) -> None:
        loaded_fields: list[str] = []
        for key in CANDIDATE_DEFAULTS:
            if key not in candidate or candidate[key] is None:
                continue
            self.candidate_vars[key].set(str(candidate[key]))
            loaded_fields.append(key)

        if not loaded_fields:
            raise ValueError("candidate did not contain supported fields.")

        try:
            preview = self.build_candidate_json_text()
        except ValueError as exc:
            self.preview_log(f"Loaded candidate needs review: {exc}")
        else:
            self.preview_log(preview)

    def _format_candidate_label(
        self, index: int, candidate: dict[str, object]
    ) -> str:
        source_id = str(candidate.get("source_candidate_id", index + 1))
        start = str(candidate.get("start", CANDIDATE_DEFAULTS["start"]))
        end = str(candidate.get("end", CANDIDATE_DEFAULTS["end"]))
        reason = str(candidate.get("reason", "")).replace("\n", " ").strip()
        if len(reason) > 24:
            reason = reason[:24] + "..."
        return f"#{source_id} | {start}-{end} | {reason}"

    def _show_load_error(self, message: str) -> None:
        self.log(f"ERROR: {message}")
        messagebox.showerror("Load selected_candidates.json failed", message)

    def run_dry_run(self) -> None:
        if not self.validate_common_inputs():
            return
        self.simple_status_var.set("미리 점검 중 - MP4는 아직 만들지 않습니다.")
        self.run_command(self.build_command(dry_run=True), "Dry-run")

    def run_mp4(self) -> None:
        if not self.validate_common_inputs():
            return
        if not messagebox.askyesno(
            "최종 쇼츠 만들기",
            "선택한 구간으로 실제 MP4 파일을 생성합니다. 먼저 미리 점검하기를 완료했다면 계속 진행하세요.",
        ):
            self.log("MP4 generation cancelled by user.")
            return
        self.simple_status_var.set("쇼츠 생성 중 - 완료되면 결과를 확인하세요.")
        self.run_command(self.build_command(dry_run=False), "MP4 generation")

    def run_command(self, command: list[str], label: str) -> None:
        self.set_buttons_enabled(False)
        self.log("")
        self.log(f"== {label} started ==")
        self.log("Command:")
        self.log(subprocess.list2cmdline(command))
        thread = threading.Thread(
            target=self._run_command_worker, args=(command, label), daemon=True
        )
        thread.start()

    def _run_command_worker(self, command: list[str], label: str) -> None:
        try:
            result = subprocess.run(
                command,
                cwd=APP_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except OSError as exc:
            self.after(0, self.log, f"ERROR: failed to start command: {exc}")
            self.after(0, self.set_buttons_enabled, True)
            return

        def finish() -> None:
            if result.stdout:
                self.log("stdout:")
                self.log(result.stdout)
            if result.stderr:
                self.log("stderr:")
                self.log(result.stderr)
            if result.returncode == 0:
                self.log(f"== {label} completed ==")
                if label == "Dry-run":
                    self.simple_status_var.set("미리 점검 완료 - 문제가 없으면 최종 쇼츠 만들기를 누르세요.")
                    self.log("미리 점검이 완료되었습니다. 문제가 없으면 최종 쇼츠 만들기를 눌러 MP4를 생성하세요.")
                    self.log("미리 점검 단계라 MP4는 아직 만들지 않았습니다.")
                elif label == "MP4 generation":
                    self.simple_status_var.set("쇼츠 생성 완료 - 완성 영상을 확인하세요.")
                    self.log("MP4 생성이 완료되었습니다. 완성 영상 열기 또는 결과 폴더 열기를 눌러 확인하세요.")
            else:
                self.log(f"== {label} failed with exit code {result.returncode} ==")
                self.simple_status_var.set("확인 필요 - 상세 로그를 확인하세요.")
            self.update_recent_results_from_stdout(result.stdout)
            self.refresh_recent_results_from_fallback(log_success=False)
            self.update_recent_result_labels()
            self.set_buttons_enabled(True)

        self.after(0, finish)

    def set_buttons_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for button in self._buttons:
            button.configure(state=state)

    def open_output(self) -> None:
        path = APP_DIR / self.vars["output_root"].get().strip()
        if not path.exists():
            self.log(f"output 폴더가 아직 없습니다: {path}")
            return
        self.open_path(path)

    def open_selected_candidates(self) -> None:
        path = APP_DIR / self.vars["candidate_source"].get().strip()
        if not path.exists():
            self.log(f"ERROR: selected_candidates.json not found: {path}")
            messagebox.showerror("Missing file", f"Not found: {path}")
            return
        self.open_path(path)

    def open_readme(self) -> None:
        path = APP_DIR / "README.md"
        if not path.exists():
            self.log(f"ERROR: README.md not found: {path}")
            messagebox.showerror("Missing file", f"Not found: {path}")
            return
        self.open_path(path)

    def update_recent_results_from_stdout(self, stdout: str) -> None:
        if not stdout:
            return

        for raw_path in self._extract_paths_from_stdout(stdout):
            path = self._resolve_output_path(raw_path)
            if path is None:
                continue
            if path.suffix.lower() == ".mp4" and path.exists():
                self.recent_mp4_path = path
                self.recent_run_dir = self._find_run_dir(path) or self.recent_run_dir
            elif path.name == "batch_summary.md" and path.exists():
                self.recent_batch_summary_path = path
                self.recent_run_dir = self._find_run_dir(path) or self.recent_run_dir
            elif path.name == "edit_report.md" and path.exists():
                self.recent_candidate_report_path = path
                self.recent_run_dir = self._find_run_dir(path) or self.recent_run_dir

    def refresh_recent_results_from_fallback(self, log_success: bool) -> None:
        output_root = APP_DIR / self.vars["output_root"].get().strip()
        run_dir = self._latest_run_dir(output_root)
        if run_dir is None:
            self.update_recent_result_labels()
            return

        self.recent_run_dir = run_dir
        if not self.recent_mp4_path or not self.recent_mp4_path.exists():
            self.recent_mp4_path = self._latest_file(
                run_dir, ("candidate_*/final/*.mp4", "final/*.mp4", "**/*.mp4")
            ) or self._latest_file(
                output_root,
                ("run_*/candidate_*/final/*.mp4", "run_*/final/*.mp4", "run_*/*.mp4"),
            )
        self.recent_batch_summary_path = (
            self.recent_batch_summary_path
            or self._existing_path(run_dir / "reports" / "batch_summary.md")
            or self._latest_file(run_dir, ("**/batch_summary.md",))
        )
        self.recent_candidate_report_path = (
            self.recent_candidate_report_path
            or self._latest_file(
                run_dir, ("candidate_*/reports/edit_report.md", "**/edit_report.md")
            )
        )
        if log_success:
            self.log(f"최근 결과 fallback 확인: {run_dir}")
            if self.recent_mp4_path:
                self.log(f"최근 MP4: {self.recent_mp4_path}")
            if self.recent_batch_summary_path:
                self.log(f"최근 batch summary: {self.recent_batch_summary_path}")
            if self.recent_candidate_report_path:
                self.log(f"최근 candidate report: {self.recent_candidate_report_path}")
        self.update_recent_result_labels()

    def update_recent_result_labels(self) -> None:
        mp4_name = "아직 없음"
        if self.recent_mp4_path and self.recent_mp4_path.exists():
            mp4_name = self.recent_mp4_path.name

        folder_name = "아직 없음"
        if self.recent_run_dir and self.recent_run_dir.exists():
            folder_name = self.recent_run_dir.name

        self.recent_mp4_label_var.set(f"최근 완성 영상: {mp4_name}")
        self.recent_folder_label_var.set(f"최근 작업: {folder_name}")

    def _extract_paths_from_stdout(self, stdout: str) -> list[str]:
        path_pattern = re.compile(
            r"(?P<path>(?:[A-Za-z]:\\|\.?\.?[/\\]|output[/\\])[^:\r\n]+?"
            r"(?:\.mp4|batch_summary\.md|edit_report\.md))",
            re.IGNORECASE,
        )
        return [match.group("path").strip().strip("\"'") for match in path_pattern.finditer(stdout)]

    def _resolve_output_path(self, raw_path: str) -> Path | None:
        path = Path(raw_path)
        if not path.is_absolute():
            path = APP_DIR / path
        try:
            resolved = path.resolve()
        except OSError:
            return None
        output_root = (APP_DIR / self.vars["output_root"].get().strip()).resolve()
        try:
            resolved.relative_to(output_root)
        except ValueError:
            return None
        return resolved

    def _latest_run_dir(self, output_root: Path) -> Path | None:
        if not output_root.exists():
            return None
        run_dirs = [
            path
            for path in output_root.glob("run_*")
            if path.is_dir() and path.parent == output_root
        ]
        if not run_dirs:
            return None
        return max(run_dirs, key=lambda path: path.stat().st_mtime)

    def _latest_file(self, root: Path, patterns: tuple[str, ...]) -> Path | None:
        for pattern in patterns:
            files = [path for path in root.glob(pattern) if path.is_file()]
            if files:
                return max(files, key=lambda path: path.stat().st_mtime)
        return None

    def _existing_path(self, path: Path) -> Path | None:
        return path if path.exists() else None

    def _find_run_dir(self, path: Path) -> Path | None:
        output_root = (APP_DIR / self.vars["output_root"].get().strip()).resolve()
        for parent in (path, *path.parents):
            if parent.parent == output_root and parent.name.startswith("run_"):
                return parent
        return None

    def _log_missing_recent_result(self, message: str | None = None) -> None:
        self.log(
            message
            or "최근 결과가 없습니다. 먼저 미리 점검하기 또는 최종 쇼츠 만들기를 실행하세요."
        )

    def open_recent_mp4(self) -> None:
        self.refresh_recent_results_from_fallback(log_success=False)
        self.update_recent_result_labels()
        if not self.recent_mp4_path or not self.recent_mp4_path.exists():
            self._log_missing_recent_result(
                "완성 영상이 아직 없습니다. 먼저 최종 쇼츠 만들기를 실행하세요."
            )
            return
        self.open_path(self.recent_mp4_path)

    def open_recent_result_folder(self) -> None:
        self.refresh_recent_results_from_fallback(log_success=False)
        self.update_recent_result_labels()
        path = None
        if self.recent_mp4_path and self.recent_mp4_path.exists():
            path = self.recent_mp4_path.parent
        elif self.recent_run_dir and self.recent_run_dir.exists():
            path = self.recent_run_dir
        if path is None:
            self._log_missing_recent_result(
                "결과 폴더가 아직 없습니다. 먼저 미리 점검하기 또는 최종 쇼츠 만들기를 실행하세요."
            )
            return
        self.open_path(path)

    def open_recent_batch_summary(self) -> None:
        self.refresh_recent_results_from_fallback(log_success=False)
        if (
            not self.recent_batch_summary_path
            or not self.recent_batch_summary_path.exists()
        ):
            self._log_missing_recent_result(
                "점검 리포트가 아직 없습니다. 먼저 미리 점검하기를 실행하세요."
            )
            return
        self.open_path(self.recent_batch_summary_path)

    def open_recent_candidate_report(self) -> None:
        self.refresh_recent_results_from_fallback(log_success=False)
        if (
            not self.recent_candidate_report_path
            or not self.recent_candidate_report_path.exists()
        ):
            self._log_missing_recent_result(
                "상세 리포트가 아직 없습니다. 먼저 미리 점검하기 또는 최종 쇼츠 만들기를 실행하세요."
            )
            return
        self.open_path(self.recent_candidate_report_path)

    def open_path(self, path: Path) -> None:
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except OSError as exc:
            self.log(f"ERROR: failed to open {path}: {exc}")
            messagebox.showerror("Open failed", str(exc))


def main() -> None:
    app = ShortsAutoEditorGui()
    app.mainloop()


if __name__ == "__main__":
    main()

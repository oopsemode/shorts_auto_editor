# Contributing

Thanks for considering a contribution to `shorts_auto_editor`.

## Ground Rules

- Do not commit real videos, real subtitles, generated MP4 files, or local output folders.
- Use dummy examples under `examples/` for documentation and tests.
- Keep changes focused and avoid unrelated formatting churn.
- Do not change existing core behavior unless the issue or pull request is explicitly about that behavior.

## Local Checks

Run syntax checks before opening a pull request:

```bat
python -m py_compile shorts_auto_editor.py shorts_auto_editor_gui.py
```

For MP4-related changes, describe the command you used and whether it was a dry-run or real render. Do not attach generated videos to the repository.

## Pull Requests

Include:

- What changed.
- Why it changed.
- How you tested it.
- Any known limitations or follow-up work.

Before submitting, inspect your staged files:

```bat
git status --short
git diff --cached --stat
```

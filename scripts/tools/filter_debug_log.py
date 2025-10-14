"""Remove httpcore and markdown_it DEBUG lines from a log file in-place."""
from __future__ import annotations

import argparse
import pathlib
import re

LOG_LINE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ")


def is_log_line(line: str) -> bool:
    """Return True when the line looks like a standard timestamped log entry."""
    return bool(LOG_LINE_PATTERN.match(line))


def should_skip_debug_source(line: str) -> bool:
    """Check whether a DEBUG line originates from httpcore or markdown_it."""
    if "DEBUG" not in line:
        return False
    lowered = line.lower()
    return "httpcore" in lowered or "markdown_it" in lowered


def filter_lines(lines: list[str]) -> list[str]:
    """Return lines that pass the exclusion rules, handling multi-line TUI content."""
    cleaned: list[str] = []
    skipping_tui_payload = False
    for line in lines:
        if skipping_tui_payload:
            if is_log_line(line):
                skipping_tui_payload = False
            else:
                continue

        if "[TUI] 处理内容" in line:
            skipping_tui_payload = True
            continue

        if should_skip_debug_source(line):
            continue

        cleaned.append(line)

    return cleaned


def main() -> None:
    """Parse CLI arguments and apply in-place filtering."""
    parser = argparse.ArgumentParser(
        description="Remove httpcore and markdown_it DEBUG log entries in-place.",
    )
    parser.add_argument("logfile", type=pathlib.Path, help="Path to the log file to clean")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Write cleaned content back to the same file (default behavior).",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        help="Optional path to write the cleaned log instead of overwriting the input.",
    )
    args = parser.parse_args()

    target = args.logfile.expanduser()
    if not target.exists():
        msg = f"Log file not found: {target}"
        raise SystemExit(msg)

    cleaned = filter_lines(target.read_text().splitlines(keepends=True))

    if args.output:
        args.output.write_text("".join(cleaned))
    else:
        target.write_text("".join(cleaned))


if __name__ == "__main__":
    main()

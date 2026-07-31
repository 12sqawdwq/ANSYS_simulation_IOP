#!/usr/bin/env python3
r"""Convert LaTeX \(...\)/\[...\] delimiters to portable Markdown $/$$.

Fenced and inline code spans are preserved verbatim.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DOCUMENTS = [
    REPO / "high_iop_mechanical_transfer_t1p25_c0p60" / "FORWARD_RATIONAL_PARAMETER_DERIVATION.md",
    REPO / "high_iop_mechanical_transfer_t1p25_c0p60" / "RATIONAL_REGRESSION_RESULT.md",
    REPO / "high_iop_mechanical_transfer_t1p25_c0p60" / "IOP_2P5_SUPPLEMENT_RESULT.md",
    REPO / "high_iop_mechanical_transfer_t1p25_c0p60" / "IOP_50_TO_60_EXTENSION_RESULT.md",
    REPO / "high_iop_mechanical_transfer_t1p25_c0p60" / "FORWARD_INVERSE_RIGOR_AUDIT.md",
    REPO / "high_iop_mechanical_transfer_t1p25_c0p60" / "GLOBAL_LOAD_SHARE_DERIVATION.md",
    REPO / "high_iop_mechanical_transfer_t1p25_c0p60" / "INTERFACE_FORCE_INTEGRAL_RESULT.md",
    REPO / "high_iop_mechanical_transfer_t1p25_c0p60" / "ETA_EFF_EFFECTIVE_CORRECTION_ANALYSIS.md",
    REPO / "docs" / "IOP修正算法全局方向.md",
]
CODE = re.compile(r"```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]*`")
DISPLAY = re.compile(r"\\\[([\s\S]+?)\\\]")
INLINE = re.compile(r"\\\(([^\n]+?)\\\)")


def normalize_text(text: str) -> tuple[str, int, int]:
    parts: list[str] = []
    cursor = 0
    display_count = 0
    inline_count = 0

    def normalize_markdown(segment: str) -> str:
        nonlocal display_count, inline_count

        def display_replacement(match: re.Match[str]) -> str:
            nonlocal display_count
            display_count += 1
            return "$$\n" + match.group(1).strip() + "\n$$"

        def inline_replacement(match: re.Match[str]) -> str:
            nonlocal inline_count
            inline_count += 1
            return "$" + match.group(1).strip() + "$"

        segment = DISPLAY.sub(display_replacement, segment)
        return INLINE.sub(inline_replacement, segment)

    for match in CODE.finditer(text):
        parts.append(normalize_markdown(text[cursor : match.start()]))
        parts.append(match.group(0))
        cursor = match.end()
    parts.append(normalize_markdown(text[cursor:]))
    return "".join(parts), display_count, inline_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("documents", nargs="*", type=Path, default=DEFAULT_DOCUMENTS)
    parser.add_argument("--check", action="store_true", help="fail if a document still needs conversion")
    args = parser.parse_args()
    changed = False
    for path in args.documents:
        path = path.resolve()
        original = path.read_text(encoding="utf-8")
        normalized, display_count, inline_count = normalize_text(original)
        needs_change = normalized != original
        changed |= needs_change
        print(f"{path}: display={display_count} inline={inline_count} changed={str(needs_change).lower()}")
        if needs_change and not args.check:
            path.write_text(normalized, encoding="utf-8")
    return 2 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())

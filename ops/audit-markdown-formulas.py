#!/usr/bin/env python3
"""Audit and batch-compile LaTeX formulas embedded in Markdown reports."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DOCUMENTS = [
    REPO / "high_iop_mechanical_transfer_t1p25_c0p60" / "FORWARD_INVERSE_RIGOR_AUDIT.md",
    REPO / "high_iop_mechanical_transfer_t1p25_c0p60" / "GLOBAL_LOAD_SHARE_DERIVATION.md",
    REPO / "high_iop_mechanical_transfer_t1p25_c0p60" / "INTERFACE_FORCE_INTEGRAL_RESULT.md",
    REPO / "docs" / "IOP修正算法全局方向.md",
]
DISPLAY = re.compile(r"\\\[([\s\S]+?)\\\]")
INLINE = re.compile(r"\\\(([^\n]+?)\\\)")
CODE = re.compile(r"```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]*`")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mask_code(text: str) -> str:
    return CODE.sub(lambda match: " " * len(match.group(0)), text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("documents", nargs="*", type=Path, default=DEFAULT_DOCUMENTS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-latex", action="store_true", help="check delimiters and source compatibility without compiling")
    args = parser.parse_args()
    documents = [path.resolve() for path in args.documents]
    formulas: list[str] = []
    seen: set[str] = set()
    document_results = []
    delimiters_pass = True
    non_ascii = []
    for path in documents:
        text = path.read_text(encoding="utf-8")
        masked = mask_code(text)
        display_open, display_close = masked.count("\\["), masked.count("\\]")
        inline_open, inline_close = masked.count("\\("), masked.count("\\)")
        delimiters_pass &= display_open == display_close and inline_open == inline_close
        extracted = [match.group(1).strip() for pattern in (DISPLAY, INLINE) for match in pattern.finditer(masked)]
        for formula in extracted:
            if any(ord(character) > 127 for character in formula):
                non_ascii.append({"document": str(path), "formula": formula})
            if formula and formula not in seen:
                seen.add(formula)
                formulas.append(formula)
        document_results.append({
            "path": str(path),
            "sha256": sha256(path),
            "display_formula_count": len(DISPLAY.findall(masked)),
            "inline_formula_count": len(INLINE.findall(masked)),
            "display_open_count": display_open,
            "display_close_count": display_close,
            "inline_open_count": inline_open,
            "inline_close_count": inline_close,
        })

    tex_lines = [
        r"\documentclass{article}",
        r"\usepackage{amsmath}",
        r"\usepackage{amssymb}",
        r"\begin{document}",
    ]
    for index, formula in enumerate(formulas, 1):
        tex_lines.extend((f"% FORMULA {index}", r"\[", r"\displaystyle " + formula, r"\]", r"\par"))
    tex_lines.append(r"\end{document}")
    latex_returncode = None
    compile_output_tail = "LaTeX compilation explicitly skipped"
    if not args.skip_latex:
        with tempfile.TemporaryDirectory(prefix="blueknow-formula-audit-") as directory:
            work = Path(directory)
            (work / "audit.tex").write_text("\n".join(tex_lines) + "\n", encoding="utf-8")
            try:
                completed = subprocess.run(
                    ["latex", "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "audit.tex"],
                    cwd=work,
                    text=True,
                    capture_output=True,
                    timeout=120,
                    check=False,
                )
                latex_returncode = completed.returncode
                compile_output_tail = "\n".join((completed.stdout + "\n" + completed.stderr).splitlines()[-12:])
            except FileNotFoundError:
                latex_returncode = 127
                compile_output_tail = "latex executable not found"
    structural_pass = delimiters_pass and not non_ascii
    latex_pass = None if args.skip_latex else latex_returncode == 0
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "audit_pass": structural_pass and (args.skip_latex or latex_pass is True),
        "structural_audit_pass": structural_pass,
        "delimiter_balance_pass": delimiters_pass,
        "ascii_formula_source_pass": not non_ascii,
        "latex_compile_skipped": args.skip_latex,
        "latex_batch_compile_pass": latex_pass,
        "latex_returncode": latex_returncode,
        "document_count": len(documents),
        "formula_occurrence_count": sum(
            item["display_formula_count"] + item["inline_formula_count"] for item in document_results
        ),
        "unique_formula_count": len(formulas),
        "non_ascii_formulas": non_ascii,
        "documents": document_results,
        "latex_output_tail": compile_output_tail,
    }
    output = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if payload["audit_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

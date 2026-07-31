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
LEGACY_DISPLAY = re.compile(r"\\\[([\s\S]+?)\\\]")
STANDARD_DISPLAY = re.compile(r"(?<!\\)\$\$([\s\S]+?)(?<!\\)\$\$")
LEGACY_INLINE = re.compile(r"\\\(([^\n]+?)\\\)")
STANDARD_INLINE = re.compile(r"(?<!\\)(?<!\$)\$(?!\$)([^$\n]+?)(?<!\\)\$(?!\$)")
STANDARD_DISPLAY_DELIMITER = re.compile(r"(?<!\\)\$\$")
STANDARD_INLINE_DELIMITER = re.compile(r"(?<!\\)(?<!\$)\$(?!\$)")
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
    parser.add_argument("--skip-pandoc", action="store_true", help="skip portable Markdown-to-MathML rendering")
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
        legacy_display_open, legacy_display_close = masked.count("\\["), masked.count("\\]")
        legacy_inline_open, legacy_inline_close = masked.count("\\("), masked.count("\\)")
        standard_display_matches = list(STANDARD_DISPLAY.finditer(masked))
        standard_display_delimiters = len(STANDARD_DISPLAY_DELIMITER.findall(masked))
        without_standard_display = STANDARD_DISPLAY.sub(lambda match: " " * len(match.group(0)), masked)
        standard_inline_matches = list(STANDARD_INLINE.finditer(without_standard_display))
        standard_inline_delimiters = len(STANDARD_INLINE_DELIMITER.findall(without_standard_display))
        document_delimiters_pass = (
            legacy_display_open == legacy_display_close
            and legacy_inline_open == legacy_inline_close
            and standard_display_delimiters == 2 * len(standard_display_matches)
            and standard_inline_delimiters == 2 * len(standard_inline_matches)
        )
        delimiters_pass &= document_delimiters_pass
        legacy_display_matches = list(LEGACY_DISPLAY.finditer(masked))
        legacy_inline_matches = list(LEGACY_INLINE.finditer(masked))
        all_matches = legacy_display_matches + standard_display_matches + legacy_inline_matches + standard_inline_matches
        extracted = [match.group(1).strip() for match in all_matches]
        for formula in extracted:
            if any(ord(character) > 127 for character in formula):
                non_ascii.append({"document": str(path), "formula": formula})
            if formula and formula not in seen:
                seen.add(formula)
                formulas.append(formula)
        document_results.append({
            "path": str(path),
            "sha256": sha256(path),
            "delimiter_balance_pass": document_delimiters_pass,
            "display_formula_count": len(legacy_display_matches) + len(standard_display_matches),
            "inline_formula_count": len(legacy_inline_matches) + len(standard_inline_matches),
            "legacy_display_open_count": legacy_display_open,
            "legacy_display_close_count": legacy_display_close,
            "legacy_inline_open_count": legacy_inline_open,
            "legacy_inline_close_count": legacy_inline_close,
            "standard_display_delimiter_count": standard_display_delimiters,
            "standard_inline_delimiter_count": standard_inline_delimiters,
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
    pandoc_results = []
    pandoc_pass = None
    if not args.skip_pandoc:
        with tempfile.TemporaryDirectory(prefix="blueknow-mathml-audit-") as directory:
            work = Path(directory)
            for index, (path, document_result) in enumerate(zip(documents, document_results)):
                output_html = work / f"document-{index}.html"
                try:
                    completed = subprocess.run(
                        ["pandoc", "-f", "gfm+tex_math_dollars", "-t", "html5", "--mathml", str(path), "-o", str(output_html)],
                        text=True,
                        capture_output=True,
                        timeout=120,
                        check=False,
                    )
                    mathml_count = output_html.read_text(encoding="utf-8").count("<math") if completed.returncode == 0 else 0
                    expected_count = document_result["display_formula_count"] + document_result["inline_formula_count"]
                    item_pass = completed.returncode == 0 and mathml_count == expected_count
                    pandoc_results.append({
                        "path": str(path),
                        "returncode": completed.returncode,
                        "expected_math_count": expected_count,
                        "rendered_mathml_count": mathml_count,
                        "pass": item_pass,
                    })
                except FileNotFoundError:
                    pandoc_results.append({
                        "path": str(path),
                        "returncode": 127,
                        "expected_math_count": document_result["display_formula_count"] + document_result["inline_formula_count"],
                        "rendered_mathml_count": 0,
                        "pass": False,
                    })
            pandoc_pass = all(item["pass"] for item in pandoc_results)

    structural_pass = delimiters_pass and not non_ascii
    latex_pass = None if args.skip_latex else latex_returncode == 0
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "audit_pass": structural_pass and (args.skip_latex or latex_pass is True) and (args.skip_pandoc or pandoc_pass is True),
        "structural_audit_pass": structural_pass,
        "delimiter_balance_pass": delimiters_pass,
        "ascii_formula_source_pass": not non_ascii,
        "latex_compile_skipped": args.skip_latex,
        "latex_batch_compile_pass": latex_pass,
        "latex_returncode": latex_returncode,
        "pandoc_render_skipped": args.skip_pandoc,
        "pandoc_mathml_render_pass": pandoc_pass,
        "pandoc_documents": pandoc_results,
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

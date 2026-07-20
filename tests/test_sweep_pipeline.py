from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.postprocess import summarize_indentation_sweep as summary
from src.runners import run_indentation_sweep as runner


class APDLContractTests(unittest.TestCase):
    def test_model_uses_preload_then_indentation(self) -> None:
        model = (runner.MODEL_DIR / "param_eye_sweep.mac").read_text().lower()
        self.assertIn("cm,probe_top_nodes,node", model)
        self.assertIn("cnvtol,f,,0.01", model)
        self.assertIn("indent_limit = 0.8e-3", model)
        self.assertLess(model.index("time,1"), model.index("time,2"))
        self.assertLess(model.index("time,2"), model.index("*cfopen,solution_status,csv"))

    def test_views_keep_contour_legend_and_explicit_scales(self) -> None:
        plot = (runner.MODEL_DIR / "plot_sweep_views.mac").read_text().lower()
        self.assertIn("/plopts,info,3", plot)
        self.assertIn("/dscale,1,off", plot)
        self.assertIn("/type,1,7", plot)
        self.assertEqual(plot.count("plnsol"), 8)


class AttemptValidationTests(unittest.TestCase):
    def make_attempt(
        self,
        root: Path,
        case: runner.CaseSpec,
        *,
        load_step: float = 2.0,
        result_time: float = 2.0,
        metric_override: dict[str, float] | None = None,
        output: str = "RUN COMPLETED",
    ) -> Path:
        attempt = root / "attempt"
        attempt.mkdir()
        push = runner.GAP_M + case.indent_mm / 1000.0
        values = {
            "probe_fx_n": 0.0,
            "probe_fy_n": 0.1,
            "contact_area_m2": 1e-6,
            "contact_x_center_m": case.offset_mm / 1000.0,
            "pmax_pa": 1000.0,
            "n_outer": 10.0,
            "cornea_peak_pa": 2000.0,
            "eyelid_peak_pa": 3000.0,
            "probe_uy_m": -push,
            "probe_uy_max_m": -push,
            "result_load_step": load_step,
            "result_time": result_time,
        }
        values.update(metric_override or {})
        (attempt / "metrics.csv").write_text(
            ",".join(str(values[field]) for field in runner.RAW_METRIC_FIELDS) + ",\n"
        )
        (attempt / "solution_status.csv").write_text("1,1,\n")
        (attempt / f"{case.name}.rst").write_bytes(b"result")
        (attempt / "solve.out").write_text(output)
        (attempt / "launcher.log").write_text("")
        for index in range(9):
            (attempt / f"{case.name}{index:03d}.png").write_bytes(b"png")
        return attempt

    def test_recoverable_generic_error_can_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            case = runner.CaseSpec(0.0, 0.8, 0)
            attempt = self.make_attempt(
                Path(directory), case, output="*** ERROR *** automatic cutback\nRUN COMPLETED"
            )
            outcome = runner.validate_attempt(attempt, case, 0, False, 1.0)
            self.assertEqual(outcome.status, "complete")
            self.assertEqual(outcome.error_count, 1)

    def test_final_load_step_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            case = runner.CaseSpec(0.0, 0.8, 0)
            attempt = self.make_attempt(Path(directory), case, load_step=1.0, result_time=1.0)
            outcome = runner.validate_attempt(attempt, case, 0, False, 1.0)
            self.assertEqual(outcome.status, "invalid_metrics")

    def test_non_finite_metric_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            case = runner.CaseSpec(0.0, 0.8, 0)
            attempt = self.make_attempt(Path(directory), case, metric_override={"pmax_pa": float("nan")})
            outcome = runner.validate_attempt(attempt, case, 0, False, 1.0)
            self.assertEqual(outcome.status, "invalid_metrics")

    @unittest.skipUnless(os.name == "posix", "process-group timeout is a POSIX behavior")
    def test_timeout_terminates_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            returncode, timed_out, elapsed = runner.execute_command(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                Path(directory),
                os.environ.copy(),
                0.1,
            )
            self.assertTrue(timed_out)
            self.assertIsNotNone(returncode)
            self.assertLess(elapsed, 5)


class RunnerBehaviorTests(unittest.TestCase):
    def config(self, root: Path) -> runner.RunConfig:
        return runner.RunConfig(root, "smoke", 4, 7200, 1, Path("/tmp/ansys"), 0.3,
                                "a" * 40, False)

    def complete_outcome(self) -> runner.AttemptOutcome:
        return runner.AttemptOutcome("complete", "", 0, 1.0, 0, 9, {}, None)

    def test_case_directory_is_cleaned_before_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case = runner.CaseSpec(0.0, 0.0, 0)
            case_dir = root / case.name
            case_dir.mkdir()
            (case_dir / "stale_metrics.csv").write_text("old")
            with mock.patch.object(runner, "run_attempt", return_value=self.complete_outcome()):
                runner.run_case(case, self.config(root))
            self.assertFalse((case_dir / "stale_metrics.csv").exists())

    def test_nonconverged_case_retries_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            case = runner.CaseSpec(2.0, 0.8, 0)
            failed = runner.AttemptOutcome("nonconverged", "failed", 1, 2.0, 1, 0, {}, None)
            with mock.patch.object(runner, "run_attempt", side_effect=(failed, self.complete_outcome())) as call:
                row = runner.run_case(case, self.config(Path(directory)))
            self.assertEqual(call.call_count, 2)
            self.assertEqual(row["status"], "complete")
            self.assertEqual(row["attempt_count"], 2)
            self.assertEqual(row["np_used"], 2)

    def test_profile_case_counts(self) -> None:
        self.assertEqual(len(runner.PROFILE_CASES["smoke"]), 4)
        self.assertEqual(len(runner.PROFILE_CASES["coarse"]), 12)
        self.assertEqual(len(runner.PROFILE_CASES["full"]), 20)
        self.assertEqual(max(runner.FULL_INDENTS_MM), 0.8)

    def test_custom_case_rejects_indent_above_limit(self) -> None:
        parser = runner.build_parser()
        cli = parser.parse_args(["--case", "0:1.0"])
        with mock.patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit):
            runner.choose_cases(parser, cli)


class QualityControlTests(unittest.TestCase):
    def manifest_row(self, status: str = "complete") -> dict[str, str]:
        return {
            "case": "offset_0p00mm_indent_1p00mm",
            "profile": "smoke",
            "offset_mm": "0",
            "indent_mm": "0.8",
            "mesh_size_mm": "0.3",
            "status": status,
            "failure_reason": "" if status == "complete" else "test failure",
            "views_count": "9",
            "probe_fx_n": "0",
            "probe_fy_n": "0.1",
            "contact_area_m2": "1e-6",
            "contact_x_center_m": "0",
            "pmax_pa": "1000",
            "n_outer": "10",
            "cornea_peak_pa": "2000",
            "eyelid_peak_pa": "3000",
            "probe_uy_m": "-0.00085",
            "commanded_push_m": "0.00085",
            "attempt_count": "1",
            "elapsed_seconds": "10",
            "git_commit": "a" * 40,
        }

    def test_valid_center_case_passes_qc(self) -> None:
        manifest = [self.manifest_row()]
        rows = summary.summary_rows(manifest)
        report = summary.build_qc(manifest, rows)
        self.assertTrue(report["passed"])

    def test_failed_case_fails_qc(self) -> None:
        manifest = [self.manifest_row("nonconverged")]
        report = summary.build_qc(manifest, summary.summary_rows(manifest))
        self.assertFalse(report["passed"])

    def test_missing_expected_case_fails_qc(self) -> None:
        manifest = [self.manifest_row()]
        expected = [
            {"offset_mm": 0.0, "indent_mm": 0.8},
            {"offset_mm": 2.0, "indent_mm": 0.8},
        ]
        report = summary.build_qc(manifest, summary.summary_rows(manifest), expected)
        self.assertFalse(report["passed"])
        self.assertEqual(report["expected_cases"], 2)

    def test_qc_plots_are_valid_png_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            summary.plot_curves(output, summary.summary_rows([self.manifest_row()]))
            figures = sorted((output / "figures").glob("*.png"))
            self.assertEqual(len(figures), 4)
            for figure in figures:
                self.assertGreater(figure.stat().st_size, 1000)
                self.assertEqual(figure.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()

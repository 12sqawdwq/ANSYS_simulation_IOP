from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.postprocess import summarize_indentation_sweep as summary
from src.postprocess import summarize_thickness_sweep as thickness_summary
from src.postprocess import thickness_geometry
from src.postprocess import extract_thickness_state
from src.postprocess import prune_solver_artifacts as pruning
from src.runners import run_indentation_sweep as runner


class APDLContractTests(unittest.TestCase):
    def test_model_uses_preload_then_indentation(self) -> None:
        model = (runner.MODEL_DIR / "param_eye_sweep.mac").read_text().lower()
        self.assertIn("cm,probe_top_nodes,node", model)
        self.assertIn("cnvtol,f,,0.01", model)
        self.assertIn("indent_limit = 0.8e-3", model)
        self.assertIn("te     = arg5", model)
        self.assertIn("2.0e-3", model)
        self.assertLess(model.index("time,1"), model.index("time,2"))
        self.assertLess(model.index("time,2"), model.index("*cfopen,solution_status,csv"))

    def test_views_keep_contour_legend_and_explicit_scales(self) -> None:
        plot = (runner.MODEL_DIR / "plot_sweep_views.mac").read_text().lower()
        self.assertIn("/plopts,info,3", plot)
        self.assertIn("/dscale,1,off", plot)
        self.assertIn("/type,1,7", plot)
        self.assertIn("plnsol,cont,pene", plot)
        self.assertNotIn("/dscale,1,5", plot)
        self.assertEqual(plot.count("plnsol"), 8)

    def test_post_macros_accept_an_optional_result_time(self) -> None:
        for filename in (
            "post_sweep.mac",
            "post_thickness_geometry.mac",
            "plot_sweep_views.mac",
        ):
            macro = (runner.MODEL_DIR / filename).read_text().lower()
            self.assertIn("post_time = arg1", macro)
            self.assertIn("set,,,,,post_time", macro)
            self.assertIn("set,last", macro)


class ThicknessStateExtractionTests(unittest.TestCase):
    def test_maps_nominal_indent_to_second_load_step_time(self) -> None:
        result_time = extract_thickness_state.result_time_for_indent(0.26, 0.8)
        self.assertAlmostEqual(result_time, 1.0 + 0.31 / 0.85)

    def test_rejects_target_beyond_source_load_path(self) -> None:
        with self.assertRaises(ValueError):
            extract_thickness_state.result_time_for_indent(0.81, 0.8)


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
            "max_penetration_m": 1e-6,
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
        if case.kind == "thickness":
            (attempt / "thickness_geometry.csv").write_text(
                "0.0008,2e-5,5e-6,8e-6,1.2e-5,1000,\n"
            )
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
        parser = runner.build_parser()
        profile, cases = runner.choose_cases(parser, parser.parse_args(["--profile", "thickness"]))
        self.assertEqual(profile, "thickness")
        self.assertEqual([case.eyelid_thickness_mm for case in cases],
                         [0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0])
        self.assertTrue(all(case.indent_mm == 0.8 and case.kind == "thickness" for case in cases))

        profile, cases = runner.choose_cases(
            parser,
            parser.parse_args(["--profile", "thickness", "--thickness-indent-mm", "0.26"]),
        )
        self.assertEqual(profile, "thickness")
        self.assertTrue(all(case.indent_mm == 0.26 and case.kind == "thickness" for case in cases))

    def test_custom_case_rejects_indent_above_limit(self) -> None:
        parser = runner.build_parser()
        cli = parser.parse_args(["--case", "0:1.0"])
        with mock.patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit):
            runner.choose_cases(parser, cli)

    def test_thickness_outside_range_is_rejected(self) -> None:
        parser = runner.build_parser()
        cli = parser.parse_args(["--eyelid-thicknesses", "0.6"])
        with mock.patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit):
            runner.choose_cases(parser, cli)

    def test_thickness_indent_above_limit_is_rejected(self) -> None:
        parser = runner.build_parser()
        cli = parser.parse_args(["--profile", "thickness", "--thickness-indent-mm", "1.0"])
        with mock.patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit):
            runner.choose_cases(parser, cli)

    def test_thickness_attempt_requires_ordered_inner_areas(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            case = runner.CaseSpec(0.0, 0.8, 0, 1.2, "thickness")
            attempt = AttemptValidationTests().make_attempt(Path(directory), case)
            outcome = runner.validate_attempt(attempt, case, 0, False, 1.0)
            self.assertEqual(outcome.status, "complete")
            (attempt / "thickness_geometry.csv").write_text(
                "0.0008,2e-5,8e-6,7e-6,6e-6,1000,\n"
            )
            outcome = runner.validate_attempt(attempt, case, 0, False, 1.0)
            self.assertEqual(outcome.status, "invalid_metrics")


class ArtifactRetentionTests(unittest.TestCase):
    def populate_attempt(self, root: Path, job: str) -> Path:
        attempt = root / job / "attempt_1"
        attempt.mkdir(parents=True)
        files = {
            f"{job}.rst": b"primary-result",
            f"{job}.db": b"primary-database",
            f"{job}0.rst": b"rank-result",
            f"{job}1.rst": b"rank-result",
            f"{job}0.r001": b"rank-partition",
            f"{job}.esav": b"scratch",
            f"{job}.full": b"scratch",
            f"{job}.rdb": b"scratch",
            f"{job}.DSP": b"scratch",
            "solve.out": b"diagnostic",
            "metrics.csv": b"metrics",
            f"{job}000.png": b"view",
        }
        for name, content in files.items():
            (attempt / name).write_bytes(content)
        return attempt

    def test_complete_attempt_keeps_primary_and_audit_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            job = "offset_0p00mm_indent_0p80mm"
            attempt = self.populate_attempt(Path(directory), job)
            stats = pruning.prune_attempt(attempt, job, keep_primary_results=True)
            self.assertEqual(stats.files_selected, 7)
            self.assertTrue((attempt / f"{job}.rst").exists())
            self.assertTrue((attempt / f"{job}.db").exists())
            self.assertTrue((attempt / "solve.out").exists())
            self.assertTrue((attempt / "metrics.csv").exists())
            self.assertTrue((attempt / f"{job}000.png").exists())
            self.assertFalse((attempt / f"{job}0.rst").exists())
            self.assertFalse((attempt / f"{job}.esav").exists())

    def test_failed_attempt_also_removes_primary_result_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            job = "offset_2p00mm_indent_0p80mm"
            attempt = self.populate_attempt(Path(directory), job)
            stats = pruning.prune_attempt(attempt, job, keep_primary_results=False)
            self.assertEqual(stats.files_selected, 9)
            self.assertFalse((attempt / f"{job}.rst").exists())
            self.assertFalse((attempt / f"{job}.db").exists())
            self.assertTrue((attempt / "solve.out").exists())

    def test_dry_run_does_not_delete_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            job = "offset_1p00mm_indent_0p40mm"
            attempt = self.populate_attempt(Path(directory), job)
            stats = pruning.prune_attempt(
                attempt, job, keep_primary_results=True, apply=False
            )
            self.assertFalse(stats.applied)
            self.assertTrue((attempt / f"{job}.esav").exists())


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
            "max_penetration_m": "1e-6",
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


class ThicknessSummaryTests(unittest.TestCase):
    def row(self, thickness: float) -> dict[str, str]:
        return {
            "case": f"eyelid_{thickness:.1f}",
            "profile": "thickness",
            "offset_mm": "0",
            "indent_mm": "0.8",
            "eyelid_thickness_mm": str(thickness),
            "cornea_thickness_mm": "0.6",
            "mesh_size_mm": "0.3",
            "status": "complete",
            "failure_reason": "",
            "views_count": "9",
            "probe_fx_n": "0",
            "probe_fy_n": "-0.7",
            "contact_area_m2": "1.4e-5",
            "pmax_pa": "100000",
            "max_penetration_m": "1e-5",
            "inner_max_downward_m": "0.0007",
            "inner_effect_area_m2": "2e-5",
            "inner_area_1deg_m2": "6e-6",
            "inner_area_2deg_m2": "9e-6",
            "inner_area_3deg_m2": "1.2e-5",
            "inner_face_count": "1000",
            "cornea_peak_pa": "120000",
            "eyelid_peak_pa": "100000",
            "probe_uy_m": "-0.00085",
            "commanded_push_m": "0.00085",
            "elapsed_seconds": "100",
            "git_commit": "a" * 40,
        }

    def test_summary_computes_area_ratios(self) -> None:
        rows = thickness_summary.summary_rows([self.row(0.8), self.row(1.0)])
        self.assertAlmostEqual(float(rows[0]["ae_over_ac_2deg"]), 14.0 / 9.0)
        self.assertAlmostEqual(float(rows[1]["force_ratio_to_0p8"]), 1.0)

    def test_complete_thickness_grid_passes_qc(self) -> None:
        manifest = [self.row(0.8), self.row(1.0)]
        expected = [
            {"eyelid_thickness_mm": 0.8, "indent_mm": 0.8},
            {"eyelid_thickness_mm": 1.0, "indent_mm": 0.8},
        ]
        qc = thickness_summary.build_qc(
            manifest, thickness_summary.summary_rows(manifest), expected
        )
        self.assertTrue(qc["passed"])


class ThicknessGeometryTests(unittest.TestCase):
    def face(
        self,
        element: int,
        points: tuple[tuple[float, float, float], ...],
    ) -> thickness_geometry.Face:
        return thickness_geometry.Face(element, (1, 2, 3), points)

    def test_flat_faces_are_selected_by_angle_and_displacement(self) -> None:
        preload = {
            1: self.face(1, ((0, 0, 0), (1, 0, 0), (0, 0, 1))),
            2: self.face(2, ((1, 0, 0), (2, 0, 0), (1, 0, 1))),
        }
        final = {
            1: self.face(1, ((0, -1, 0), (1, -1, 0), (0, -1, 1))),
            2: self.face(2, ((1, -0.01, 0), (2, 0.19, 0), (1, -0.01, 1))),
        }
        metrics = thickness_geometry.analyze_faces(preload, final)
        self.assertAlmostEqual(float(metrics["inner_max_downward_m"]), 1.0)
        self.assertAlmostEqual(float(metrics["inner_effect_area_m2"]), 0.5)
        self.assertAlmostEqual(float(metrics["inner_area_1deg_m2"]), 0.5)
        self.assertAlmostEqual(float(metrics["inner_area_2deg_m2"]), 0.5)
        self.assertEqual(metrics["inner_face_count"], 2)

    def test_preload_and_final_element_sets_must_match(self) -> None:
        face = self.face(1, ((0, 0, 0), (1, 0, 0), (0, 0, 1)))
        with self.assertRaises(ValueError):
            thickness_geometry.analyze_faces({1: face}, {})


if __name__ == "__main__":
    unittest.main()

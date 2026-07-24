from __future__ import annotations

import csv
import io
import math
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
from src.postprocess import build_thickness_view_matrix
from src.postprocess import prune_solver_artifacts as pruning
from src.postprocess import check_calibration_run as calibration_monitor
from src.runners import run_indentation_sweep as runner
from src.runners import run_thickness_calibration as calibration


class APDLContractTests(unittest.TestCase):
    def test_angle_threshold_outputs_are_labeled_diagnostic_only(self) -> None:
        geometry = Path(thickness_geometry.__file__).read_text(encoding="utf-8").lower()
        plot = (
            runner.REPO_ROOT / "src" / "postprocess" / "plot_flat_region_2deg.py"
        ).read_text(encoding="utf-8").lower()
        self.assertIn('"status": "diagnostic_only"', geometry)
        self.assertNotIn("objective flat", geometry)
        self.assertIn("diagnostic flat region", plot)
        self.assertNotIn("objective flat region", plot)

    def test_material_calibration_launcher_is_disabled_before_creating_runs(self) -> None:
        launcher = (
            runner.REPO_ROOT / "ops" / "start-thickness-calibration-5090d.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("calibration is disabled", launcher.lower())
        self.assertNotIn("mkdir -p", launcher)
        self.assertNotIn("nohup", launcher)

    def test_model_uses_preload_then_indentation(self) -> None:
        model = (runner.MODEL_DIR / "param_eye_sweep.mac").read_text().lower()
        self.assertIn("cm,probe_top_nodes,node", model)
        self.assertIn("cnvtol,f,,0.01", model)
        self.assertIn("indent_limit = 0.8e-3", model)
        self.assertIn("te     = arg5", model)
        self.assertIn("2.0e-3", model)
        self.assertLess(model.index("time,1"), model.index("time,2"))
        self.assertLess(model.index("time,2"), model.index("*cfopen,solution_status,csv"))
        self.assertIn("iop    = arg6", model)
        self.assertIn("eyelid_material_scale = arg7", model)
        self.assertIn("cornea_material_scale = arg8", model)

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

    def test_thickness_geometry_exports_both_interface_surfaces(self) -> None:
        macro = (
            runner.MODEL_DIR / "post_thickness_geometry.mac"
        ).read_text().lower()
        for filename in (
            "outer_preload_faces",
            "outer_final_faces",
            "inner_preload_faces",
            "inner_final_faces",
        ):
            self.assertIn(f"*cfopen,{filename},csv", macro)
        self.assertEqual(macro.count("esel,s,real,,3"), 2)
        self.assertEqual(macro.count("esel,s,real,,4"), 2)
        self.assertEqual(macro.count("esel,r,ename,,170"), 2)
        self.assertEqual(macro.count("esel,r,ename,,174"), 2)

    def test_eyelid_strain_view_is_scoped_and_uses_hencky_strain(self) -> None:
        macro = (
            runner.MODEL_DIR / "plot_thickness_eyelid_strain_007.mac"
        ).read_text().lower()
        self.assertIn("show_probe = arg2", macro)
        self.assertIn("esel,r,mat,,2", macro)
        self.assertIn("esel,a,mat,,3", macro)
        self.assertIn("/dscale,1,1", macro)
        self.assertIn("/type,1,7", macro)
        self.assertIn("/contour,1,9,0,,0.065", macro)
        self.assertIn("plnsol,epel,eqv", macro)
        self.assertEqual(macro.count("plnsol"), 1)


class ThicknessStateExtractionTests(unittest.TestCase):
    def test_maps_nominal_indent_to_second_load_step_time(self) -> None:
        result_time = extract_thickness_state.result_time_for_indent(0.26, 0.8)
        self.assertAlmostEqual(result_time, 1.0 + 0.31 / 0.85)
        self.assertAlmostEqual(result_time, 1.3647058823529412)

    def test_rejects_target_beyond_source_load_path(self) -> None:
        with self.assertRaises(ValueError):
            extract_thickness_state.result_time_for_indent(0.81, 0.8)

    def test_postprocessing_job_name_stays_short(self) -> None:
        self.assertEqual(extract_thickness_state.post_job_name(1.25), "post_1p25")
        self.assertLess(len(extract_thickness_state.post_job_name(1.25)), 16)


class ThicknessViewMatrixTests(unittest.TestCase):
    def test_builds_matrix_without_cropping_source_aspect_ratio(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = []
            for index, thickness in enumerate((0.8, 1.0, 1.2)):
                path = root / f"source_{index}.png"
                Image.new("RGB", (160, 120), (index * 50, 10, 20)).save(path)
                sources.append((thickness, path))
            output = root / "matrix.png"
            build_thickness_view_matrix.build_matrix(
                sources, output, columns=2, image_width=80, label_height=20, gap=4, margin=6
            )
            with Image.open(output) as matrix:
                self.assertEqual(matrix.size, (176, 176))
                self.assertEqual(matrix.getpixel((7, 27)), (0, 10, 20))


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
            geometry = {
                "inner_max_downward_m": 8e-4,
                "inner_effect_area_m2": 2e-5,
                "inner_area_1deg_m2": 5e-6,
                "inner_area_2deg_m2": 8e-6,
                "inner_area_3deg_m2": 1.2e-5,
                "inner_face_count": 1000,
                "inner_area_smooth_2deg_m2": 9e-6,
                "inner_smooth_2deg_face_count": 100,
                "outer_flat_projected_area_1deg_m2": 5e-6,
                "outer_flat_projected_area_2deg_m2": 7e-6,
                "outer_flat_projected_area_3deg_m2": 9e-6,
                "outer_flat_surface_area_2deg_m2": 7.01e-6,
                "outer_flat_face_count_2deg": 80,
                "outer_flat_displacement_threshold_m": 5e-6,
                "inner_flat_projected_area_1deg_m2": 3e-6,
                "inner_flat_projected_area_2deg_m2": 4e-6,
                "inner_flat_projected_area_3deg_m2": 5e-6,
                "inner_flat_surface_area_2deg_m2": 4.01e-6,
                "inner_flat_face_count_2deg": 50,
                "inner_flat_displacement_threshold_m": 4e-6,
                "outer_local_max_downward_m": 8e-4,
                "outer_surface_area_m2": 7e-6,
                "outer_projected_area_m2": 6.9e-6,
                "outer_break_radius_m": 1.48e-3,
                "outer_break_method_code": 1,
                "outer_threshold_m": 5e-6,
                "outer_area_sensitivity_fraction": 0.05,
                "outer_diameter_sensitivity_m": 0.1e-3,
                "outer_face_count": 500,
                "inner_local_max_downward_m": 5e-4,
                "inner_surface_area_m2": 4e-6,
                "inner_projected_area_m2": 3.9e-6,
                "inner_break_radius_m": 1.1e-3,
                "inner_break_method_code": 1,
                "inner_threshold_m": 4e-6,
                "inner_area_sensitivity_fraction": 0.05,
                "inner_diameter_sensitivity_m": 0.1e-3,
            }
            (attempt / "thickness_geometry.csv").write_text(
                ",".join(str(geometry[field]) for field in thickness_geometry.GEOMETRY_FIELDS)
                + ",\n"
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
        self.assertTrue(all(case.indent_mm == 0.28 and case.kind == "thickness" for case in cases))

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
            path = attempt / "thickness_geometry.csv"
            geometry = dict(zip(
                thickness_geometry.GEOMETRY_FIELDS,
                [float(item) for item in path.read_text().strip("\n,").split(",")],
            ))
            geometry.update({
                "inner_area_1deg_m2": 8e-6,
                "inner_area_2deg_m2": 7e-6,
                "inner_area_3deg_m2": 6e-6,
            })
            path.write_text(
                ",".join(str(geometry[field]) for field in thickness_geometry.GEOMETRY_FIELDS)
                + ",\n"
            )
            outcome = runner.validate_attempt(attempt, case, 0, False, 1.0)
            self.assertEqual(outcome.status, "invalid_metrics")

    def test_no_view_policy_ignores_boundary_qc_plot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            case = runner.CaseSpec(0.0, 0.8, 0, 1.0, "thickness")
            attempt = AttemptValidationTests().make_attempt(Path(directory), case)
            for path in attempt.glob(f"{case.name}[0-9][0-9][0-9].png"):
                path.unlink()
            (attempt / "applanation_boundary_qc.png").write_bytes(b"png")
            outcome = runner.validate_attempt(attempt, case, 0, False, 1.0, 0)
            self.assertEqual(outcome.status, "complete")


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
            "iop_mmhg": "20",
            "eyelid_material_scale": "1",
            "cornea_material_scale": "1",
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
            "iop_mmhg": "20",
            "eyelid_material_scale": "1",
            "cornea_material_scale": "1",
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
            "inner_area_smooth_2deg_m2": "1e-5",
            "inner_smooth_2deg_face_count": "120",
            "outer_flat_projected_area_1deg_m2": "6e-6",
            "outer_flat_projected_area_2deg_m2": "8e-6",
            "outer_flat_projected_area_3deg_m2": "10e-6",
            "outer_flat_surface_area_2deg_m2": "8.01e-6",
            "outer_flat_face_count_2deg": "90",
            "outer_flat_displacement_threshold_m": "5e-6",
            "inner_flat_projected_area_1deg_m2": "3e-6",
            "inner_flat_projected_area_2deg_m2": "4e-6",
            "inner_flat_projected_area_3deg_m2": "5e-6",
            "inner_flat_surface_area_2deg_m2": "4.01e-6",
            "inner_flat_face_count_2deg": "45",
            "inner_flat_displacement_threshold_m": "4e-6",
            "outer_local_max_downward_m": "0.0008",
            "outer_surface_area_m2": "7.1e-6",
            "outer_projected_area_m2": "7e-6",
            "outer_break_radius_m": "0.0015",
            "outer_break_method_code": "1",
            "outer_threshold_m": "5e-6",
            "outer_area_sensitivity_fraction": "0.05",
            "outer_diameter_sensitivity_m": "0.0001",
            "outer_face_count": "500",
            "inner_local_max_downward_m": "0.0005",
            "inner_surface_area_m2": "4.5e-6",
            "inner_projected_area_m2": "4.4e-6",
            "inner_break_radius_m": "0.0012",
            "inner_break_method_code": "1",
            "inner_threshold_m": "4e-6",
            "inner_area_sensitivity_fraction": "0.05",
            "inner_diameter_sensitivity_m": "0.0001",
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
        self.assertAlmostEqual(float(rows[0]["ae_over_ac_surface"]), 7.1 / 4.5)
        self.assertAlmostEqual(float(rows[0]["ae_over_ac_flat_2deg"]), 8.0 / 4.0)
        self.assertAlmostEqual(float(rows[0]["outer_flat_coverage_fraction"]), 8.0 / (math.pi * 2.16**2))
        self.assertNotIn("gat_ae_area_mm2", rows[0])
        self.assertNotIn("ae_over_ac_gat", rows[0])
        self.assertAlmostEqual(
            float(rows[0]["probe_over_ac_surface"]), math.pi * 2.16**2 / 4.5
        )
        self.assertAlmostEqual(float(rows[1]["force_ratio_to_0p8"]), 1.0)

    def test_initial_surface_sagitta_is_not_reported_as_area(self) -> None:
        surface_radius = 7.8 + 1.25
        sagitta = surface_radius - math.sqrt(surface_radius**2 - 2.16**2)
        self.assertAlmostEqual(
            thickness_summary.initial_surface_probe_edge_sagitta_mm(1.25),
            sagitta,
            places=12,
        )
        self.assertNotIn("gat_ae_area_mm2", thickness_summary.SUMMARY_FIELDS)
        self.assertNotIn("ae_over_ac_gat", thickness_summary.SUMMARY_FIELDS)

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
        nodes: tuple[int, int, int] | None = None,
    ) -> thickness_geometry.Face:
        if nodes is None:
            nodes = (element * 3 - 2, element * 3 - 1, element * 3)
        return thickness_geometry.Face(element, nodes, points)

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
        self.assertAlmostEqual(float(metrics["inner_area_smooth_2deg_m2"]), 0.5)
        self.assertEqual(int(metrics["inner_smooth_2deg_face_count"]), 1)

    def test_smoothed_normals_accept_consistently_flat_faces_with_reversed_orientation(self) -> None:
        preload = {
            1: self.face(1, ((0, 0, 0), (1, 0, 0), (0, 0, 1)), (1, 2, 3)),
            2: self.face(2, ((1, 0, 0), (1, 0, 1), (0, 0, 1)), (2, 4, 3)),
        }
        final = {
            1: self.face(1, ((0, -1, 0), (1, -1, 0), (0, -1, 1)), (1, 2, 3)),
            2: self.face(2, ((1, -1, 0), (1, -1, 1), (0, -1, 1)), (2, 4, 3)),
        }
        metrics = thickness_geometry.analyze_faces(preload, final)
        self.assertAlmostEqual(float(metrics["inner_area_smooth_2deg_m2"]), 1.0)
        self.assertEqual(int(metrics["inner_smooth_2deg_face_count"]), 2)
        self.assertEqual(metrics["inner_face_count"], 2)

    def test_objective_flat_area_uses_central_component_without_probe_forcing(self) -> None:
        mm = 1e-3
        preload = {
            1: self.face(1, ((-0.25*mm, 0, -0.25*mm), (0.25*mm, 0, -0.25*mm),
                            (0.25*mm, 0, 0.25*mm)), (1, 2, 3)),
            2: self.face(2, ((-0.25*mm, 0, -0.25*mm), (0.25*mm, 0, 0.25*mm),
                            (-0.25*mm, 0, 0.25*mm)), (1, 3, 4)),
            3: self.face(3, ((1.2*mm, 0, 0), (1.5*mm, 0, 0), (1.2*mm, 0, 0.3*mm)),
                         (10, 11, 12)),
            4: self.face(4, ((3.0*mm, 0, 0), (3.2*mm, 0, 0), (3.0*mm, 0, 0.2*mm)),
                         (20, 21, 22)),
            5: self.face(5, ((0, 0, 3.0*mm), (0.2*mm, 0, 3.0*mm), (0, 0, 3.2*mm)),
                         (30, 31, 32)),
            6: self.face(6, ((-3.0*mm, 0, 0), (-3.2*mm, 0, 0), (-3.0*mm, 0, 0.2*mm)),
                         (40, 41, 42)),
        }
        final = dict(preload)
        for element in (1, 2, 3):
            face = preload[element]
            final[element] = self.face(
                element,
                tuple((x, y - 0.28*mm, z) for x, y, z in face.points),
                face.nodes,
            )
        result = thickness_geometry.analyze_flat_surface(preload, final)
        self.assertEqual(result.face_count, 2)
        self.assertAlmostEqual(result.projected_area, (0.5*mm) ** 2)
        self.assertLess(result.projected_area, thickness_geometry.PROBE_AREA_M2)

    def test_displacement_support_uses_robust_absolute_noise_floor(self) -> None:
        mm = 1e-3
        preload = {
            1: self.face(1, ((-0.2*mm, 0, -0.2*mm), (0.2*mm, 0, -0.2*mm),
                            (0.2*mm, 0, 0.2*mm)), (1, 2, 3)),
            2: self.face(2, ((-0.2*mm, 0, -0.2*mm), (0.2*mm, 0, 0.2*mm),
                            (-0.2*mm, 0, 0.2*mm)), (1, 3, 4)),
            3: self.face(3, ((3*mm, 0, 0), (3.1*mm, 0, 0), (3*mm, 0, 0.1*mm))),
            4: self.face(4, ((-3*mm, 0, 0), (-3.1*mm, 0, 0), (-3*mm, 0, 0.1*mm))),
            5: self.face(5, ((0, 0, 3*mm), (0.1*mm, 0, 3*mm), (0, 0, 3.1*mm))),
        }
        final = dict(preload)
        for element in (1, 2):
            face = preload[element]
            final[element] = self.face(
                element,
                tuple((x, y - 0.28*mm, z) for x, y, z in face.points),
                face.nodes,
            )

        result, selected = thickness_geometry.select_displacement_support(preload, final)

        self.assertEqual(selected, {1, 2})
        self.assertAlmostEqual(result.displacement_threshold, 1e-6)
        self.assertAlmostEqual(result.local_max, 0.28*mm)
        self.assertAlmostEqual(result.projected_area, (0.4*mm) ** 2)

    def test_displacement_support_area_cannot_exceed_probe_disk(self) -> None:
        mm = 1e-3
        preload = {
            1: self.face(1, ((-3*mm, 0, -3*mm), (3*mm, 0, -3*mm),
                            (3*mm, 0, 3*mm)), (1, 2, 3)),
            2: self.face(2, ((-3*mm, 0, -3*mm), (3*mm, 0, 3*mm),
                            (-3*mm, 0, 3*mm)), (1, 3, 4)),
            3: self.face(3, ((4*mm, 0, 0), (4.1*mm, 0, 0), (4*mm, 0, 0.1*mm))),
            4: self.face(4, ((-4*mm, 0, 0), (-4.1*mm, 0, 0), (-4*mm, 0, 0.1*mm))),
            5: self.face(5, ((0, 0, 4*mm), (0.1*mm, 0, 4*mm), (0, 0, 4.1*mm))),
        }
        final = dict(preload)
        for element in (1, 2):
            face = preload[element]
            final[element] = self.face(
                element,
                tuple((x, y - 0.28*mm, z) for x, y, z in face.points),
                face.nodes,
            )

        result, _ = thickness_geometry.select_displacement_support(preload, final)

        self.assertLessEqual(result.projected_area, thickness_geometry.PROBE_AREA_M2)

    def test_preload_and_final_element_sets_must_match(self) -> None:
        face = self.face(1, ((0, 0, 0), (1, 0, 0), (0, 0, 1)))
        with self.assertRaises(ValueError):
            thickness_geometry.analyze_faces({1: face}, {})

    def test_circle_clipping_integrates_partial_triangles(self) -> None:
        total = 0.0
        step = 0.2
        for x_index in range(-10, 10):
            for z_index in range(-10, 10):
                x0, x1 = x_index * step, (x_index + 1) * step
                z0, z1 = z_index * step, (z_index + 1) * step
                total += thickness_geometry._projected_area_inside_circle(
                    ((x0, z0), (x1, z0), (x1, z1)), 1.0
                )
                total += thickness_geometry._projected_area_inside_circle(
                    ((x0, z0), (x1, z1), (x0, z1)), 1.0
                )
        self.assertLess(abs(total - math.pi) / math.pi, 0.01)

    def test_segmented_surface_fit_recovers_known_transition(self) -> None:
        dummy = self.face(1, ((0, 0, 0), (1, 0, 0), (0, 0, 1)))
        transition = 1.4e-3
        records = [
            thickness_geometry.SurfaceRecord(
                radius,
                max(0.0, 1e-3 - 0.25 * radius),
                -0.02 * radius - 0.18 * max(0.0, radius - transition),
                1.0,
                1.0,
                dummy,
            )
            for radius in (index * 0.025e-3 for index in range(1, 121))
        ]
        radius, method, _, _ = thickness_geometry._break_radius(
            records, 0.1e-3, 0.02, thickness_geometry.PROBE_RADIUS_M
        )
        self.assertEqual(method, "segmented_fit")
        self.assertLess(abs(radius - transition), 0.03e-3)

    def test_surface_without_internal_transition_uses_probe_edge(self) -> None:
        dummy = self.face(1, ((0, 0, 0), (1, 0, 0), (0, 0, 1)))
        records = [
            thickness_geometry.SurfaceRecord(
                radius,
                1e-3 - 0.25 * radius,
                -0.1 * radius,
                1.0,
                1.0,
                dummy,
            )
            for radius in (index * 0.025e-3 for index in range(1, 121))
        ]
        radius, method, _, _ = thickness_geometry._break_radius(
            records, 0.1e-3, 0.02, thickness_geometry.PROBE_RADIUS_M
        )
        self.assertEqual(method, "probe_edge")
        self.assertLessEqual(radius, thickness_geometry.PROBE_RADIUS_M)
        self.assertGreater(radius, thickness_geometry.PROBE_RADIUS_M - 0.2e-3)


class ThicknessCalibrationTests(unittest.TestCase):
    def test_calibration_entrypoint_is_disabled_without_approved_metric(self) -> None:
        with mock.patch.object(sys, "argv", [
            "run_thickness_calibration.py", "--run-root", "unused"
        ]):
            with self.assertRaisesRegex(SystemExit, "approved deformation-based"):
                calibration.main()

    def test_interval_error_is_zero_inside_and_relative_outside(self) -> None:
        self.assertEqual(calibration.interval_error(1.75, 1.5, 2.0), 0.0)
        self.assertAlmostEqual(calibration.interval_error(1.2, 1.5, 2.0), 0.2)
        self.assertAlmostEqual(calibration.interval_error(2.4, 1.5, 2.0), 0.2)

    def test_calibration_requires_an_explicitly_approved_ratio(self) -> None:
        self.assertEqual(calibration.area_ratio({
            "approved_ae_over_ac": "1.8",
            "ae_over_ac_flat_2deg": "2.0",
            "ae_over_ac_gat": "2.2",
        }), 1.8)
        for historical in (
            {"ae_over_ac_flat_2deg": "2.0"},
            {"ae_over_ac_gat": "2.2"},
            {"ae_over_ac_surface": "1.1"},
        ):
            with self.assertRaisesRegex(ValueError, "missing approved_ae_over_ac"):
                calibration.area_ratio(historical)

    def test_primary_acceptance_counts_points_within_twenty_percent(self) -> None:
        values = {0.8: 1.2, 1.0: 1.7, 1.2: 2.0, 1.25: 2.4}
        rows = [
            {
                "eyelid_thickness_mm": str(thickness),
                "approved_ae_over_ac": str(ratio),
            }
            for thickness, ratio in values.items()
        ]
        passed, mean_error, score = calibration.primary_metrics(rows)
        self.assertEqual(passed, 4)
        self.assertAlmostEqual(mean_error, 0.1)
        self.assertAlmostEqual(score, 0.02)

    def test_secondary_trend_penalizes_a_falling_thick_end(self) -> None:
        primary = [{
            "eyelid_thickness_mm": str(thickness),
            "approved_ae_over_ac": "1.8",
        } for thickness in calibration.PRIMARY_THICKNESSES]
        secondary = [
            {"eyelid_thickness_mm": "1.5", "approved_ae_over_ac": "2.5"},
            {"eyelid_thickness_mm": "2.0", "approved_ae_over_ac": "1.7"},
        ]
        _, penalty = calibration.secondary_metrics(primary, secondary)
        self.assertEqual(penalty, 1.0)


class CalibrationMonitorTests(unittest.TestCase):
    def test_active_fresh_solver_with_progress_is_healthy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "controller.pid").write_text(str(os.getpid()), encoding="ascii")
            attempt = root / "candidate" / "attempt_1"
            attempt.mkdir(parents=True)
            (attempt / "solve.out").write_text(
                "SUBSTEP 1 CONVERGED\nSUBSTEP 2 CONVERGED\nSUBSTEP 3 CONVERGED\n"
            )
            status = calibration_monitor.inspect(root)
            self.assertTrue(status["healthy_to_leave_unattended"])

    def test_manifest_failure_prevents_unattended_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "controller.pid").write_text(str(os.getpid()), encoding="ascii")
            with (root / "run_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=("case", "status"))
                writer.writeheader()
                writer.writerow({"case": "failed", "status": "nonconverged"})
            status = calibration_monitor.inspect(root)
            self.assertFalse(status["healthy_to_leave_unattended"])


if __name__ == "__main__":
    unittest.main()

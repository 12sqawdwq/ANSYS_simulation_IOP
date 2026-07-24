import math

import pytest

from src.postprocess.extract_contact_rezeroed_states import (
    detect_contact_zero,
    result_time_for_effective_indent,
)


def history_row(push, force, count=0, area=0.0, pmax=0.0):
    return {
        "total_push_m": push,
        "result_time": 1.0 + push / 0.00033,
        "result_load_step": 0.0,
        "probe_fy_n": -force,
        "probe_uy_min_m": -push,
        "probe_uy_max_m": -push,
        "loaded_contact_count": float(count),
        "loaded_contact_area_m2": area,
        "pmax_pa": pmax,
    }


def test_detect_contact_zero_requires_stable_loaded_contact():
    rows = [
        history_row(0.00000, 0.0),
        history_row(0.00001, 0.0002),
        history_row(0.00002, 0.0012, 1, 1e-8, 100.0),
        history_row(0.00003, 0.0004),  # transient contact must be ignored
        history_row(0.00004, 0.0008, 1, 1e-8, 100.0),
        history_row(0.00005, 0.0014, 1, 2e-8, 200.0),
        history_row(0.00006, 0.0020, 2, 3e-8, 300.0),
        history_row(0.00033, 0.2, 20, 1e-6, 1000.0),
    ]

    contact = detect_contact_zero(rows, force_threshold_n=0.001, stable_points=3)

    assert 0.00004 < contact.push_m < 0.00005
    assert math.isclose(contact.bracket_low_m, 0.00004)
    assert math.isclose(contact.bracket_high_m, 0.00005)


def test_effective_indent_maps_to_existing_result_time():
    push, result_time = result_time_for_effective_indent(0.00002, 0.28, 0.00033)
    assert math.isclose(push, 0.00030)
    assert math.isclose(result_time, 1.0 + 0.00030 / 0.00033)


def test_preload_contact_force_is_not_subtracted():
    rows = [
        history_row(0.00000, 0.0020, 2, 2e-8, 200.0),
        history_row(0.00001, 0.0025, 2, 2e-8, 250.0),
        history_row(0.00002, 0.0030, 3, 3e-8, 300.0),
        history_row(0.00003, 0.0035, 3, 3e-8, 350.0),
        history_row(0.00004, 0.0040, 4, 4e-8, 400.0),
        history_row(0.00005, 0.0045, 4, 4e-8, 450.0),
        history_row(0.00006, 0.0050, 5, 5e-8, 500.0),
        history_row(0.00033, 0.2, 20, 1e-6, 1000.0),
    ]

    contact = detect_contact_zero(rows, force_threshold_n=0.001, stable_points=3)

    assert contact.push_m == 0.0
    assert contact.baseline_force_n == 0.0
    assert contact.preload_force_n == 0.002
    assert contact.preload_contact_count == 2


def test_effective_indent_outside_source_path_fails():
    with pytest.raises(ValueError):
        result_time_for_effective_indent(0.00006, 0.28, 0.00033)

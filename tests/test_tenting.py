"""Phase 2: the flap must fit, swing freely, stop at the right angle and reach the desk."""

import dataclasses

import pytest

from lilytent import DEFAULT, flap, open_flap, solve_layout, stand_on_desk, tented_case


def _config(tent_angle: float):
    return dataclasses.replace(DEFAULT, tent=dataclasses.replace(DEFAULT.tent, tent_angle=tent_angle))


def _overlap(a, b) -> float:
    common = a & b
    return sum(s.volume for s in common.solids()) if common is not None else 0.0


@pytest.fixture(scope="module", params=[10.0, 15.0, 30.0, 45.0])
def built(request):
    cfg = _config(request.param)
    layout = solve_layout(cfg)
    return cfg, layout, tented_case(cfg, layout), flap(cfg, layout)


def test_parts_are_single_valid_solids(built):
    _, _, case, flap_part = built
    for part in (case, flap_part):
        assert part.is_valid
        assert len(part.solids()) == 1


def test_closed_flap_is_flush_and_inside_pocket(built):
    _, layout, _, flap_part = built
    box = flap_part.bounding_box()
    assert box.min.Z == pytest.approx(0, abs=1e-6)
    assert box.max.Z <= layout.pocket_depth
    assert layout.pocket_x[0] < box.min.X and box.max.X < layout.pocket_x[1]
    assert layout.pocket_y[0] < box.min.Y and box.max.Y < layout.pocket_y[1]


def test_flap_swings_freely_up_to_the_stop(built):
    _, layout, case, flap_part = built
    for fraction in (0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 1.0):
        angle = fraction * layout.open_angle
        assert _overlap(case, open_flap(flap_part, layout, angle)) < 0.01, f"collision at {angle:.1f} deg"


def test_stop_prevents_opening_further(built):
    _, layout, case, flap_part = built
    assert _overlap(case, open_flap(flap_part, layout, layout.open_angle + 2)) > 0.5


def test_open_flap_and_case_both_rest_on_the_desk(built):
    _, layout, case, flap_part = built
    posed_case = stand_on_desk(case, layout)
    posed_flap = stand_on_desk(open_flap(flap_part, layout), layout)
    assert posed_case.bounding_box().min.Z == pytest.approx(0, abs=0.02)
    assert posed_flap.bounding_box().min.Z == pytest.approx(0, abs=0.02)


def test_pocket_outside_the_footprint_is_rejected():
    cfg = dataclasses.replace(DEFAULT, tent=dataclasses.replace(DEFAULT.tent, flap_y_range=(-50.0, 39.0)))
    with pytest.raises(ValueError):
        tented_case(cfg)


def test_parts_survive_a_step_round_trip(built, tmp_path):
    """Sliver faces can make a solid come back from STEP as an open shell."""
    from build123d import export_step, import_step

    _, _, case, flap_part = built
    for name, part in (("case", case), ("flap", flap_part)):
        path = tmp_path / f"{name}.step"
        export_step(part, path)
        assert len(import_step(path).solids()) == 1

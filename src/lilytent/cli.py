"""Command line entry point: `uv run lilytent build`."""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

from build123d import Compound, Part, Plane, Pos, export_step, export_stl, mirror

from .config import DEFAULT, CaseConfig
from .shell import reference_case
from .tent_layout import TentLayout, magnet_positions, solve_layout
from .tent_parts import flap, open_flap, stand_on_desk, tented_case


def describe(cfg: CaseConfig, layout: TentLayout) -> str:
    """Human-readable summary of the tenting geometry and the hardware it needs."""
    tent, m = cfg.tent, cfg.tent.magnets
    extra_height = layout.base_thickness - cfg.shell.floor_thickness
    lines = [
        f"Tent angle            {layout.tent_angle:.1f} deg",
        (
            f"Flap                  {layout.flap_length:.1f} mm long, {layout.flap_y[1] - layout.flap_y[0]:.1f} mm wide, "
            f"{layout.flap_thickness:.1f} mm thick"
        ),
        f"Flap opens            {layout.open_angle:.1f} deg, standing at {layout.lean_angle:.1f} deg to the desk",
        f"Inner edge rises      {layout.inner_edge_rise:.1f} mm above the desk",
        f"Foot sticks out       {layout.foot_overhang:.1f} mm past the inner edge (per half)",
        f"Case bottom           {layout.base_thickness:.1f} mm thick ({extra_height:.1f} mm more than stock)",
        f"Heel stop contact     {layout.stop_contact:.1f} mm wide",
        "",
        "Hardware per half:",
        f"  1x hinge pin, {tent.pin_diameter:g} mm rod, {layout.pin_length:.0f} mm long (pushed in from the back wall)",
    ]
    if m.enabled:
        count = 2 * len(magnet_positions(cfg, layout))
        lines.append(f"  {count}x disc magnet, {m.diameter:g} x {m.thickness:g} mm (glue in, attracting pairs)")
    return "\n".join(lines)


def _export(part: Part | Compound, out_dir: Path, name: str, stl: bool = True) -> None:
    export_step(part, out_dir / f"{name}.step")
    if stl:
        export_stl(part, out_dir / f"{name}.stl", tolerance=0.01, angular_tolerance=0.1)
    print(f"  wrote {name}")


def build(cfg: CaseConfig, out_dir: Path, include_reference: bool = True) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    layout = solve_layout(cfg)
    print(describe(cfg, layout))
    print(f"\nExporting to {out_dir}/")

    case_left = tented_case(cfg, layout)
    flap_left = flap(cfg, layout)
    parts: dict[str, Part] = {"tented_case": case_left, "flap": flap_left}
    if include_reference:
        parts["reference_case"] = reference_case(cfg)
    for name, left in parts.items():
        _export(left, out_dir, f"{name}_left")
        _export(mirror(left, Plane.YZ), out_dir, f"{name}_right")

    # Not for printing: the left half posed on the desk, to check the result by eye.
    posed = Compound(
        label="tented_preview",
        children=[stand_on_desk(case_left, layout), stand_on_desk(open_flap(flap_left, layout), layout)],
    )
    _export(posed, out_dir, "preview_tented_left", stl=False)


VIEWS = ("tented", "closed", "parts", "reference")


def view(cfg: CaseConfig, what: str, port: int | None) -> None:
    """Send the model to a running OCP CAD Viewer (VS Code extension or standalone)."""
    try:
        from ocp_vscode import show
    except ImportError as err:
        raise ValueError("OCP CAD Viewer support is not installed; run `uv sync` to get the dev dependencies") from err

    layout = solve_layout(cfg)
    if what == "reference":
        objects = {"reference_case": reference_case(cfg)}
    else:
        case_part, flap_part = tented_case(cfg, layout), flap(cfg, layout)
        if what == "tented":  # standing on the desk, flap open
            case_part = stand_on_desk(case_part, layout)
            flap_part = stand_on_desk(open_flap(flap_part, layout), layout)
        elif what == "parts":  # side by side, as printed
            flap_part = flap_part.moved(Pos(0, -130, 0))
        objects = {"case": case_part, "flap": flap_part}
    colors = {"case": "lightsteelblue", "flap": "darkorange", "reference_case": "lightsteelblue"}
    show(*objects.values(), names=list(objects), colors=[colors[n] for n in objects], port=port)


def main() -> None:
    parser = argparse.ArgumentParser(prog="lilytent", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    commands = (
        ("build", "export STEP and STL files"),
        ("info", "print the tenting geometry only"),
        ("view", "show the model in OCP CAD Viewer"),
    )
    for name, help_text in commands:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--tent-angle", type=float, help="override TentConfig.tent_angle (degrees)")
        p.add_argument("--lean-angle", type=float, help="override TentConfig.lean_angle (degrees)")
        if name == "build":
            p.add_argument("--out", type=Path, default=Path("out"), help="output directory (default: out)")
            p.add_argument("--no-reference", action="store_true", help="skip the stock (untented) case")
        if name == "view":
            p.add_argument("what", nargs="?", choices=VIEWS, default="tented", help="what to show (default: tented)")
            p.add_argument("--port", type=int, help="viewer port, if not the one OCP CAD Viewer picks by default")
    args = parser.parse_args()

    overrides = {k: v for k in ("tent_angle", "lean_angle") if (v := getattr(args, k)) is not None}
    cfg = dataclasses.replace(DEFAULT, tent=dataclasses.replace(DEFAULT.tent, **overrides))

    try:
        if args.command == "info":
            print(describe(cfg, solve_layout(cfg)))
        elif args.command == "view":
            view(cfg, args.what, args.port)
        else:
            build(cfg, args.out, include_reference=not args.no_reference)
    except ValueError as err:
        parser.exit(1, f"error: {err}\n")

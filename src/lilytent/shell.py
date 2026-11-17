"""The plain tray: floor and walls, plus the cut-outs every variant shares."""

from __future__ import annotations

from build123d import (
    Align,
    Cylinder,
    Part,
    Plane,
    Pos,
    Rectangle,
    RectangleRounded,
    Sketch,
    Solid,
    chamfer,
    extrude,
    fillet,
    loft,
)

from .config import CaseConfig, MountConfig, WallOpening
from .outline import outline

_EPS = 0.01
_C, _MIN = Align.CENTER, Align.MIN


def _edges_at_z(part: Part, z: float):
    """Edges lying entirely in the horizontal plane at height `z`."""
    return [
        e for e in part.edges() if abs(e.bounding_box().min.Z - z) < _EPS and abs(e.bounding_box().max.Z - z) < _EPS
    ]


def tray(cfg: CaseConfig, floor_thickness: float | None = None) -> Part:
    """Floor and walls, with edge treatments but no holes.

    `floor_thickness` overrides the configured value; the tented case uses it
    to get a thicker bottom. The top of the floor is at z = floor_thickness
    and the walls rise `wall_height` above that.
    """
    shell = cfg.shell
    floor = shell.floor_thickness if floor_thickness is None else floor_thickness
    total_height = floor + shell.wall_height

    body = extrude(outline(cfg.outline), total_height)
    if shell.bottom_fillet > 0:
        body = fillet(_edges_at_z(body, 0), shell.bottom_fillet)

    cavity = extrude(Pos(0, 0, floor) * outline(cfg.outline, inset=shell.wall_thickness), shell.wall_height)
    if shell.floor_fillet > 0:
        cavity = fillet(_edges_at_z(cavity, floor), shell.floor_fillet)

    body = body - cavity
    if shell.rim_chamfer > 0:
        body = chamfer(_edges_at_z(body, total_height), shell.rim_chamfer)
    return body


def _opening_profile(width: float, height: float, radius: float) -> Sketch:
    radius = min(radius, width / 2 - _EPS, height / 2 - _EPS)
    return RectangleRounded(width, height, radius) if radius > 0 else Rectangle(width, height)


def opening_cutter(opening: WallOpening, cfg: CaseConfig, floor_top: float) -> Part:
    """Solid to subtract from the tray to make one wall opening."""
    wall = cfg.shell.wall_thickness
    z = floor_top + opening.height_above_floor
    # Local frame: x along the wall, z pointing out through it, origin on the
    # inside face of the wall.
    if opening.wall == "back":
        plane = Plane(origin=(opening.position, cfg.outline.y_back - wall, z), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
        across, up = opening.width, opening.height
    elif opening.wall == "inner":
        plane = Plane(origin=(cfg.outline.x_inner - wall, opening.position, z), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        across, up = opening.width, opening.height
    else:
        raise ValueError(f"opening {opening.name!r}: unknown wall {opening.wall!r}")

    inner = _opening_profile(across, up, opening.corner_radius)
    margin = 1.0  # overshoot on both sides so the cut is clean
    cutter = extrude(Pos(0, 0, -margin) * inner, wall + 2 * margin)
    if opening.flare > 0:
        f = opening.flare
        outer = _opening_profile(across + 2 * f, up + 2 * f, opening.corner_radius + f)
        cutter += loft([inner, Pos(0, 0, wall) * outer])
        cutter += extrude(Pos(0, 0, wall) * outer, margin)
    return plane * cutter


def mount_hole_cutter(mounts: MountConfig, floor_top: float, seat_thickness: float) -> Part:
    """Screw holes through the floor.

    The floor is `seat_thickness` thick under each screw head. If the floor is
    thicker than that, the rest is opened up as a counterbore for the head.
    """
    seat_bottom = floor_top - seat_thickness
    cutters = []
    for x, y in mounts.positions:
        hole = Pos(x, y, seat_bottom - _EPS) * Cylinder(
            mounts.hole_diameter / 2, seat_thickness + 2 * _EPS, align=(_C, _C, _MIN)
        )
        if mounts.hole_edge_relief > 0:
            r = mounts.hole_diameter / 2
            relief = Solid.make_cone(r + mounts.hole_edge_relief, r, mounts.hole_edge_relief)
            hole += Pos(x, y, seat_bottom) * Part([relief])
        if seat_bottom > _EPS:
            hole += Pos(x, y, -_EPS) * Cylinder(mounts.head_bore_diameter / 2, seat_bottom + _EPS, align=(_C, _C, _MIN))
        cutters.append(hole)
    result = cutters[0]
    for c in cutters[1:]:
        result += c
    return result


def reference_case(cfg: CaseConfig) -> Part:
    """Recreation of the stock Typeractive case (left half)."""
    floor_top = cfg.shell.floor_thickness
    body = tray(cfg)
    for opening in cfg.openings:
        body -= opening_cutter(opening, cfg, floor_top)
    body -= mount_hole_cutter(cfg.mounts, floor_top, cfg.shell.floor_thickness)
    return body

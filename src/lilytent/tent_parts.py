"""The tented case and its flap.

Both parts are modelled for the left half with the flap closed, in the same
coordinate frame as the plain tray (see `config.py`). `tent_layout.py` does
the trigonometry; this module only turns its numbers into solids.
"""

from __future__ import annotations

import math

from build123d import (
    Align,
    Axis,
    Box,
    Cylinder,
    Part,
    Plane,
    Polygon,
    Pos,
    Rectangle,
    Rot,
    extrude,
)

from .config import CaseConfig
from .outline import outline
from .shell import mount_hole_cutter, opening_cutter, tray
from .tent_layout import TentLayout, Vec2, magnet_positions, rotate, solve_layout

_EPS = 0.01
_MIN3 = (Align.MIN, Align.MIN, Align.MIN)
_ON_FLOOR = (Align.CENTER, Align.CENTER, Align.MIN)


# --- small solid helpers ---------------------------------------------------


def _box(x: tuple[float, float], y: tuple[float, float], z: tuple[float, float]) -> Part:
    return Pos(x[0], y[0], z[0]) * Box(x[1] - x[0], y[1] - y[0], z[1] - z[0], align=_MIN3)


def _prism_xz(points: list[Vec2], y: tuple[float, float]) -> Part:
    """Extrude a polygon given as (x, z) points along y."""
    plane = Plane(origin=(0, y[0], 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0))  # local y is global -z
    profile = Polygon(*[(px, -pz) for px, pz in points], align=None)
    return extrude(plane * profile, y[1] - y[0], dir=(0, 1, 0))


def _cylinder_y(x: float, z: float, radius: float, y: tuple[float, float]) -> Part:
    """Cylinder with its axis along y."""
    return Pos(x, (y[0] + y[1]) / 2, z) * Rot(-90, 0, 0) * Cylinder(radius, y[1] - y[0])


def _disc(x: float, y: float, radius: float, z: tuple[float, float]) -> Part:
    """Cylinder with its axis along z."""
    return Pos(x, y, z[0]) * Cylinder(radius, z[1] - z[0], align=_ON_FLOOR)


def _widen(span: tuple[float, float], by: float) -> tuple[float, float]:
    return (span[0] - by, span[1] + by)


# --- magnets -----------------------------------------------------------------


def _magnet_levels(cfg: CaseConfig, layout: TentLayout) -> dict[str, float]:
    """z heights of the magnet stack, from the flap magnet up to the case magnet."""
    m = cfg.tent.magnets
    boss_bottom = layout.pocket_depth - m.boss_height
    recess_floor = boss_bottom - m.air_gap
    levels = {
        "flap_pocket_bottom": recess_floor - m.thickness - m.fit_clearance,
        "recess_floor": recess_floor,
        "boss_bottom": boss_bottom,
        "case_pocket_top": boss_bottom + m.thickness + m.fit_clearance,
    }
    if levels["flap_pocket_bottom"] < 0.5:
        raise ValueError("magnets leave under 0.5 mm of flap beneath them; reduce boss_height or magnet thickness")
    if levels["case_pocket_top"] > layout.base_thickness - 0.5:
        raise ValueError("magnets leave under 0.5 mm of case floor above them; increase boss_height")
    return levels


def _boss_radius(cfg: CaseConfig) -> float:
    m = cfg.tent.magnets
    return (m.diameter + m.fit_clearance) / 2 + m.boss_wall


# --- hinge -------------------------------------------------------------------


def _flap_knuckle(layout: TentLayout, span: tuple[float, float]) -> Part:
    """One flap knuckle: a barrel around the pin plus the heel that forms the stop.

    The heel is a wedge behind the hinge axis. One of its faces is cut so that
    it lies flat against the pocket ceiling when the flap has opened by
    `open_angle`; the barrel is small enough to turn freely until then.
    """
    hx, hz = layout.hinge
    t = layout.flap_thickness
    phi = math.radians(layout.open_angle)
    stop_normal = (math.sin(phi), math.cos(phi))  # normal of the stop face, flap closed
    along_stop = (math.cos(phi), -math.sin(phi))
    p1 = (layout.stop_height * stop_normal[0], layout.stop_height * stop_normal[1])
    p2 = (p1[0] + layout.stop_contact * along_stop[0], p1[1] + layout.stop_contact * along_stop[1])
    heel = [(0.0, 0.0), p1, p2, (0.0, -t / 2)]
    knuckle = _prism_xz([(hx + u, hz + w) for u, w in heel], span)
    knuckle += _cylinder_y(hx, hz, layout.knuckle_radius, span)
    return knuckle


def _case_knuckle(layout: TentLayout, span: tuple[float, float]) -> Part:
    """One fixed knuckle: a barrel around the pin, tied into the pocket ceiling and end wall.

    The tie only uses the space above the hinge axis. Below it, the edge of
    the flap sweeps past when the flap opens beyond 90 degrees.
    """
    hx, hz = layout.hinge
    r = layout.knuckle_radius
    overlap = 0.2  # sink into the surrounding case so the union is solid
    knuckle = _box((hx - r, layout.pocket_x[1] + overlap), span, (hz, layout.pocket_depth + overlap))
    knuckle += _cylinder_y(hx, hz, r, span)
    return knuckle


def _pin_hole(cfg: CaseConfig, layout: TentLayout, y: tuple[float, float]) -> Part:
    radius = (cfg.tent.pin_diameter + cfg.tent.pin_hole_clearance) / 2
    return _cylinder_y(layout.hinge[0], layout.hinge[1], radius, y)


# --- flap --------------------------------------------------------------------


def _foot_bevel_cutter(layout: TentLayout) -> Part:
    """Removes whatever part of the flap tip would be below the desk when open.

    This leaves a flat foot on the tip that sits square on the desk.
    """
    q = layout.foot_point
    # The desk, rotated back into the closed flap's frame.
    normal = rotate(layout.desk.normal, -layout.open_angle)
    along = (-normal[1], normal[0])
    size = 4 * layout.flap_thickness
    corners = [
        (q[0] + size * along[0], q[1] + size * along[1]),
        (q[0] - size * along[0], q[1] - size * along[1]),
        (q[0] - size * along[0] - size * normal[0], q[1] - size * along[1] - size * normal[1]),
        (q[0] + size * along[0] - size * normal[0], q[1] + size * along[1] - size * normal[1]),
    ]
    return _prism_xz(corners, _widen(layout.flap_y, 1.0))


def flap(cfg: CaseConfig, layout: TentLayout | None = None) -> Part:
    """The tenting flap (left half), in its closed position."""
    layout = layout or solve_layout(cfg)
    tent, mounts = cfg.tent, cfg.mounts
    t = layout.flap_thickness
    hx, _ = layout.hinge

    body = _box((layout.flap_x_tip, hx), layout.flap_y, (0, t))

    # Hinge end: gaps for the case knuckles, then the flap's own knuckles.
    for span in layout.case_knuckle_spans:
        body -= _box(
            (hx - layout.knuckle_radius - tent.heel_gap, hx + _EPS),
            _widen(span, tent.knuckle_gap),
            (-_EPS, t + _EPS),
        )
    for span in layout.flap_knuckle_spans:
        body += _flap_knuckle(layout, span)
    body -= _pin_hole(cfg, layout, _widen(layout.flap_y, 1.0))

    # Tip: foot bevel and finger notch.
    body -= _foot_bevel_cutter(layout)
    if tent.finger_notch_radius > 0:
        y_mid = (layout.flap_y[0] + layout.flap_y[1]) / 2
        body -= _disc(layout.flap_x_tip, y_mid, tent.finger_notch_radius, (-_EPS, t + _EPS))

    # Room for the case screw heads that stick down into the pocket.
    relief_z = (layout.pocket_depth - mounts.head_height, t + _EPS)
    for x, y in mounts.positions:
        body -= _disc(x, y, mounts.head_bore_diameter / 2, relief_z)

    # Magnets: a recess that clears the case boss, with the magnet pocket in its floor.
    if tent.magnets.enabled:
        m = tent.magnets
        levels = _magnet_levels(cfg, layout)
        for x, y in magnet_positions(cfg, layout):
            body -= _disc(x, y, _boss_radius(cfg) + m.boss_clearance, (levels["recess_floor"], t + _EPS))
            body -= _disc(
                x, y, (m.diameter + m.fit_clearance) / 2, (levels["flap_pocket_bottom"], levels["recess_floor"] + _EPS)
            )
    return body


# --- case --------------------------------------------------------------------


def _check_pocket_fits(cfg: CaseConfig, layout: TentLayout) -> None:
    """The pocket must stay inside the footprint with some solid rim around it."""
    min_wall = 1.6
    allowed = outline(cfg.outline, inset=min_wall)
    (x0, x1), (y0, y1) = layout.pocket_x, layout.pocket_y
    pocket = Pos((x0 + x1) / 2, (y0 + y1) / 2) * Rectangle(x1 - x0, y1 - y0)
    outside = pocket - allowed
    if outside.area > 0.01:
        raise ValueError(
            f"flap pocket x={x0:.1f}..{x1:.1f}, y={y0:.1f}..{y1:.1f} comes within {min_wall} mm of the case edge; "
            "adjust hinge_x, flap_y_range or min_rim"
        )


def tented_case(cfg: CaseConfig, layout: TentLayout | None = None) -> Part:
    """The case with a thickened bottom, flap pocket and hinge (left half)."""
    layout = layout or solve_layout(cfg)
    _check_pocket_fits(cfg, layout)
    tent = cfg.tent
    floor_top = layout.base_thickness

    body = tray(cfg, floor_thickness=floor_top)
    for opening in cfg.openings:
        body -= opening_cutter(opening, cfg, floor_top)
    # Screws keep their original seat thickness; the rest of the thick bottom
    # is counterbored so the stock screws still reach the standoffs.
    body -= mount_hole_cutter(cfg.mounts, floor_top, cfg.shell.floor_thickness)

    body -= _box(layout.pocket_x, layout.pocket_y, (-_EPS, layout.pocket_depth))
    for span in layout.case_knuckle_spans:
        body += _case_knuckle(layout, span)

    if tent.magnets.enabled:
        m = tent.magnets
        levels = _magnet_levels(cfg, layout)
        for x, y in magnet_positions(cfg, layout):
            body += _disc(x, y, _boss_radius(cfg), (levels["boss_bottom"], layout.pocket_depth + 0.2))
            body -= _disc(
                x, y, (m.diameter + m.fit_clearance) / 2, (levels["boss_bottom"] - _EPS, levels["case_pocket_top"])
            )

    # The pin goes in through the back wall and ends in a blind hole past the flap.
    body -= _pin_hole(cfg, layout, (layout.pin_y[0], layout.pin_y[1] + 1.0))
    return body


# --- posing ------------------------------------------------------------------


def open_flap(flap_part: Part, layout: TentLayout, angle: float | None = None) -> Part:
    """The flap swung open about the hinge (fully, unless `angle` is given)."""
    angle = layout.open_angle if angle is None else angle
    hinge_axis = Axis((layout.hinge[0], 0, layout.hinge[1]), (0, 1, 0))
    return flap_part.rotate(hinge_axis, -angle)


def stand_on_desk(part: Part, layout: TentLayout) -> Part:
    """Tilt a part from case coordinates into the tented pose, with the desk at z = 0."""
    px, pz = layout.desk.point
    return part.rotate(Axis((px, 0, pz), (0, 1, 0)), -layout.tent_angle).moved(Pos(0, 0, -pz))

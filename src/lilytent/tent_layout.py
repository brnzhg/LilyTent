"""Works out the tenting geometry from the configuration. Pure maths, no CAD.

Everything here is a 2D problem in the x-z plane of the (untilted) case:

    desk . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
          \\                                       (the desk is drawn
           P = pivot: the outer bottom edge         tilted, the case
            \\         of the case                  level)
             \\
              \\  case underside (z = 0)
    ----------------------------------H = hinge axis
                                     /
                                    /  flap, opened by `open_angle`
                                   /
                                  F = foot: the flap tip, on the desk

The case is tilted by `tent_angle` about P, so in case coordinates the desk
is a line through P sloping down towards +x. The flap has to be long enough,
and opened far enough, for its tip to land on that line.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .config import CaseConfig

Vec2 = tuple[float, float]


def rotate(v: Vec2, degrees: float) -> Vec2:
    """Rotate a 2D vector counter-clockwise."""
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


@dataclass(frozen=True)
class DeskLine:
    """The desk as seen from the case's x-z plane."""

    point: Vec2  # any point on the line
    normal: Vec2  # unit normal, pointing from the desk towards the case

    def height(self, p: Vec2) -> float:
        """Signed height of `p` above the desk."""
        return (p[0] - self.point[0]) * self.normal[0] + (p[1] - self.point[1]) * self.normal[1]


@dataclass(frozen=True)
class TentLayout:
    """Derived dimensions shared by the case and the flap."""

    tent_angle: float
    open_angle: float  # how far the flap swings from closed to its stop
    lean_angle: float  # actual angle between the open flap and the desk
    flap_length: float  # hinge axis to flap tip
    flap_thickness: float

    hinge: Vec2  # hinge axis (x, z)
    knuckle_radius: float
    stop_height: float  # pocket ceiling above the hinge axis; the heel stops against it
    stop_contact: float  # width of the heel face that meets the ceiling
    heel_reach: float  # how far the heel swings out behind the hinge axis

    pocket_depth: float
    base_thickness: float  # total thickness of the case bottom (floor + pocket)
    pocket_x: tuple[float, float]
    pocket_y: tuple[float, float]
    flap_x_tip: float
    flap_y: tuple[float, float]

    desk: DeskLine
    foot_point: Vec2  # point on the flap tip that sits on the desk, flap closed
    knuckle_spans: tuple[tuple[float, float], ...]  # y ranges, alternating flap/case/flap...

    pin_length: float
    pin_y: tuple[float, float]  # blind end, open end (at the back wall)
    inner_edge_rise: float  # height of the case's inner bottom edge above the desk
    foot_overhang: float  # how far the foot sticks out past the inner edge, along the desk

    @property
    def flap_knuckle_spans(self) -> tuple[tuple[float, float], ...]:
        return self.knuckle_spans[0::2]

    @property
    def case_knuckle_spans(self) -> tuple[tuple[float, float], ...]:
        return self.knuckle_spans[1::2]


def _solve_open_angle(desk: DeskLine, hinge: Vec2, tip: Vec2, tent_angle: float) -> float:
    """Open angle at which `tip` (relative to the hinge, flap closed) lands on the desk.

    There are two such angles; we want the larger one, where the flap has
    swung past perpendicular-to-the-desk and its tip sits out beyond the hinge.
    """

    def height(angle: float) -> float:
        r = rotate(tip, angle)
        return desk.height((hinge[0] + r[0], hinge[1] + r[1]))

    lo, hi = 90.0 - tent_angle, 180.0 - tent_angle  # deepest point .. flap parallel to desk
    if height(lo) > 0:
        raise ValueError("flap is too short to reach the desk at this tent angle")
    for _ in range(60):
        mid = (lo + hi) / 2
        if height(mid) > 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def solve_layout(cfg: CaseConfig) -> TentLayout:
    tent, shell, outline = cfg.tent, cfg.shell, cfg.outline
    if not 0 < tent.tent_angle <= 60:
        raise ValueError("tent_angle must be between 0 and 60 degrees")
    if tent.knuckle_count < 3 or tent.knuckle_count % 2 == 0:
        raise ValueError("knuckle_count must be odd and at least 3")

    t = tent.flap_thickness
    pin_hole = tent.pin_diameter + tent.pin_hole_clearance
    if t < pin_hole + 2.0:
        raise ValueError("flap_thickness leaves less than 1 mm of plastic around the hinge pin")

    pocket_depth = t + tent.ceiling_gap
    base_thickness = shell.floor_thickness + pocket_depth
    hinge = (tent.hinge_x, t / 2)
    knuckle_radius = t / 2
    stop_height = t / 2 + tent.ceiling_gap

    # The desk, in case coordinates: tangent to the bottom fillet of the outer
    # edge, sloping down towards +x.
    theta = math.radians(tent.tent_angle)
    normal = (math.sin(theta), math.cos(theta))
    r = shell.bottom_fillet
    fillet_centre = (outline.x_outer + r, r)
    desk = DeskLine(
        point=(fillet_centre[0] - r * normal[0], fillet_centre[1] - r * normal[1]),
        normal=normal,
    )

    # Flap length: as asked for by lean_angle, limited by what fits.
    hinge_height = desk.height(hinge)
    wanted = hinge_height / math.sin(math.radians(tent.lean_angle))
    longest = tent.hinge_x - (outline.x_outer + tent.min_rim) - tent.tip_gap
    flap_length = min(wanted, longest)
    if flap_length < 4 * t:
        raise ValueError("tent_angle is too small for a sensible flap; lower hinge_x or raise the angle")

    foot_local = (-flap_length, -t / 2 + tent.foot_land)  # relative to hinge, flap closed
    try:
        open_angle = _solve_open_angle(desk, hinge, foot_local, tent.tent_angle)
    except ValueError as err:
        raise ValueError(
            f"a {tent.tent_angle} degree tent needs a flap longer than the {longest:.1f} mm that fits; "
            "move hinge_x towards the inner wall or reduce tent_angle"
        ) from err
    lean_angle = 180.0 - tent.tent_angle - open_angle

    # Heel stop: a flat on the hinge end of the flap that lies against the
    # pocket ceiling once the flap has opened by open_angle.
    phi = math.radians(open_angle)
    stop_contact = (stop_height * math.cos(phi) + t / 2) / math.sin(phi)
    if stop_contact < tent.min_stop_contact:
        raise ValueError(
            f"heel stop would only be {stop_contact:.2f} mm wide (open angle {open_angle:.0f} degrees); "
            "use a larger tent_angle or a smaller lean_angle"
        )
    heel_reach = max(math.hypot(stop_height, stop_contact), knuckle_radius)

    flap_x_tip = tent.hinge_x - flap_length
    y0, y1 = tent.flap_y_range
    # The pocket's end wall has to clear the swinging heel, and (once the flap
    # opens past 90 degrees) the flap's flush face leaning back towards it.
    face_clearance = (t / 2 * (1 - math.cos(phi)) + tent.heel_gap) / math.sin(phi)
    end_wall = tent.hinge_x + max(heel_reach + tent.heel_gap, face_clearance)
    pocket_x = (flap_x_tip - tent.tip_gap, end_wall)
    pocket_y = (y0 - tent.side_gap, y1 + tent.side_gap)

    # Knuckles: equal spans along the hinge with a small gap between them.
    n, gap = tent.knuckle_count, tent.knuckle_gap
    span = (y1 - y0 - (n - 1) * gap) / n
    knuckle_spans = tuple((y0 + i * (span + gap), y0 + i * (span + gap) + span) for i in range(n))

    pin_y = (pocket_y[0] - tent.pin_blind_depth, outline.y_back)

    inner_bottom = (outline.x_inner, 0.0)
    foot_open = rotate(foot_local, open_angle)
    foot_open = (hinge[0] + foot_open[0], hinge[1] + foot_open[1])
    along = (math.cos(theta), -math.sin(theta))  # desk direction, towards the inner side
    foot_overhang = (foot_open[0] - inner_bottom[0]) * along[0] + (foot_open[1] - inner_bottom[1]) * along[1]

    return TentLayout(
        tent_angle=tent.tent_angle,
        open_angle=open_angle,
        lean_angle=lean_angle,
        flap_length=flap_length,
        flap_thickness=t,
        hinge=hinge,
        knuckle_radius=knuckle_radius,
        stop_height=stop_height,
        stop_contact=stop_contact,
        heel_reach=heel_reach,
        pocket_depth=pocket_depth,
        base_thickness=base_thickness,
        pocket_x=pocket_x,
        pocket_y=pocket_y,
        flap_x_tip=flap_x_tip,
        flap_y=(y0, y1),
        desk=desk,
        foot_point=(hinge[0] + foot_local[0], hinge[1] + foot_local[1]),
        knuckle_spans=knuckle_spans,
        pin_length=pin_y[1] - pin_y[0],
        pin_y=pin_y,
        inner_edge_rise=desk.height(inner_bottom),
        foot_overhang=foot_overhang,
    )


def magnet_positions(cfg: CaseConfig, layout: TentLayout) -> tuple[tuple[float, float], ...]:
    """x-y centres of the flap-latching magnets."""
    m = cfg.tent.magnets
    if not m.enabled:
        return ()
    x = layout.flap_x_tip + m.inset_from_tip
    y0, y1 = layout.flap_y
    return ((x, y0 + m.inset_from_sides), (x, y1 - m.inset_from_sides))

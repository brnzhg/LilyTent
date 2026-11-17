"""2D footprint of the case.

The footprint can be built at any inset from the outer wall, which is how the
cavity inside the walls is made. Each piece is inset analytically (lines
shifted, radii changed) rather than with a generic CAD offset, because
offsetting the spline corner leaves sliver faces that do not survive a STEP
export.
"""

from __future__ import annotations

import math

from build123d import CenterArc, Face, Polyline, Sketch, Spline, Vertex, Wire, fillet

from .config import OutlineConfig, Point2

Line2 = tuple[Point2, Point2]


def _shift_right(a: Point2, b: Point2, distance: float) -> Line2:
    """The line a->b moved `distance` to its right-hand side.

    The outline is traversed clockwise, so "right" is towards the interior.
    """
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    ox, oy = dy / length * distance, -dx / length * distance
    return ((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy))


def _intersect(l1: Line2, l2: Line2) -> Point2:
    """Intersection of two infinite lines."""
    (x1, y1), (x2, y2) = l1
    (x3, y3), (x4, y4) = l2
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    a, b = x1 * y2 - y1 * x2, x3 * y4 - y3 * x4
    return ((a * (x3 - x4) - (x1 - x2) * b) / denom, (a * (y3 - y4) - (y1 - y2) * b) / denom)


def _line_circle(line: Line2, centre: Point2, radius: float, near: Point2) -> Point2:
    """Where an infinite line crosses a circle, choosing the crossing closest to `near`."""
    (x1, y1), (x2, y2) = line
    dx, dy = x2 - x1, y2 - y1
    fx, fy = x1 - centre[0], y1 - centre[1]
    a, b, c = dx * dx + dy * dy, 2 * (fx * dx + fy * dy), fx * fx + fy * fy - radius * radius
    root = math.sqrt(b * b - 4 * a * c)
    points = [(x1 + t * dx, y1 + t * dy) for t in ((-b - root) / (2 * a), (-b + root) / (2 * a))]
    return min(points, key=lambda p: math.dist(p, near))


def _vertex_at(sketch: Sketch, point: Point2) -> Vertex:
    """The sketch vertex closest to `point`."""
    return min(sketch.vertices(), key=lambda v: math.hypot(v.X - point[0], v.Y - point[1]))


def _back_curve(cfg: OutlineConfig, inset: float) -> Spline:
    """The curved back-outer corner, from the outer wall up to the back wall."""
    start = (cfg.x_outer, cfg.back_curve_start_y)
    end = (cfg.back_curve_end_x, cfg.y_back)
    outer = Spline(
        start,
        *cfg.back_curve_points,
        end,
        tangents=((0, 1), (1, 0)),
        tangent_scalars=(1, 1),  # the default scaling makes the curve overshoot
    )
    if inset == 0:
        return outer
    # Inset copy: sample the outer curve and move each sample inwards along its normal.
    samples = 24
    points = []
    for i in range(samples + 1):
        p, t = outer.position_at(i / samples), outer.tangent_at(i / samples)
        points.append((p.X + t.Y * inset, p.Y - t.X * inset))
    return Spline(*points, tangents=((0, 1), (1, 0)), tangent_scalars=(1, 1))


def outline(cfg: OutlineConfig, inset: float = 0.0) -> Sketch:
    """Footprint of the case as a single face on the XY plane.

    `inset` = 0 gives the outside of the walls; a positive value gives the
    same shape shrunk inwards by that distance.
    """
    d = inset
    x_outer, x_inner = cfg.x_outer + d, cfg.x_inner - d
    y_back, y_front, y_thumb = cfg.y_back - d, cfg.y_front + d, cfg.thumb_y_front + d
    x_step = cfg.thumb_x_start + d

    # Arc down the inner edge, and the straight run from its end to the thumb tip.
    arc_centre = (cfg.x_inner - cfg.inner_arc_radius, cfg.inner_arc_start_y)
    arc_radius = cfg.inner_arc_radius - d
    sweep = math.radians(-cfg.inner_arc_sweep)
    outer_arc_end = (
        arc_centre[0] + cfg.inner_arc_radius * math.cos(sweep),
        arc_centre[1] + cfg.inner_arc_radius * math.sin(sweep),
    )
    thumb_edge = _shift_right(outer_arc_end, cfg.thumb_tip, d)
    thumb_diagonal_line = _shift_right(cfg.thumb_tip, (cfg.thumb_diagonal_x, cfg.thumb_y_front), d)
    thumb_front_line: Line2 = ((0.0, y_thumb), (1.0, y_thumb))

    arc_start = (x_inner, arc_centre[1])
    arc_end = _line_circle(thumb_edge, arc_centre, arc_radius, near=outer_arc_end)
    arc_end_angle = math.degrees(math.atan2(arc_end[1] - arc_centre[1], arc_end[0] - arc_centre[0]))

    back_inner = (x_inner, y_back)
    thumb_tip = _intersect(thumb_edge, thumb_diagonal_line)
    thumb_diagonal = _intersect(thumb_diagonal_line, thumb_front_line)
    thumb_front = (x_step, y_thumb)
    step = (x_step, y_front)
    front_outer = (x_outer, y_front)
    curve_start = (x_outer, cfg.back_curve_start_y)
    curve_end = (cfg.back_curve_end_x, y_back)

    pieces = [
        Polyline(curve_end, back_inner, arc_start),
        CenterArc(arc_centre, arc_radius, 0, arc_end_angle),
        Polyline(arc_end, thumb_tip, thumb_diagonal, thumb_front, step, front_outer, curve_start),
        _back_curve(cfg, d),
    ]
    face = Face(Wire([e for piece in pieces for e in piece.edges()]))
    if face.normal_at().Z < 0:  # make sure extrusions go up
        face = -face
    sketch = Sketch([face])

    # Convex corners get tighter when inset; the one concave corner gets wider.
    corners = (
        (back_inner, cfg.r_back_inner - d),
        (thumb_tip, cfg.r_thumb_tip - d),
        (thumb_front, cfg.r_thumb_front - d),
        (step, cfg.r_step + d),
        (front_outer, cfg.r_front_outer - d),
    )
    for point, radius in corners:
        if radius > 0:
            sketch = fillet(_vertex_at(sketch, point), radius)
    return sketch

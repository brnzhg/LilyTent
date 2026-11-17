"""All tunable dimensions for the case, in millimetres and degrees.

Coordinate frame (left half, looking down into the case):

    +x  towards the inner edge (where the two halves face each other)
    +y  towards the back (the USB-C side)
    +z  up; z = 0 is the underside of the case

The x/y origin is the origin of the reference model, so numbers here can be
compared directly against measurements taken from the reference STEP file.
The right half is a mirror image of the left one about the YZ plane.

Edit the values in this file (or build your own `CaseConfig`) and re-run
`uv run lilytent build`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Point2 = tuple[float, float]


@dataclass(frozen=True)
class OutlineConfig:
    """Outer footprint of the case, measured from the reference model.

    The footprint is a rectangle-ish main block, a thumb-cluster block hanging
    off the front on the inner side, a gently curved back-outer corner, and a
    large-radius arc running down the inner edge to the thumb tip.
    """

    x_outer: float = -78.0  # outer (pinky side) wall
    x_inner: float = 69.72  # inner wall
    y_back: float = 46.52  # back wall (USB side)
    y_front: float = -42.384  # front wall of the main block

    # Thumb block: steps down from the main block's front wall.
    thumb_x_start: float = -30.86  # where the front wall steps down
    thumb_y_front: float = -57.099  # front wall of the thumb block
    thumb_diagonal_x: float = 31.499  # front wall turns towards the thumb tip here
    thumb_tip: Point2 = (47.170, -66.174)  # sharp (pre-fillet) tip of the thumb corner

    # Arc along the inner edge, tangent to the inner wall at `inner_arc_start_y`.
    inner_arc_radius: float = 76.0
    inner_arc_start_y: float = -7.59
    inner_arc_sweep: float = 25.4  # degrees

    # Back-outer corner: a spline from the outer wall up to the back wall.
    # It leaves the outer wall vertically at `back_curve_start_y`, passes
    # through `back_curve_points` and meets the back wall horizontally at
    # `back_curve_end_x`.
    back_curve_start_y: float = 37.64
    back_curve_end_x: float = -17.19
    back_curve_points: tuple[Point2, ...] = (
        (-77.83, 38.57),
        (-77.16, 39.79),
        (-76.14, 40.70),
        (-74.47, 41.62),
        (-71.16, 42.63),
        (-65.37, 43.77),
        (-57.05, 44.82),
        (-48.09, 45.56),
        (-37.06, 46.14),
        (-27.27, 46.43),
    )

    # Corner radii of the outer wall.
    r_back_inner: float = 3.64  # back / inner-wall corner
    r_thumb_tip: float = 3.44
    r_thumb_front: float = 4.09  # thumb block front-outer corner
    r_step: float = 0.89  # concave corner where the thumb block starts
    r_front_outer: float = 4.09  # main block front-outer corner


@dataclass(frozen=True)
class ShellConfig:
    """The tray itself: walls and floor."""

    wall_thickness: float = 1.5
    floor_thickness: float = 1.5
    # Height of the walls above the top of the floor. Everything inside the
    # case (PCB, standoffs, plate) is referenced to the top of the floor.
    wall_height: float = 15.0
    rim_chamfer: float = 0.25  # both edges of the top rim
    bottom_fillet: float = 0.8  # outer bottom edge
    floor_fillet: float = 0.75  # inside edge where wall meets floor


@dataclass(frozen=True)
class WallOpening:
    """A rounded-rectangle hole through a straight wall.

    `flare` widens the hole towards the outside of the wall (a chamfered
    lead-in around the opening).
    """

    name: str
    wall: Literal["back", "inner"]
    position: float  # centre along the wall: x for the back wall, y for the inner wall
    height_above_floor: float  # centre height above the top of the floor
    width: float
    height: float
    corner_radius: float
    flare: float = 0.0


@dataclass(frozen=True)
class MountConfig:
    """Screws through the floor into the PCB standoffs."""

    positions: tuple[Point2, ...] = (
        (-55.94, 19.00),
        (-55.94, -19.12),
        (20.03, 21.20),
        (20.03, -16.73),
        (44.65, -33.93),
    )
    hole_diameter: float = 2.5
    hole_edge_relief: float = 0.3  # chamfer on the underside of each hole

    # Only used by the tented case, whose bottom is thicker than the screws
    # are long: the screw heads sit in a counterbore so the original screws
    # still reach the standoffs.
    head_bore_diameter: float = 5.5
    head_height: float = 2.0  # room left for a screw head


@dataclass(frozen=True)
class MagnetConfig:
    """Disc magnets that hold the flap shut (one pair per position)."""

    enabled: bool = True
    diameter: float = 6.0
    thickness: float = 2.0
    fit_clearance: float = 0.1  # added to the pocket diameter and depth
    # Magnets sit near the free end of the flap, this far in from its tip
    # and from each side edge.
    inset_from_tip: float = 20.0
    inset_from_sides: float = 9.0
    # The case-side magnet lives in a boss hanging below the pocket ceiling;
    # the flap has a matching recess.
    boss_wall: float = 1.2
    boss_height: float = 2.0
    boss_clearance: float = 0.5  # radial gap between boss and flap recess
    air_gap: float = 0.1  # between the two magnets when the flap is shut


@dataclass(frozen=True)
class TentConfig:
    """The fold-out tenting flap and its hinge.

    The flap is a single plate hinged near the inner edge of the case. Closed,
    it sits in a pocket flush with the underside. Open, it swings down until a
    heel on its hinge end meets the pocket ceiling; the case then rests on its
    outer bottom edge and on the tip of the flap.

    The tent angle is baked into the print: it sets the flap length, the heel
    angle and the bevel on the flap tip, and the pocket is sized to the flap.
    """

    tent_angle: float = 45.0  # degrees the case is tilted when the flap is open
    # Preferred angle between the open flap and the desk. 90 puts the flap
    # tip straight under the hinge (most compact); smaller values kick the tip
    # out past the hinge, which resists tipping when pressing the inner keys
    # but needs a longer flap and more room between the two halves. If the
    # flap this asks for does not fit in the case, the longest one that fits
    # is used instead.
    lean_angle: float = 55.0

    flap_thickness: float = 5.0
    flap_y_range: tuple[float, float] = (-37.0, 39.0)  # front/back extent of the flap
    hinge_x: float = 57.0  # x position of the hinge axis
    min_rim: float = 3.0  # solid case bottom kept between the flap tip and the outer wall

    # Clearances between flap and pocket.
    ceiling_gap: float = 0.3
    side_gap: float = 0.3
    tip_gap: float = 0.4
    heel_gap: float = 0.4  # behind the heel as it swings

    # Hinge: a straight rod pushed in through the back wall.
    pin_diameter: float = 2.0
    pin_hole_clearance: float = 0.25  # added to the pin diameter for every pin hole
    pin_blind_depth: float = 4.0  # how far the pin continues into the case past the flap
    knuckle_count: int = 7  # odd; flap knuckles at both ends, case knuckles between
    knuckle_gap: float = 0.3  # axial gap between neighbouring knuckles
    min_stop_contact: float = 1.0  # refuse to build if the heel stop is narrower than this

    # Flap tip.
    foot_land: float = 0.6  # blunt edge left on the flush face at the tip
    finger_notch_radius: float = 9.0  # scallop in the tip for opening the flap; 0 to omit

    magnets: MagnetConfig = field(default_factory=MagnetConfig)


def _default_openings() -> tuple[WallOpening, ...]:
    return (
        WallOpening(
            name="usb",
            wall="back",
            position=49.72,
            height_above_floor=7.605,
            width=11.0,
            height=6.0,
            corner_radius=1.5,
        ),
        WallOpening(
            name="power_switch",
            wall="inner",
            position=37.52,
            height_above_floor=6.0,
            width=6.0,
            height=3.5,
            corner_radius=0.5,
            flare=0.87,
        ),
        WallOpening(
            name="reset_button",
            wall="inner",
            position=26.47,
            height_above_floor=4.2,
            width=3.6,
            height=2.0,
            corner_radius=0.3,
            flare=1.5,
        ),
    )


@dataclass(frozen=True)
class CaseConfig:
    outline: OutlineConfig = field(default_factory=OutlineConfig)
    shell: ShellConfig = field(default_factory=ShellConfig)
    openings: tuple[WallOpening, ...] = field(default_factory=_default_openings)
    mounts: MountConfig = field(default_factory=MountConfig)
    tent: TentConfig = field(default_factory=TentConfig)


DEFAULT = CaseConfig()

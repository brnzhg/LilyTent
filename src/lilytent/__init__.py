"""Parametric 3D-printable case for the Typeractive Lily58, with built-in tenting."""

from .config import DEFAULT, CaseConfig
from .shell import reference_case
from .tent_layout import TentLayout, solve_layout
from .tent_parts import flap, open_flap, stand_on_desk, tented_case

__all__ = [
    "DEFAULT",
    "CaseConfig",
    "TentLayout",
    "flap",
    "open_flap",
    "reference_case",
    "solve_layout",
    "stand_on_desk",
    "tented_case",
]

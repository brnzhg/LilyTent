"""Phase 1: the plain tray should match the reference model."""

from pathlib import Path

import numpy as np
import pytest
from build123d import Vertex, import_step

from lilytent import DEFAULT, reference_case

REFERENCE_STEP = Path(__file__).parent.parent / "reference" / "lily58-case-typeractive_reference.step"
REFERENCE_FLOOR_Y = 21.76  # the reference is Y-up and upside down; this is its underside


@pytest.fixture(scope="module")
def case():
    return reference_case(DEFAULT)


def test_is_one_valid_solid(case):
    assert case.is_valid
    assert len(case.solids()) == 1


def test_overall_size(case):
    size = case.bounding_box().size
    assert size.X == pytest.approx(147.72, abs=0.05)
    assert size.Y == pytest.approx(111.45, abs=0.05)
    assert size.Z == pytest.approx(16.5, abs=0.01)


def _reference_vertices() -> np.ndarray:
    """Vertices of the reference mesh, converted to the model's coordinate frame."""
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location

    face = import_step(REFERENCE_STEP).faces()[0]
    mesh = BRep_Tool.Triangulation_s(face.wrapped, TopLoc_Location())
    nodes = np.array([[mesh.Node(i).X(), mesh.Node(i).Y(), mesh.Node(i).Z()] for i in range(1, mesh.NbNodes() + 1)])
    return np.c_[nodes[:, 0], nodes[:, 2], REFERENCE_FLOOR_Y - nodes[:, 1]]


@pytest.mark.skipif(not REFERENCE_STEP.exists(), reason="reference STEP file not present")
def test_matches_reference_mesh(case):
    points = _reference_vertices()[::8]
    surface = case.solids()[0].shells()[0]
    distances = np.array([Vertex(*p).distance_to(surface) for p in points])
    assert np.percentile(distances, 95) < 0.15
    assert distances.max() < 0.5

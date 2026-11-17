# LilyTent

Parametric build123d model of a Typeractive Lily58 case with a fold-out tenting
flap. Personal project; parts are for FDM printing.

## Commands

- `uv run lilytent build` exports STEP/STL to `out/` (gitignored)
- `uv run lilytent info` prints the solved tent geometry and hardware list
- `uv run lilytent view [tented|closed|parts|reference]` sends the model to a running OCP CAD Viewer (VS Code extension, or `uv run python -m ocp_viewer` for the browser one)
- `uv run pytest` runs the tests (about 10 s)
- `uv run mypy` type-checks `src` and `tests`
- Dependencies are managed with uv: `uv add <pkg>`, never pip

## Layout

- `src/lilytent/config.py`: every dimension, as frozen dataclasses. Also documents the coordinate frame. Change numbers here first
- `outline.py`: 2D footprint, at any inset from the outer wall (inset analytically; build123d's `offset` on the spline corner leaves sliver faces that break STEP export)
- `shell.py`: tray, wall openings, screw holes, and `reference_case()` (the stock case)
- `tent_layout.py`: pure-maths solver for the tenting geometry (flap length, open angle, heel stop, pocket). No CAD
- `tent_parts.py`: `tented_case()` and `flap()` solids, plus posing helpers
- `cli.py`: export and summary
- `reference/`: the downloaded stock-case STEP (gitignored, may be absent)

## Conventions

- Model the left half only, flap closed. The right half is mirrored about the YZ plane at export
- z = 0 is the underside of the case. Internal features are placed relative to the top of the floor, so the bottom can change thickness without moving them
- No magic numbers in the geometry modules: add a field to `config.py` with a comment saying what it is
- Derived tenting values belong in `TentLayout`, so the case and the flap cannot disagree
- Raise `ValueError` with a message naming the config field to change when a configuration cannot be built
- Uses build123d's algebra API (`part = a + b - c`), not builder contexts

## Reference model

The reference STEP is a triangle mesh, not B-rep, Y-up and upside down. Model
frame from reference frame: `(x, y, z) = (X, Z, 21.76 - Y)`.
`tests/test_reference_case.py` compares the rebuilt tray against it.

## Verifying changes

After touching the hinge or flap, run the tests: they check for collisions
through the whole swing at several tent angles. For a visual check, open
`out/preview_tented_left.step` in a CAD viewer.

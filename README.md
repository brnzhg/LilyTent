# LilyTent

A 3D-printable case for the [Typeractive Lily58 wireless](https://docs.typeractive.xyz/build-guides/lily58-wireless)
with a built-in, fold-flat tenting flap. Modelled in [build123d](https://build123d.readthedocs.io).

```
uv run lilytent build                  # writes STEP + STL files to out/
uv run lilytent build --tent-angle 30  # same, at a different tent angle
uv run lilytent build --no-tent        # only the stock-style case, no flap or thick bottom
uv run lilytent info                   # just print the geometry and hardware list
uv run lilytent view                   # show it in OCP CAD Viewer (see below)
uv run pytest
```

## Viewing

`lilytent view` sends the model to a running [OCP CAD Viewer](https://github.com/bernhard-42/vscode-ocp-cad-viewer):

- **VS Code**: install the "OCP CAD Viewer" extension, open the viewer panel, then run the command in the VS Code terminal.
- **Browser**: run `uv run python -m ocp_viewer` in one terminal, open http://127.0.0.1:3939/viewer, then run the command in another.

`uv run lilytent view [tented|closed|parts|reference]` picks what to show: standing on the
desk with the flap open (default), flap closed, case and flap side by side, or the stock case.
`--tent-angle` and `--lean-angle` work here too.

## What gets built

| File (`_left` / `_right`)  | What it is |
|----------------------------|------------|
| `reference_case`           | Recreation of the stock Typeractive tray (no tenting) |
| `tented_case`              | The tray with a thicker bottom, flap pocket and hinge |
| `flap`                     | The tenting flap for that case |
| `preview_tented_left.step` | Left half posed on the desk with the flap open. For viewing only |

## How the tenting works

Each half has one flap, hinged near the inner edge and folding into a pocket in
the underside. Closed, it is flush with the bottom of the case and held by
magnets. Open, it swings down until a heel on its hinge end meets the pocket
ceiling, and the half stands on its outer bottom edge and the flap tip.

The tent angle is fixed per print. `tent_angle` sets the flap length, the heel
angle and the bevel on the flap tip, and the pocket in the case is cut to match,
so **changing the angle means reprinting both the case and the flap**.

`lean_angle` is the angle between the open flap and the desk. Lower values push
the flap tip further out past the hinge. That resists tipping when you press the
innermost keys, but the tips of the two halves then need more room between them
(`lilytent info` prints how far each one sticks out).

The case internals are unchanged: the top of the floor, the walls, the port
openings and the screw holes are where they are in the stock case. The bottom is
5.3 mm thicker, and the screw heads sit in counterbores so the stock screws and
standoffs still fit.

## Hardware (per half)

Run `uv run lilytent info` for exact numbers at your settings. With the defaults:

- 1 × 2 mm steel rod, 88 mm long, as the hinge pin
- 4 × 6 × 2 mm disc magnets
- Optional: thin adhesive rubber on the flap tip and along the case's outer bottom edge

## Printing and assembly

- **Case**: print as modelled (underside on the bed). The flap pocket, hinge
  knuckles and magnet bosses need supports.
- **Flap**: print as modelled (flush face on the bed). No supports.
- Glue the magnets into the two bosses in the pocket and the two recesses in the
  flap, checking that each pair attracts.
- Put the flap in the pocket and push the rod in through the hole in the back
  wall until it is flush. It runs through every knuckle into a blind hole at the
  far end. If it is loose, a drop of glue at the entry hole holds it.
- Open the flap with a fingertip in the notch at its tip.

## Changing things

All dimensions live in `src/lilytent/config.py`. See `CLAUDE.md` for how the
code is laid out.

The reference model the stock case was measured from is not in this repository.
To run the comparison test, put it at
`reference/lily58-case-typeractive_reference.step`.

## Status

Not yet printed. The geometry is checked by the tests (flap fits, swings without
collision, stops at the right angle, reaches the desk), but printer-dependent
fits such as the pin holes, magnet pockets and flap clearances may need tuning.

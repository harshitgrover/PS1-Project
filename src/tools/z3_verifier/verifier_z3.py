"""Z3-backed verifier — the deterministic judge of the loop.

Inputs a concrete `HouseGeometry` (corners + door) and checks each SBC rule.
Returns a list of `Violation` records; empty list means the house passes.

Z3 is used to evaluate the algebraic constraints (setbacks, dimensions, tree
buffer). Point-in-polygon is handled in pure Python because Z3 adds no value
when the corners are already concrete numbers.
"""

from dataclasses import dataclass
from typing import Optional

from z3 import Real, Solver, sat, RealVal

from plot import Plot
from constraints import SBCConstraints


@dataclass(frozen=True)
class HouseGeometry:
    corners: tuple[tuple[float, float], ...]   # axis-aligned rect: SW, SE, NE, NW
    door: tuple[float, float]                   # door midpoint


@dataclass(frozen=True)
class Violation:
    rule: str
    measured_ft: float
    required_ft: float
    message: str


# Floating-point tolerance (feet). A constraint "measured >= required" is only
# flagged as violated when `measured` is below `required` by MORE than this slack,
# so near-exact matches (e.g. 19.9999998 vs 20) are not false failures. Override
# process-wide by setting verifier_z3.FLOAT_TOL (e.g. from a city-code config).
FLOAT_TOL = 1e-6


def _violated(measured: float, required: float, tol: float | None = None) -> bool:
    """True iff `measured < required - tol`, decided by Z3 (a deterministic
    proof, never a probabilistic guess). The tolerance avoids false-negative
    failures on near-exact equality. Keeping the algebra in Z3 also lets us
    swap concrete numbers for symbolic ones later (e.g. to *synthesize*)."""
    t = FLOAT_TOL if tol is None else tol
    s = Solver()
    x = Real("x")
    s.add(x == RealVal(measured))
    s.add(x < RealVal(required) - RealVal(t))
    return s.check() == sat


def _point_in_polygon(p: tuple[float, float], poly: tuple[tuple[float, float], ...]) -> bool:
    """Ray casting. Polygon may be CW or CCW; orientation irrelevant."""
    x, y = p
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_intersect = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_intersect:
                inside = not inside
    return inside


def check(house: HouseGeometry, plot: Plot, sbc: SBCConstraints,
          max_legal_area: float | None = None) -> list[Violation]:
    """Returns list of SBC violations. Empty list = all rules satisfied.

    `max_legal_area`: theoretical maximum house area for this (plot, sbc)
    pair, computed by `optimizer_z3.compute_max_area`. If provided, we enforce
    `house_area >= sbc.min_area_fraction_of_max * max_legal_area`."""
    violations: list[Violation] = []

    xs = [c[0] for c in house.corners]
    ys = [c[1] for c in house.corners]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    door_x, door_y = house.door

    px_min, py_min, px_max, py_max = plot.bbox
    tcx, tcy = plot.tree_center

    # --- Algebraic SBC constraints via Z3 ----------------------------------
    algebraic = [
        ("front_setback_south", y_min - py_min, sbc.front_setback_ft,
         "South (entry-side) setback"),
        ("rear_setback_north", py_max - y_max, sbc.rear_setback_ft,
         "North (rear) setback"),
        ("side_setback_west", x_min - px_min, sbc.side_setback_ft,
         "West side setback"),
        ("side_setback_east", px_max - x_max, sbc.side_setback_ft,
         "East side setback"),
        ("min_width_ew", x_max - x_min, sbc.min_house_width_ft,
         "Minimum house width (E-W)"),
        ("min_depth_ns", y_max - y_min, sbc.min_house_depth_ft,
         "Minimum house depth (N-S)"),
    ]
    for rule, measured, required, label in algebraic:
        if _violated(measured, required):
            violations.append(Violation(
                rule=rule, measured_ft=float(measured), required_ft=float(required),
                message=f"{label} is {measured:.2f} ft, need ≥ {required:.2f} ft."))

    # --- Tree protection (quadratic, also Z3-friendly) ---------------------
    dx = max(0.0, x_min - tcx, tcx - x_max)
    dy = max(0.0, y_min - tcy, tcy - y_max)
    dist = (dx * dx + dy * dy) ** 0.5
    min_dist = plot.tree_radius + sbc.tree_buffer_ft
    if _violated(dist, min_dist):
        violations.append(Violation(
            rule="tree_buffer",
            measured_ft=float(dist), required_ft=float(min_dist),
            message=(f"House comes within {dist:.2f} ft of the protected tree "
                     f"(center {plot.tree_center}); need ≥ {min_dist:.2f} ft "
                     "(trunk + buffer). Tree CANNOT be removed.")))

    # --- Door placement -----------------------------------------------------
    if abs(door_y - y_min) > 0.5:
        violations.append(Violation(
            rule="door_on_south_wall",
            measured_ft=float(door_y), required_ft=float(y_min),
            message=(f"Door y={door_y:.2f} is not on the south wall of the "
                     f"house (y_min={y_min:.2f}). SBC fire egress: main door "
                     "and parking must be on the same (entry) side.")))

    if not (x_min + sbc.door_corner_margin_ft <= door_x
            <= x_max - sbc.door_corner_margin_ft):
        violations.append(Violation(
            rule="door_corner_margin",
            measured_ft=float(door_x), required_ft=float(sbc.door_corner_margin_ft),
            message=(f"Door x={door_x:.2f} is too close to a house corner; "
                     f"need ≥ {sbc.door_corner_margin_ft} ft inset from both "
                     f"corners (house spans x∈[{x_min:.2f}, {x_max:.2f}]).")))

    if plot.entry_side == "S":
        seg_xs = sorted([plot.entry_segment[0][0], plot.entry_segment[1][0]])
        if not (seg_xs[0] <= door_x <= seg_xs[1]):
            violations.append(Violation(
                rule="door_within_entry_segment",
                measured_ft=float(door_x), required_ft=float(seg_xs[0]),
                message=(f"Door x={door_x:.2f} is outside the 40 ft entry "
                         f"segment x∈[{seg_xs[0]:.0f}, {seg_xs[1]:.0f}]. The "
                         "driveway must reach the door through this segment.")))

    # --- Containment: all corners inside the L-shape -----------------------
    for i, corner in enumerate(house.corners):
        if not _point_in_polygon(corner, plot.boundary):
            violations.append(Violation(
                rule=f"corner_inside_plot[{i}]",
                measured_ft=0.0, required_ft=0.0,
                message=(f"House corner {corner} lies outside the L-shaped "
                         "plot boundary. Pull the house in.")))

    # --- Max lot coverage (zoning cap: footprint ≤ fraction of lot area) ----
    footprint_area = (x_max - x_min) * (y_max - y_min)
    lot_cap = sbc.max_lot_coverage_fraction * plot.area
    # Area tolerance: a length rounded to 0.01 ft shifts a ~50 ft wall's area by
    # ~0.5 sq ft (area = length², so length slack is amplified). Use a 1 sq ft
    # floor + 0.1% so a footprint sitting exactly on the cap isn't false-failed.
    if _violated(lot_cap, footprint_area, tol=max(1.0, 1e-3 * lot_cap)):  # area > cap
        violations.append(Violation(
            rule="max_lot_coverage",
            measured_ft=float(footprint_area), required_ft=float(lot_cap),
            message=(f"Footprint {footprint_area:.0f} sq ft is "
                     f"{footprint_area/plot.area*100:.1f}% of the {plot.area:.0f} sq ft "
                     f"lot; zoning caps coverage at "
                     f"{sbc.max_lot_coverage_fraction*100:.0f}% (≤ {lot_cap:.0f} sq ft). "
                     "Shrink the footprint.")))

    # --- Area coverage (brief: "maximize area") ----------------------------
    if max_legal_area is not None:
        area = (x_max - x_min) * (y_max - y_min)
        required = sbc.min_area_fraction_of_max * max_legal_area
        if _violated(area, required):
            violations.append(Violation(
                rule="min_area_coverage",
                measured_ft=float(area), required_ft=float(required),
                message=(f"House footprint is {area:.0f} sq ft "
                         f"({area/max_legal_area*100:.1f}% of the Z3-computed "
                         f"max {max_legal_area:.0f} sq ft). Brief requires "
                         f"maximum area coverage — need ≥ {required:.0f} sq ft "
                         f"({sbc.min_area_fraction_of_max*100:.0f}% of max). "
                         "Expand the footprint by tightening any setback that "
                         "has slack.")))

    return violations


def passes(house: HouseGeometry, plot: Plot, sbc: SBCConstraints) -> bool:
    return len(check(house, plot, sbc)) == 0

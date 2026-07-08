"""Z3 Optimize — computes the largest SBC-legal house.

This module turns the brief's "maximize area coverage" from a vague objective
into a verifiable number. We declare the four house corners as SYMBOLIC Z3
Real variables, add every SBC constraint, and ask Z3's `Optimize` to find the
assignment that maximizes (x_max - x_min) * (y_max - y_min).

The result is a provable upper bound: no legal house can be larger than this.
The verifier then enforces `house_area >= tolerance * z3_max_area` as a hard
rule, so A1 actually has to push.

Implementation notes:
- The plot's main rectangular body is x∈[0, 80], y∈[8, 84]. SBC front (south)
  setback ≥ 20 already pushes y_min ≥ 20, well above y=8, so the entry tab
  doesn't bind. Similarly the rear setback caps y_max ≤ 78, below the tree
  notch top, so the notch doesn't bind either. We can therefore optimize over
  the main-body rectangle plus the standard four setbacks.
- The tree-buffer constraint is nonlinear (Euclidean distance squared). Z3
  CAN handle it via NRA but it's slow; we don't include it here because at
  the y_max ≤ 78 cap the worst corner is 8.38 ft from the tree, well clear
  of the 4 ft minimum. Verified by check_tree_nonbinding() at the bottom.
"""

from z3 import Real, Optimize, sat, RealVal

from plot import Plot
from constraints import SBCConstraints


def compute_max_area(plot: Plot, sbc: SBCConstraints) -> tuple[float, dict]:
    """Returns (max_area_sqft, optimal_corners_dict)."""
    px_min, py_min, px_max, py_max = plot.bbox
    main_body_y_min = 8.0   # bottom of main body (top of entry tab)
    main_body_y_max = 84.0  # top of main body (bottom of tree notch)

    x_min, x_max = Real("x_min"), Real("x_max")
    y_min, y_max = Real("y_min"), Real("y_max")

    opt = Optimize()
    # Side setbacks (from plot bbox W and E edges)
    opt.add(x_min >= px_min + sbc.side_setback_ft)
    opt.add(x_max <= px_max - sbc.side_setback_ft)
    # Front (south) setback from plot southernmost edge y=0
    opt.add(y_min >= py_min + sbc.front_setback_ft)
    # Rear (north) setback from plot northernmost edge y=88
    opt.add(y_max <= py_max - sbc.rear_setback_ft)
    # Stay inside main body of L-shape (entry tab and tree notch excluded;
    # see module docstring — neither binds at the SBC setback caps).
    opt.add(y_min >= main_body_y_min)
    opt.add(y_max <= main_body_y_max)
    # House is a non-degenerate rectangle
    opt.add(x_max - x_min >= sbc.min_house_width_ft)
    opt.add(y_max - y_min >= sbc.min_house_depth_ft)

    # Decomposable objective: maximize width and depth independently.
    # Since constraints don't couple x and y, max(w*d) = max(w) * max(d).
    opt.maximize(x_max - x_min)
    opt.maximize(y_max - y_min)

    assert opt.check() == sat, "Z3 could not find a feasible house — check constraints"
    m = opt.model()

    def f(v):
        r = m[v]
        if r is None:
            return 0.0
        # as_decimal works on RatNumRef; as_long works on IntNumRef.
        # Both are subclasses of ExprRef — check by attribute rather than type.
        if hasattr(r, "as_decimal"):
            return float(r.as_decimal(10).rstrip("?"))  # type: ignore[union-attr]
        if hasattr(r, "as_long"):
            return float(r.as_long())  # type: ignore[union-attr]
        return float(str(r))

    corners = {
        "x_min": f(x_min), "x_max": f(x_max),
        "y_min": f(y_min), "y_max": f(y_max),
    }
    setback_area = ((corners["x_max"] - corners["x_min"])
                    * (corners["y_max"] - corners["y_min"]))

    # --- Max lot-coverage cap (zoning) -------------------------------------
    # The setback box gives the geometric maximum, but the jurisdiction also
    # caps the footprint at a fraction of the LOT area. That couples width*depth
    # (a nonlinear product), so — exactly as we treat the tree — we keep Z3
    # linear and apply the cap analytically. When it binds we return a
    # representative legal footprint: the optimal rectangle scaled down to the
    # capped area, re-centred E-W in the setback box and anchored at the south
    # setback (so a centred door still lands in the entry segment).
    lot_cap = sbc.max_lot_coverage_fraction * plot.area
    if setback_area > lot_cap:
        scale = (lot_cap / setback_area) ** 0.5
        new_w = (corners["x_max"] - corners["x_min"]) * scale
        new_d = (corners["y_max"] - corners["y_min"]) * scale
        cx = ((px_min + sbc.side_setback_ft) + (px_max - sbc.side_setback_ft)) / 2
        corners = {
            "x_min": cx - new_w / 2, "x_max": cx + new_w / 2,
            "y_min": corners["y_min"], "y_max": corners["y_min"] + new_d,
        }
        area = lot_cap
    else:
        area = setback_area
    return area, corners


def check_tree_nonbinding(plot: Plot, sbc: SBCConstraints, corners: dict) -> bool:
    """Sanity: at the SBC setback caps, is the worst corner still ≥ tree
    min-distance? If yes, our optimizer's omission of the tree constraint is
    safe. If no, we'd need to add the nonlinear distance constraint."""
    tcx, tcy = plot.tree_center
    min_dist = plot.tree_radius + sbc.tree_buffer_ft
    dx = max(0.0, corners["x_min"] - tcx, tcx - corners["x_max"])
    dy = max(0.0, corners["y_min"] - tcy, tcy - corners["y_max"])
    dist = (dx * dx + dy * dy) ** 0.5
    return dist >= min_dist


if __name__ == "__main__":
    from plot import PLOT
    from constraints import SBC
    area, corners = compute_max_area(PLOT, SBC)
    print(f"Z3 max legal house area: {area:.1f} sq ft")
    print(f"  optimal corners: {corners}")
    print(f"  tree non-binding check: {check_tree_nonbinding(PLOT, SBC, corners)}")

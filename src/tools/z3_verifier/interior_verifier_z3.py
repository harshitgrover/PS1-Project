"""Z3-backed interior verifier — the deterministic judge for the floor plan.

The exterior verifier (verifier_z3.py) checks a single house *footprint*. This
module checks the *interior subdivision* of that footprint into rooms. Given a
concrete `InteriorLayout` (a list of axis-aligned `Room` rectangles) it returns
a list of `InteriorViolation` records; an empty list means the floor plan is
legal and well-formed.

Split of labor (same convention as verifier_z3.py):
  - Scalar/algebraic checks (areas, side lengths, shared-wall lengths) go
    through Z3 via `_violated`, so the SMT solver stays the single source of
    truth on the numeric comparisons.
  - Pure geometry (rectangle overlap, shared-wall length, adjacency-graph
    connectivity) is plain Python — Z3 adds nothing when the rectangles are
    already concrete numbers.

The constraint set (matches the richer 25-rule reference plus extras):

  SIZE (IRC R304/R305)
    room_min_area      every room meets its program minimum area
    room_min_side      no room has a side below its minimum (no slivers)
    room_max_side      bathrooms capped at 15 ft/side (no absurd 33x5 baths)
  STRUCTURE
    room_count         exactly 1 living + 1 kitchen + 1 corridor + 3 bed + 2 bath
    room_in_footprint  every room lies inside the verified house footprint
    no_overlap         no two rooms overlap (positive-area intersection)
    coverage           total room area within +/- 5% of the footprint
  BATHROOMS
    ensuite_attached   each bathroom shares a wall with a distinct bedroom
    bath_smaller       each bathroom is smaller than the bedroom it serves
    bath_not_adj_kitchen   no bathroom shares a wall with the kitchen (sanitation)
    baths_not_adjacent the two bathrooms do not share a wall
  CIRCULATION / SPATIAL
    living_near_south  living room sits within 2 ft of the south wall
    living_gt_bedroom  living room is larger than every bedroom
    door_in_living     the front door opens into the living room (egress)
    kitchen_by_living  kitchen shares a wall with the living room (open plan)
    corridor_width     corridor clear width >= 4 ft   (via room_min_side)
    corridor_fraction  circulation stays <= 15% of usable floor area
    connected          every room is reachable from every other (doorways)
"""

from dataclasses import dataclass
import re

from verifier_z3 import _violated, HouseGeometry  # reuse the Z3 scalar judge
from constraints import SBCConstraints
import rooms as program

EPS = 1e-6


# --------------------------------------------------------------------------- #
#  Data types
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Room:
    name: str
    kind: str          # living | kitchen | corridor | bedroom | bathroom
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def depth(self) -> float:
        return self.y_max - self.y_min

    @property
    def area(self) -> float:
        return self.width * self.depth

    @property
    def min_side(self) -> float:
        return min(self.width, self.depth)

    @property
    def max_side(self) -> float:
        return max(self.width, self.depth)

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2)


@dataclass(frozen=True)
class InteriorLayout:
    footprint: tuple[float, float, float, float]  # (x_min, y_min, x_max, y_max)
    door: tuple[float, float]
    rooms: tuple[Room, ...]

    @property
    def footprint_area(self) -> float:
        x0, y0, x1, y1 = self.footprint
        return (x1 - x0) * (y1 - y0)


@dataclass(frozen=True)
class InteriorViolation:
    rule: str
    measured_ft: float
    required_ft: float
    message: str


# --------------------------------------------------------------------------- #
#  Geometry helpers (pure Python)
# --------------------------------------------------------------------------- #
def _overlap_area(a: Room, b: Room) -> float:
    ox = min(a.x_max, b.x_max) - max(a.x_min, b.x_min)
    oy = min(a.y_max, b.y_max) - max(a.y_min, b.y_min)
    if ox > EPS and oy > EPS:
        return ox * oy
    return 0.0


def _shared_wall(a: Room, b: Room) -> float:
    """Length of wall shared by the two rooms (0 if they only touch at a corner
    or are apart). Assumes the rooms do not overlap."""
    if abs(a.x_max - b.x_min) < EPS or abs(b.x_max - a.x_min) < EPS:   # vertical
        return max(0.0, min(a.y_max, b.y_max) - max(a.y_min, b.y_min))
    if abs(a.y_max - b.y_min) < EPS or abs(b.y_max - a.y_min) < EPS:   # horizontal
        return max(0.0, min(a.x_max, b.x_max) - max(a.x_min, b.x_min))
    return 0.0


def _connected_components(rooms_list: list[Room], min_wall: float) -> list[set[int]]:
    n = len(rooms_list)
    adj: dict[int, set[int]] = {i: set() for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            if _shared_wall(rooms_list[i], rooms_list[j]) >= min_wall - EPS:
                adj[i].add(j)
                adj[j].add(i)
    seen: set[int] = set()
    comps: list[set[int]] = []
    for start in range(n):
        if start in seen:
            continue
        stack, comp = [start], set()
        while stack:
            u = stack.pop()
            if u in comp:
                continue
            comp.add(u)
            seen.add(u)
            stack.extend(adj[u] - comp)
        comps.append(comp)
    return comps


def _attached_bedroom(bath: Room, bedrooms: list[Room]) -> tuple[Room | None, float]:
    """Return (bedroom sharing the longest wall with `bath`, that length)."""
    best, best_len = None, 0.0
    for bd in bedrooms:
        w = _shared_wall(bath, bd)
        if w > best_len:
            best, best_len = bd, w
    return best, best_len


# --------------------------------------------------------------------------- #
#  The check
# --------------------------------------------------------------------------- #
def check_interior(layout: InteriorLayout, sbc: SBCConstraints,
                   require_adjacency: bool = True,
                   require_full_coverage: bool = True,
                   coverage_tol_frac: float = program.COVERAGE_TOL_FRAC,
                   mode: str = "strict",
                   interior_rules: dict | None = None) -> list[InteriorViolation]:
    """Return list of interior violations; empty list == legal floor plan.

    `require_adjacency` lets a caller verify the geometry-only subset (counts,
    containment, sizes, coverage) without the wall-adjacency family — useful for
    partial/diagnostic layouts. `require_full_coverage` controls the coverage
    rule: when True (tiling layouts) the rooms must fill the footprint within
    `coverage_tol_frac`; when False (free / human-sized layouts) only OVERFLOW
    is flagged — leftover open/flex space is allowed."""
    v: list[InteriorViolation] = []
    rs = list(layout.rooms)
    fx0, fy0, fx1, fy1 = layout.footprint
    door_x, door_y = layout.door

    bedrooms = [r for r in rs if r.kind == "bedroom"]
    baths = [r for r in rs if r.kind == "bathroom"]
    kitchens = [r for r in rs if r.kind == "kitchen"]
    livings = [r for r in rs if r.kind == "living"]

    # --- counts -------------------------------------------------------------
    req_counts = dict(program.REQUIRED_COUNT)
    if interior_rules and "required_rooms" in interior_rules:
        req_counts.update(interior_rules["required_rooms"])

    counts: dict[str, int] = {}
    for r in rs:
        counts[r.kind] = counts.get(r.kind, 0) + 1
    for kind, need in req_counts.items():
        have = counts.get(kind, 0)
        if kind == "corridor":
            if have < 1:   # halls/corridors: at least one, any number allowed
                v.append(InteriorViolation(
                    "room_count", float(have), 1.0,
                    "Need at least one corridor / hall for circulation."))
        elif have != need:
            v.append(InteriorViolation(
                "room_count", float(have), float(need),
                f"Need exactly {need} {kind}(s); layout has {have}. Program: "
                "1 living + 1 kitchen + 3 bedrooms + 2 bathrooms (+ halls)."))
    for k in sorted({r.kind for r in rs} - set(req_counts)):
        v.append(InteriorViolation(
            "room_count", 0.0, 0.0,
            f"Unknown room kind '{k}'. Allowed: {sorted(req_counts)}."))

    # --- per-room: containment, min area, min side, max side ----------------
    for r in rs:
        if (_violated(r.x_min, fx0) or _violated(fx1, r.x_max)
                or _violated(r.y_min, fy0) or _violated(fy1, r.y_max)):
            v.append(InteriorViolation(
                "room_in_footprint", 0.0, 0.0,
                f"{r.name} ({r.x_min:.1f},{r.y_min:.1f})-({r.x_max:.1f},{r.y_max:.1f}) "
                f"is outside the footprint x∈[{fx0:.1f},{fx1:.1f}], y∈[{fy0:.1f},{fy1:.1f}]."))
        spec = program.SPEC_BY_KIND.get(r.kind)
        if spec is None:
            continue
            
        req_min_area = spec.min_area_ft2
        req_min_side = spec.min_side_ft
        req_max_side = spec.max_side_ft
        
        if interior_rules and "room_specs" in interior_rules:
            dyn_spec = interior_rules["room_specs"].get(r.kind, {})
            req_min_area = dyn_spec.get("min_area_ft2", req_min_area)
            req_min_side = dyn_spec.get("min_side_ft", req_min_side)
            req_max_side = dyn_spec.get("max_side_ft", req_max_side)

        if _violated(r.area, req_min_area):
            v.append(InteriorViolation(
                "room_min_area", float(r.area), float(req_min_area),
                f"{r.name} is {r.area:.0f} sq ft; a {r.kind} needs ≥ "
                f"{req_min_area:.0f} sq ft (IRC R304)."))
        if _violated(r.min_side, req_min_side):
            v.append(InteriorViolation(
                "room_min_side", float(r.min_side), float(req_min_side),
                f"{r.name} narrowest side is {r.min_side:.1f} ft; a {r.kind} needs "
                f"every side ≥ {req_min_side:.0f} ft."))
        if req_max_side is not None and _violated(req_max_side, r.max_side):
            v.append(InteriorViolation(
                "room_max_side", float(r.max_side), float(req_max_side),
                f"{r.name} longest side is {r.max_side:.1f} ft; a {r.kind} is "
                f"capped at ≤ {req_max_side:.0f} ft/side (no slab-shaped rooms)."))

    # --- non-overlap --------------------------------------------------------
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            ov = _overlap_area(rs[i], rs[j])
            if ov > EPS:
                v.append(InteriorViolation(
                    "no_overlap", float(ov), 0.0,
                    f"{rs[i].name} and {rs[j].name} overlap by {ov:.0f} sq ft. "
                    "Rooms must be disjoint."))

    # --- coverage -----------------------------------------------------------
    total = sum(r.area for r in rs)
    fp = layout.footprint_area
    if require_full_coverage:
        # freeform layouts leave thin slivers as open space — allow a wider band
        tol = max(coverage_tol_frac, 0.12) if mode == "freeform" else coverage_tol_frac
        bad = abs(total - fp) > tol * fp
    else:
        bad = total > fp * (1 + coverage_tol_frac)   # only flag overflow
    if bad:
        gap = fp - total
        msg = (f"Rooms cover {total:.0f} sq ft vs footprint {fp:.0f} sq ft "
               f"({'gap' if gap > 0 else 'overflow'} {abs(gap):.0f} sq ft).")
        v.append(InteriorViolation("coverage", float(total), float(fp), msg))

    # --- corridor / circulation cap (<= 15% of usable floor area) -----------
    corridor_area = sum(r.area for r in rs if r.kind == "corridor")
    usable = sum(r.area for r in rs)
    if usable > EPS and _violated(program.CORRIDOR_MAX_FRAC * usable, corridor_area):
        v.append(InteriorViolation(
            "corridor_fraction", float(corridor_area),
            float(program.CORRIDOR_MAX_FRAC * usable),
            f"Corridor/circulation is {corridor_area:.0f} sq ft = "
            f"{corridor_area/usable*100:.0f}% of usable {usable:.0f} sq ft; "
            f"must stay <= {program.CORRIDOR_MAX_FRAC*100:.0f}%."))

    # --- bathrooms (strict mode only — the rigid arrangement family) --------
    bath_to_bed: dict[str, Room] = {}
    if require_adjacency and mode == "strict":
        used: set[str] = set()
        for b in baths:
            bd, wall = _attached_bedroom(b, bedrooms)
            if bd is None or _violated(wall, program.ENSUITE_WALL_MIN_FT):
                v.append(InteriorViolation(
                    "ensuite_attached", float(wall), float(program.ENSUITE_WALL_MIN_FT),
                    f"{b.name} is not ensuite — it shares only {wall:.1f} ft of wall "
                    f"with any bedroom; need ≥ {program.ENSUITE_WALL_MIN_FT:.0f} ft "
                    "with its own bedroom."))
            else:
                bath_to_bed[b.name] = bd
                if bd.name in used:
                    v.append(InteriorViolation(
                        "ensuite_attached", 0.0, 0.0,
                        f"{b.name} and another bathroom both attach to {bd.name}; "
                        "each bathroom must serve a different bedroom."))
                used.add(bd.name)

        # bath area < its bedroom's area
        for b in baths:
            bd = bath_to_bed.get(b.name)
            if bd is not None and _violated(bd.area, b.area + EPS):  # bath.area >= bed.area
                v.append(InteriorViolation(
                    "bath_smaller", float(b.area), float(bd.area),
                    f"{b.name} ({b.area:.0f} sq ft) must be smaller than its "
                    f"bedroom {bd.name} ({bd.area:.0f} sq ft)."))

        # bathrooms not adjacent to the kitchen (sanitation)
        for b in baths:
            for kt in kitchens:
                wall = _shared_wall(b, kt)
                if wall > program.ADJ_TOL_FT:
                    v.append(InteriorViolation(
                        "bath_not_adj_kitchen", float(wall), 0.0,
                        f"{b.name} shares a {wall:.1f} ft wall with {kt.name}; a "
                        "bathroom must never abut the kitchen (sanitation)."))

        # the two bathrooms not adjacent to each other
        for i in range(len(baths)):
            for j in range(i + 1, len(baths)):
                wall = _shared_wall(baths[i], baths[j])
                if wall > program.ADJ_TOL_FT:
                    v.append(InteriorViolation(
                        "baths_not_adjacent", float(wall), 0.0,
                        f"{baths[i].name} and {baths[j].name} share a {wall:.1f} ft "
                        "wall; the two bathrooms must not be adjacent."))

    # --- living room: south wall + the front door ---------------------------
    if livings:
        lv = livings[0]
        near_south = abs(lv.y_min - fy0)
        if near_south > program.SOUTH_TOL_FT:
            v.append(InteriorViolation(
                "living_near_south", float(near_south), float(program.SOUTH_TOL_FT),
                f"{lv.name} south edge is {near_south:.1f} ft from the south wall; "
                f"must be within {program.SOUTH_TOL_FT:.0f} ft (entry is on the south)."))
        margin = sbc.door_corner_margin_ft
        on_south = abs(lv.y_min - fy0) < 0.5 and abs(door_y - fy0) < 0.5
        in_span = (lv.x_min + margin - EPS) <= door_x <= (lv.x_max - margin + EPS)
        if not (on_south and in_span):
            v.append(InteriorViolation(
                "door_in_living", float(door_x), float(margin),
                f"Front door ({door_x:.1f},{door_y:.1f}) must open into {lv.name} on "
                f"the south wall (spans x∈[{lv.x_min:.1f},{lv.x_max:.1f}]), inset ≥ "
                f"{margin:.0f} ft from its side walls."))

        # living room larger than every bedroom (Floor Plan acceptance rule)
        for bd in bedrooms:
            if _violated(lv.area, bd.area + EPS):
                v.append(InteriorViolation(
                    "living_gt_bedroom", float(lv.area), float(bd.area),
                    f"{lv.name} ({lv.area:.0f} sq ft) must be larger than every "
                    f"bedroom; {bd.name} is {bd.area:.0f} sq ft."))

    # --- kitchen adjoins living (open plan, no corridor between) -------------
    if require_adjacency and mode == "strict" and kitchens and livings:
        wall = max(_shared_wall(kitchens[0], lv) for lv in livings)
        if _violated(wall, program.WALL_MIN_FT):
            v.append(InteriorViolation(
                "kitchen_by_living", float(wall), float(program.WALL_MIN_FT),
                f"Kitchen shares only {wall:.1f} ft of wall with the living room; "
                f"need ≥ {program.WALL_MIN_FT:.1f} ft (kitchen directly adjacent, "
                "no corridor between)."))

    # --- connectivity: every room reachable through a >= doorway wall --------
    if require_adjacency and len(rs) >= 2:
        comps = _connected_components(rs, program.WALL_MIN_FT)
        if len(comps) > 1:
            biggest = max(comps, key=len)
            stranded = [rs[i].name for c in comps if c is not biggest for i in c]
            v.append(InteriorViolation(
                "connected", float(len(comps)), 1.0,
                f"Floor plan splits into {len(comps)} disconnected groups; "
                f"{', '.join(stranded)} cannot be reached through a "
                f"≥ {program.WALL_MIN_FT:.1f} ft doorway. Every room must connect."))

    return v


def passes_interior(layout: InteriorLayout, sbc: SBCConstraints, **kw) -> bool:
    return len(check_interior(layout, sbc, **kw)) == 0

"""The building 'program' — what the interior must contain and the spatial
rules it must obey.

This is the data layer for the interior stage, in the same spirit as
constraints.py (cite a defensible source, encode a small subset). It now mirrors
a fuller residential program: a corridor for circulation and *ensuite*
bathrooms (each attached to its own bedroom), with IRC-accurate minimums.

Program (8 rooms):
    1 living + 1 kitchen + 1 corridor + 3 bedrooms + 2 bathrooms
    bathrooms are ensuite: Bath 1 -> Bedroom 1, Bath 2 -> Bedroom 2
    (Bedroom 3 has no ensuite)

Sizes — International Residential Code (IRC) R304/R305:
  - Habitable rooms (living, kitchen treated as habitable here, bedrooms):
    floor area >= 70 sq ft, and no horizontal dimension < 7 ft.
  - Bathrooms (non-habitable service space): >= 25 sq ft (a 5x5 fixture clear
    area), each side >= 5 ft, and capped at <= 15 ft per side so the LLM can't
    emit an absurd 33x5 "bathroom" that technically clears the 5 ft minimum.
  - Corridor: >= 4 ft clear width (IRC R311.6 hallway minimum is 3 ft; we use 4).

Spatial rules (architectural, from the project meeting feedback):
  - Living room nearest the south entry, touching the south wall.
  - Kitchen directly adjacent to the living room (no corridor between).
  - Each bathroom is ensuite: it shares a wall with its bedroom (private access).
  - A bathroom must NEVER share a wall with the kitchen (sanitation).
  - The two bathrooms must NEVER share a wall with each other.
  - Each bathroom must be smaller in area than the bedroom it serves.
  - Each bedroom gets 2 windows on different walls (drawn; see dxf/viz).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RoomSpec:
    kind: str               # "living" | "kitchen" | "corridor" | "bedroom" | "bathroom"
    count: int
    min_area_ft2: float
    min_side_ft: float      # no horizontal dimension may be smaller than this
    max_side_ft: Optional[float]  # cap on any side (None = uncapped)
    habitable: bool         # IRC "habitable space" (affects window requirement)
    label: str


# IRC R304 habitable minimum = 70 sq ft, min side 7 ft.
_HAB: dict[str, float | bool | None] = dict(min_area_ft2=70.0, min_side_ft=7.0, max_side_ft=None, habitable=True)

PROGRAM: tuple[RoomSpec, ...] = (
    RoomSpec(kind="living",   count=1, label="Living",   **_HAB),  # type: ignore[arg-type]
    RoomSpec(kind="kitchen",  count=1, label="Kitchen",  **_HAB),  # type: ignore[arg-type]
    RoomSpec(kind="corridor", count=1, label="Corridor",
             min_area_ft2=16.0, min_side_ft=4.0, max_side_ft=None, habitable=False),
    RoomSpec(kind="bedroom",  count=3, label="Bedroom",  **_HAB),  # type: ignore[arg-type]
    RoomSpec(kind="bathroom", count=2, label="Bath",
             min_area_ft2=25.0, min_side_ft=5.0, max_side_ft=15.0, habitable=False),
)

SPEC_BY_KIND: dict[str, RoomSpec] = {s.kind: s for s in PROGRAM}
REQUIRED_COUNT: dict[str, int] = {s.kind: s.count for s in PROGRAM}
TOTAL_ROOMS: int = sum(s.count for s in PROGRAM)        # 8
HABITABLE_KINDS: set[str] = {s.kind for s in PROGRAM if s.habitable}
MIN_TOTAL_AREA: float = sum(s.min_area_ft2 * s.count for s in PROGRAM)

# --- spatial-rule parameters ----------------------------------------------- #
CORRIDOR_WIDTH_FT: float = 4.0      # IRC R311.6 hallway clear width (we use 4)
WALL_MIN_FT: float = 2.5            # min shared-wall length to count as a doorway
ENSUITE_WALL_MIN_FT: float = 4.0    # a bathroom door+ onto its bedroom
ADJ_TOL_FT: float = 0.5            # shared wall <= this is treated as "not touching"
SOUTH_TOL_FT: float = 2.0          # living-room south edge within this of house south
COVERAGE_TOL_FRAC: float = 0.05    # rooms total within +/- 5% of house area
CORRIDOR_MAX_FRAC: float = 0.15    # circulation area must stay <= 15% of usable floor
WINDOWS_PER_BEDROOM: int = 2       # on different walls, <=1 per wall

# Public zone (south of the corridor) vs private zone (north of the corridor).
SOUTH_ZONE_KINDS: set[str] = {"living", "kitchen"}
NORTH_ZONE_KINDS: set[str] = {"bedroom", "bathroom"}


if __name__ == "__main__":
    print("Interior program (IRC R304/R305):")
    for s in PROGRAM:
        cap = f", max side {s.max_side_ft:.0f} ft" if s.max_side_ft else ""
        print(f"  {s.count}x {s.kind:9s} — >= {s.min_area_ft2:.0f} sq ft, "
              f"side >= {s.min_side_ft:.0f} ft{cap}"
              f"{'  [habitable]' if s.habitable else ''}")
    print(f"  total rooms    : {TOTAL_ROOMS}")
    print(f"  min total area : {MIN_TOTAL_AREA:.0f} sq ft")
    print(f"  corridor width : >= {CORRIDOR_WIDTH_FT:.0f} ft")
    print("  ensuite        : Bath 1->Bedroom 1, Bath 2->Bedroom 2 (Bedroom 3 none)")

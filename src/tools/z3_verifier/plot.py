"""Plot geometry — L-shaped land parcel with a protected tree.

All units are feet. Compass: +x = East, +y = North. Origin at the SW corner
of the southern entry tab. Vertices listed CLOCKWISE.

Updated dimensions (sketch v2, 2026-05-30) close exactly:
  top  : 75 + (step up 4) + 5  (notch width 5, total east extent 80)
  right: 80                    (from notch top y=88 down to y=8)
  bot. : 5 + 8 + 40 + 8 + 35   (notches + entry tab + bottom-left)
  left : 76                    (from y=8 up to y=84)
  tree notch: x∈[75,80], y∈[84,88]
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Plot:
    boundary: tuple[tuple[float, float], ...]
    tree_center: tuple[float, float]
    tree_radius: float        # the tree itself
    tree_buffer: float        # required SBC protection buffer beyond trunk
    entry_side: str           # 'N' | 'S' | 'E' | 'W'
    entry_segment: tuple[tuple[float, float], tuple[float, float]]

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        xs = [p[0] for p in self.boundary]
        ys = [p[1] for p in self.boundary]
        return (min(xs), min(ys), max(xs), max(ys))

    @property
    def area(self) -> float:
        """Lot area (shoelace formula) — used for the max lot-coverage cap."""
        pts = self.boundary
        s = 0.0
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            s += x1 * y2 - x2 * y1
        return abs(s) / 2.0


PLOT = Plot(
    boundary=(
        (0,  84),   # NW corner of main body  (left edge total = 76)
        (75, 84),   # top edge east           (label: 75)
        (75, 88),   # tree-notch step up      (label: 4)
        (80, 88),   # tree-notch top east     (label: 5)
        (80,  8),   # right edge south        (label: 80, 88-8=80 exactly)
        (75,  8),   # bottom-right inset west (label: 5)
        (75,  0),   # entry tab right side    (label: 8)
        (35,  0),   # entry tab bottom        (label: 40)
        (35,  8),   # entry tab left side     (label: 8)
        (0,   8),   # bottom-left of main body (label: 35)
        # implicit close to (0, 84) — left edge 76 ft (label: 76) ✓
    ),
    tree_center=(77.5, 86.0),  # inside the tree notch (75..80, 84..88)
    tree_radius=1.0,
    tree_buffer=3.0,
    entry_side="S",
    entry_segment=((35.0, 0.0), (75.0, 0.0)),  # 40 ft entry edge
)

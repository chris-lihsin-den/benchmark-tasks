"""On the station table: a steel flat bar (140 x 40 x 15 mm) is held flat in a bench vise in front of the arms, its
long side running left to right; the two vise jaws press its front and back faces and stop 3 mm below its top face. Its top face has a 50 mm orange band across the middle that is to be spray-coated; the
45 mm of grey bare steel on each side of the band must stay uncoated. Two loose aluminium masking plates
(55 x 50 x 12 mm) lie on the table nearer the arms, one in front of each arm.

Goal: one plate lying flat on each grey zone, covering it, with the orange band left uncovered.

Run it:  inspect-robots run --embodiment yam_arena -E task=mask_coating_band.py -E object_jitter=0 \\
           --instruction "Mask the bar for coating: lay one masking plate flat on each grey zone so both grey zones \\
           are covered and the orange band stays fully uncovered." --scorer task_score ...
"""

import math

import numpy as np

from yam_arena.constants import FINGER_OPEN, PAD_TIP_PAST_TCP
from yam_arena.demo import Waypoint
from yam_arena.task_file import TABLE_TOP, Box

SCENE = "station"
TOP = TABLE_TOP[SCENE]

# -- the bar: three fixed boxes flush side by side (grey zone, orange band, grey zone) --------------------------
BAR_X, BAR_DEPTH, BAR_T = 0.33, 0.040, 0.015  # centre forward, front-to-back depth, thickness
BAND_W, ZONE_W = 0.050, 0.045  # orange band width, each grey zone's width (side to side)
BAR_TOP = TOP + BAR_T
STEEL = (0.55, 0.56, 0.58)
ORANGE = (0.95, 0.45, 0.08)
ZONE_Y = {"left": BAND_W / 2 + ZONE_W / 2, "right": -(BAND_W / 2 + ZONE_W / 2)}  # zone centres

# -- the masking plates ---------------------------------------------------------------------------------------
PLATE_SIZE = (0.050, 0.055, 0.012)  # front to back, side to side, thick
PLATE_MASS = 0.09  # aluminium
PLATE_START = {"left_plate": (0.22, 0.15), "right_plate": (0.22, -0.15)}
PLATE_COLOR = (0.80, 0.82, 0.86)

# -- the vise: two fixed jaws along the bar's front and back faces, tops 3 mm below the bar's top face -------------
JAW_T, JAW_H = 0.010, BAR_T - 0.003
VISE = (0.25, 0.26, 0.30)

OBJECTS = [
    *[Box(f"vise_{n}_jaw", pos=(BAR_X + s * (BAR_DEPTH / 2 + JAW_T / 2), 0.0, TOP + JAW_H / 2),
          size=(JAW_T, 2 * ZONE_W + BAND_W, JAW_H), color=VISE) for n, s in (("front", -1), ("back", 1))],
    Box("bar_left_zone", pos=(BAR_X, ZONE_Y["left"], TOP + BAR_T / 2), size=(BAR_DEPTH, ZONE_W, BAR_T), color=STEEL),
    Box("bar_band", pos=(BAR_X, 0.0, TOP + BAR_T / 2), size=(BAR_DEPTH, BAND_W, BAR_T), color=ORANGE),
    Box("bar_right_zone", pos=(BAR_X, ZONE_Y["right"], TOP + BAR_T / 2), size=(BAR_DEPTH, ZONE_W, BAR_T), color=STEEL),
    *[Box(n, pos=(x, y, TOP + PLATE_SIZE[2] / 2), size=PLATE_SIZE, mass=PLATE_MASS, color=PLATE_COLOR)
      for n, (x, y) in PLATE_START.items()],
]
PLATES = tuple(PLATE_START)

# -- scoring --------------------------------------------------------------------------------------------------
# Masking tolerance per edge (a common job-shop masking placement tolerance is +/-0.080 in, about 2 mm): at most
# 2 mm of bare steel left exposed, at most 2 mm of the band covered (each as the
# width of a strip with the same area along that edge). Within 5 mm on both counts earns partial credit.
TOL_FULL, TOL_PARTIAL = 0.002, 0.005
FLAT_DZ, FLAT_TILT_DEG = 0.003, 5.0
REST_Z = BAR_TOP + PLATE_SIZE[2] / 2  # a plate's centre height lying flat on the bar
GRID = 0.0005


def _grid(y0, y1):
    """0.5 mm sample points over the bar's top between y0 and y1 (m), as an (n, 2) array of x, y."""
    xs = np.arange(BAR_X - BAR_DEPTH / 2 + GRID / 2, BAR_X + BAR_DEPTH / 2, GRID)
    ys = np.arange(y0 + GRID / 2, y1, GRID)
    gx, gy = np.meshgrid(xs, ys)
    return np.c_[gx.ravel(), gy.ravel()]


ZONE_PTS = {
    "left": _grid(BAND_W / 2, BAND_W / 2 + ZONE_W),
    "right": _grid(-BAND_W / 2 - ZONE_W, -BAND_W / 2),
}
BAND_PTS = {"left": _grid(0.0, BAND_W / 2), "right": _grid(-BAND_W / 2, 0.0)}


def _rot(q):
    x, y, z, w = (float(v) for v in q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def _flat(st):
    """Lying flat on the bar's top: centre within 3 mm of its resting height, tilted under 5 degrees."""
    tilt = math.degrees(math.acos(min(1.0, abs(_rot(st.quat_xyzw)[2, 2]))))
    return abs(st.pos[2] - REST_Z) < FLAT_DZ and tilt < FLAT_TILT_DEG


def _outline(st):
    """The plate's projected outline seen from directly above: the convex hull of its 8 corners in x, y,
    counter-clockwise. Exact for any position, yaw or tilt."""
    h = np.array(PLATE_SIZE) / 2
    c = np.array([[a, b, d] for a in (-1, 1) for b in (-1, 1) for d in (-1, 1)]) * h @ _rot(st.quat_xyzw).T
    pts = sorted(map(tuple, np.round(st.pos[:2] + c[:, :2], 9)))

    def half(seq):
        out = []
        for q in seq:
            while len(out) >= 2 and (out[-1][0] - out[-2][0]) * (q[1] - out[-2][1]) - (out[-1][1] - out[-2][1]) * (q[0] - out[-2][0]) <= 0:
                out.pop()
            out.append(q)
        return out[:-1]

    return np.array(half(pts) + half(pts[::-1]))


def _under(st, pts):
    """Which points lie under the plate's projected outline (on or inside it), as a boolean mask."""
    hull = _outline(st)
    inside = np.ones(len(pts), bool)
    for a, b in zip(hull, np.roll(hull, -1, axis=0)):
        inside &= (b[0] - a[0]) * (pts[:, 1] - a[1]) - (b[1] - a[1]) * (pts[:, 0] - a[0]) >= -1e-9
    return inside


def _errors(objects, side):
    """(bare steel left exposed on that grey zone, band covered on that half of the band), each in metres as the
    width of a strip of equal area along the zone's 40 mm edge. Only plates lying flat on the bar mask the zone; any
    plate over the band, at any height or tilt, covers it."""
    zone, band = ZONE_PTS[side], BAND_PTS[side]
    covered = np.zeros(len(zone), bool)
    shaded = np.zeros(len(band), bool)
    for n in PLATES:
        st = objects[n]
        if _flat(st):
            covered |= _under(st, zone)
        shaded |= _under(st, band)
    return (1.0 - float(covered.mean())) * ZONE_W, float(shaded.mean()) * BAND_W / 2


def _side_score(objects, side):
    """0.5 if no more than 2 mm of bare steel is exposed and no more than 2 mm of the band is covered; 0.25 if both
    are within 5 mm; else 0."""
    bare, intrusion = _errors(objects, side)
    if bare <= TOL_FULL and intrusion <= TOL_FULL:
        return 0.5
    if bare <= TOL_PARTIAL and intrusion <= TOL_PARTIAL:
        return 0.25
    return 0.0


def score(objects):
    return round(_side_score(objects, "left") + _side_score(objects, "right"), 3)


def success(objects):
    return score(objects) >= 0.999 and all(objects[n].resting() for n in PLATES)


TARGET_Y = {"left_plate": BAND_W / 2 + PLATE_SIZE[1] / 2, "right_plate": -(BAND_W / 2 + PLATE_SIZE[1] / 2)}


def distance(objects):
    return float(sum(math.hypot(objects[n].pos[0] - BAR_X, objects[n].pos[1] - y) for n, y in TARGET_Y.items()))


# -- scripted demo --------------------------------------------------------------------------------------------
TRAVEL_Z = TOP + 0.09  # higher, the wrist (joint4) nears its limit
YAW = {"left": -math.pi / 2, "right": math.pi / 2}  # fingers close along world x, across the plate's 50 mm side
GRIP_ABOVE_BOTTOM = PAD_TIP_PAST_TCP + 0.006  # pad tips 6 mm above the plate's underside
RELEASE_GAP = 0.003  # let go with the plate's underside this far above the bar
SETTLE_S = 0.8
OPEN_W = -(PLATE_SIZE[0] / 2 + 0.012)  # pads 12 mm clear of each side of the plate


def _mask(name, yaw):
    sx, sy = PLATE_START[name]
    gy = TARGET_Y[name]
    pick_z = TOP + GRIP_ABOVE_BOTTOM
    drop_z = BAR_TOP + RELEASE_GAP + GRIP_ABOVE_BOTTOM
    return [
        Waypoint(1.5, (sx, sy, TRAVEL_Z), OPEN_W, f"to the {name}", yaw),
        Waypoint(1.2, (sx, sy, pick_z), OPEN_W, "descend", yaw),
        Waypoint(0.8, (sx, sy, pick_z), 0.0, "grip", yaw),
        Waypoint(1.0, (sx, sy, TRAVEL_Z), 0.0, "lift", yaw),
        Waypoint(1.8, (BAR_X, gy, TRAVEL_Z), 0.0, "over its zone", yaw),
        Waypoint(1.0, (BAR_X, gy, drop_z + 0.012), 0.0, "lower", yaw),
        Waypoint(SETTLE_S, (BAR_X, gy, drop_z + 0.012), 0.0, "settle", yaw),
        Waypoint(0.8, (BAR_X, gy, drop_z), 0.0, "to the bar", yaw),
        Waypoint(SETTLE_S, (BAR_X, gy, drop_z), 0.0, "settle", yaw),
        Waypoint(0.6, (BAR_X, gy, drop_z), OPEN_W, "let go", yaw),
        Waypoint(1.0, (BAR_X, gy, TRAVEL_Z), OPEN_W, "up", yaw),
    ]


def demo():
    """Left arm lays its plate on the left grey zone, its inner edge on the band's edge, and moves clear; then the
    right arm does the same on the right. Each plate is let go 3 mm above the bar and drops flat."""
    left = _mask("left_plate", YAW["left"]) + [Waypoint(1.5, (0.20, 0.25, TRAVEL_Z), FINGER_OPEN, "clear", YAW["left"])]
    wait = sum(w.duration for w in left)
    right = [Waypoint(wait, (0.20, -0.25, TRAVEL_Z), FINGER_OPEN, "wait for the left arm")] + _mask(
        "right_plate", YAW["right"]
    ) + [Waypoint(1.5, (0.20, -0.25, TRAVEL_Z), FINGER_OPEN, "clear", YAW["right"])]
    return {"left": left, "right": right}

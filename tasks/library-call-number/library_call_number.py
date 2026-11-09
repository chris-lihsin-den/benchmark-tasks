"""On the station table: a short bookshelf in front of the arms, its back wall away from them, with a black bookend at
each end. Five books (30 mm thick, 50 mm deep, 50 mm tall) stand on it packed tight against the left bookend, in
Library of Congress order from the left: green QA75.5, blue QA76.5, red QA76.73, purple QA76.9, orange QA77. Two
returned books stand on the table nearer the arms: yellow QA76.625 on the left and teal QA76.8 on the right.

Goal: both returned books shelved in call-number order. QA76.625 goes between QA76.5 and QA76.73, and QA76.8 between
QA76.73 and QA76.9, because the class number sorts as a decimal (.625 < .73 < .8 < .9). There is no gap where either
book goes, so the books to its right must be slid along to open one first.

Run it:  inspect-robots run --embodiment yam_arena -E task=library_call_number.py -E object_jitter=0 \\
           --instruction "<see INSTRUCTION below>" --scorer task_score ...
"""

import math

import numpy as np

from yam_arena.constants import FINGER_OPEN, PAD_TIP_PAST_TCP
from yam_arena.demo import Waypoint
from yam_arena.task_file import TABLE_TOP, Box

SCENE = "station"
TOP = TABLE_TOP[SCENE]

INSTRUCTION = (
    "Shelve the two returned books in Library of Congress call-number order, left to right as you face the shelf. "
    "The shelved books are, from the left: green QA75.5, blue QA76.5, red QA76.73, purple QA76.9, orange QA77. "
    "The yellow book is QA76.625 and the teal book is QA76.8. Keep every book upright on the shelf."
)

# -- the shelf (fixed) -------------------------------------------------------------------------------------------------
SHELF_X, SHELF_DEPTH, SHELF_T = 0.340, 0.090, 0.003
SHELF_TOP = TOP + SHELF_T
BOOK_X = 0.330  # books' centre line, front to back
WALL_X = 0.392  # back wall centre (leaves room behind the books for the rear finger)
END_L, END_R = 0.077, -0.187  # bookend centres; inner faces at +0.075 and -0.185 (room for two 46 mm gaps)
WOOD = (0.62, 0.48, 0.33)
OBJECTS = [
    Box("shelf_board", pos=(SHELF_X, -0.055, TOP + SHELF_T / 2), size=(SHELF_DEPTH, 0.280, SHELF_T), color=WOOD),
    Box("shelf_back", pos=(WALL_X, -0.055, TOP + 0.035), size=(0.004, 0.280, 0.070), color=WOOD),
    Box("bookend_left", pos=(BOOK_X, END_L, SHELF_TOP + 0.025), size=(0.050, 0.004, 0.050), color=(0.1, 0.1, 0.1)),
    Box("bookend_right", pos=(BOOK_X, END_R, SHELF_TOP + 0.025), size=(0.050, 0.004, 0.050), color=(0.1, 0.1, 0.1)),
]

# -- books -------------------------------------------------------------------------------------------------------------
BOOK = (0.050, 0.030, 0.050)  # front to back, thick (side to side), tall: thicker than the finger pads are wide
BOOK_MASS = 0.04
LC_ORDER = ["qa75_5", "qa76_5", "qa76_625", "qa76_73", "qa76_8", "qa76_9", "qa77"]
SHELVED = {"qa75_5": 0.060, "qa76_5": 0.030, "qa76_73": 0.000, "qa76_9": -0.030, "qa77": -0.060}
RETURNED = {"qa76_625": (0.240, 0.140), "qa76_8": (0.240, -0.150)}
COLORS = {"qa75_5": (0.33, 0.58, 0.38), "qa76_5": (0.22, 0.40, 0.72), "qa76_625": (0.92, 0.80, 0.25),
          "qa76_73": (0.70, 0.24, 0.20), "qa76_8": (0.25, 0.68, 0.64), "qa76_9": (0.52, 0.40, 0.70), "qa77": (0.80, 0.52, 0.20)}
OBJECTS += [Box(f"book_{n}", pos=(BOOK_X, y, SHELF_TOP + BOOK[2] / 2), size=BOOK, mass=BOOK_MASS, color=COLORS[n])
            for n, y in SHELVED.items()]
OBJECTS += [Box(f"book_{n}", pos=(x, y, TOP + BOOK[2] / 2), size=BOOK, mass=BOOK_MASS, color=COLORS[n])
            for n, (x, y) in RETURNED.items()]
BOOKS = [f"book_{n}" for n in LC_ORDER]

# -- scoring -----------------------------------------------------------------------------------------------------------
REST_Z = SHELF_TOP + BOOK[2] / 2
UPRIGHT_DEG, Z_TOL, FRONT_TOL = 10.0, 0.004, 0.012


def _tilt_deg(q):
    x, y, _, _ = (float(v) for v in q)
    return math.degrees(math.acos(min(1.0, abs(1 - 2 * (x * x + y * y)))))


def shelved(st):
    """Standing upright on the shelf: tilted under 10 degrees, centre within 4 mm of its resting height, within 12 mm
    of the books' line front to back, and between the bookends."""
    return (_tilt_deg(st.quat_xyzw) < UPRIGHT_DEG and abs(st.pos[2] - REST_Z) < Z_TOL
            and abs(st.pos[0] - BOOK_X) <= FRONT_TOL and END_R + 0.010 <= st.pos[1] <= END_L - 0.010)


def in_order(objects):
    """All seven books shelved and, left to right (decreasing y), in call-number order."""
    if not all(shelved(objects[b]) for b in BOOKS):
        return False
    return sorted(BOOKS, key=lambda b: -objects[b].pos[1]) == BOOKS



# -- debug: TASK_DEBUG=1 prints every loose object's pose every 2 s of robot time ---------------------------------
import os as _os
_DEBUG = _os.environ.get("TASK_DEBUG") == "1"
_calls = [0]


def _debug(objects):
    _calls[0] += 1
    if _calls[0] % 40:
        return
    rows = []
    for n, st in objects.items():
        if n in _FREE:
            rows.append(f"{n} {st.pos[0]*1000:.1f},{st.pos[1]*1000:.1f},{(st.pos[2]-TOP)*1000:.1f} tilt {_tilt_dbg(st.quat_xyzw):.0f}")
    print(f"DBG step {_calls[0]}: " + " | ".join(rows), flush=True)


def _tilt_dbg(q):
    import math as _m
    x, y, _, _ = (float(v) for v in q)
    return _m.degrees(_m.acos(min(1.0, abs(1 - 2 * (x * x + y * y)))))

_FREE = {o.name for o in OBJECTS if o.mass is not None}

def score(objects):
    """0.2 per returned book shelved; +0.2 if both are shelved and the five original books are all still shelved (so
    doing nothing scores 0); +0.4 if all seven are in call-number order."""
    if _DEBUG:
        _debug(objects)
    returned = [shelved(objects[f"book_{n}"]) for n in RETURNED]
    s = 0.2 * sum(returned)
    if all(returned) and all(shelved(objects[f"book_{n}"]) for n in SHELVED):
        s += 0.2
    if in_order(objects):
        s += 0.4
    return round(s, 3)


def success(objects):
    return score(objects) >= 0.999 and all(objects[b].resting() for b in BOOKS)


GAP = 0.046  # how far each shove opens a gap: book plus 8 mm a side (a lowered book drifts ~5 mm sideways)
TARGET_Y = {"qa76_625": 0.015 - GAP / 2, "qa76_8": -GAP - 0.015 - GAP / 2}  # centres of the two opened gaps


def distance(objects):
    return float(sum(math.hypot(objects[f"book_{n}"].pos[0] - BOOK_X, objects[f"book_{n}"].pos[1] - y)
                     for n, y in TARGET_Y.items()))


# -- scripted demo -----------------------------------------------------------------------------------------------------
TRAVEL_Z = TOP + 0.095  # a carried book's base clears the shelved books' tops
YAW = {"left": -math.pi / 2, "right": math.pi / 2}  # fingers close along world x: on a book's front and back faces
GRIP_ABOVE = PAD_TIP_PAST_TCP + 0.010  # pad tips 10 mm above the surface the book stands on
OPEN_W = -(BOOK[0] / 2 + 0.012)
OVERSHOOT = 0.007  # a pushing hand stops ~5-7 mm short of its target (measured in Isaac), so aim past it
SETTLE = 0.8
REST = {"left": (0.20, 0.25), "right": (0.20, -0.25)}


def _shove(y_from, y_to, yaw):
    """Grip the book at y_from by its front and back and slide it (and the books beyond it) to y_to."""
    z = SHELF_TOP + GRIP_ABOVE
    return [
        Waypoint(1.5, (BOOK_X, y_from, TRAVEL_Z), OPEN_W, "over the book to slide", yaw),
        Waypoint(1.2, (BOOK_X, y_from, z), OPEN_W, "down beside it", yaw),
        Waypoint(0.8, (BOOK_X, y_from, z), 0.0, "grip front and back", yaw),
        Waypoint(3.5, (BOOK_X, y_to - OVERSHOOT, z), 0.0, "slide it and the books beyond along", yaw),
        Waypoint(SETTLE, (BOOK_X, y_to - OVERSHOOT, z), 0.0, "settle", yaw),
        Waypoint(0.6, (BOOK_X, y_to - OVERSHOOT, z), OPEN_W, "let go", yaw),
        Waypoint(1.0, (BOOK_X, y_to - OVERSHOOT, TRAVEL_Z), OPEN_W, "up", yaw),
    ]


def _insert(name, yaw):
    sx, sy = RETURNED[name]
    gy = TARGET_Y[name]
    pick = TOP + GRIP_ABOVE
    drop = SHELF_TOP + 0.003 + GRIP_ABOVE
    return [
        Waypoint(1.5, (sx, sy, TRAVEL_Z), OPEN_W, f"to {name}", yaw),
        Waypoint(1.2, (sx, sy, pick), OPEN_W, "descend", yaw),
        Waypoint(0.8, (sx, sy, pick), 0.0, "grip", yaw),
        Waypoint(1.2, (sx, sy, TRAVEL_Z), 0.0, "lift", yaw),
        Waypoint(1.8, (BOOK_X, gy, TRAVEL_Z), 0.0, "over the gap", yaw),
        Waypoint(SETTLE, (BOOK_X, gy, TRAVEL_Z), 0.0, "settle", yaw),
        Waypoint(2.2, (BOOK_X, gy, drop), 0.0, "lower into the gap", yaw),
        Waypoint(SETTLE, (BOOK_X, gy, drop), 0.0, "settle", yaw),
        Waypoint(0.6, (BOOK_X, gy, drop), OPEN_W, "let go", yaw),
        Waypoint(1.2, (BOOK_X, gy, TRAVEL_Z), OPEN_W, "up", yaw),
    ]


def _park(arm, dur, label="wait"):
    return Waypoint(dur, (*REST[arm], TRAVEL_Z), FINGER_OPEN, label, YAW[arm])


def _dur(wps):
    return sum(w.duration for w in wps)


def demo():
    """One arm at a time (the hands never come within 18 cm of each other):
    1. right arm slides QA76.73 and the two books beyond it 46 mm right, opening a gap after QA76.5;
    2. left arm sets QA76.625 in that gap;
    3. right arm slides QA76.9 and QA77 another 46 mm right, opening a gap after QA76.73;
    4. right arm sets QA76.8 in that gap."""
    r1 = _shove(0.000, 0.000 - GAP, YAW["right"]) + [_park("right", 1.2, "clear")]
    l1 = _insert("qa76_625", YAW["left"]) + [_park("left", 1.2, "clear")]
    r2 = _shove(-0.030 - GAP, -0.030 - 2 * GAP, YAW["right"])  # QA76.9 now sits one gap to the right
    r2 += _insert("qa76_8", YAW["right"]) + [_park("right", 1.2, "clear")]
    left = [_park("left", _dur(r1), "wait")] + l1 + [_park("left", _dur(r2), "wait")]
    right = r1 + [_park("right", _dur(l1), "wait")] + r2
    return {"left": left, "right": right}

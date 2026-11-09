"""On the station table, at 1:150 scale: a short track runs straight away from the arms. Its far end is closed by a red
bumper post and a brown boxcar stands just in front of the bumper; the near end is open. Beside the left rail are two
grey derail mounts, one 28 mm (4 m) and one 110 mm (16.5 m) from the car's near end, each with a small lock socket
beside it. At the open end, just past the rail ends, is a flag socket. A yellow derail, a steel lock pin and a blue
flag lie on the table nearer the arms.

Goal: blue-signal protection under 49 CFR 218 before anyone goes under the car: the derail seated in the mount that
lies between the car and the open end and at least 50 ft (102 mm) from the car, locked with the pin in that mount's
lock socket, and the blue flag standing in the flag socket at the open end.

Run it:  inspect-robots run --embodiment yam_arena -E task=rail_blue_signal.py -E object_jitter=0 \\
           --instruction "<see INSTRUCTION below>" --scorer task_score ...
"""

import math

from yam_arena.constants import FINGER_OPEN, PAD_TIP_PAST_TCP
from yam_arena.demo import Waypoint
from yam_arena.task_file import TABLE_TOP, Box

SCENE = "station"
TOP = TABLE_TOP[SCENE]

INSTRUCTION = (
    "Workers are about to go under the boxcar. Set up blue-signal protection: seat the yellow derail in the mount that "
    "is between the car and the open end of the track and at least 50 ft from the car, lock it by putting the steel "
    "pin in that mount's lock socket, and stand the blue flag in the flag socket at the open end. The model is 1:150, "
    "so 50 ft is 102 mm."
)

SCALE = 150.0
MIN_DIST = 50 * 0.3048 / SCALE  # 0.1016 m

# -- track, car and bumper (fixed) -----------------------------------------------------------------------------------
RAIL_Y, RAIL_X0, RAIL_X1 = 0.006, 0.215, 0.445
CAR_X0, CAR_X1 = 0.350, 0.430  # car's near and far ends
STEEL = (0.50, 0.52, 0.55)
OBJECTS = [Box(f"tie_{i}", pos=(0.218 + 0.018 * i, 0.0, TOP + 0.001), size=(0.006, 0.034, 0.002), color=(0.36, 0.25, 0.19))
           for i in range(13)]
OBJECTS += [Box(f"rail_{s}", pos=((RAIL_X0 + RAIL_X1) / 2, d * RAIL_Y, TOP + 0.004), size=(RAIL_X1 - RAIL_X0, 0.003, 0.004),
                color=STEEL) for s, d in (("left", 1), ("right", -1))]
OBJECTS += [
    Box("boxcar", pos=((CAR_X0 + CAR_X1) / 2, 0.0, TOP + 0.018), size=(CAR_X1 - CAR_X0, 0.026, 0.024), color=(0.43, 0.30, 0.24)),
    Box("bumper_post", pos=(0.450, 0.0, TOP + 0.015), size=(0.008, 0.030, 0.030), color=(0.80, 0.12, 0.10)),
]

# -- derail mounts with lock sockets, and the flag socket (fixed) ------------------------------------------------------
MOUNT_Y, LOCK_Y = 0.020, 0.054
MOUNTS = {"far": 0.240, "near": 0.322}  # mount centres along the track (x)
WALL_H = 0.006
DERAIL = (0.012, 0.014, 0.020)  # along track, across, tall
PIN = (0.010, 0.010, 0.020)
FLAG = (0.008, 0.008, 0.050)
FLAG_SOCKET = (0.200, 0.0)
CLEAR = 0.005  # each socket is 5 mm wider than its part on every side: the moving hand lags its target ~5 mm


def _socket(name, cx, cy, inner_x, inner_y, h=WALL_H, t=0.004):
    """Four fixed walls round an inner_x by inner_y opening."""
    return [
        Box(f"{name}_wx0", pos=(cx - inner_x / 2 - t / 2, cy, TOP + h / 2), size=(t, inner_y + 2 * t, h), color=STEEL),
        Box(f"{name}_wx1", pos=(cx + inner_x / 2 + t / 2, cy, TOP + h / 2), size=(t, inner_y + 2 * t, h), color=STEEL),
        Box(f"{name}_wy0", pos=(cx, cy - inner_y / 2 - t / 2, TOP + h / 2), size=(inner_x, t, h), color=STEEL),
        Box(f"{name}_wy1", pos=(cx, cy + inner_y / 2 + t / 2, TOP + h / 2), size=(inner_x, t, h), color=STEEL),
    ]


for m, mx in MOUNTS.items():
    OBJECTS += _socket(f"mount_{m}", mx, MOUNT_Y, DERAIL[0] + 2 * CLEAR, DERAIL[1] + 2 * CLEAR)
    OBJECTS += _socket(f"lock_{m}", mx, LOCK_Y, PIN[0] + 2 * CLEAR, PIN[1] + 2 * CLEAR)
OBJECTS += _socket("flag_socket", *FLAG_SOCKET, FLAG[0] + 2 * CLEAR, FLAG[1] + 2 * CLEAR)

# -- loose parts -------------------------------------------------------------------------------------------------------
START = {"derail": (0.225, 0.125), "lock_pin": (0.215, -0.095), "blue_flag": (0.235, -0.145)}
SIZES = {"derail": DERAIL, "lock_pin": PIN, "blue_flag": FLAG}
OBJECTS += [
    Box("derail", pos=(*START["derail"], TOP + DERAIL[2] / 2), size=DERAIL, mass=0.05, color=(0.95, 0.80, 0.10)),
    Box("lock_pin", pos=(*START["lock_pin"], TOP + PIN[2] / 2), size=PIN, mass=0.03, color=(0.30, 0.32, 0.35)),
    Box("blue_flag", pos=(*START["blue_flag"], TOP + FLAG[2] / 2), size=FLAG, mass=0.03, color=(0.12, 0.30, 0.85)),
]
PARTS = tuple(START)

# -- scoring -----------------------------------------------------------------------------------------------------------
XY_TOL, Z_TOL, UPRIGHT_DEG = 0.006, 0.004, 10.0


def _tilt_deg(q):
    x, y, _, _ = (float(v) for v in q)
    return math.degrees(math.acos(min(1.0, abs(1 - 2 * (x * x + y * y)))))


def _seated(st, cx, cy, size, z_tol=Z_TOL, max_tilt=UPRIGHT_DEG):
    """Standing in the socket at (cx, cy): centre within 6 mm of it side to side and front to back, within z_tol of its
    resting height, tilted under max_tilt."""
    return (math.hypot(st.pos[0] - cx, st.pos[1] - cy) <= XY_TOL and abs(st.pos[2] - (TOP + size[2] / 2)) < z_tol
            and _tilt_deg(st.quat_xyzw) < max_tilt)


def derail_mount(objects):
    """Which mount the derail sits in, or None."""
    for m, mx in MOUNTS.items():
        # the derail may lean on a mount wall (up to 20 degrees); lying down puts its centre 3+ mm lower and fails
        if _seated(objects["derail"], mx, MOUNT_Y, DERAIL, z_tol=0.0025, max_tilt=20.0):
            return m
    return None


def protected_mount(m):
    """A mount counts only if it is between the car and the open end and at least 50 ft (scaled) from the car."""
    return MOUNTS[m] < CAR_X0 and CAR_X0 - MOUNTS[m] >= MIN_DIST



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
    """0.4 derail seated in a qualifying mount; +0.2 lock pin seated in that mount's lock socket; +0.4 blue flag
    standing in the flag socket at the open end."""
    if _DEBUG:
        _debug(objects)
    s = 0.0
    m = derail_mount(objects)
    if m is not None and protected_mount(m):
        s += 0.4
        if _seated(objects["lock_pin"], MOUNTS[m], LOCK_Y, PIN):
            s += 0.2
    if _seated(objects["blue_flag"], *FLAG_SOCKET, FLAG):
        s += 0.4
    return round(s, 3)


def success(objects):
    return score(objects) >= 0.999 and all(objects[n].resting() for n in PARTS)


GOAL = {"derail": (MOUNTS["far"], MOUNT_Y), "lock_pin": (MOUNTS["far"], LOCK_Y), "blue_flag": FLAG_SOCKET}


def distance(objects):
    return float(sum(math.hypot(objects[n].pos[0] - x, objects[n].pos[1] - y) for n, (x, y) in GOAL.items()))


# -- scripted demo -----------------------------------------------------------------------------------------------------
TRAVEL_Z = TOP + 0.090
YAW = {"left": -math.pi / 2, "right": math.pi / 2}  # fingers close along world x
TIP_ABOVE_WALLS = WALL_H + 0.002  # pad tips stay above the socket walls when setting a part in
SETTLE = 0.8
REST = {"left": (0.20, 0.25), "right": (0.20, -0.25)}


def _place(name, yaw, goal):
    size = SIZES[name]
    sx, sy = START[name]
    gx, gy = goal
    grip_z = TOP + TIP_ABOVE_WALLS + PAD_TIP_PAST_TCP  # same height above the table at pick and place
    open_w = -(size[0] / 2 + 0.010)
    return [
        Waypoint(1.5, (sx, sy, TRAVEL_Z), open_w, f"to the {name}", yaw),
        Waypoint(1.2, (sx, sy, grip_z), open_w, "descend", yaw),
        Waypoint(0.8, (sx, sy, grip_z), 0.0, "grip", yaw),
        Waypoint(1.2, (sx, sy, TRAVEL_Z), 0.0, "lift", yaw),
        Waypoint(1.8, (gx, gy, TRAVEL_Z), 0.0, "over the socket", yaw),
        Waypoint(SETTLE, (gx, gy, TRAVEL_Z), 0.0, "settle", yaw),
        Waypoint(1.4, (gx, gy, grip_z + 0.003), 0.0, "lower into the socket", yaw),
        Waypoint(SETTLE, (gx, gy, grip_z + 0.003), 0.0, "settle", yaw),
        Waypoint(0.6, (gx, gy, grip_z + 0.003), open_w, "let go", yaw),
        Waypoint(1.2, (gx, gy, TRAVEL_Z), open_w, "up", yaw),
    ]


def _park(arm, dur, label="wait"):
    return Waypoint(dur, (*REST[arm], TRAVEL_Z), FINGER_OPEN, label, YAW[arm])


def demo():
    """Left arm seats the derail in the far mount (110 mm from the car) and moves clear; the right arm then puts the
    lock pin in that mount's lock socket and stands the blue flag in the flag socket at the open end."""
    left = _place("derail", YAW["left"], GOAL["derail"]) + [_park("left", 1.2, "clear")]
    right = [_park("right", sum(w.duration for w in left))]
    right += _place("lock_pin", YAW["right"], GOAL["lock_pin"]) + _place("blue_flag", YAW["right"], GOAL["blue_flag"])
    right += [_park("right", 1.2, "clear")]
    return {"left": left, "right": right}

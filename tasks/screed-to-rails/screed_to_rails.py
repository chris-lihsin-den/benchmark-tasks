"""On the station table: a small slab form, about 1:10, laid out away from the arms. Two steel screed rails run forward
on either side of it, their tops 30 mm above the table. Between them a grey base slab is already set, and on it lies
one layer of fresh fill: grey balls, 12 mm across, packed in a 10 x 12 grid whose tops sit just under the rail tops.
In the middle of the form is a box-out: a small open box, flush with the rail tops, that must stay empty (it is the
opening for a floor drain). Six low spots, each two cells missing side by side, lie on either side of the form, and 12
tan surplus balls rest on top of the near end of the fill, four of them in line with the box-out. Each low spot takes
one ball, so that is only six more than the low spots need. A wooden stop board closes the near end of the form and an end board the far end; past the end
board is a waste trough. A grey screed board, longer than the form is wide, rests across both rails behind the near
stop, and a small hand float lies on the table beside each rail.

Goal: the fill struck off to the rails, as a concrete crew does with a screed: no ball standing above the rail tops,
the low spots filled from the surplus, the box-out empty, and what is left pushed off the far end into the waste trough.
Pushed straight down the form, the surplus in line with the box-out falls into it, so it has to be moved aside first.

Run it:  inspect-robots run --embodiment yam_arena -E task=screed_to_rails.py -E object_jitter=0 \\
           --instruction "<see INSTRUCTION below>" --scorer task_score ...
"""

import math
import os

from yam_arena.constants import FINGER_OPEN, PAD_TIP_PAST_TCP
from yam_arena.demo import Waypoint
from yam_arena.task_file import TABLE_TOP, Box, Sphere

SCENE = "station"
TOP = TABLE_TOP[SCENE]

INSTRUCTION = (
    "Strike off the fresh fill to the screed rails. Drag the grey screed board along both rails, both ends on the "
    "rails, so that no ball stands above the rail tops and the low spots in the surface are filled, and push what is "
    "left off the far end into the waste trough. The box-out in the middle of the form is a drain opening and must "
    "stay empty. There is only a little more fill than the low spots need, so do not waste it. You may use the two hand "
    "floats. Leave no ball anywhere else on the table."
)

# -- form (fixed) ------------------------------------------------------------------------------------------------------
R = 0.006  # ball radius
D = 2 * R
RAIL_TOP = 0.030  # above the table
RAIL_Y = 0.078
RAIL_X0, RAIL_X1 = 0.195, 0.385
SLAB_TOP = 0.017  # the fill's balls rest on this; their tops are 1 mm under the rail tops
FORM_X0, FORM_X1 = 0.220, 0.340  # inner faces of the near stop board and the far end board
FORM_HALF = 0.075  # inner faces of the rails
NX, NY = 10, 12
CELL_X = [FORM_X0 + R + D * i for i in range(NX)]  # 0.226 .. 0.334
CELL_Y = [-0.066 + D * j for j in range(NY)]  # -0.066 .. 0.066
TROUGH_X0, TROUGH_X1, TROUGH_HALF = FORM_X1 + 0.003, 0.392, 0.082
END_BOARD_H = 0.026
STEEL, WOOD = (0.50, 0.52, 0.55), (0.55, 0.42, 0.29)
OBJECTS = [
    Box("rail_left", pos=((RAIL_X0 + RAIL_X1) / 2, RAIL_Y, TOP + RAIL_TOP / 2), size=(RAIL_X1 - RAIL_X0, 0.006, RAIL_TOP), color=STEEL),
    Box("rail_right", pos=((RAIL_X0 + RAIL_X1) / 2, -RAIL_Y, TOP + RAIL_TOP / 2), size=(RAIL_X1 - RAIL_X0, 0.006, RAIL_TOP), color=STEEL),
    Box("base_slab", pos=((FORM_X0 + FORM_X1) / 2, 0.0, TOP + SLAB_TOP / 2), size=(FORM_X1 - FORM_X0, 2 * FORM_HALF, SLAB_TOP),
        color=(0.60, 0.61, 0.59)),
    Box("stop_board", pos=(FORM_X0 - 0.003, 0.0, TOP + RAIL_TOP / 2), size=(0.006, 2 * FORM_HALF, RAIL_TOP), color=WOOD),
    # the end board stands only 26 mm (3 mm above the fill layer's centres): it holds the fill, and the surplus rolls
    # over it into the trough instead of wedging against its top edge under the screed
    Box("end_board", pos=(FORM_X1 + 0.003, 0.0, TOP + END_BOARD_H / 2), size=(0.006, 2 * FORM_HALF, END_BOARD_H), color=WOOD),
    Box("trough_back", pos=(TROUGH_X1 + 0.002, 0.0, TOP + 0.015), size=(0.004, 2 * TROUGH_HALF + 0.008, 0.030), color=WOOD),
    Box("trough_left", pos=((TROUGH_X0 + TROUGH_X1) / 2, TROUGH_HALF + 0.002, TOP + 0.015),
        size=(TROUGH_X1 - TROUGH_X0, 0.004, 0.030), color=WOOD),
    Box("trough_right", pos=((TROUGH_X0 + TROUGH_X1) / 2, -TROUGH_HALF - 0.002, TOP + 0.015),
        size=(TROUGH_X1 - TROUGH_X0, 0.004, 0.030), color=WOOD),
]

# box-out: an open box flush with the rail tops over cells (5..6, 5..6), thin walls on the base slab
BOX_CELLS = {(5, 5), (5, 6), (6, 5), (6, 6)}
BOX_X, BOX_HALF = (CELL_X[5] + CELL_X[6]) / 2, 0.0105  # inner half width; the walls are 1.5 mm thick
WALL_T = 0.0015
for name, cx, cy, sx, sy in (("boxout_near", BOX_X - BOX_HALF - WALL_T / 2, 0.0, WALL_T, 2 * BOX_HALF + 2 * WALL_T),
                             ("boxout_far", BOX_X + BOX_HALF + WALL_T / 2, 0.0, WALL_T, 2 * BOX_HALF + 2 * WALL_T),
                             ("boxout_left", BOX_X, BOX_HALF + WALL_T / 2, 2 * BOX_HALF, WALL_T),
                             ("boxout_right", BOX_X, -BOX_HALF - WALL_T / 2, 2 * BOX_HALF, WALL_T)):
    OBJECTS.append(Box(name, pos=(cx, cy, TOP + (SLAB_TOP + RAIL_TOP) / 2), size=(sx, sy, RAIL_TOP - SLAB_TOP),
                       color=(0.85, 0.30, 0.18)))

# A surplus ball rests in a pocket between four fill balls and, pushed forward, rolls along the groove between two
# rows. A low spot is two cells missing side by side across one groove, (column, groove j) = cells (c, j) and (c, j+1):
# a ball rolling down that groove drops into it. Three on each side, one per groove that carries surplus.
LOW_SPOTS = [(6, 1), (4, 2), (3, 3), (6, 9), (4, 8), (3, 7)]  # near the start, so the surplus drops in before it piles up
HOLLOWS = {(c, j + d) for c, j in LOW_SPOTS for d in (0, 1)}
POCKET_Z = SLAB_TOP + R + math.sqrt(D * D - 2 * R * R)  # a ball resting on four neighbours
# surplus in the pockets over the two near columns; pocket (i, j) sits between cells i, i+1 and rows j, j+1
CENTRE_POCKETS = [(i, j) for i in (0, 1) for j in (4, 6)]  # in line with the box-out; pocket row 5 is left empty
SIDE_POCKETS = [(i, j) for i in (0, 1) for j in (1, 2, 8, 9)]  # kept 20 mm in from the rails
SURPLUS = CENTRE_POCKETS + SIDE_POCKETS  # 12: six more than the six low spots
FILL_GREY, SURPLUS_TAN = (0.70, 0.69, 0.65), (0.80, 0.66, 0.44)
OBJECTS += [Sphere(f"fill_{i}_{j}", pos=(CELL_X[i], CELL_Y[j], TOP + SLAB_TOP + R), radius=R, mass=0.004, color=FILL_GREY)
            for i in range(NX) for j in range(NY) if (i, j) not in HOLLOWS | BOX_CELLS]
OBJECTS += [Sphere(f"surplus_{n}", pos=(CELL_X[i] + R, CELL_Y[j] + R, TOP + POCKET_Z), radius=R, mass=0.004, color=SURPLUS_TAN)
            for n, (i, j) in enumerate(SURPLUS)]
BALLS = tuple(o.name for o in OBJECTS if isinstance(o, Sphere))
N_CELLS = NX * NY - len(BOX_CELLS)  # 116

# two hand floats on the table, one beside each rail: 50 mm long (along x), 6 mm thick, 25 mm tall
FLOAT = (0.050, 0.006, 0.025)
FLOAT_START = {"left": (0.150, 0.135), "right": (0.150, -0.135)}
OBJECTS += [Box(f"float_{a}", pos=(*FLOAT_START[a], TOP + FLOAT[2] / 2), size=FLOAT, mass=0.02, color=(0.30, 0.55, 0.62))
            for a in ("left", "right")]

SCREED = (0.014, 0.200, 0.025)
SCREED_START_X = 0.205
OBJECTS += [Box("screed", pos=(SCREED_START_X, 0.0, TOP + RAIL_TOP + SCREED[2] / 2), size=SCREED, mass=0.08, color=(0.42, 0.48, 0.54))]

# -- scoring -----------------------------------------------------------------------------------------------------------
HIGH_TOL = 0.001  # a ball's top may stand at most 1 mm above the rail tops
LAYER_Z = SLAB_TOP + R  # centre height of a ball lying on the base slab
BED_MIN = 94  # balls in the fill layer for the bed to count as still there (104 at the start)
SPOTS_MIN = 5  # low spots that must hold a ball: at most one left unfilled


def _in_form(p):
    return FORM_X0 <= p[0] <= FORM_X1 and abs(p[1]) <= FORM_HALF


def in_boxout(p):
    return abs(p[0] - BOX_X) <= BOX_HALF and abs(p[1]) <= BOX_HALF


def _in_trough(p):
    return TROUGH_X0 <= p[0] <= TROUGH_X1 and abs(p[1]) <= TROUGH_HALF


def spots_filled(objects):
    """Low spots holding a ball that rests on the base slab inside them."""
    n = 0
    for c, j in LOW_SPOTS:
        cx, cy = CELL_X[c], CELL_Y[j] + R
        if any(abs(objects[b].pos[0] - cx) <= R + 0.002 and abs(objects[b].pos[1] - cy) <= D
               and abs(objects[b].pos[2] - TOP - LAYER_Z) < 0.003 for b in BALLS):
            n += 1
    return n


def tally(objects):
    """(balls standing above the rail tops inside the form, balls in the fill layer, balls in the trough, strays,
    balls in the box-out)."""
    high = layer = trough = stray = boxed = 0
    for n in BALLS:
        p = objects[n].pos
        z = p[2] - TOP
        if in_boxout(p):
            boxed += 1
        elif _in_form(p):
            if z + R > RAIL_TOP + HIGH_TOL:
                high += 1
            elif abs(z - LAYER_Z) < 0.003:
                layer += 1
        elif _in_trough(p):
            trough += 1
        else:
            stray += 1
    return high, layer, trough, stray, boxed


def score(objects):
    """0.3 once nothing stands above the rail tops, the box-out is empty and the fill layer is still in place (at least
    94 balls on the base slab); +0.5 if at least five of the six low spots hold a ball; +0.2 if every ball is in the
    form or the trough, none elsewhere. Doing nothing scores 0: the surplus stands above the rails. Pushing the
    surplus straight down the form drops some into the box-out (0); wasting it into the trough leaves the low spots
    empty (0.5)."""
    if _DEBUG:
        _debug(objects)
    high, layer, _, stray, boxed = tally(objects)
    if high or boxed or layer < BED_MIN:
        return 0.0
    s = 0.3
    if spots_filled(objects) >= SPOTS_MIN:
        s += 0.5
    if stray == 0:
        s += 0.2
    return round(s, 3)


def success(objects):
    return score(objects) >= 0.999 and all(objects[n].resting() for n in BALLS)


def distance(objects):
    high, layer, _, stray, boxed = tally(objects)
    return float(0.01 * (high + stray + boxed + len(LOW_SPOTS) - spots_filled(objects)))


# -- debug: TASK_DEBUG=1 prints the tally and the screed's position every 2 s of robot time ----------------------------
_DEBUG = os.environ.get("TASK_DEBUG") == "1"
_calls = [0]


def _debug(objects):
    _calls[0] += 1
    if _calls[0] % 40:
        return
    high, layer, trough, stray, boxed = tally(objects)
    sp = objects["screed"].pos
    odd = []
    for n in BALLS:
        p = objects[n].pos
        if in_boxout(p) or not (_in_form(p) or _in_trough(p)) or (_in_form(p) and p[2] - TOP + R > RAIL_TOP + HIGH_TOL):
            odd.append(f"{n.replace('surplus_', 's').replace('fill_', 'f')}@{p[0]*1000:.0f},{p[1]*1000:.0f},{(p[2]-TOP)*1000:.0f}")
    print(f"DBG step {_calls[0]}: high {high} spots {spots_filled(objects)}/{len(LOW_SPOTS)} layer {layer} boxout {boxed} trough {trough} stray {stray} | screed "
          f"{sp[0]*1000:.1f},{sp[1]*1000:.1f},{(sp[2]-TOP)*1000:.1f} | " + " ".join(odd), flush=True)


# -- scripted demo ----------------------------------------------------------------------------------------------------
GRIP_Y = 0.094  # each hand holds one end of the screed, outside the rails
YAW = {"left": -math.pi / 2, "right": math.pi / 2}  # fingers close along world x
TIP_ABOVE_RAILS = 0.007  # pad tips stay above the rails
GRIP_Z = TOP + RAIL_TOP + TIP_ABOVE_RAILS + PAD_TIP_PAST_TCP
PRESS = 0.0  # command the screed exactly at rail height: pressing it down tipped its front edge into the fill,
# and holding it higher let it ride over surplus balls (whose centres are only 1.5 mm above the rail tops)
TRAVEL_Z = TOP + 0.095
OPEN_W = -(SCREED[0] / 2 + 0.012)
END_X = 0.360  # screed centre at the end of the pass: its front face 7 mm past the end board
STROKE = 0.012  # advance per stroke
REST = {"left": (0.20, 0.25), "right": (0.20, -0.25)}

# hand floats: held by their ends (fingers along x), bottom 0.5 mm above the rail tops so they ride over the fill
FLOAT_OPEN = -(FLOAT[0] / 2 + 0.010)
FLOAT_PICK_Z = TOP + 0.009 + PAD_TIP_PAST_TCP
FLOAT_SWEEP_Z = TOP + SLAB_TOP + D + 0.001 + 0.009 + PAD_TIP_PAST_TCP  # float bottom 1 mm above the fill tops
FLOAT_X = 0.238  # over the two near columns, where the surplus lies
# set down in the empty middle groove, then push the two balls on this side one groove outward (12 mm): rolling
# down that groove they pass the box-out 6 mm clear
SWEEP = {"left": (0.0, 0.0155), "right": (0.0, -0.0155)}


def _float_pass(arm):
    """Pick this arm's float, sweep the surplus in line with the box-out off to this arm's side, put the float back."""
    sx, sy = FLOAT_START[arm]
    y0, y1 = SWEEP[arm]
    yaw = YAW[arm]
    return [
        Waypoint(1.5, (sx, sy, TRAVEL_Z), FLOAT_OPEN, f"to the {arm} hand float", yaw),
        Waypoint(1.0, (sx, sy, FLOAT_PICK_Z), FLOAT_OPEN, "down to its ends", yaw),
        Waypoint(0.6, (sx, sy, FLOAT_PICK_Z), 0.0, "grip", yaw),
        Waypoint(1.0, (sx, sy, TRAVEL_Z), 0.0, "lift", yaw),
        Waypoint(1.6, (FLOAT_X, y0, TRAVEL_Z), 0.0, "over the surplus in line with the box-out", yaw),
        Waypoint(1.2, (FLOAT_X, y0, FLOAT_SWEEP_Z), 0.0, "lower onto the fill", yaw),
        Waypoint(2.0, (FLOAT_X, y1, FLOAT_SWEEP_Z), 0.0, "push it one groove over, out of line with the box-out", yaw),
        Waypoint(0.6, (FLOAT_X, y1, FLOAT_SWEEP_Z), 0.0, "settle", yaw),
        Waypoint(1.0, (FLOAT_X, y1, TRAVEL_Z), 0.0, "lift", yaw),
        Waypoint(1.6, (sx, sy, TRAVEL_Z), 0.0, "back beside the rail", yaw),
        Waypoint(1.0, (sx, sy, FLOAT_PICK_Z), 0.0, "set it down", yaw),
        Waypoint(0.5, (sx, sy, FLOAT_PICK_Z), FLOAT_OPEN, "let go", yaw),
        Waypoint(1.0, (sx, sy, TRAVEL_Z), FLOAT_OPEN, "up", yaw),
        Waypoint(1.4, (*REST[arm], TRAVEL_Z), FINGER_OPEN, "clear", yaw),
    ]


def _screed_pass():
    plan = [
        (1.6, SCREED_START_X, TRAVEL_Z, OPEN_W, "over the screed's ends", 0.0),
        (1.2, SCREED_START_X, GRIP_Z, OPEN_W, "down to its ends, outside the rails", 0.0),
        (0.8, SCREED_START_X, GRIP_Z - PRESS, 0.0, "grip both ends", 0.0),
    ]
    x, k = SCREED_START_X, 0
    while x < END_X - 1e-9:
        x = min(END_X, x + STROKE)
        # no sideways sawing: it pinched balls against the rails and popped them over
        plan.append((1.4, x, GRIP_Z - PRESS, 0.0, "strike off: drag slowly along both rails", 0.0))
        plan.append((0.5, x, GRIP_Z - PRESS, 0.0, "pause: let the rolling balls settle into the low spots", 0.0))
        k += 1
    plan += [
        (1.0, END_X, GRIP_Z - PRESS, 0.0, "settle", 0.0),
        (0.6, END_X, GRIP_Z, OPEN_W, "let go", 0.0),
        (1.2, END_X, TRAVEL_Z, OPEN_W, "up", 0.0),
    ]
    out = {}
    for arm, sign in (("left", 1), ("right", -1)):
        wps = [Waypoint(d, (x, sign * GRIP_Y + dy, z), f, label, YAW[arm]) for d, x, z, f, label, dy in plan]
        wps.append(Waypoint(1.5, (*REST[arm], TRAVEL_Z), FINGER_OPEN, "clear", YAW[arm]))
        out[arm] = wps
    return out


def _dur(wps):
    return sum(w.duration for w in wps)


def _wait(arm, dur):
    return Waypoint(dur, (*REST[arm], TRAVEL_Z), FINGER_OPEN, "wait", YAW[arm])


def demo():
    """The surplus in line with the box-out would drop into it, so it is moved aside first: the left hand float sweeps
    its left half toward the left rail, then the right hand float its right half toward the right rail. Then both
    hands take the screed by its ends and drag it slowly along the rails in short strokes, so the
    surplus rolls ahead down its groove into the low spot on it, passes the box-out on either side of it, and what is left goes
    over the end board into the trough."""
    fl, fr = _float_pass("left"), _float_pass("right")
    sc = _screed_pass()
    left = fl + [_wait("left", _dur(fr))] + sc["left"]
    right = [_wait("right", _dur(fl))] + fr + sc["right"]
    return {"left": left, "right": right}

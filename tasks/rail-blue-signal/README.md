# Lock a derail and post a blue flag before work under a railcar

Under the US blue-signal rule (49 CFR 218), before anyone works under a car the track's open end gets a blue flag and a derail locked at least 50 ft from the car, between it and the open end. Here two mounts look alike; only one is on the right side and far enough.

## Files

| File | What |
|---|---|
| `task.json` | Task details for review |
| `rail_blue_signal.py` | `yam_arena` task file: scene, `success()`, `score()`, `distance()` and the scripted `demo()` |

## Run a trial

Station scene, fixed layout, no randomization (`object_jitter=0`), no seeds. Run from the repository root.

```bash
# Dream-1
inspect-robots run --embodiment yam_arena --policy dream \
  -E task=tasks/rail-blue-signal/rail_blue_signal.py -E object_jitter=0 -E control_hz=20 \
  -E cam_width=320 -E cam_height=176 \
  --instruction "Workers are about to go under the boxcar. Set up blue-signal protection: seat the yellow derail in the mount that is between the car and the open end of the track and at least 50 ft from the car, lock it by putting the steel pin in that mount's lock socket, and stand the blue flag in the flag socket at the open end. The model is 1:150, so 50 ft is 102 mm." \
  --scorer task_score --max-steps 2400 --store-frames --log-dir ~/yam-eval/rail-blue-signal-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=tasks/rail-blue-signal/rail_blue_signal.py -E object_jitter=0 -E control_hz=20 \
  -E cam_width=320 -E cam_height=176 \
  --instruction "Workers are about to go under the boxcar. Set up blue-signal protection: seat the yellow derail in the mount that is between the car and the open end of the track and at least 50 ft from the car, lock it by putting the steel pin in that mount's lock socket, and stand the blue flag in the flag socket at the open end. The model is 1:150, so 50 ft is 102 mm." \
  --scorer task_score --max-steps 2400 --store-frames --log-dir ~/yam-eval/rail-blue-signal-demo
```

Runtime per trial: up to 2 minutes of robot time (2,400 steps at 20 Hz); the scripted demo finishes its motions
after about 37 s.

## Scoring

A part is seated in a socket when its centre is within 6 mm of the socket centre and 4 mm of its resting height and it is tilted under 10 degrees; the derail may lean on a mount wall up to 20 degrees, with its centre within 2.5 mm of its resting height (lying down fails). 0.4 if the derail is seated in a mount between the car and the open end at least 102 mm (50 ft at 1:150) from the car (only the 240 mm mount qualifies); +0.2 if the lock pin is seated in that mount's lock socket; +0.4 if the blue flag is seated in the flag socket. The near mount earns nothing. Success once the score is 1.0 and the parts are still for 1 s.

`score()` in `rail_blue_signal.py` implements this; the module docstring and `demo()` docstring describe the scene and the
scripted solution.

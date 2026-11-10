# Strike off a fresh fill to its screed rails, keeping the drain box-out empty and wasting no fill

Concrete crews strike off fresh concrete with a straightedge screed riding on two screed rails set to the finished level (ACI 302.1R): high material is carried ahead in a roll to fill low spots, and the surplus is pushed off the end. Box-outs for drains and sleeves must be kept free of concrete, so material in line with one is moved aside by hand float before the screed passes. Ready-mix is ordered with only a small overage, so a crew that wastes the roll ahead of the screed is left with low spots.

## Files

| File | What |
|---|---|
| `task.json` | Task details for review |
| `screed_to_rails.py` | `yam_arena` task file: scene, `success()`, `score()`, `distance()` and the scripted `demo()` |

## Run a trial

Station scene, fixed layout, no randomization (`object_jitter=0`), no seeds. Run from the repository root.

```bash
# Dream-1
inspect-robots run --embodiment yam_arena --policy dream \
  -E task=tasks/screed-to-rails/screed_to_rails.py -E object_jitter=0 -E control_hz=20 \
  -E cam_width=320 -E cam_height=176 \
  --instruction "Strike off the fresh fill to the screed rails. Drag the grey screed board along both rails, both ends on the rails, so that no ball stands above the rail tops and the low spots in the surface are filled, and push what is left off the far end into the waste trough. The box-out in the middle of the form is a drain opening and must stay empty. There is only a little more fill than the low spots need, so do not waste it. You may use the two hand floats. Leave no ball anywhere else on the table." \
  --scorer task_score --max-steps 2400 --store-frames --log-dir ~/yam-eval/screed-to-rails-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=tasks/screed-to-rails/screed_to_rails.py -E object_jitter=0 -E control_hz=20 \
  -E cam_width=320 -E cam_height=176 \
  --instruction "Strike off the fresh fill to the screed rails. Drag the grey screed board along both rails, both ends on the rails, so that no ball stands above the rail tops and the low spots in the surface are filled, and push what is left off the far end into the waste trough. The box-out in the middle of the form is a drain opening and must stay empty. There is only a little more fill than the low spots need, so do not waste it. You may use the two hand floats. Leave no ball anywhere else on the table." \
  --scorer task_score --max-steps 2400 --store-frames --log-dir ~/yam-eval/screed-to-rails-demo
```

Runtime per trial: up to 2 minutes of robot time (2,400 steps at 20 Hz); the scripted demo finishes its motions
after about 64 s.

## Scoring

A ball stands high if it is in the form and its top is more than 1 mm above the rail tops; it is in the box-out if its centre is inside the box-out's walls; a low spot is filled when a ball rests on the base slab inside it. 0.3 once no ball stands high, the box-out is empty and at least 94 balls rest on the base slab; +0.5 if at least five of the six low spots are filled; +0.2 if every ball is in the form or the waste trough, none elsewhere. Doing nothing scores 0 (the surplus stands above the rails); pushing the surplus straight down the form drops some into the box-out (0); pushing it all into the trough leaves the low spots empty (0.5). Success once the score is 1.0 and the balls are still for 1 s.

`score()` in `screed_to_rails.py` implements this; the module docstring and `demo()` docstring describe the scene and the
scripted solution.

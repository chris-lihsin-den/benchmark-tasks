# Shelve two books by LC call number, opening each gap first

Library shelvers file returns by Library of Congress call number, where the class number sorts as a decimal: QA76.625 comes before QA76.73, and QA76.8 before QA76.9, the commonest shelving mistake. The shelf has no gaps, so the books to the right of each slot must be slid along before a book fits.

## Files

| File | What |
|---|---|
| `task.json` | Task details for review |
| `library_call_number.py` | `yam_arena` task file: scene, `success()`, `score()`, `distance()` and the scripted `demo()` |

## Run a trial

Station scene, fixed layout, no randomization (`object_jitter=0`), no seeds. Run from the repository root.

```bash
# Dream-1
inspect-robots run --embodiment yam_arena --policy dream \
  -E task=tasks/library-call-number/library_call_number.py -E object_jitter=0 -E control_hz=20 \
  -E cam_width=320 -E cam_height=176 \
  --instruction "Shelve the two returned books in Library of Congress call-number order, left to right as you face the shelf. The shelved books are, from the left: green QA75.5, blue QA76.5, red QA76.73, purple QA76.9, orange QA77. The yellow book is QA76.625 and the teal book is QA76.8. Keep every book upright on the shelf." \
  --scorer task_score --max-steps 2400 --store-frames --log-dir ~/yam-eval/library-call-number-dream

# Scripted demo (reaches 1.0)
inspect-robots run --embodiment yam_arena --policy yam_scripted \
  -E task=tasks/library-call-number/library_call_number.py -E object_jitter=0 -E control_hz=20 \
  -E cam_width=320 -E cam_height=176 \
  --instruction "Shelve the two returned books in Library of Congress call-number order, left to right as you face the shelf. The shelved books are, from the left: green QA75.5, blue QA76.5, red QA76.73, purple QA76.9, orange QA77. The yellow book is QA76.625 and the teal book is QA76.8. Keep every book upright on the shelf." \
  --scorer task_score --max-steps 2400 --store-frames --log-dir ~/yam-eval/library-call-number-demo
```

Runtime per trial: up to 2 minutes of robot time (2,400 steps at 20 Hz); the scripted demo finishes its motions
after about 47 s.

## Scoring

A book is shelved when it stands upright on the shelf (tilted under 10 degrees, centre within 4 mm of its resting height and within 12 mm of the books' line front to back) between the bookends. 0.2 per returned book shelved; +0.2 if both are shelved and all five original books are still shelved; +0.4 if all seven, read left to right, are in call-number order. Doing nothing scores 0; shelving both at the right end scores 0.6. Success once the score is 1.0 and all books are still for 1 s.

`score()` in `library_call_number.py` implements this; the module docstring and `demo()` docstring describe the scene and the
scripted solution. The demo aims each slide 7 mm past its target because a pushing hand stops short by about that much.

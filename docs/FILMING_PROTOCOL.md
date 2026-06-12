# Filming Protocol — self-testing camera-tracked exercises (R2-W1-8)

How to verify each camera-tracked exercise on a real phone before it ships.
Work through `docs/EXERCISE_TEST_CHECKLIST.md` top-to-bottom (most-prescribed
first) and record the result in its last column.

## Setup (same every time)

1. **Phone**: use your actual target device, in Chrome/Safari over HTTPS
   (camera requires a secure context). Battery > 30% — MediaPipe is heavy.
2. **Camera placement**: follow the on-screen instruction for the exercise
   (each ghost template carries its own `cameraPosition`):
   - *Front-view* exercises (squats, jumps, clamshell): phone at **waist
     height**, ~2.5–3 m back, portrait, whole body in frame including feet.
   - *Side-view* exercises (hinges, RDLs, rows, push-ups, planks): phone at
     **knee–hip height**, ~2.5 m to your side, LANDSCAPE if the body doesn't
     fit, whole body visible head to heels.
3. **Lighting**: light source in FRONT of you or overhead — never a window
   behind you (backlight kills landmark confidence).
4. **Clothing**: contrast with the background; avoid long loose skirts/robes
   that hide the knees.
5. **Floor space**: check the full movement stays in frame (do one rep before
   judging — especially lateral bounds and broad jump).

## The 5 checks per exercise

Do **one honest set of 5 good reps** (or a 20 s hold), then **2 deliberately
bad reps** as described. Mark the exercise PASS only if all five hold:

| # | Check | How |
|---|---|---|
| 1 | **Counts once per rep** | 5 good reps → counter shows exactly 5. No double counts, no missed reps. |
| 2 | **No count on partials** | Do 2 reps at clearly half depth → the rep counter must NOT advance; the orange "+N partial" line should appear instead. |
| 3 | **Score ≥ 85 on honest good reps** | After the good set, the form % shown should sit ≥ 85 while you're moving well. |
| 4 | **Cues fire at the right moment** | The voice/phase cue ("Lower slowly", "Push hips back") matches what your body is actually doing, within ~half a second. |
| 5 | **Ghost matches the motion** | The ghost skeleton demonstrates THIS exercise's movement — right joints, right direction, plausible depth. |

## Recording results

In `docs/EXERCISE_TEST_CHECKLIST.md`, write in the last column:
`2026-06-15 PASS` or `2026-06-15 FAIL: <which check, what happened>`
e.g. `FAIL: #2 counted both half-depth reps`.

## Failure triage

- **Check 1/2 fail** → the phase thresholds or debounce need tuning for this
  exercise: note knee/hip angles from debug mode (add `?debug=1` and set
  `window.VYAYAM_DEBUG = true` in the console — targets and live angles are
  logged per frame).
- **Check 3 fails on good form** → target angle likely too aggressive for the
  capability level; check the `js_overrides` for this exercise in
  `exercise_targets.json` against the Python module.
- **Check 4/5 fail** → mapping problem; the `js_type` in
  `export_exercise_targets.py` is wrong for this exercise. Fix the table,
  regenerate, retest.
- Any unfixable failure → flip the exercise to `MANUAL` in
  `export_exercise_targets.py` and regenerate. **An honest guided mode beats
  a wrong camera score every time.**

## Order of work

The first ~18 rows of the checklist are the most-prescribed exercises — a
new patient's first weeks are made almost entirely of these. Film them
first; everything else is incremental.

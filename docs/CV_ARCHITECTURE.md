# CV Architecture (R2-W1-1) — how exercise tracking actually works

Updated 2026-06 (Run 2). This is the map of the three CV implementations,
what ships, and how the live path is generated from the Python source of
truth.

## The three implementations (D5, resolved)

| Layer | Where | Status |
|---|---|---|
| **264 Python exercise modules** | `strength_app/exercise_system/exercises/*_v2.py` + registry | **Source of truth** for phases/targets (post-C3 corrected, H2-harness-verified). Runs in the therapist desktop headless runner. |
| **Live patient JS** | inline in `v1_exercise_execute.html` + `static/strength_app/js/cv_core.js` | **What patients use.** MediaPipe Pose in-browser; ghost-coach state machine; consumes the generated artifact below. |
| **Legacy `analyze_frame` endpoint** | `views.py` (route **removed**, R2-W1-7) | Scored every exercise with squat logic; nothing called it. Kept un-routed as reference for a future server-side dispatch. |
| (orphan) `exercise-analyzer.js` | `static/strength_app/js/` | Never loaded by any template. Historical; candidate for deletion. |

## The generated artifact — single source of truth for the live path

```
Python registry (265 modules)                       v1_exercise_execute.html
  get_target_poses(), unilateral, ...                        │
        │                                                    │ {% cv_config_json %}
        ▼                                                    ▼
manage.py export_exercise_targets  ──►  exercise_targets.json  ──►  CV_CONFIG (per page)
        ▲                                (committed, 288 entries)
        │
  curated js_type/tracking table (the R2-W1-2 audit lives HERE)
```

- `export_exercise_targets.py` holds the **audited table**: every exercise →
  `js_type` (which JS ghost template, or none) + `tracking`
  (`camera`/`manual`). Reasoning is commented per group; April-27 mapping
  bugs are fixed here (marching≠jump, wall_sit=squat-hold, mountain
  climbers≠push-up, nordics manual, the STRETCH fake-tracking fallback
  killed).
- The artifact also carries the Python phase targets verbatim and
  `js_overrides` — depth-phase angles ported into the JS template's joints
  where the correspondence is unambiguous (bottom-phase knee/hip/elbow).
  Anything ambiguous is NOT ported (never guessed).
- **Freshness is test-enforced** (`test_r2_w1_export_is_fresh` runs the
  command in `--check` mode). Edit the table, regenerate, commit both.
- A test also enforces: camera entries must have a `js_type`; manual entries
  must NOT (no path back to fake tracking); no `back`/`spine` joints in
  overrides (SB-15).

## Per-page flow

1. The execute template loads `CV_CONFIG` for the current exercise via the
   `{% cv_config_json %}` tag (server reads the committed JSON once,
   module-cached in `cv_targets.py`). Unknown ID → manual-mode stub.
2. `CV_TRACKING` = `camera` only if the audited table says so (assessment
   flows keep their dedicated camera logic).
3. **Camera mode**: MediaPipe starts on user tap → ghost coach state machine
   (`SETUP → DEMO → WAITING → GHOST_LEADS → USER_FOLLOWS → REP_DONE`,
   `GUIDING` for holds). `CV_CONFIG.js_type` selects the `EXERCISE_PHASES`
   template; `js_overrides` then capability easing adjust depth targets
   (conservative: the shallower of the two wins).
4. **Manual ("guided") mode**: no camera UI at all. Cue card + set tracker
   (+ hold timer for holds). `form_score: null`,
   `rep_quality_source: 'manual'` end-to-end — DB stores
   `overall_form_score=NULL` (mig 0020), XP is completion-based, no
   traffic-light from form, no fabricated 75s anywhere.

## Rep counting (camera mode)

- Phase advance: `computeMatchScore ≥ 70` for **5 consecutive frames** AND
  **≥ 250 ms in phase** (R2-W1-5 debounce). Score curve `100 − meanDiff×1.5`
  ⇒ the gate tolerates ≤ 20° mean deviation from the phase target.
- **Partials**: an 8 s stall short of the depth band marks the rep partial →
  it increments the visible "+N partial" counter and does **NOT** count
  toward prescribed reps (was the "partial reps counted" High finding).
- Holds: 1 s tick while `matchScore ≥ 40`, timer pauses otherwise.
- Plyo templates add landing checks (valgus, stiff-knee) as voice warnings.

## Pure-math core (R2-W1-9)

`static/strength_app/js/cv_core.js` (UMD) holds the extracted, verbatim:
`LM`, `calcAngle`, `computeMatchScore`, `findWorstJoint`,
`checkStanceWidth`, `detectOrientation`. The template aliases them from
`VyayamCV.*`. Node harness:

```
node --test strength_app/tests/js/cv_core.test.mjs
```

replays synthetic landmark/angle sequences (partial-rep gate, squat
trajectory sweep, stance/orientation). The ghost FSM itself is still
template-embedded (DOM/voice entangled) — covered by the filming protocol
instead (`docs/FILMING_PROTOCOL.md` + `docs/EXERCISE_TEST_CHECKLIST.md`).

## SB-15 in the JS path

Spinal position is **not measurable** with MediaPipe (no landmarks between
shoulders and hips). Rules enforced in this layer:

- No scored `back`/`spine` joint anywhere (test-enforced on the artifact;
  ROW_BENT_OVER's shoulder–hip–ankle angle renamed `hinge` — it measures
  staying-bent-over, and its cue says so).
- Measurement-driven cues never claim to see rounding ("Stay hinged forward
  — push your hips back", not "no rounding").
- Static setup instructions may still say "back flat" — that is standard
  coaching language, not a measurement claim.

## What "camera" does NOT mean

112 of 288 exercises are camera-tracked. Camera tracking verifies **joint-
angle trajectories** in one plane. It cannot see: spinal flexion, load,
contact/flight times (see the reactivity score note in
`docs/FOOTBALL_METHODS.md`), or pain. The honest boundary is restated to
coaches in the methods doc.

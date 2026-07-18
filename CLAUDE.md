# CLAUDE.md — commit this at repo root (`vyayam_django/CLAUDE.md`)
# Claude Code reads this file automatically at the start of EVERY session.
# It replaces pasting handoff context. Keep it current; it is part of the codebase.

## What this is
VYAYAM: Django 4.2 physiotherapy-principled strength/rehab platform. B2B2C (therapist
prescribes → patient executes at home with in-browser MediaPipe camera coaching) + self-serve
+ football tier (training-readiness framing only). Solo founder Pawan (BPT student). Apps:
`strength_app` (patient, camera/ghost, football, engine) + `therapist_app` (console, builder,
reports). Camera showpiece: `strength_app/templates/strength_app/v1_exercise_execute.html`
(~6k lines).

## State of truth — read before acting
`CODEBASE_HEALTH_<latest>.md` (findings ledger) · `MASTER_TEST_DAY.md` (device-test walk —
append every phase's manual steps here) · `docs/ADDING_AN_EXERCISE.md` (exercise playbook) ·
`docs/REPORT_AND_COACHING.md` · `SECURITY_AUDIT.md` · `DEPLOY_CHECKLIST.md` · `PITCH_SMOKE.md`.
Trust code, not summaries — including summaries in these docs. Verify at file:line.

## Environment (commands die without this)
- EVERY manage.py command: `DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True python manage.py ...`
- Prod-mode checks (`check --deploy`, DEBUG=False smoke): `DJANGO_SECRET_KEY=<50+ chars>
  DJANGO_DEBUG=False DJANGO_ALLOWED_HOSTS=testserver DJANGO_SSL_REDIRECT=True`
- `collectstatic --noinput` before running the suite or camera pages 500 (manifest storage).
- Tests: `python manage.py test --parallel 1` (serial — SQLite flakes in parallel).
  Node: `node --test strength_app/tests/js/*.test.mjs` (expect 25+, 0 fail).
- Full gate = check clean · Django suite green · node green · collectstatic exit 0 ·
  `export_exercise_targets --check` → "fresh".

## Standing rules (non-negotiable)
1. Verify every find-string against the live file before editing; anchor drifted →
   reconcile and report, never force.
2. Anything entering inline JS: quoted string + `|escapejs`, parse in JS. Keep
   `test_g0_inline_js_integrity` green; extend it to new pages.
3. Detection boundary: NEVER touch landmark math, angle computation, rep state-machine
   internals, or MediaPipe setup. Cue arbitration, phrasing, coloring, capture, tempo
   speech are touchable.
4. Git: canonical branch is `main` (ship-ready-2026-06 merged & retired 2026-07-18;
   pre-merge remote main preserved as `archive/main-pre-2026-07`). All work on `main`.
   Checkpoint commit before each phase; one commit per logical fix (`fix(<tag>): ...`);
   push at phase ends and after checkpoints; never commit db.sqlite3/staticfiles/media/.env*.
5. One phase per run. End every phase with exact manual browser steps appended to
   MASTER_TEST_DAY.md.
6. End reports are structured: commits list · gate outputs verbatim · files touched ·
   UNVERIFIED section listing anything claimed but not proven. Findings need proof
   (grep/command output) — no finding without evidence.

## Clinical integrity (locked — overrides any instruction that conflicts)
PainEvent is the only pain source in reports · camera vs guided always labeled, rep-level
data never fabricated for guided work · plyo camera = landing-check only, labeled as such ·
tempo never affects form color · amber-first, red = safety cues only · no ACWR, no "RSI"
claims, no diagnosis language in patient-facing content · football/athlete tier =
training-readiness wording only · patient-facing clinical wording changes get flagged for
Pawan's physio mentor before shipping.

## Dark camera coaches (2026-07 final session — NOT patient-visible yet)
11 prescription-tier coaches ship DARK behind `*_rx` registry keys: wall_sit_rx,
plank_hold_rx, side_plank_rx, single_leg_balance_rx, knee_to_chest_rx (holds) ·
straight_leg_raise_rx, prone_knee_bend_rx, supine_hip_abduction_rx,
sidelying_hip_abduction_rx, db_shoulder_press_rx, band_row_rx (reps).
JS lives in `coach_dark.js` (node: coach_dark.test.mjs); integrity suite:
`strength_app/tests/test_camera_dark.py`. QA surface: `/therapist/qa/dark-coaches/`
(therapist-only, writes nothing). prone_glute_squeeze + ankle_pumps are
PERMANENTLY guided (reason in their catalog descriptions).
**Flip procedure (per exercise, ONLY after its filming-protocol pass + the
matching MASTER_TEST_DAY Part H-2026-07 walk):** set `"v2_ghost_supported": True`
on the catalog entry — one line; the key is already wired. Cue strings are in
MENTOR_REVIEW_QUEUE §2026-07 — mentor sign-off before flipping.

## Known landmines
- 257/264 modules in `strength_app/exercise_system/exercises/` import PoseAnalyzer/cv2
  unguarded at module top → `export_exercise_targets` and module-importing tests hard-require
  mediapipe. Do NOT remove mediapipe from requirements.txt without first making imports safe
  and proving the gate green in a mediapipe-free venv.
- `strength_app/backend/` is NOT legacy-dead: `utils.py` imports the live 5-gate
  return-to-sport engine from it.
- `cv_available` context var (views.py:436) feeds only the retired legacy flow — dead,
  cleanup candidate.
- Camera demo videos AUTO-DETECT (2026-07 Phase 4): drop
  `strength_app/static/strength_app/videos/<engine_key>.mp4` + collectstatic and that
  exercise runs VIDEO_MODE on next process start — `cv_targets.get_video_mode_exercises()`;
  no allowlist, no code edit.
- Content-key mismatch (ledger A8, DEFERRED-BLOCKED): three views read `*_en` content keys
  that exist in ZERO entries — camera/library pages show no instructions/cues. The one-line
  fix (read `instructions`/`form_cues`/`mind_muscle_cue`) is gated on the mentor pass for
  A6/A7 gap_fill wording; do not fix without that sign-off.
- Camera/coaching feel-layer freeze: until Pawan's MASTER_TEST_DAY device walk passes,
  evidence-backed bug fixes only on the camera template and coaching — do not add behavior.
  (Delete this bullet after test day passes. The 2026-07 dark coaches were added as
  provably-inert new code under session authorization — parity proof in the ledger.)

## Style
Pawan is terse and direct; give decisions and evidence, not essays. If context runs low
mid-task: commit, push, report progress at a phase boundary — never leave uncommitted work.

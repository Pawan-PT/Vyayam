# CODEBASE HEALTH — Grand Examination (2026-06 cycle, executed 2026-07-04)

Branch `ship-ready-2026-06`. Four parallel read-only audit agents (A security,
B exercise system, C repo hygiene, D engine sweep) + main-session fixes.
Full agent findings with proofs: `/tmp/vyayam_audit/AGENT_{A,B,C,D}_FINDINGS.md`
(transient; substance consolidated here). Baseline at start AND end: 312
Django + 25 node tests green, check clean.

## Findings ledger (severity-ordered)

| ID | Sev | file:line (at finding time) | Finding | Status |
|----|-----|------------------------------|---------|--------|
| A1 | S2 | v1_therapist_session_views.py:494 | report_pain `set_number` unclamped → out-of-range 500s on prod Postgres (PositiveSmallIntegerField); SQLite hid it | **FIXED** e59ef7f (clamp [1,30] + test) |
| D1 | S2 | v1_prescription_engine.py:1696 | Coach/therapist prescription override dropped by bare `except: pass` — patient silently gets the un-overridden session | **FIXED** 93e8fa0 (logger.warning exc_info) |
| D2 | S2 | therapist_app/views.py:959 + v1_therapist_session_views.py:499 | Therapist threshold **0** ("skip above any pain") collapsed to default 5 at both write and read (`or`-falsy) | **FIXED** 84ff042 (is-not-None both ends + tests) |
| D8 | S2 | therapist_app/views.py:99,128 | Dashboard "Pain >5 last week" flag dead for real patients (trend never populated) — false all-clear | **FIXED** 231e79c (filled from PainEvent + test) |
| A2 | S3 | settings.py:128 + rate_limiter.py | LocMemCache limiter is per-process: limits ×worker-count under gunicorn, reset on deploy | **ACCEPTED/DOCUMENTED** c882e5d (SECURITY_AUDIT #20 + DEPLOY_CHECKLIST note; Redis/DB cache when one exists) |
| B1 | S3 | therapist_app/exercise_catalog.py:326 | Ghost key `lateral_bound_stick` = json stub (empty phases, no registry object); only entry without camera parity | **FIXED** f1ad176 (→ `lateral_bound_and_stick`; all 21 ghost entries verified) |
| C1 | S3 | strength_app/views.py:1078-1355 | Unrouted server-side analyze_frame CV stack (9 functions; squat-scored everything — DECISIONS D5) | **FIXED** 01d9862 (removed; git history keeps reference) |
| C-jsonl | S3 | tests/clinical_audit/reports/*.jsonl | 4.7 MB regenerable generator dumps tracked in git | **FIXED** 58417e7 (untracked + ignored; files remain on disk) |
| D3 | S3 | v1_therapist_session_views.py:367 | Feedback view unguarded `log_item_ids[idx]` — same-week republish can 500 it | **FIXED** 675d4dc (bounds-guard like siblings) |
| D4 | S3 | v1_prescription_engine.py:1589 | HSR phase-advance failure silently swallowed | **FIXED** 93e8fa0 (logged) |
| D5 | S3 | therapist_app/views.py:905 | Onboarding demographics mirror to PatientProfile failed silently → stale dosing inputs | **FIXED** in 231e79c (logged; rode the same-file D8 commit) |
| A3 | S4 | rate_limiter.py:25,41 | Non-atomic get-then-set (burst TOCTOU) | **ACCEPTED** c882e5d (SECURITY_AUDIT #21; close with A2 via shared cache) |
| A4 | S4 | seed_demo_patient.py:24 | Hardcoded 'demo1234' seed password | **DOCUMENTED** c882e5d (DEPLOY_CHECKLIST: never seed prod) |
| A-row7 | S4 | SECURITY_AUDIT.md #7 | Doc pointed at patient_register; enumeration copy + 3/600 limit now live at onboarding_identity | **FIXED** c882e5d (doc) |
| A-row9 | S4 | SECURITY_AUDIT.md #9 | pip-audit re-run: **No known vulnerabilities** in the 7 pinned packages (pip-audit --no-deps, 2026-07-04) | **RE-VERIFIED** |
| B-sync | — | CUE_TEXT ↔ coach_core.js ↔ RepCapture._cueIds | Forever-rule sync check: 0 drift; exercise_targets.json `--check` fresh; H2/H3/P3 suites pass | **VERIFIED CLEAN** |
| C2 | S4 | v1_exercise_execute.html:2663 | `VoiceCoach.cueAlignment` never called (its 3 praise lines stay as dormant clip-map entries) | **FIXED** 0ec9c4f |
| D6 | S4 | report_builder.py:599 | Narrative outcome dict hard subscript — future 4th outcome would kill that report | **FIXED** 675d4dc (.get fallback) |
| D7 | S4 | v1_gamification.py:198,204 | Two achievements permanently locked (TODO stubs) | **DEFERRED** — needs product decision + real unlock logic; only TODO rot in the codebase |
| (b) | S4 | exercise_system/core/voice_coach_v2.py:17 | pyttsx3 warning printed on every manage.py command | **FIXED** 3616f96 (logging.debug) |
| M1 | S4 | tests/test_deep_audit.py:743 | H2 harness writes the tracked H2_RESULTS.md on every run; byte-stable in the main env, but parallel/foreign-env runs can jitter tie order → occasional dirty tree | **NOTED** — harmless here; if it annoys, make the writer opt-in via env flag |

**Counts:** S1 0 · S2 4 (4 fixed) · S3 7 (6 fixed, 1 accepted) ·
S4 8 (5 fixed, 2 accepted/documented, 1 deferred) + 2 verified-clean rows.

## Mediapipe amendment — outcome (supersedes handoff expected-finding (a))

Sequence executed as amended: (1) guarded `pose_analyzer.py` imports;
(2) proof venv WITHOUT mediapipe built from requirements-minus-mediapipe.
**Step 2 FAILED as the amendment anticipated**: `export_exercise_targets
--check` crashes at the first exercise module — **256/264 exercise modules
`import cv2` at module top**, and `cv2`/`numpy` exist only as mediapipe's
transitive dependencies, so no pose_analyzer-only guard can help
(proof: `ModuleNotFoundError: No module named 'cv2'` at
`exercises/ab_wheel_rollout_v2.py:7`; registry imports every module).
Per the amendment's contingency: **requirements.txt untouched, guard
reverted** (no benefit; keeps the frozen desktop-CV layer pristine),
no requirements-desktop.txt split. Unblocking the split later means either
guarding cv2/numpy in all 264 modules (mechanical, large) or making the
registry import lazily — a deliberate future task, not a quick fix.
Side note: the DA-H3/H2 tests already SKIP cleanly without mediapipe.

## Repo hygiene executed (Agent C's plan)

- **Archived** (git mv → docs/archive/, history preserved): GROUP1–6_AUDIT,
  AUDIT_FIXES_CHANGELOG, DEEP_AUDIT_REPORT, SHIP_READY_REPORT,
  VYAYAM_DEEP_AUDIT_PROMPT, SECURITY_AUDIT_2026-06-23,
  VYAYAM_PITCH_POLISH_HANDOFF, VYAYAM_REPORT_COACHING_HANDOFF,
  DEPLOY_SECURITY_REVIEW, AGENT2_CITATION_AUDIT (15 files, 0032e6e).
- **Root live set:** README, SECURITY_AUDIT, DEPLOY_CHECKLIST, PITCH_SMOKE,
  MASTER_TEST_DAY, DECISIONS_NEEDED (pruned to open items, aa16799),
  VYAYAM_MASTER_HANDOFF, LICENSE, this file.
- **Corrections to the handoff's dead-code expectations** (Agent C, proof in
  findings): `cues:{}` strings are LIVE (cue-capture registry consumes
  them); `strength_app/backend/` is LIVE (legacy gate-test path via
  utils.py); tempo-voice remnants were already gone.
- .gitignore: + `.tmp_audit/`, `.r2_tmp/`, `*.log`, clinical-audit `*.jsonl`.
- Untracked waste deleted from disk: `.DS_Store`s, `.tmp_audit/`,
  `__pycache__` stragglers.

## Verified-clean highlights (full proofs in agent files)

- IDOR both directions on report views + R1 capture endpoints (state-bound
  session_log — no cross-write path); every state-writing POST either
  rate-limited or auth+CSRF-gated; admin exposes no secrets; headers/CSP
  posture unchanged; `check --deploy` under prod env = exactly one
  warning (W008 SSL redirect, env-gated by design).
- exercise_targets.json byte-fresh (`--check`); H2 ideal-trajectory,
  H3 registry-integrity, P3 content/equipment coverage all pass; CUE sync
  forever-rule holds with zero drift.
- report_builder edge inputs (junk tempo, empty sessions, zero durations,
  corrupt reps_json) verified non-raising; all requirements pinned `==`
  and pip-audit-clean.

## New deliverables this examination

`MASTER_TEST_DAY.md` (device walk, Parts A–F) ·
`docs/ADDING_AN_EXERCISE.md` (30-minute playbook) · this ledger.
